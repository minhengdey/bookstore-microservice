import urllib.request
import urllib.error

try:
    response = urllib.request.urlopen("http://localhost")
    print(response.read().decode())
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"Error: {e}")
