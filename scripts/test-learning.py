"""Local only: personalized skills, spaced reviews, privacy, unlimited ranked tests."""
import json,runpy,subprocess
from datetime import datetime,timedelta,timezone
helpers=runpy.run_path('scripts/test-api.py');Client,BASE=helpers['Client'],helpers['BASE']
assert BASE.startswith(('http://localhost:','http://127.0.0.1:'))
ids=[]
def sql(q):return subprocess.check_output(['docker','compose','exec','-T','db','psql','-U','little_steps','-d','little_steps','-At','-v','ON_ERROR_STOP=1','-c',q],text=True).strip()
def new(role='student'):
 c=Client();uid=c.request('/api/auth/guest',{})['user']['id'];ids.append(uid);c.rpc('setup_profile',{'p_name':'Cycle tester','p_role':role,'p_grade':2 if role=='student' else None});return c,uid
def answers(session):return [q[2] for q in json.loads(sql("SELECT questions FROM exam_sessions WHERE id='"+session['session_id']+"'"))]
def take(c,session,wrong=False):
 a=answers(session)
 if wrong:a=[(v+1)%len(q['options']) for v,q in zip(a,session['questions'])]
 return c.rpc('submit_exam',{'p_session':session['session_id'],'p_answers':a})
try:
 child,uid=new();parent,pid=new('parent');other,oid=new()
 data=child.request('/api/learning');assert data['skills']==[] and data['review_intervals']==[1,3,7,14,30]
 topic='Subtraction with borrowing';lesson=child.request('/api/lesson?subject=maths&topic=Subtraction%20with%20borrowing');assert len(lesson['steps'])==3 and all(q['explanation'] for q in lesson['examples'])
 session=child.rpc('targeted_practice',{'p_subject':'maths','p_topic':topic});assert session['focus_count']==10 and session['mixed_count']==0
 assert [q['difficulty'] for q in session['questions']]==['easier']*5+['normal']*5
 assert all('answer' not in q and 'explanation' not in q for q in session['questions'])
 result=take(child,session,True);assert result['rr_delta']==0 and all(q['explanation'] for q in result['review'])
 skill=next(s for s in child.request('/api/learning')['skills'] if s['topic']==topic);assert skill['weak'] and skill['stage']==0
 firstdue=skill['due_at']
 for stage,days in enumerate([3,7,14,30],1):
  sql("UPDATE learning_skills SET due_at=now()-interval '1 second' WHERE student_id='"+uid+"' AND topic='"+topic+"'")
  perfect=take(child,child.rpc('targeted_practice',{'p_subject':'maths','p_topic':topic}))
  skill=next(s for s in child.request('/api/learning')['skills'] if s['topic']==topic)
  assert not skill['weak'] and skill['stage']==stage and skill['review_days']==days
  due=datetime.fromisoformat(skill['due_at']);assert abs((due-datetime.now(timezone.utc)).total_seconds()-days*86400)<10
 # Early successful practice must not advance the review stage or move the date.
 before=skill['due_at'];early=take(child,child.rpc('targeted_practice',{'p_subject':'maths','p_topic':topic}));skill=next(s for s in child.request('/api/learning')['skills'] if s['topic']==topic);assert skill['stage']==4 and skill['due_at']==before
 child.rpc('mistake_note',{'p_attempt':early['id'],'p_index':0,'p_reason':'unsure','p_note':'<Think carefully>'})
 skill=next(s for s in child.request('/api/learning')['skills'] if s['topic']==topic);assert skill['weak'] and skill['last_accuracy']==100 and skill['stage']==0
 other.request('/api/learning?student_id='+uid,status=403);parent.request('/api/learning?student_id='+uid,status=403)
 other.rpc('mistake_note',{'p_attempt':early['id'],'p_index':0,'p_reason':'other','p_note':''},403)
 parent.rpc('link_child',{'p_code':child.rpc('create_link_code')});assert parent.request('/api/learning?student_id='+uid)['notes'][0]['note']=='<Think carefully>'
 parent.request('/api/lesson?student_id='+uid+'&subject=maths&topic=Subtraction%20with%20borrowing')
 parent.rpc('targeted_practice',{'p_subject':'maths','p_topic':topic},403)
 exams=child.rpc('available_exams');exam=next(e for e in exams if e['subject']=='maths');sessions=set()
 for n in range(12):
  s=child.rpc('start_exam',{'p_exam':exam['id'],'p_mode':'ranked'});assert s['session_id'] not in sessions;sessions.add(s['session_id']);assert len(s['questions'])==10
  if n==0:assert any(q['topic']==topic for q in s['questions'])
  result=take(child,s);assert result['rr_delta']==30
  assert child.rpc('submit_exam',{'p_session':s['session_id'],'p_answers':[0]*10})['id']==result['id']
 rewards=child.request('/api/rewards');assert rewards['rank']['points']==410 and rewards['rank']['name']=='Bronze 2'
 assert rewards['daily']==[] and rewards['weekly']==[]
 board=child.rpc('leaderboard',{'p_grade':2,'p_week':exam['week_start']});own=next(r for r in board if r['is_you']);assert own['completed']==1 and 0<=own['score']<=100
 bad=take(child,child.rpc('start_exam',{'p_exam':exam['id'],'p_mode':'ranked'}),True);assert bad['rr_delta']==-20 and child.request('/api/rewards')['rank']['points']==390
 print('Learning checks passed: 5 easier + 5 normal questions, worked steps, 1/3/7/14/30 day scheduling, uncertainty, parent permissions, mixed weak-skill tests, twelve ranked retakes, RR promotions/losses, idempotence and bounded leaderboard.')
finally:
 if ids:sql('DELETE FROM users WHERE is_guest=true AND id IN ('+','.join("'"+uid+"'" for uid in ids)+')')
