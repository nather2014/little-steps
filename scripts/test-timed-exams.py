"""Local integration: lengths, challenges, saved answers and authoritative deadlines."""
import json,secrets,subprocess
from datetime import datetime
import runpy
helpers=runpy.run_path('scripts/test-api.py')
Client,BASE=helpers['Client'],helpers['BASE']
assert BASE.startswith(('http://localhost:','http://127.0.0.1:'))
def sql(query):
 return subprocess.check_output(['docker','compose','exec','-T','db','psql','-U','little_steps','-d','little_steps','-At','-c',query],text=True).strip()
ids=[]
try:
 for grade in [-1,0,*range(1,11)]:
  client=Client();uid=client.request('/api/auth/guest',{})['user']['id'];ids.append(uid)
  client.rpc('setup_profile',{'p_name':'Timer tester','p_role':'student','p_grade':grade})
  exams=client.rpc('available_exams');challenges=[e for e in exams if e['category']=='olympiad']
  assert len(challenges)==2
  for category in ['regular','olympiad']:
   ex=next(e for e in exams if e['category']==category)
   session=client.rpc('start_exam',{'p_exam':ex['id'],'p_mode':'weekly'})
   assert len(session['questions'])==10 and len(session['answers'])==10
   duration=(datetime.fromisoformat(session['deadline_at'])-datetime.fromisoformat(session['server_now'])).total_seconds()
   assert abs(duration-(900 if category=='regular' else 1200))<2
   answers=[0,1]+[None]*8
   client.rpc('save_answers',{'p_session':session['session_id'],'p_answers':answers})
   resumed=client.rpc('start_exam',{'p_exam':ex['id'],'p_mode':'weekly'})
   assert resumed['session_id']==session['session_id'] and abs((datetime.fromisoformat(resumed['deadline_at'])-datetime.fromisoformat(session['deadline_at'])).total_seconds())<0.001 and resumed['answers']==answers
   if grade==2 and category=='regular':
    stranger=Client();sid=stranger.request('/api/auth/guest',{})['user']['id'];ids.append(sid)
    stranger.rpc('setup_profile',{'p_name':'Other timer tester','p_role':'student','p_grade':grade})
    stranger.rpc('save_answers',{'p_session':session['session_id'],'p_answers':answers},403)
   sql("UPDATE exam_sessions SET deadline_at=now()-interval '1 second' WHERE id='"+session['session_id']+"'")
   client.rpc('save_answers',{'p_session':session['session_id'],'p_answers':[0]*10},400)
   client.rpc('not_studied',{'p_session':session['session_id'],'p_index':0},400)
   result=client.rpc('submit_exam',{'p_session':session['session_id'],'p_answers':[0]*10})
   assert result['total']==10 and all(r['selected']=='Not answered' for r in result['review'][2:])
   assert result['correct']<=2
   assert client.rpc('submit_exam',{'p_session':session['session_id'],'p_answers':[1]*10})['id']==result['id']
 print('Timed exams passed for all 12 levels: 10 questions, both challenge sets, durations, resume, saved answers, privacy, expired answer/replacement rejection and timeout grading.')
finally:
 if ids:sql('DELETE FROM users WHERE is_guest=true AND id IN ('+','.join("'"+x+"'" for x in ids)+')')
