import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api_gateway.settings")
django.setup()

import jwt, re
from django.test import Client
from django.conf import settings

token = jwt.encode({'user_id': 1, 'entity_id': 1, 'roles': ['CUSTOMER']}, settings.JWT_SECRET_KEY, algorithm='HS256')
c = Client()
session = c.session
session['user'] = {'entity_id': 1, 'roles': ['CUSTOMER']}
session['access_token'] = token
session.save()

res = c.get('/orders/customer/1/')
html = res.content.decode('utf-8').replace('\n', ' ')

# print table rows to see statuses
matches = re.findall(r'<span\s+class=\"badge.*?\">(.*?)</span>', html)
print("Statuses in HTML:")
for match in matches:
    print(match.strip())
