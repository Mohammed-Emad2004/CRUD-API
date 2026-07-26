import json
import urllib.request

base = 'http://127.0.0.1:8000'
req = urllib.request.Request(
    base + '/tasks/4',
    data=json.dumps({'title': 'Buy milk', 'done': True}).encode(),
    headers={'Content-Type': 'application/json'},
    method='PUT',
)
with urllib.request.urlopen(req) as response:
    print(response.status)
    print(response.read().decode())
