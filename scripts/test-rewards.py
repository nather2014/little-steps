"""Run only against a disposable local database."""
import concurrent.futures
import importlib.util
import json
import secrets
import subprocess
from pathlib import Path
spec=importlib.util.spec_from_file_location('test_api',Path(__file__).with_name('test-api.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
Client=module.Client
assert module.BASE in ('http://localhost:8090','http://127.0.0.1:8090')
users=[];exam_ids=[]
def sql(query):
    return subprocess.check_output(['docker','compose','exec','-T','db','psql','-U','little_steps','-d','little_steps','-tA','-v','ON_ERROR_STOP=1'],input=query.encode()).decode().strip()
def quote(s):return "'"+str(s).replace("'","''")+"'"
def new(role='student',grade=2):
    c=Client();uid=c.request('/api/auth/guest',{})['user']['id'];users.append(uid)
    c.rpc('setup_profile',{'p_name':'Rewards check','p_role':role,'p_grade':grade if role=='student' else None})
    return c,uid
def exam(week,n):
    questions=[[f'Reward check {n}-{i}', ['Correct','Try again'],0,f'Topic {i}'] for i in range(5)]
    sid='reward-test-'+secrets.token_hex(8)
    eid=int(sql("INSERT INTO exams(grade,subject,title,topic,week_start,questions) VALUES(2,"+quote(sid)+",'Rewards API check','Test topics',"+quote(week)+","+quote(json.dumps(questions))+") RETURNING id;").splitlines()[0])
    exam_ids.append(eid);return eid
def take(c,eid,correct,mode='weekly'):
    s=c.rpc('start_exam',{'p_exam':eid,'p_mode':mode})
    answers=[0]*correct+[1]*(5-correct)
    return c.rpc('submit_exam',{'p_session':s['session_id'],'p_answers':answers})
try:
    learner,uid=new();parent,pid=new('parent');peers=[new()[0] for _ in range(3)];stranger,_=new()
    week=learner.rpc('available_exams')[0]['week_start']
    eid=exam(week,1)
    initial=learner.request('/api/rewards')
    assert initial['xp']==0 and initial['rank']['name']=='Iron 1' and initial['rank']['rr']==50
    mine=take(learner,eid,4)
    assert mine['xp_earned']==140 and mine['rr_delta']==20
    for c,n in zip(peers[:2],[1,3]):take(c,eid,n)
    comp=next(r for r in learner.request('/api/comparisons') if r['attempt_id']==mine['id'])
    assert comp['peer_count']==2 and comp['average'] is None
    take(peers[2],eid,5)
    comp=next(r for r in learner.request('/api/comparisons') if r['attempt_id']==mine['id'])
    assert comp['peer_count']==3 and comp['average']==60 and comp['score']==80
    for n,c in enumerate(peers):take(c,eid,[0,1,5][n],'practice')
    take(peers[0],eid,5,'practice')
    practice=[]
    for i in range(4):practice.append(take(learner,eid,5,'practice'))
    assert [a['xp_earned'] for a in practice]==[90,90,90,0]
    assert all(a['rr_delta']==0 for a in practice)
    comp=next(r for r in learner.request('/api/comparisons') if r['attempt_id']==practice[-1]['id'])
    assert comp['average']==40 and comp['peer_count']==3,'Repeated practice biased peer average'
    rewards=learner.request('/api/rewards')
    assert rewards['xp']==410 and rewards['level']==1 and rewards['rank']['points']==70
    assert rewards['practice_rewards_left']==0 and rewards['daily']==[] and rewards['weekly']==[]
    second=take(learner,exam(week,2),5)
    assert second['rr_delta']==30 and learner.request('/api/rewards')['rank']['name']=='Iron 2'
    third=take(learner,exam(week,3),0)
    assert third['rr_delta']==-20 and third['xp_earned']==100
    rewards=learner.request('/api/rewards')
    assert rewards['xp']==660 and rewards['rank']['name']=='Iron 1' and rewards['rank']['rr']==80
    def retry():
        return learner.rpc('submit_exam',{'p_session':third['session_id'],'p_answers':[0]*5})
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda _:retry(),range(2)))
    assert all(r['rr_delta']==-20 and r['xp_earned']==100 for r in results)
    assert learner.request('/api/rewards')['xp']==660
    assert int(sql("SELECT count(*) FROM rank_events WHERE student_id="+quote(uid)))==3
    for path in ['/api/rewards','/api/comparisons']:
        stranger.request(path+'?student_id='+uid,status=403)
        parent.request(path+'?student_id='+uid,status=403)
    code=learner.rpc('create_link_code');parent.rpc('link_child',{'p_code':code})
    assert parent.request('/api/rewards?student_id='+uid)['xp']==660
    assert len(parent.request('/api/comparisons?student_id='+uid))==7
    learner.rpc('unlink_parent',{'p_parent':pid})
    parent.request('/api/rewards?student_id='+uid,status=403)
    parent.request('/api/comparisons?student_id='+uid,status=403)
    # Move the learner's daily activity into yesterday: the next quiz must regain daily eligibility.
    today=rewards['daily_date']
    yesterday=sql("SELECT ("+quote(today)+"::date-1)::text")
    sql("UPDATE xp_events SET earned_at=earned_at-interval '1 day', event_key=CASE WHEN kind='daily' THEN replace(event_key,"+quote('daily:'+today+':')+","+quote('daily:'+yesterday+':')+") ELSE event_key END WHERE student_id="+quote(uid))
    reset=learner.request('/api/rewards')
    assert reset['practice_rewards_left']==3 and reset['daily']==[] and reset['weekly']==[]
    fresh=take(learner,eid,5,'practice')
    assert fresh['xp_earned']==90,'Practice reward allowance did not reset'
    assert learner.request('/api/rewards')['rank']['points']==80
    # Seed rating boundaries in the disposable test database.
    sql("UPDATE rank_events SET before_points=30,after_points=10 WHERE id=(SELECT max(id) FROM rank_events WHERE student_id="+quote(uid)+")")
    floor=take(learner,exam(week,4),0)
    assert floor['rr_delta']==-10 and learner.request('/api/rewards')['rank']['points']==0
    sql("UPDATE rank_events SET before_points=2400,after_points=2390 WHERE id=(SELECT max(id) FROM rank_events WHERE student_id="+quote(uid)+")")
    radiant=take(learner,exam(week,5),5)
    assert radiant['rr_delta']==30 and learner.request('/api/rewards')['rank']['name']=='Radiant'
    print('Rewards checks passed: private unbiased exam averages, XP, caps, retired missions, practice allowance reset, positive/negative RR, promotion/demotion, concurrent retries and parent permissions.')
finally:
    if users:sql("DELETE FROM users WHERE id IN ("+','.join(map(quote,users))+")")
    if exam_ids:sql("DELETE FROM exams WHERE id IN ("+','.join(map(str,exam_ids))+")")
