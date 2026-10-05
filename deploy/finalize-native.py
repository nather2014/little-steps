import json
import pathlib
import re
import secrets
import subprocess
import urllib.request

def sql(query, database='postgres'):
 return subprocess.run(['runuser','-u','postgres','--','psql','-d',database,'-v','ON_ERROR_STOP=1','-At'],input=query,text=True,capture_output=True,check=True).stdout.strip()

p=pathlib.Path('/etc/little-steps.env')
if sql('SHOW server_encoding;', 'little_steps')!='UTF8':
 if sql('SELECT count(*) FROM users;', 'little_steps')!='0':
  raise SystemExit('Existing accounts found; migrate data before changing database encoding.')
 if not sql("SELECT 1 FROM pg_database WHERE datname='little_steps_utf8';"):
  sql("CREATE DATABASE little_steps_utf8 OWNER little_steps TEMPLATE template0 ENCODING 'UTF8';")
 p.write_text(p.read_text().replace('/little_steps?', '/little_steps_utf8?'))
 p.chmod(0o600)
 backup=pathlib.Path('/usr/local/sbin/little-steps-backup')
 backup.write_text(backup.read_text().replace('-d little_steps ', '-d little_steps_utf8 '))
 subprocess.run(['systemctl','restart','little-steps'],check=True)
subprocess.run(['systemctl','enable','--now','cron'],check=True)

import time
for _ in range(20):
 try:
  health=json.load(urllib.request.urlopen('http://127.0.0.1:8090/api/health',timeout=2))
  assert health['status']=='ok'
  break
 except Exception:
  time.sleep(.5)
else: raise SystemExit('API did not become healthy')

import http.cookiejar
jar=http.cookiejar.CookieJar()
http=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
def request(path,body=None):
 headers={'Host':'51.77.117.66','Origin':'http://51.77.117.66','Content-Type':'application/json','X-Little-Steps':'1'}
 return json.load(http.open(urllib.request.Request('http://127.0.0.1'+path,headers=headers,data=None if body is None else json.dumps(body).encode()),timeout=10))
assert request('/api/health')['status']=='ok'
page=http.open(urllib.request.Request('http://127.0.0.1/',headers={'Host':'51.77.117.66'})).read().decode()
assert 'api.js' in page and 'portal.js' in page
request('/api/auth/register',{'email':secrets.token_hex(8)+'@deployment-test.invalid','password':secrets.token_hex(16)})
id=request('/api/auth/me')['user']['id']
assert re.fullmatch('[a-f0-9]{32}',id)
try:
 request('/api/rpc/setup_profile',{'p_name':'Élodie 🌱','p_role':'student','p_grade':2})
 assert request('/api/profile')['display_name']=='Élodie 🌱'
 exams=request('/api/rpc/available_exams',{})
 assert len(exams)==3
 session=request('/api/rpc/start_exam',{'p_exam':exams[0]['id'],'p_mode':'weekly'})
 assert len(session['questions'])==5
 assert all('answer' not in q for q in session['questions'])
 result=request('/api/rpc/submit_exam',{'p_session':session['session_id'],'p_answers':[0]*5})
 assert len(result['review'])==5
 assert len(request('/api/attempts'))==1
 print('Native deployment checks passed: proxy, health, signup, UTF-8 names, exams, grading, and saved history.')
finally:
 db='little_steps_utf8' if '/little_steps_utf8?' in p.read_text() else 'little_steps'
 sql("BEGIN; DELETE FROM attempts WHERE student_id='"+id+"'; DELETE FROM exam_sessions WHERE student_id='"+id+"'; DELETE FROM users WHERE id='"+id+"'; COMMIT;",db)
subprocess.run(['/usr/local/sbin/little-steps-backup'],check=True)
