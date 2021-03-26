#!/usr/bin/env python3
# this is for AUTH
# get your url from https://wayf.grnet.gr/
# TEST ONLY
# TODO: integrate into epresence.py

import requests
from urllib import parse
from bs4 import BeautifulSoup

# fill this
username = ''
password = ''

s = requests.Session()
url = 'https://new.epresence.grnet.gr/login'
r = s.get(url)
headers= { 'Referer': r.request.url }
ck, cv = r.cookies.items()[0]
data = {'user_idp': 'https://login.auth.gr/saml2/idp/metadata.php', 'savetype': 'session', 'csrfmiddlewaretoken': cv}
#r = s.post(r.url, data=data, headers=headers, verify='/etc/ssl/certs/Hellenic_Academic_and_Research_Institutions_RootCA_2011.pem')
r = s.post(r.url, data=data, headers=headers, verify=False)
data=dict(parse.parse_qsl(parse.urlsplit(r.url).query))
data.update({'username': username})
data.update({'password': password})
r = s.post(r.url, data=data)

soup = BeautifulSoup(r.text, 'lxml')
form = soup.find('form')
fields = form.findAll('input')
formdata = dict( (field.get('name'), field.get('value')) for field in fields)
formdata.pop(None)
posturl = parse.urljoin(r.url, form['action'])

r = s.post(posturl, data=formdata)
