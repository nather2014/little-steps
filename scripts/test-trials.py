"""Local-only checks for authoritative time-trial scoring, rewards and persistence."""
import concurrent.futures,json,runpy,secrets,subprocess,time,urllib.request
helpers=runpy.run_path('scripts/test-api.py');Client,BASE=helpers['Client'],helpers['BASE']
assert BASE.startswith(('http://localhost:','http://127.0.0.1:'))
ids=[];test_exam=None
def sql(q):return subprocess.check_output(['docker','compose','exec','-T','db','psql','-U','little_steps','-d','little_steps','-At','-v','ON_ERROR_STOP=1','-c',q],text=True).strip()
def new(role='student',grade=2):
 c=Client();uid=c.request('/api/auth/guest',{})['user']['id'];ids.append(uid);c.rpc('setup_profile',{'p_name':'Time trial tester','p_role':role,'p_grade':grade if role=='student' else None});return c,uid
def answer(c,state,wrong=False,skip=False):
 qs=json.loads(sql("SELECT questions FROM exam_sessions WHERE id='"+state['session_id']+"'"));q=qs[state['index']%len(qs)];choice=q[2]
 if wrong:choice=(choice+1)%len(q[1])
 return c.rpc('answer_time_trial',{'p_session':state['session_id'],'p_index':state['index'],'p_answer':None if skip else choice})
def start(c,eid,seconds=60):return c.rpc('start_time_trial',{'p_exam':eid,'p_seconds':seconds})
def finish(c,s):return c.rpc('finish_time_trial',{'p_session':s['session_id']})['result']
try:
 child,uid=new();parent,pid=new('parent');other,oid=new(grade=3)
 exams=child.rpc('available_exams');eid=next(e['id'] for e in exams if e['subject']=='maths')
 # Isolate comparison cohorts from other local tests and saved browser guests.
 test_exam=int(sql("INSERT INTO exams(grade,subject,title,topic,week_start,questions) SELECT grade,'trial-test-"+secrets.token_hex(8)+"',title,topic,week_start,questions FROM exams WHERE id="+str(eid)+" RETURNING id").splitlines()[0]);eid=test_exam
 for seconds in [0,30,61,120,600]:child.rpc('start_time_trial',{'p_exam':eid,'p_seconds':seconds},400)
 other.rpc('start_time_trial',{'p_exam':eid,'p_seconds':60},403);parent.rpc('start_time_trial',{'p_exam':eid,'p_seconds':60},403)
 s=start(child,eid);assert s['index']==0 and s['duration_seconds']==60 and 'answer' not in s['question'] and 'explanation' not in s['question']
 other.rpc('resume_time_trial',{'p_session':s['session_id']},403)
 child.rpc('answer_time_trial',{'p_session':s['session_id'],'p_index':5,'p_answer':0},400)
 child.rpc('answer_time_trial',{'p_session':s['session_id'],'p_index':0,'p_answer':999},400)
 child.rpc('save_answers',{'p_session':s['session_id'],'p_answers':[0]},400)
 child.rpc('not_studied',{'p_session':s['session_id'],'p_index':0},400)
 child.rpc('submit_exam',{'p_session':s['session_id'],'p_answers':[0]},400)
 for points in [10,12,14,16,18,20,20]:s=answer(child,s);assert s['feedback']['points']==points and s['feedback']['correct']
 assert s['points']==110 and s['streak']==7
 retry=child.rpc('answer_time_trial',{'p_session':s['session_id'],'p_index':0,'p_answer':0});assert retry['points']==110 and retry['index']==7 and retry['feedback']['points']==10
 s=answer(child,s,wrong=True);assert s['points']==110 and s['streak']==0 and not s['feedback']['correct']
 s=answer(child,s,skip=True);assert s['index']==9 and s['feedback']['selected']=='Skipped' and s['best_streak']==7
 resumed=start(child,eid);assert resumed['session_id']==s['session_id'] and resumed['index']==9 and resumed['deadline_at']==s['deadline_at']
 with concurrent.futures.ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda _:finish(child,s),range(2)))
 for r in results:assert r['points']==110 and r['correct']==7 and r['answered']==9 and r['rr_delta']==0 and r['personal_best']==110
 assert len({r['attempt_id'] for r in results})==1 and results[0]['xp_earned']==results[1]['xp_earned']
 saved=child.request('/api/attempts');assert len(saved)==1 and saved[0]['mode']=='time_trial'
 rewards=child.request('/api/rewards');assert rewards['rank']['points']==50 and rewards['daily']==[] and rewards['weekly']==[]
 parent.request('/api/time_trials?student_id='+uid,status=403);other.request('/api/time_trials?student_id='+uid,status=403)
 parent.rpc('link_child',{'p_code':child.rpc('create_link_code')});assert parent.request('/api/time_trials?student_id='+uid)['bests'][0]['points']==110
 parent.rpc('resume_time_trial',{'p_session':s['session_id']},403)
 for seconds,n in [(60,2),(300,1),(180,1)]:
  s=start(child,eid,seconds)
  for _ in range(n):s=answer(child,s)
  r=finish(child,s)
 assert r['xp_earned']==0 # First three scoring rounds have already received XP.
 assert int(sql("SELECT count(*) FROM xp_events x JOIN attempts a ON a.id=x.attempt_id WHERE a.student_id='"+uid+"' AND a.mode='time_trial' AND x.kind='quiz'"))==3
 empty=start(child,eid,180);count=len(child.request('/api/attempts'));r=finish(child,empty);assert r['answered']==0 and r['attempt_id'] is None and r['xp_earned']==0 and len(child.request('/api/attempts'))==count
 # Average cohorts must match the round duration, exclude self and require 3 peers.
 for correct,total in [(0,1),(1,1),(1,2)]:
  peer,_=new();ps=start(peer,eid)
  for i in range(total):ps=answer(peer,ps,wrong=i>=correct)
  finish(peer,ps)
 for _ in range(3):
  peer,_=new();ps=answer(peer,start(peer,eid,180));finish(peer,ps)
 comp=next(c for c in child.request('/api/comparisons') if c['attempt_id']==saved[0]['id']);assert comp['duration_seconds']==60 and comp['peer_count']==3 and comp['average']==50
 english=next(e['id'] for e in exams if e['subject']=='english');s=start(child,english,300);pool=json.loads(sql("SELECT questions FROM exam_sessions WHERE id='"+s['session_id']+"'"));first=s['question']['prompt']
 for _ in range(len(pool)):s=answer(child,s)
 assert s['question']['prompt']==first and s['index']==len(pool);finish(child,s)
 late=start(child,eid);late=answer(child,late);sql("UPDATE exam_sessions SET deadline_at=now()-interval '1 second' WHERE id='"+late['session_id']+"'")
 expired=answer(child,late);assert expired['finished'] and expired['result']['answered']==1 and expired['result']['correct']==1
 # Persist a running round across a real app restart; this also checks schema reruns with time-trial rows.
 live=answer(child,start(child,eid,180));subprocess.run(['docker','compose','restart','app'],check=True,stdout=subprocess.DEVNULL)
 for _ in range(30):
  try:urllib.request.urlopen(BASE+'/api/health',timeout=1);break
  except OSError:time.sleep(.2)
 else:raise AssertionError('App did not recover after restart')
 restored=child.rpc('resume_time_trial',{'p_session':live['session_id']});assert restored['index']==1 and restored['points']==10 and restored['deadline_at']==live['deadline_at'];finish(child,restored)
 assert child.request('/api/rewards')['rank']['points']==50
 print('Time-trial checks passed: durations, private questions, combos, skips, retries/concurrency, resume, server deadline, XP cap, no RR, zero-answer rounds, duration-matched averages, pool cycling, parent access and restart persistence.')
finally:
 if ids:sql('DELETE FROM users WHERE is_guest=true AND id IN ('+','.join("'"+uid+"'" for uid in ids)+')')

 if test_exam:sql('DELETE FROM exams WHERE id='+str(test_exam))
