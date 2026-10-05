"""Validate expanded Class 2 content and its local API grading."""
import json,re,runpy,subprocess
from pathlib import Path
banks=[json.loads(Path('backend/data/'+f+'.json').read_text()) for f in ['curriculum','olympiad']]
new=0
for bank in banks:
 for subject in bank['2']:
  prompts=set()
  for q in subject['questions']:
   assert q[0] not in prompts;prompts.add(q[0]);assert len(q[1])==len(set(q[1])) and 0<=q[2]<len(q[1])
   if len(q)==5 and q[4].get('generator')=='class2-expansion-v1':
    new+=1;assert len(q[1])==4 and q[4]['explanation'] and q[4]['difficulty'] in ['easier','normal','challenging']
    if m:=re.fullmatch(r'Add (\d+) and (\d+)\.',q[0]):assert int(q[1][q[2]])==sum(map(int,m.groups()))
    if m:=re.fullmatch(r'Subtract (\d+) from (\d+)\.',q[0]):assert int(q[1][q[2]])==int(m[2])-int(m[1])
    if m:=re.fullmatch(r'Fill the box: □ \+ 7 = (\d+)\.',q[0]):assert int(q[1][q[2]])==int(m[1])-7
assert new==802
helpers=runpy.run_path('scripts/test-api.py');Client,BASE=helpers['Client'],helpers['BASE'];assert BASE.startswith(('http://localhost:','http://127.0.0.1:'))
ids=[]
def sql(q):return subprocess.check_output(['docker','compose','exec','-T','db','psql','-U','little_steps','-d','little_steps','-At','-c',q],text=True).strip()
try:
 c=Client();uid=c.request('/api/auth/guest',{})['user']['id'];ids.append(uid);c.rpc('setup_profile',{'p_name':'Class 2 bank check','p_role':'student','p_grade':2})
 coverage=c.rpc('curriculum',{'p_grade':2});counts={s['subject']:s['questions'] for s in coverage};assert counts=={'maths':314,'english':248,'evs':90,'olympiad_maths':164,'olympiad_reasoning':123},counts
 exams=c.rpc('available_exams')
 for e in exams:
  s=c.rpc('start_exam',{'p_exam':e['id'],'p_mode':'ranked'});assert len(s['questions'])==10 and len({q['prompt'] for q in s['questions']})==10
  assert all('answer' not in q and 'explanation' not in q for q in s['questions'])
  questions=json.loads(sql("SELECT questions FROM exam_sessions WHERE id='"+s['session_id']+"'"));r=c.rpc('submit_exam',{'p_session':s['session_id'],'p_answers':[q[2] for q in questions]});assert r['correct']==r['total']==10 and r['rr_delta']==30
  assert any(q.get('explanation') for q in r['review'])
 s=c.rpc('targeted_practice',{'p_subject':'english','p_topic':'Articles'});assert s['focus_count']==10 and s['mixed_count']==0
 print('Class 2 checks passed: 802 original additions, 939 runtime entries, unique prompts/options, arithmetic answers, five ranked subjects, private answers, authored feedback and full focused article sets.')
finally:
 if ids:sql('DELETE FROM users WHERE is_guest=true AND id IN ('+','.join("'"+x+"'" for x in ids)+')')
