import urllib.request
import urllib.error

try:
    response = urllib.request.urlopen("http://localhost:80/")
    print("Status:", response.status)
    print("Body:", response.read().decode())
except urllib.error.HTTPError as e:
    print("Status:", e.code)
    print("Body:", e.read().decode())
except Exception as e:
    print("Exception:", e)
