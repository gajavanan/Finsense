import http.client, json, uuid
def req(m,p,body=None,token=None):
    c=http.client.HTTPConnection('localhost',8000,timeout=10)
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
    return r.status,j

from app.core.database import SessionLocal
from app.models import User
email='final_'+uuid.uuid4().hex[:6]+'@example.com'
s,j=req('POST','/api/v1/auth/register', {'name':'Final Tester','email':email,'password':'password123'})
print('reg',s)
db=SessionLocal()
u=db.query(User).filter(User.email==email).first()
u.is_verified=True; u.verification_token=None; db.commit(); db.close()
s,j=req('POST','/api/v1/auth/login', {'email':email,'password':'password123'})
tok=j['access_token']
print('login', bool(tok))

tests=[
    ('Salary',30000,'Salary','Company','income'),
    ('Rent',8000,'Rent','Owner','expense'),
    ('Swiggy',450,'Food','Swiggy','expense'),
    ('Indian Oil',1500,'Transport','Indian Oil','expense'),
    ('Amazon',2200,'Shopping','Amazon','expense'),
    ('TANGEDCO',900,'Utilities','TANGEDCO','expense'),
]
for name, amt, expected_cat, merchant, ttype in tests:
    s,j=req('POST','/api/v1/transactions', {'date':'2026-08-29','description':name,'merchant':merchant,'amount':amt,'transaction_type':ttype,'payment_method':'UPI'}, token=tok)
    cat=j.get('category')
    ok='OK' if cat==expected_cat else f'WRONG expected {expected_cat} got {cat}'
    print(f'{name} {amt} -> {cat} {ok}')

s,j=req('GET','/api/v1/transactions?category=Food', token=tok)
if j.get('count',0)>0:
    tid=j['data'][0]['id']
    s2,j2=req('PUT',f'/api/v1/transactions/{tid}', {'category':'Groceries'}, token=tok)
    print(f'correction {tid} Food->Groceries {s2} new {j2.get("category")}')

s,j=req('GET','/api/v1/dashboard', token=tok)
print(f"dashboard balance {j.get('total_balance')} income {j.get('monthly_income')} expenses {j.get('monthly_expenses')} savings {j.get('monthly_savings')} rate {j.get('savings_rate')}")

for i in range(10,17):
    s,j=req('POST','/api/v1/transactions', {'date':f'2026-08-{i:02d}','description':'Test','merchant':'Test','amount':500,'transaction_type':'expense','category':'Food','payment_method':'UPI'}, token=tok)
s,j=req('POST','/api/v1/ml/predict/spending', {'period':'30d'}, token=tok)
print(f"forecast {j.get('status')} total {j.get('total_forecast')}")

s,j=req('POST','/api/v1/transactions', {'date':'2026-08-29','description':'Huge food','merchant':'Swiggy','amount':8000,'transaction_type':'expense','payment_method':'UPI'}, token=tok)
print(f"anomaly 8000 is_anomaly {j.get('is_anomaly')}")

s,j=req('POST','/api/v1/budgets', {'category':'Food','monthly_limit':3000}, token=tok)
print(f"budget food {s}")
s,j=req('GET','/api/v1/budgets', token=tok)
print(f"budgets list {len(j)} first pct {j[0].get('pct') if j else 'none'}")

s,j=req('POST','/api/v1/advisor/chat', {'message':'How is my food spending?'}, token=tok)
resp=j.get('response','')
print(f"advisor {s} {resp[:200] if resp else ''}")

# isolation test
email2='final2_'+uuid.uuid4().hex[:6]+'@example.com'
s,j=req('POST','/api/v1/auth/register', {'name':'Second','email':email2,'password':'password123'})
db=SessionLocal()
u=db.query(User).filter(User.email==email2).first()
u.is_verified=True; db.commit(); db.close()
s,j=req('POST','/api/v1/auth/login', {'email':email2,'password':'password123'})
tok2=j['access_token']
s,j=req('GET','/api/v1/transactions', token=tok2)
print(f"isolation second user count {j.get('count')} should be 0")
print("FINAL CHECK DONE")
