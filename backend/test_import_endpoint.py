import http.client, json, uuid, mimetypes, os
from pathlib import Path

# Register and verify user
def req(method, path, body=None, token=None):
    c=http.client.HTTPConnection('localhost',8000,timeout=15)
    h={}
    if token: h['Authorization']=f'Bearer {token}'
    d=json.dumps(body) if body else None
    if d: h['Content-Type']='application/json'
    c.request(method, path, d, h)
    r=c.getresponse()
    b=r.read().decode()
    try: j=json.loads(b)
    except: j=b
    return r.status, j

def register_and_verify(email):
    s,j=req('POST','/api/v1/auth/register', {'name':'Importer','email':email,'password':'password123'})
    print(f"register {s}")
    from app.core.database import SessionLocal
    from app.models import User
    db=SessionLocal()
    u=db.query(User).filter(User.email==email.lower()).first()
    if u:
        u.is_verified=True; u.verification_token=None; db.commit()
        print(f"verified {email}")
    db.close()
    s,j=req('POST','/api/v1/auth/login', {'email':email,'password':'password123'})
    print(f"login {s}")
    return j.get('access_token')

email=f"importer_{uuid.uuid4().hex[:6]}@example.com"
tok=register_and_verify(email)
print(f"tok {bool(tok)}")

# Test generic CSV first (FORMAT A)
generic_csv="""Date,Description,Debit,Credit
2026-08-01,Swiggy order,450,
2026-08-02,Salary credit,,30000
2026-08-03,Amazon purchase,1200,
"""
def upload_csv(token, content_bytes, filename="test.csv"):
    import uuid as puuid, http.client
    boundary="----Boundary"+puuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
    ).encode() + content_bytes + f"\r\n--{boundary}--\r\n".encode()
    c=http.client.HTTPConnection('localhost',8000,timeout=15)
    c.request('POST','/api/v1/transactions/import', body, headers={'Authorization':f'Bearer {token}', 'Content-Type':f'multipart/form-data; boundary={boundary}'})
    r=c.getresponse()
    b=r.read().decode()
    try: j=json.loads(b)
    except: j=b
    return r.status, j, b

print("=== GENERIC CSV TEST ===")
s,j,b=upload_csv(tok, generic_csv.encode(), "generic.csv")
print(f"GENERIC status {s} json {j}")
if s==200:
    print(f"generic format detected? {j.get('format')} detected {j.get('transactions_detected')} imported {j.get('imported')} failed {j.get('failed')} duplicates {j.get('duplicates')}")
    # verify not 0/failed
    if j.get('imported',0)==2 and j.get('failed',0)==0:
        print("GENERIC PASS")
    else:
        print("GENERIC CHECK")

# Now test bank statement (FORMAT B)
bank_path=r"C:\Users\ggaja\Downloads\Account Statement.csv"
with open(bank_path,'rb') as f:
    bank_bytes=f.read()
print("=== BANK STATEMENT TEST (FORMAT B) ===")
print(f"file size {len(bank_bytes)}")
s,j,b=upload_csv(tok, bank_bytes, "Account Statement.csv")
print(f"BANK status {s}")
print(f" BANK json {json.dumps(j, indent=2)[:2000]}")
if s==200:
    print(f"format {j.get('format')} detected {j.get('transactions_detected')} imported {j.get('imported')} duplicates {j.get('duplicates')} failed {j.get('failed')}")
    if j.get('imported',0) > 100:
        print(f"BANK PASS imported {j.get('imported')} >100, Branch Address not parsed as date")
        # check Branch Address not in errors
        errors_str=json.dumps(j.get('errors',[]))
        if "Branch Address" in errors_str or "Unknown datetime string format" in errors_str:
            print("FAIL Branch Address still being parsed!")
        else:
            print("Branch Address correctly ignored")
        # check one failed not 481
        if j.get('failed',0) < 10:
            print(f"Failed low as expected {j.get('failed')}")
        # check example normalized
        # fetch transactions
        s2,j2=req('GET','/api/v1/transactions?limit=3', token=tok)
        print(f"transactions after import count {j2.get('count')} sample {json.dumps(j2.get('data',[])[:1], indent=2)[:1000]}")
        # dashboard
        s3,j3=req('GET','/api/v1/dashboard', token=tok)
        print(f"dashboard monthly_expenses {j3.get('monthly_expenses')} monthly_income {j3.get('monthly_income')} todays {j3.get('todays_spending')}")
        if j3.get('monthly_expenses',0) > 0:
            print("Dashboard updated PASS")
    else:
        print(f"BANK FAIL imported {j.get('imported')} expected >100")
else:
    print(f"BANK status not 200: {b[:1000]}")

# Test duplicate re-upload should give duplicates
print("=== DUPLICATE RE-UPLOAD TEST ===")
s,j,b=upload_csv(tok, bank_bytes, "Account Statement.csv")
print(f"DUPLICATE status {s} json {j}")
if s==200:
    print(f"duplicates {j.get('duplicates')} imported {j.get('imported')}")
    if j.get('duplicates',0) > 100 and j.get('imported',0)==0:
        print("DUPLICATE PASS")
    else:
        print("DUPLICATE CHECK")

# Test that generic still works after bank
print("=== SECOND GENERIC AFTER BANK (isolation) ===")
generic2="""Date,Description,Merchant,Amount,Transaction Type
2026-08-15,Test generic,TestMerch,500,expense
"""
s,j,b=upload_csv(tok, generic2.encode(), "generic2.csv")
print(f"generic2 {s} {j}")

print("DONE")
