import http.client, json, uuid
def req(m,p,body=None,token=None):
    c=http.client.HTTPConnection('localhost',8000,timeout=15)
    h={}
    if token: h['Authorization']=f'Bearer {token}'
    d=json.dumps(body) if body else None
    if d: h['Content-Type']='application/json'
    c.request(m,p,d,h)
    r=c.getresponse()
    b=r.read().decode()
    import json as js
    try: j=js.loads(b)
    except: j=b
    return r.status, j

import uuid as _uu
email=f"longtest_{_uu.uuid4().hex[:6]}@example.com"
s,j=req('POST','/api/v1/auth/register', {'name':'LongTester','email':email,'password':'password123'})
print('register',s, j)
# verify via DB
from app.core.database import SessionLocal
from app.models import User
db=SessionLocal()
u=db.query(User).filter(User.email==email.lower()).first()
if u:
    print('before verified',u.is_verified)
    u.is_verified=True; u.verification_token=None; u.verification_token_expires=None
    db.commit()
    print('after verified',u.is_verified)
db.close()
s,j=req('POST','/api/v1/auth/login', {'email':email,'password':'password123'})
print('login',s, j)
tok=j.get('access_token') if isinstance(j,dict) else None
print('tok', bool(tok), tok[:20] if tok else None)

if tok:
    import uuid as puuid, http.client
    path=r'C:\Users\ggaja\Downloads\Account Statement.csv'
    with open(path,'rb') as f:
        content=f.read()
    boundary='----Boundary'+puuid.uuid4().hex
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="Account Statement.csv"\r\nContent-Type: text/csv\r\n\r\n').encode() + content + f'\r\n--{boundary}--\r\n'.encode()
    c=http.client.HTTPConnection('localhost',8000,timeout=60)
    c.request('POST','/api/v1/transactions/import', body, headers={'Authorization':f'Bearer {tok}', 'Content-Type':f'multipart/form-data; boundary={boundary}'})
    print('sent, waiting')
    r=c.getresponse()
    b=r.read().decode()
    print('status',r.status)
    print(b[:3000])
    try:
        j=json.loads(b)
        print(f"format {j.get('format')} detected {j.get('transactions_detected')} imported {j.get('imported')} duplicates {j.get('duplicates')} failed {j.get('failed')}")
        if j.get('imported',0) > 100:
            print("BANK PASS")
        # check Branch Address not in errors
        errors=json.dumps(j.get('errors',[]))
        if "Branch Address" in errors:
            print("FAIL Branch Address")
        else:
            print("Branch Address correctly ignored")
    except Exception as e:
        print("parse fail",e)
