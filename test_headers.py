import urllib.request
import urllib.error

url = "http://localhost/"
print(f"Fetching {url}")
try:
    response = urllib.request.urlopen(url)
    print("Status:", response.status)
    print("Headers:", dict(response.headers))
    print("Body:", response.read().decode())
except urllib.error.HTTPError as e:
    print("Status:", e.code)
    print("Headers:", dict(e.headers))
    print("Body:", e.read().decode())
except Exception as e:
    print("Exception:", e)
