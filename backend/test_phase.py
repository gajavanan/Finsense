import http.client, json, uuid
from datetime import date, timedelta

def req(method, path, body=None, token=None, headers=None, raw_body=False):
    import http.client, json
    conn = http.client.HTTPConnection('localhost',8000,timeout=10)
    hdrs = {}
    if headers: hdrs.update(headers)
    if token:
        hdrs['Authorization'] = f'Bearer {token}'
    data=None
    if body is not None and not raw_body:
        hdrs['Content-Type']='application/json'
        data=json.dumps(body)
    elif raw_body:
        data=body
        # headers already set
    else:
        if method in ('POST','PUT'):
            hdrs['Content-Type']='application/json'
            data='{}'
    conn.request(method, path, data, hdrs)
    r=conn.getresponse()
    b=r.read().decode()
    try: j=json.loads(b)
    except: j=b
    return r.status, j, b

def register_and_verify(email, name="Test", pwd="password123"):
    # register
    s,j,_=req('POST','/api/v1/auth/register', {"name":name,"email":email,"password":pwd})
    print(f"Register {email}: {s} {str(j)[:200]}")
    # verify via DB directly
    from app.core.database import SessionLocal
    from app.models import User
    db=SessionLocal()
    u=db.query(User).filter(User.email==email.lower()).first()
    if u:
        u.is_verified=True
        u.verification_token=None
        u.verification_token_expires=None
        db.commit()
        print(f"Verified {email} via DB")
    db.close()
    # login
    s,j,_=req('POST','/api/v1/auth/login', {"email":email,"password":pwd})
    print(f"Login {email}: {s} {str(j)[:200]}")
    if s!=200:
        return None
    return j.get('access_token')

# Clean previous test data via DB
from app.core.database import SessionLocal
from app.models import User, Transaction, Budget, SpendingAlert
db=SessionLocal()
# keep
db.close()

uid=str(uuid.uuid4().hex[:6])
emailA=f"a_test_{uid}@example.com"
emailB=f"b_test_{uid}@example.com"
print(f"Testing with {emailA} and {emailB}")
tokenA=register_and_verify(emailA, "User A")
tokenB=register_and_verify(emailB, "User B")
print(f"tokenA {bool(tokenA)} tokenB {bool(tokenB)}")
if not tokenA or not tokenB:
    print("Failed to get tokens")
    exit(1)

# Test manual expense per spec
examples=[
    {"date":"2026-08-29","description":"Salary credit","merchant":"Company","amount":30000,"transaction_type":"income","category":"Salary","payment_method":"Bank Transfer"},
    {"date":"2026-08-29","description":"Rent payment","merchant":"Owner","amount":8000,"transaction_type":"expense","category":"Rent","payment_method":"Bank Transfer"},
    {"date":"2026-08-29","description":"Swiggy food order","merchant":"Swiggy","amount":450,"transaction_type":"expense","payment_method":"UPI"}, # auto category should be Food via rule
    {"date":"2026-08-29","description":"Indian Oil petrol","merchant":"Indian Oil","amount":1500,"transaction_type":"expense","payment_method":"Credit Card"},
    {"date":"2026-08-29","description":"Amazon purchase","merchant":"Amazon","amount":2200,"transaction_type":"expense","payment_method":"Credit Card"},
    {"date":"2026-08-29","description":"TANGEDCO electricity","merchant":"TANGEDCO","amount":900,"transaction_type":"expense","payment_method":"UPI"},
]

created=[]
for ex in examples:
    s,j,_=req('POST','/api/v1/transactions', ex, token=tokenA)
    print(f"Create {ex['description']}: {s} cat={j.get('category')} conf={j.get('confidence_score')} anom={j.get('is_anomaly')}")
    if s==200:
        created.append(j)
        # check expected categories for those without explicit category
        if ex['description']=='Swiggy food order' and j.get('category')!='Food':
            print("FAIL Swiggy should be Food got", j.get('category'))
        if ex['description']=='Indian Oil petrol' and j.get('category')!='Transport':
            print("FAIL Indian Oil should be Transport got", j.get('category'))
        if ex['description']=='Amazon purchase' and j.get('category')!='Shopping':
            print("FAIL Amazon should be Shopping got", j.get('category'))
        if ex['description']=='TANGEDCO electricity' and j.get('category') not in ('Utilities','Bills'):
            print(f"Note TANGEDCO got {j.get('category')} expected Utilities")
    else:
        print(f"Failed {ex}: {j}")

# Test GET filters
s,j,_=req('GET','/api/v1/transactions?transaction_type=expense', token=tokenA)
print(f"GET expense filter: {s} count={j.get('count')} data_len={len(j.get('data',[]))}")

s,j,_=req('GET',f'/api/v1/transactions?date_from=2026-08-29&date_to=2026-08-29', token=tokenA)
print(f"GET date filter: {s} count={j.get('count')}")

s,j,_=req('GET','/api/v1/transactions?category=Food', token=tokenA)
print(f"GET category Food: {s} count={j.get('count')}")

# Test isolation: User B should not see A's transactions
s,j,_=req('GET','/api/v1/transactions', token=tokenB)
print(f"B sees transactions: {s} count={j.get('count')} (should be 0)")

# Test PUT ownership violation: Try to edit A's transaction with B token
if created:
    tid=created[0]['id']
    s,j,_=req('PUT',f'/api/v1/transactions/{tid}', {"category":"Other"}, token=tokenB)
    print(f"B trying to edit A tx {tid}: {s} {j} (should be 404)")

# Test CSV import for A
import io
csv_content="""Date,Description,Merchant,Amount,Transaction Type,Category
2026-08-15,Swiggy order,Swiggy,320,expense,Food
2026-08-16,Salary credit,Company,30000,income,Salary
2026-08-17,Debit test,TestMerchant,500,,,
2026-08-29,Duplicate Swiggy,Swiggy,450,expense,Food
"""
# need to test Debit/Credit columns separately
csv2="""Date,Narration,Debit,Credit
2026-08-10,Zomato order,450,
2026-08-11,Salary credit,,30000
"""
# do multipart import via http.client
import http.client, mimetypes, uuid as puuid
def upload_csv(token, content, filename="test.csv"):
    import http.client
    boundary = "----Boundary"+puuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
        f"{content}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    conn=http.client.HTTPConnection('localhost',8000,timeout=10)
    conn.request('POST','/api/v1/transactions/import', body, headers={'Authorization':f'Bearer {token}', 'Content-Type':f'multipart/form-data; boundary={boundary}'})
    r=conn.getresponse()
    b=r.read().decode()
    try: j=json.loads(b)
    except: j=b
    return r.status, j

s,j=upload_csv(tokenA, csv_content)
print(f"CSV import test1: {s} {j}")

s,j=upload_csv(tokenA, csv2)
print(f"CSV import Debit/Credit: {s} {j}")

# Test duplicate prevention: re-upload same should fail some rows
s,j=upload_csv(tokenA, csv_content)
print(f"CSV duplicate re-upload: {s} {j} (failed should increase)")

# Test anomaly: create large food transaction 8000 vs normal 200-700
s,j,_=req('POST','/api/v1/transactions', {"date":"2026-08-29","description":"Huge food party","merchant":"Swiggy","amount":8000,"transaction_type":"expense","payment_method":"UPI"}, token=tokenA)
print(f"Anomaly test 8000 food: {s} is_anomaly={j.get('is_anomaly')} cat={j.get('category')}")
if j.get('is_anomaly'):
    print("Anomaly detected as expected (unusual spending)")

# Test budget system
s,j,_=req('POST','/api/v1/budgets', {"category":"Food","monthly_limit":3000}, token=tokenA)
print(f"Create Food budget 3000: {s} {j}")
s,j,_=req('POST','/api/v1/budgets', {"category":"Transport","monthly_limit":2000}, token=tokenA)
print(f"Create Transport budget: {s}")
s,j,_=req('POST','/api/v1/budgets', {"category":"Shopping","monthly_limit":4000}, token=tokenA)
print(f"Create Shopping budget: {s}")

# Check budget usage via dashboard
s,j,_=req('GET','/api/v1/dashboard', token=tokenA)
print(f"Dashboard: {s} balance={j.get('total_balance')} income={j.get('monthly_income')} expenses={j.get('monthly_expenses')} savings={j.get('monthly_savings')} rate={j.get('savings_rate')} todays={j.get('todays_spending')}")
if s==200:
    for b in j.get('budget_usage',[])[:3]:
        print(f"  Budget {b['category']}: {b['spent']}/{b['monthly_limit']} {b['pct']}%")
    # check alerts
    alerts=j.get('alerts') or j.get('spending_alerts') or []
    print(f"Alerts count {len(alerts)}")
    # also check via alerts endpoint
    s2,j2,_=req('GET','/api/v1/alerts', token=tokenA)
    print(f"Alerts endpoint: {s2} {j2[:2] if isinstance(j2,list) else j2}")

# Test forecast
s,j,_=req('POST','/api/v1/ml/predict/spending', {"period":"30d"}, token=tokenA)
print(f"Forecast: {s} {str(j)[:200]}")

# Test categorizer directly
s,j,_=req('POST','/api/v1/ml/predict/category', {"description":"Swiggy","merchant":"Swiggy"}, token=tokenA)
print(f"Categorizer Swiggy: {s} {j}")
s,j,_=req('POST','/api/v1/ml/predict/category', {"description":"Indian Oil petrol","merchant":"Indian Oil"}, token=tokenA)
print(f"Categorizer Indian Oil: {s} {j}")

# Test delete and edit
if created:
    tid2=created[1]['id']
    s,j,_=req('DELETE',f'/api/v1/transactions/{tid2}', token=tokenA)
    print(f"Delete {tid2}: {s} {j}")
    # verify deleted not visible
    s,j,_=req('GET','/api/v1/transactions', token=tokenA)
    print(f"After delete count {j.get('count')}")
    # edit category correction
    tid3=created[2]['id']
    s,j,_=req('PUT',f'/api/v1/transactions/{tid3}', {"category":"Groceries"}, token=tokenA)
    print(f"Edit category correction {tid3} to Groceries: {s} {j.get('category')}")

print("=== TEST DONE ===")
