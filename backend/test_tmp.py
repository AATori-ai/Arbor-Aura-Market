import urllib.request, urllib.error, json
try:
    r = urllib.request.Request('http://127.0.0.1:8000/api/auth/register', data=json.dumps({'email':'test@test.com', 'password':'Test1234'}).encode(), headers={'Content-Type':'application/json'})
    print("Success:", urllib.request.urlopen(r).read().decode())
except urllib.error.HTTPError as e:
    print("Error:", e.code, e.read().decode())
