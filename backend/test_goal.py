import urllib.request, json
data = json.dumps({'user_id': 'test_user_123', 'goal': 'Master in AI in Germany'}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:8000/goal-analysis/', data=data, headers={'Content-Type': 'application/json'})
try:
    res = urllib.request.urlopen(req)
    print(res.read().decode())
except Exception as e:
    print(f'ERROR: {e}')
