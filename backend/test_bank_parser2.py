import pandas as pd, io, re
from datetime import datetime

path=r'C:\Users\ggaja\Downloads\Account Statement.csv'
with open(path,'rb') as f:
    content=f.read()

def _parse_date_safe(s):
    s=s.strip().strip("()").strip()
    fmts=["%d-%b-%y","%d-%b-%Y","%d/%m/%Y","%d-%m-%Y","%Y-%m-%d","%d/%m/%y","%d-%m-%y"]
    for fmt in fmts:
        try:
            test_s=s.title() if "%b" in fmt else s
            dt=datetime.strptime(test_s, fmt)
            return dt.date()
        except: continue
    try:
        return pd.to_datetime(s, dayfirst=True).date()
    except:
        raise ValueError(f"Unknown datetime {s}")

def _is_strict_date(s):
    """True if s is date like 30-Aug-26 without parentheses"""
    if not isinstance(s, str): return False
    s=s.strip()
    if not s or s.lower() in ("nan","-",""): return False
    if s.startswith("(") or s.endswith(")"):
        return False
    # check pattern
    patterns=[r"^\d{1,2}-[A-Za-z]{3}-\d{2,4}$", r"^\d{1,2}/\d{1,2}/\d{2,4}$", r"^\d{1,2}-\d{1,2}-\d{2,4}$", r"^\d{4}-\d{1,2}-\d{1,2}$"]
    s_clean=s.strip()
    for pat in patterns:
        if re.match(pat, s_clean):
            try:
                _parse_date_safe(s_clean)
                return True
            except: continue
    return False

def _is_any_date(s):
    if not isinstance(s, str): return False
    s=s.strip()
    if not s or s.lower() in ("nan","-",""): return False
    inner=s.strip().strip("()").strip()
    if not inner: return False
    try:
        _parse_date_safe(inner)
        if re.search(r"\d", inner) and ("-" in inner or "/" in inner):
            return True
        return False
    except: return False

def _parse_amount_safe(s):
    if s is None: return None
    s=str(s).strip()
    if s.lower() in ("","-","nan","none","null"): return None
    s=s.replace(",","").replace("₹","").replace("Rs","").replace("Rs.","").strip()
    try:
        v=float(s)
        if v==0: return None
        return v
    except: return None

df=pd.read_csv(io.BytesIO(content), header=None, dtype=str, keep_default_na=False, engine='python', on_bad_lines='skip')
print(f"shape {df.shape}")
text=content.decode('utf-8', errors='ignore')[:8000].lower()
is_bank = "report generation date" in text or "statement of the account" in text
print(f"is_bank {is_bank}")
header_idx=None
for idx,row in df.iterrows():
    row_str=" ".join([str(v).lower() for v in row.values if str(v).strip()]).lower()
    if "debit(rs)" in row_str and "credit(rs)" in row_str:
        header_idx=idx
        print(f"header at {idx}")
        break
start_idx=header_idx+2 if header_idx is not None else 0
print(f"start_idx {start_idx}")

detected=[]
i=start_idx
skipped_pages=0
while i < len(df):
    row=df.iloc[i]
    row_str=" ".join([str(v) for v in row.values])
    if "Page" in row_str and "of" in row_str:
        i+=1
        continue
    if "Effective available balance" in row_str or "computer generated statement" in row_str or "15078.34" in row_str:
        break
    if row_str.strip()=="" or row_str.strip().lower()=="nan":
        i+=1
        continue
    col0=str(row[0]).strip() if 0 in row else ""
    if col0.lower()=="nan": col0=""
    if _is_strict_date(col0):
        group=[row]
        # look ahead up to 2 rows, handle page
        for offset in [1,2,3]: # allow 3 to skip page
            if i+offset >= len(df): break
            nxt=df.iloc[i+offset]
            nxt_str=" ".join([str(v) for v in nxt.values])
            if "Page" in nxt_str and "of" in nxt_str:
                # skip page, but allow next row to be considered for same transaction?
                # we will not add page to group, but we need to consider next row after page as potential continuation?
                # For bank statement, page never inside transaction, it's between transactions, so break group and let outer loop skip page
                # So don't add page, don't count offset, but continue to check next offset as continuation?
                # To handle, we just continue without adding, but we need to track that we consumed page rows separately
                # For simplicity, break group and let outer handle page skip
                break
            if "Effective available balance" in nxt_str or "computer generated statement" in nxt_str:
                break
            nxt_col0=str(nxt[0]).strip() if 0 in nxt else ""
            if nxt_col0.lower()=="nan": nxt_col0=""
            if _is_strict_date(nxt_col0):
                break
            nxt_content=" ".join([str(v) for v in nxt.values if str(v).strip()]).strip()
            if nxt_content=="" or nxt_content.lower()=="nan":
                continue
            group.append(nxt)
            if len(group)>=3:
                break
        # normalize
        date_str=str(group[0][0]).strip()
        try:
            norm_date=_parse_date_safe(date_str)
        except Exception as e:
            print(f"date fail at {i} {date_str} {e}")
            i+=len(group)
            continue
        parts=[]
        ref_no=None
        trans_type=None
        debit=None
        credit=None
        balance=None
        for grow in group:
            p1=str(grow[1]).strip() if 1 in grow and str(grow[1]).strip().lower() not in ("","nan","-") else ""
            if p1 and not _is_any_date(p1) and "Page" not in p1:
                # avoid adding header fragments like "Particulars"
                if p1.lower() not in ("particulars","type"):
                    parts.append(p1)
            c2=str(grow[2]).strip() if 2 in grow else ""
            if c2.lower() not in ("","nan","-") and "Page" not in c2:
                if re.match(r"S\d+",c2) or c2.isdigit():
                    if not ref_no:
                        ref_no=c2
            c3=str(grow[3]).strip() if 3 in grow else ""
            if c3.lower() not in ("","nan","-"):
                if c3.lower() in ("transfer","imps","neft","upi"):
                    trans_type=c3
                elif not trans_type and c3.lower() not in ("type","/cheque no"):
                    trans_type=c3
            c4=str(grow[4]).strip() if 4 in grow else ""
            c5=str(grow[5]).strip() if 5 in grow else ""
            c6=str(grow[6]).strip() if 6 in grow else ""
            dval=_parse_amount_safe(c4)
            cval=_parse_amount_safe(c5)
            if dval is not None and debit is None:
                debit=dval
            if cval is not None and credit is None:
                credit=cval
            if c6 and balance is None:
                bval=_parse_amount_safe(c6)
                if bval: balance=bval
        description=" ".join(parts).strip()
        description=re.sub(r"\s+"," ",description).strip()
        # skip if no amount
        amount=None
        ttype=None
        if debit is not None and debit>0:
            amount=debit; ttype="expense"
        elif credit is not None and credit>0:
            amount=credit; ttype="income"
        else:
            print(f"skip no amount at {i} desc={description[:30]} debit={debit} credit={credit}")
            i+=len(group)
            continue
        pay="UPI" if "UPI/" in description or "upi" in description.lower() else "Bank Transfer"
        detected.append({"date":norm_date.isoformat(),"description":description,"debit":debit,"credit":credit,"amount":amount,"transaction_type":ttype,"payment_method":pay,"ref":ref_no,"balance":balance})
        i+=len(group)
    else:
        i+=1

print(f"detected {len(detected)}")
for d in detected[:5]:
    print(d)
print("---last5---")
for d in detected[-5:]:
    print(d)
from collections import Counter
print(Counter([d['transaction_type'] for d in detected]))
# check particulars merging for first transaction
print("first desc:", detected[0]['description'])
# should contain /YES/UPI
if "/YES/UPI" in detected[0]['description']:
    print("merging OK for first")
else:
    print("merging FAILED for first, expected /YES/UPI")
# check INDANE
for d in detected:
    if "INDANE" in d['description']:
        print("INDANE found:", d)
        break
