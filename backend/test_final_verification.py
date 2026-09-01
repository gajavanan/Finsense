import http.client, json, uuid, time

def req(m,p,body=None,token=None):
    c=http.client.HTTPConnection('localhost',8000,timeout=15)
    h={}
    if token: h['Authorization']=f'Bearer {token}'
    d=json.dumps(body) if body else None
    if d: h['Content-Type']='application/json'
    c.request(m,p,d,h)
    r=c.getresponse()
    b=r.read().decode()
    try: j=json.loads(b)
    except: j=b
    return r.status, j

# Use the longtest user from previous run? Create fresh
email=f"verify_{uuid.uuid4().hex[:6]}@example.com"
s,j=req('POST','/api/v1/auth/register', {'name':'Verifier','email':email,'password':'password123'})
print(f"register {s}")
from app.core.database import SessionLocal
from app.models import User, Transaction
db=SessionLocal()
u=db.query(User).filter(User.email==email.lower()).first()
u.is_verified=True; u.verification_token=None; u.verification_token_expires=None
db.commit()
db.close()
s,j=req('POST','/api/v1/auth/login', {'email':email,'password':'password123'})
tok=j['access_token']
print(f"login {s} tok {bool(tok)}")

# Generic test
generic="""Date,Description,Debit,Credit
2026-08-01,Swiggy order,450,
2026-08-02,Salary credit,,30000
"""
def upload(token, path, content_bytes=None, filename="test.csv"):
    import uuid as puuid, http.client
    if content_bytes is None:
        with open(path,'rb') as f:
            content_bytes=f.read()
    boundary='----Boundary'+puuid.uuid4().hex
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: text/csv\r\n\r\n').encode() + content_bytes + f'\r\n--{boundary}--\r\n'.encode()
    c=http.client.HTTPConnection('localhost',8000,timeout=60)
    c.request('POST','/api/v1/transactions/import', body, headers={'Authorization':f'Bearer {token}', 'Content-Type':f'multipart/form-data; boundary={boundary}'})
    r=c.getresponse()
    b=r.read().decode()
    try: j=json.loads(b)
    except: j=b
    return r.status, j

print("=== GENERIC ===")
s,j=upload(tok, None, generic.encode(), "generic.csv")
print(f"generic status {s} detected {j.get('transactions_detected')} imported {j.get('imported')} failed {j.get('failed')} format {j.get('format')}")
assert j.get('imported')==2, "generic should import 2"

# Bank statement first import
print("=== BANK FIRST IMPORT ===")
s,j=upload(tok, r"C:\Users\ggaja\Downloads\Account Statement.csv", None, "Account Statement.csv")
print(f"bank first status {s} detected {j.get('transactions_detected')} imported {j.get('imported')} duplicates {j.get('duplicates')} failed {j.get('failed')} format {j.get('format')}")
print(f"errors {j.get('errors')}")
# Check Branch Address not in errors
err_str=json.dumps(j.get('errors',[]))
if "Branch Address" in err_str:
    print("FAIL Branch Address still parsed")
else:
    print("Branch Address correctly ignored PASS")
# Check transactions detected 152
if j.get('transactions_detected')==152 and j.get('imported')==152:
    print("BANK FIRST PASS")
else:
    print(f"BANK FIRST: expected 152 detected/imported got {j.get('transactions_detected')}/{j.get('imported')}")

# Check example normalized transaction via DB
from app.core.database import SessionLocal as SL2
db2=SL2()
# need user id - re-query
from app.models import User as U2
usr=db2.query(U2).filter(U2.email==email.lower()).first()
uid=usr.id
from app.models import Transaction as T2
tx=db2.query(T2).filter(T2.user_id==uid).order_by(T2.date.desc()).limit(3).all()
print(f"DB sample transactions after import:")
for t in tx[:2]:
    print(f"  {t.date} | {t.description[:50]} | cat={t.category} | type={t.transaction_type} | {t.amount} | {t.payment_method} | conf={t.confidence_score}")
db2.close()
# Check dashboard
s,jd=req('GET','/api/v1/dashboard', token=tok)
print(f"dashboard expenses {jd.get('monthly_expenses')} income {jd.get('monthly_income')} balance {jd.get('total_balance')} todays {jd.get('todays_spending')}")
if jd.get('monthly_expenses',0) > 5000:
    print("Dashboard updated PASS")
# Duplicate re-upload
print("=== BANK DUPLICATE RE-UPLOAD ===")
s,j=upload(tok, r"C:\Users\ggaja\Downloads\Account Statement.csv", None, "Account Statement.csv")
print(f"bank duplicate status {s} detected {j.get('transactions_detected')} imported {j.get('imported')} duplicates {j.get('duplicates')} failed {j.get('failed')}")
if j.get('duplicates',0)==152 and j.get('imported',0)==0:
    print("DUPLICATE PASS")
else:
    print(f"DUPLICATE expected 152 duplicates 0 imported got {j.get('duplicates')}/{j.get('imported')}")
# Check that no new transactions added
s,jd=req('GET','/api/v1/transactions?limit=5', token=tok)
print(f"transactions count after duplicate {jd.get('count')}")

print("=== TESTS DONE ===")
