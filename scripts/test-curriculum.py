"""Integration checks against a disposable local database."""
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('test_api',Path(__file__).with_name('test-api.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
Client=module.Client
student_ids=[]
for grade in range(-1,11):
    client=Client()
    uid=client.request('/api/auth/guest',{})['user']['id']
    student_ids.append(uid)
    client.rpc('setup_profile',{'p_name':'Curriculum check','p_role':'student','p_grade':grade})
    coverage=[s for s in client.rpc('curriculum',{'p_grade':grade}) if not s['subject'].startswith('olympiad_')]
    assert len(coverage)==(3 if grade<6 else 4)
    assert all(s['questions']>=10 and s['sources'] and len(s['topics'])>=6 for s in coverage)
    client.rpc('curriculum',{'p_grade':11},403)
    exams=client.rpc('available_exams')
    assert len({e['subject'] for e in exams if e['category']=='regular'})==len(coverage)
    session=client.rpc('start_exam',{'p_exam':exams[0]['id'],'p_mode':'practice'})
    assert len(session['questions'])==10
    assert len({q['topic'] for q in session['questions']})>=6
    assert all('answer' not in q for q in session['questions'])
    old=session['questions'][0]
    client.rpc('not_studied',{'p_session':session['session_id'],'p_index':-1},400)
    replaced=client.rpc('not_studied',{'p_session':session['session_id'],'p_index':0})
    assert replaced['questions'][0]['prompt']!=old['prompt']
    assert replaced['questions'][0]['topic']!=old['topic']
    assert replaced['questions'][1:]==session['questions'][1:]
    assert replaced['not_studied']==[{'prompt':old['prompt'],'topic':old['topic']}]
    result=client.rpc('submit_exam',{'p_session':session['session_id'],'p_answers':[0]*10})
    assert result['total']==10 and result['not_studied']==replaced['not_studied']
    assert result['review'][0]['prompt']==replaced['questions'][0]['prompt']
    client.rpc('not_studied',{'p_session':session['session_id'],'p_index':0},400)
    assert client.request('/api/attempts')[0]['not_studied']==result['not_studied']
    if grade==-1:
        child=client
        first_session=session['session_id']
    if grade==0:
        client.rpc('not_studied',{'p_session':first_session,'p_index':0},403)
parent=Client()
parent.request('/api/auth/guest',{})
parent.rpc('setup_profile',{'p_name':'Parent check','p_role':'parent','p_grade':None})
code=child.rpc('create_link_code')
parent.rpc('link_child',{'p_code':code})
assert parent.request('/api/children')[0]['grade']==-1
assert parent.request('/api/attempts?student_id='+student_ids[0])[0]['not_studied']
assert len(parent.rpc('curriculum',{'p_grade':-1}))==5
parent.rpc('curriculum',{'p_grade':0},403)
print('Curriculum checks passed: all 12 levels, subject coverage, private answers, replacement, grading, topic records, permissions and parent access.')
