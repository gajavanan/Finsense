import http.client, json, uuid
def req(method, path, body=None, token=None):
    conn=http.client.HTTPConnection('localhost',8000,timeout=10)
    hdrs={}
    if token: hdrs['Authorization']=f'Bearer {token}'
    data=None
    if body is not None:
        hdrs['Content-Type']='application/json'
        data=json.dumps(body)
    conn.request(method, path, data, hdrs)
    r=conn.getresponse()
    b=r.read().decode()
    try: j=json.loads(b)
    except: j=b
    return r.status, j

def register_and_verify(email):
    s,j=req('POST','/api/v1/auth/register', {"name":"Tester","email":email,"password":"password123"})
    print(f"reg {s}")
    from app.core.database import SessionLocal
    from app.models import User
    db=SessionLocal()
    u=db.query(User).filter(User.email==email.lower()).first()
    if u:
        u.is_verified=True; u.verification_token=None; db.commit()
    db.close()
    s,j=req('POST','/api/v1/auth/login', {"email":email,"password":"password123"})
    return j.get('access_token')

email=f"alert_{uuid.uuid4().hex[:6]}@example.com"
tok=register_and_verify(email)
print(f"tok {bool(tok)}")

# create budgets first
for cat, lim in [("Food",3000),("Transport",2000),("Shopping",4000)]:
    s,j=req('POST','/api/v1/budgets', {"category":cat,"monthly_limit":lim}, token=tok)
    print(f"budget {cat} {s} {j.get('id')}")

# create expenses incrementally to hit thresholds
def create_exp(desc, merch, amt, cat=None):
    payload={"date":"2026-08-29","description":desc,"merchant":merch,"amount":amt,"transaction_type":"expense","payment_method":"UPI"}
    if cat: payload["category"]=cat
    s,j=req('POST','/api/v1/transactions', payload, token=tok)
    print(f"exp {desc} {amt} -> {s} cat={j.get('category')} anom={j.get('is_anomaly')}")
    return s,j

# Food 75% = 2250
create_exp("Swiggy lunch","Swiggy",800, "Food")
create_exp("Zomato dinner","Zomato",700, "Food")
# now 1500/3000 =50% no alert yet
s,j=req('GET','/api/v1/alerts', token=tok)
print(f"alerts after 1500 {len(j) if isinstance(j,list) else j}")
# add 800 => 2300/3000=76% should trigger 75%
create_exp("A2B breakfast","A2B",800, "Food")
s,j=req('GET','/api/v1/alerts', token=tok)
print(f"alerts after 2300 (75%) {j}")

# add 400 => 2700/3000=90% trigger 90%
create_exp("Food big","Swiggy",400, "Food")
s,j=req('GET','/api/v1/alerts', token=tok)
print(f"alerts after 2700 (90%) {j}")

# add 500 => 3200/3000=106% trigger 100%
create_exp("Food over","Swiggy",500, "Food")
s,j=req('GET','/api/v1/alerts', token=tok)
print(f"alerts after 3200 (100%) {j}")

# check dashboard
s,j=req('GET','/api/v1/dashboard', token=tok)
print(f"dashboard alerts {len(j.get('alerts',[]))} spending_alerts {len(j.get('spending_alerts',[]))}")
for a in j.get('alerts',[])[:3]:
    print(a)

# test duplicate alert not created again for same threshold
create_exp("Food duplicate trigger","Swiggy",10, "Food")
s,j=req('GET','/api/v1/alerts', token=tok)
print(f"alerts after duplicate 10 (should not duplicate 100) count {len(j)} {j}")

# test transport 75%
create_exp("Indian Oil","Indian Oil",1500, "Transport")
s,j=req('GET','/api/v1/alerts', token=tok)
print(f"alerts after transport 1500/2000 75% {j}")

# test forecast with more dates
for i in range(1,8):
    d=f"2026-08-{10+i:02d}"
    s,j=req('POST','/api/v1/transactions', {"date":d,"description":f"Test day {i}","merchant":"Test","amount":500,"transaction_type":"expense","category":"Food","payment_method":"UPI"}, token=tok)
    print(f"forecast fill day {d} {s}")

s,j=req('POST','/api/v1/ml/predict/spending', {"period":"30d"}, token=tok)
print(f"forecast after 7 days {j.get('status')} total {j.get('total_forecast')}")

# test manual income
s,j=req('POST','/api/v1/transactions', {"date":"2026-08-29","description":"Salary","merchant":"Company","amount":30000,"transaction_type":"income","category":"Salary","payment_method":"Bank Transfer"}, token=tok)
print(f"income {s} {j}")

# test dashboard calculations
s,j=req('GET','/api/v1/dashboard', token=tok)
print(f"dashboard final: balance {j.get('total_balance')} income {j.get('monthly_income')} expenses {j.get('monthly_expenses')} savings {j.get('monthly_savings')} rate {j.get('savings_rate')} todays {j.get('todays_spending')}")

# test CSV with proper format (use previous successful Debit/Credit)
import http.client, uuid as puuid
def upload_csv(token, content, filename="test.csv"):
    boundary="----Boundary"+puuid.uuid4().hex
    body=(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: text/csv\r\n\r\n{content}\r\n--{boundary}--\r\n").encode()
    conn=http.client.HTTPConnection('localhost',8000,timeout=10)
    conn.request('POST','/api/v1/transactions/import', body, headers={'Authorization':f'Bearer {token}', 'Content-Type':f'multipart/form-data; boundary={boundary}'})
    r=conn.getresponse()
    b=r.read().decode()
    import json
    try: j=json.loads(b)
    except: j=b
    return r.status, j

csv_good="""Date,Description,Merchant,Amount,Transaction Type
2026-08-01,Swiggy order,Swiggy,450,expense
2026-08-02,Salary credit,Company,30000,income
"""
s,j=upload_csv(tok, csv_good)
print(f"csv good import {s} {j}")

# test isolation: create second user and verify not seeing first
email2=f"alert2_{uuid.uuid4().hex[:6]}@example.com"
tok2=register_and_verify(email2)
s,j=req('GET','/api/v1/transactions', token=tok2)
print(f"second user sees {j.get('count')} tx (should be 0)")

print("DONE")
