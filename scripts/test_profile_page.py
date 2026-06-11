"""Quick test: profile page via localhost (port 80) after nginx fix."""
import random
import re
import string

import requests

BASE = "http://localhost"
s = requests.Session()
user = "prof_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
pwd = "TestPass@123"

requests.post(
    "http://localhost:8012/auth/register/",
    json={"username": user, "email": f"{user}@t.com", "password": pwd, "role": "customer"},
    timeout=10,
)

r1 = s.get(f"{BASE}/login/", timeout=10)
m = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', r1.text)
csrf = m.group(1) if m else s.cookies.get("csrftoken", "")
s.post(
    f"{BASE}/login/",
    data={"username": user, "password": pwd, "login_type": "customer", "csrfmiddlewaretoken": csrf},
    headers={"Referer": f"{BASE}/login/"},
    allow_redirects=True,
    timeout=10,
)

r3 = s.get(f"{BASE}/profile/", timeout=10)
ok = "H\u1ed3 s\u01a1" in r3.text or "S\u1ed5 \u0111\u1ecba ch\u1ec9" in r3.text
print("profile_status", r3.status_code)
print("profile_ok", ok)
print("final_url", r3.url)
