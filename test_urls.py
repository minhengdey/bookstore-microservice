import urllib.request
import sys

def test_url(url):
    print(f"\n--- Testing {url} ---")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        resp = urllib.request.urlopen(req)
        print("Status:", resp.status)
        print("Headers:", dict(resp.headers))
        print("Body:", resp.read().decode())
    except Exception as e:
        if hasattr(e, 'code'):
            print("Status:", e.code)
            print("Headers:", dict(e.headers))
            print("Body:", e.read().decode())
        else:
            print("Exception:", e)

test_url("http://localhost/")
test_url("http://localhost:8000/")
test_url("http://localhost/health/")
