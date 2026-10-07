import json
import urllib.request
import urllib.error

API = 'http://127.0.0.1:5000/api'

def post_json(url, data, token=None):
    data_b = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=data_b, headers={'Content-Type':'application/json'})
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req) as res:
            print('STATUS', res.status)
            print(res.read().decode())
    except urllib.error.HTTPError as e:
        print('HTTP', e.code)
        print(e.read().decode())

# 1) Login as seeded student to get token
login_payload = {'email': 'student@college.edu', 'password': 'Student@12345', 'role': 'student'}
req = urllib.request.Request(API + '/auth/login', data=json.dumps(login_payload).encode('utf-8'), headers={'Content-Type':'application/json'})
try:
    with urllib.request.urlopen(req) as res:
        body = res.read().decode()
        print('Login response:', body)
        token = json.loads(body).get('accessToken')
        if not token:
            print('No token in login response.')
        else:
            # 2) Submit a complaint
            complaint = {
                'title': 'Test submission from script',
                'description': 'This is a test complaint submitted by automated script.',
                'block': 'Block A',
                'floor': '1',
                'roomNo': '101',
                'category': 'Plumbing',
                'priority': 'Medium'
            }
            post_json(API + '/complaints', complaint, token)
except urllib.error.HTTPError as e:
    print('Login HTTP', e.code)
    print(e.read().decode())
except Exception as ex:
    print('Error', ex)
