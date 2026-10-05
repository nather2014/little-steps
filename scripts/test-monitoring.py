"""Local-only monitoring authorization, activity, timings and timer checks."""
import json,runpy,subprocess
helpers=runpy.run_path('scripts/test-api.py');Client,BASE=helpers['Client'],helpers['BASE'];assert BASE.startswith(('http://localhost:','http://127.0.0.1:'))
ids=[]
def sql(q):return subprocess.check_output(['docker','compose','exec','-T','db','psql','-U','little_steps','-d','little_steps','-At','-v','ON_ERROR_STOP=1','-c',q],text=True).strip()
def new(role):
 c=Client();uid=c.request('/api/auth/guest',{})['user']['id'];ids.append(uid);c.rpc('setup_profile',{'p_name':'Monitor tester','p_role':role,'p_grade':2 if role=='student' else None});return c,uid
try:
 Client().request('/api/admin/metrics',status=401)
 child,uid=new('student');admin,aid=new('parent')
 child.request('/api/admin/metrics',status=403);admin.request('/api/admin/metrics',status=403)
 subprocess.run(['docker','compose','exec','-T','app','./little-steps','grant-admin',aid],check=True)
 assert admin.request('/api/auth/me')['user']['is_admin'] is True
 m=admin.request('/api/admin/metrics');assert m['database']['size_bytes']>0 and m['database_queries']['count']>0 and m['usage']['online_users']>=2
 assert uid not in json.dumps(m) and aid not in json.dumps(m)
 eid=next(e['id'] for e in child.rpc('available_exams') if e['subject']=='maths');before=m['usage']['active_matches'];s=child.rpc('start_time_trial',{'p_exam':eid,'p_seconds':60});assert admin.request('/api/admin/metrics')['usage']['active_matches']==before+1
 sql("UPDATE exam_sessions SET deadline_at=now()-interval '1 second' WHERE id='"+s['session_id']+"'");assert admin.request('/api/admin/metrics')['usage']['active_matches']==before
 before=admin.request('/api/admin/metrics')['page_load']['count'];child.request('/api/telemetry',{'load_ms':123});assert admin.request('/api/admin/metrics')['page_load']['count']==before+1
 for payload in [{'load_ms':-1},{'load_ms':120001},{'load_ms':100,'extra':True}]:child.request('/api/telemetry',payload,status=400)
 child.request('/api/activity');assert sql("SELECT last_active_at IS NOT NULL FROM users WHERE id='"+uid+"'")=='t'
 subprocess.run(['docker','compose','exec','-T','app','./little-steps','revoke-admin',aid],check=True);admin.request('/api/admin/metrics',status=403)
 print('Monitoring checks passed: anonymous/student/parent denied, server-only grant/revoke, aggregate privacy, online activity, expired-match exclusion, real DB timing and browser timing validation.')
finally:
 if ids:sql('DELETE FROM users WHERE is_guest=true AND id IN ('+','.join("'"+x+"'" for x in ids)+')')
