"""Run against a disposable local database: python3 scripts/test-api.py."""
import concurrent.futures
import http.cookiejar
import json
import os
import secrets
import urllib.error
import urllib.request

BASE = os.environ.get('TEST_BASE_URL', 'http://localhost:8090')


class Client:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.http = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, path, body=None, status=200):
        headers = {'Origin': BASE, 'X-Little-Steps': '1', 'Content-Type': 'application/json'}
        request = urllib.request.Request(BASE + path, headers=headers,
            data=None if body is None else json.dumps(body).encode())
        try:
            response = self.http.open(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        data = json.load(response)
        assert response.status == status, (path, response.status, data)
        return data

    def rpc(self, name, body=None, status=200):
        return self.request('/api/rpc/' + name, body or {}, status)

    def register(self, role, grade=None):
        email = secrets.token_hex(8) + '@test.example'
        self.request('/api/auth/register', {'email': email, 'password': 'Test-password-123!'})
        user = self.request('/api/auth/me')['user']
        self.rpc('setup_profile', {'p_name': '<Tester>', 'p_role': role, 'p_grade': grade})
        return user['id'], email


def main():
    guest, other_guest = Client(), Client()
    created = guest.request('/api/auth/guest', {})
    assert created['user']['is_guest'] is True
    guest_id = created['user']['id']
    assert guest.request('/api/auth/me')['user']['id'] == guest_id
    cookie = next(iter(guest.jar))
    import time
    assert cookie.expires > time.time() + 29 * 86400
    guest.rpc('setup_profile', {'p_name': 'Guest learner', 'p_role': 'student', 'p_grade': 2})
    guest_exams = guest.rpc('available_exams')
    guest_exam = guest.rpc('start_exam', {'p_exam': guest_exams[0]['id'], 'p_mode': 'practice'})
    guest.rpc('submit_exam', {'p_session': guest_exam['session_id'], 'p_answers': [0]*10})
    assert len(guest.request('/api/attempts?student_id=' + guest_id)) == 1
    second = other_guest.request('/api/auth/guest', {})
    assert second['user']['id'] != guest_id
    other_guest.request('/api/attempts?student_id=' + guest_id, status=403)
    guest.request('/api/auth/logout', {})
    guest.request('/api/auth/me', status=401)
    student, parent, stranger = Client(), Client(), Client()
    student_id, student_email = student.register('student', 2)
    parent.register('parent')
    stranger.register('student', 2)
    exams = student.rpc('available_exams')
    assert len(exams) == 5
    exam_id = exams[0]['id']
    session = student.rpc('start_exam', {'p_exam': exam_id, 'p_mode': 'weekly'})
    assert len(session['questions']) == 10
    assert all('answer' not in q for q in session['questions'])
    stranger.rpc('submit_exam', {'p_session': session['session_id'], 'p_answers': [0]*10}, 403)
    student.rpc('submit_exam', {'p_session': session['session_id'], 'p_answers': [None]*9}, 400)
    student.rpc('submit_exam', {'p_session': session['session_id'], 'p_answers': [0]*10, 'score': 100}, 400)
    result = student.rpc('submit_exam', {'p_session': session['session_id'], 'p_answers': [0]*10})
    assert len(result['review']) == 10
    answers = [q['options'].index(r['answer']) for q, r in zip(session['questions'], result['review'])]
    assert result['correct'] == sum(answer == 0 for answer in answers)
    retry = student.rpc('submit_exam', {'p_session': session['session_id'], 'p_answers': [1]*10})
    assert retry['id'] == result['id']
    student.rpc('start_exam', {'p_exam': exam_id, 'p_mode': 'weekly'}, 400)
    practice = student.rpc('start_exam', {'p_exam': exam_id, 'p_mode': 'practice'})
    practice_result = student.rpc('submit_exam', {'p_session': practice['session_id'], 'p_answers': [0]*10})
    assert practice_result['total'] == 10
    student.rpc('setup_profile', {'p_name': 'Other', 'p_role': 'parent', 'p_grade': None}, 409)
    parent.request('/api/attempts?student_id=' + student_id, status=403)
    stranger.request('/api/attempts?student_id=' + student_id, status=403)
    code = student.rpc('create_link_code')
    parent.rpc('link_child', {'p_code': code})
    parent.rpc('link_child', {'p_code': code}, 400)
    assert parent.request('/api/children')[0]['id'] == student_id
    assert len(parent.request('/api/attempts?student_id=' + student_id)) == 2
    board = parent.rpc('leaderboard', {'p_grade': 2, 'p_week': exams[0]['week_start']})
    own = next(row for row in board if row['is_you'])
    assert own['completed'] == 1
    assert abs(own['score'] - round(result['correct']/result['total']/own['exam_count']*100, 1)) < .01
    parent.rpc('leaderboard', {'p_grade': 3, 'p_week': exams[0]['week_start']}, 403)
    # Two tabs cannot submit two weekly results for the same subject.
    s1 = student.rpc('start_exam', {'p_exam': exams[1]['id'], 'p_mode': 'weekly'})
    s2 = student.rpc('start_exam', {'p_exam': exams[1]['id'], 'p_mode': 'weekly'})
    def submit(s):
        try:
            student.rpc('submit_exam', {'p_session': s['session_id'], 'p_answers': [0]*10})
            return True
        except AssertionError as e:
            assert e.args[0][1] == 400, e
            return False
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        assert s1["session_id"] == s2["session_id"]
        assert sum(pool.map(submit, [s1, s2])) == 2
    parent_id = parent.request('/api/auth/me')['user']['id']
    student.rpc('unlink_parent', {'p_parent': parent_id})
    parent.request('/api/attempts?student_id=' + student_id, status=403)
    assert parent.request('/api/children') == []
    request = urllib.request.Request(BASE + '/api/auth/logout', data=b'{}', headers={
        'Origin': 'https://attacker.example', 'Content-Type': 'application/json', 'X-Little-Steps': '1'})
    try:
        student.http.open(request)
        raise AssertionError('Cross-origin write accepted')
    except urllib.error.HTTPError as e:
        assert e.code == 403
    student.request('/api/auth/logout', {})
    student.request('/api/auth/me', status=401)
    student.request('/api/auth/login', {'email': student_email, 'password': 'wrong-password'}, 401)
    student.request('/api/auth/login', {'email': student_email, 'password': 'Test-password-123!'})
    assert len(student.request('/api/attempts')) == 3
    print('API flows passed: accounts, permissions, grading, retries, concurrent weekly submissions, practice, linking, analytics, ranking, logout, and login.')


if __name__ == '__main__':
    main()
