import pandas as pd, io, re
from datetime import datetime

path=r'C:\Users\ggaja\Downloads\Account Statement.csv'
with open(path,'rb') as f:
    content=f.read()

def _parse_date_safe(s):
    s=s.strip().strip("()").strip()
    fmts=["%d-%b-%y","%d-%b-%Y","%d/%m/%Y","%d-%m-%Y","%Y-%m-%d","%d/%m/%y","%d-%m-%y"]
    # handle month abbreviation case
    for fmt in fmts:
        try:
            # normalize: if fmt contains %b, ensure s is title case
            test_s=s.title() if "%b" in fmt else s
            dt=datetime.strptime(test_s, fmt)
            # fix 2-digit year 00-99 -> 2000-2099? strptime does 69-99 ->1969-1999, we want 26->2026 which is fine (26<69 =>2026)
            return dt.date()
        except: continue
    try:
        return pd.to_datetime(s, dayfirst=True).date()
    except:
        raise ValueError(f"Unknown datetime {s}")

def _is_date_like(s):
    if not isinstance(s, str): return False
    s=s.strip()
    if not s or s.lower() in ("nan","-",""): return False
    # strip parentheses for check
    inner=s.strip().strip("()").strip()
    if not inner: return False
    try:
        _parse_date_safe(inner)
        # ensure inner matches date pattern not random text
        # check that it contains digit and '-' or '/'
        if re.search(r"\d", inner) and ("-" in inner or "/" in inner):
            # avoid Branch Address etc which has no digits? but Branch Address has no digits, so fails
            return True
        return False
    except:
        return False

def _parse_amount_safe(s):
    if s is None: return None
    s=str(s).strip()
    if s.lower() in ("","-","nan","none","null"): return None
    # remove commas, Rs, ₹, spaces
    s=s.replace(",","").replace("₹","").replace("Rs","").replace("Rs.","").strip()
    # handle like "34.8"
    try:
        v=float(s)
        if v==0: return None
        return v
    except:
        return None

# Read with header=None
df=pd.read_csv(io.BytesIO(content), header=None, dtype=str, keep_default_na=False, engine='python', on_bad_lines='skip')
print(f"df shape {df.shape}")
# Detect format
text=content.decode('utf-8', errors='ignore')[:8000].lower()
is_bank = "report generation date" in text or "statement of the account" in text or "branch address" in text
print(f"is_bank by text {is_bank}")

# Find transaction header region
header_idx=None
for idx,row in df.iterrows():
    row_str=" ".join([str(v).lower() for v in row.values if str(v).strip().lower() not in ("","nan","-")])
    if "debit(rs)" in row_str and "credit(rs)" in row_str:
        header_idx=idx
        print(f"header found at {idx} row_str: {row_str[:100]}")
        break

if header_idx is None:
    print("no header found, assume generic")
else:
    print(f"header_idx {header_idx}")

# Now test multi-row merging starting after header
# For bank, data starts after header block; header block may be 2-3 rows around header_idx
# We'll start scanning from header_idx+1
start_idx = header_idx+2 if header_idx is not None else 0  # skip header continuation row 17
print(f"start_idx {start_idx}")

detected=[]
i=start_idx
while i < len(df):
    row=df.iloc[i]
    # combine row values for page check
    row_str=" ".join([str(v) for v in row.values if str(v).strip()])
    if "Page" in row_str and "of" in row_str:
        print(f"skip page at {i}: {row_str}")
        i+=1
        continue
    # check if empty row
    if row_str.strip()=="" or row_str.strip().lower()=="nan":
        i+=1
        continue
    col0=str(row[0]).strip() if 0 in row else ""
    # also handle case where col0 is "nan" string due to keep_default_na=False? we used keep_default_na=False so NaN becomes ""? Actually dtype=str so maybe "nan"
    if col0.lower()=="nan": col0=""
    if _is_date_like(col0):
        # start new transaction group
        group=[row]
        # look ahead up to 2 rows
        for offset in [1,2]:
            if i+offset >= len(df): break
            nxt=df.iloc[i+offset]
            nxt_str=" ".join([str(v) for v in nxt.values if str(v).strip()])
            if "Page" in nxt_str and "of" in nxt_str:
                # skip page but don't count as group, look further
                # we need to check offset+1 beyond page?
                continue
            nxt_col0=str(nxt[0]).strip() if 0 in nxt else ""
            if nxt_col0.lower()=="nan": nxt_col0=""
            if _is_date_like(nxt_col0):
                # next transaction start, stop
                break
            # check if nxt is empty
            if nxt_str.strip()=="" or nxt_str.strip().lower()=="nan":
                continue
            # need to ensure nxt is not summary row like "15078.34 14829" or "Effective available balance"
            if "15078.34" in nxt_str or "Effective available balance" in nxt_str or "computer generated statement" in nxt_str:
                break
            group.append(nxt)
            if len(group)>=3:
                # check if we already have debit/credit?
                # stop after 3
                break
        # Now normalize group
        # Need to find date from first row col0
        date_str=str(group[0][0]).strip()
        try:
            norm_date=_parse_date_safe(date_str)
        except Exception as e:
            print(f"failed date parse at {i} col0={col0} err {e}")
            i+=len(group)
            continue
        # Collect particulars
        particulars_parts=[]
        ref_no=None
        trans_type=None
        debit=None
        credit=None
        balance=None
        for gidx, grow in enumerate(group):
            # col1 particulars
            p1=str(grow[1]).strip() if 1 in grow and str(grow[1]).strip().lower() not in ("","nan","-") else ""
            if p1:
                # skip if p1 is just date-like or header?
                if not _is_date_like(p1):
                    particulars_parts.append(p1)
            # Look for ref/transaction/debit/credit in each row
            # col2 ref, col3 trans type, col4 debit, col5 credit, col6 balance
            # Check each row for numeric debit/credit
            c2=str(grow[2]).strip() if 2 in grow else ""
            if c2.lower() not in ("","nan","-") and c2.strip() and "Page" not in c2:
                # ref no usually starts with S or numeric?
                if re.match(r"S\d+", c2) or c2.isdigit():
                    if not ref_no:
                        ref_no=c2
            c3=str(grow[3]).strip() if 3 in grow else ""
            if c3.lower() not in ("","nan","-") and "page" not in c3.lower():
                if c3.lower() in ("transfer","imps","neft","upi"):
                    trans_type=c3
                elif not trans_type:
                    # keep first non-empty
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

        description=" ".join(particulars_parts).strip()
        # clean duplicate spaces, remove NaN fragments
        description=re.sub(r"\s+"," ",description).strip()
        # Determine amount and transaction_type
        amount=None
        ttype=None
        if debit is not None and debit>0:
            amount=debit
            ttype="expense"
        elif credit is not None and credit>0:
            amount=credit
            ttype="income"
        else:
            # no amount -> skip? maybe summary row
            print(f"skip group at {i} no amount debit={debit} credit={credit} desc={description[:30]}")
            i+=len(group)
            continue
        # payment method
        pay="UPI" if "UPI/" in description or "upi" in description.lower() else "Bank Transfer"
        detected.append({
            "date": norm_date.isoformat(),
            "description": description,
            "debit": debit,
            "credit": credit,
            "amount": amount,
            "transaction_type": ttype,
            "payment_method": pay,
            "ref": ref_no,
            "balance": balance
        })
        # Advance
        # Need to advance i by number of rows in group plus any skipped page rows?
        # Our group length is number of rows consumed, but we skipped page rows via continue without adding to group, need to count them
        # For simplicity, advance by len(group) plus if we saw page at offset, we already continued, so we need to find actual consumed rows
        # Let's just advance by 1 and rely on loop? But we already grouped, so we need to skip those rows
        # Instead of complex, set i += len(group)
        # But if there was a page between, we didn't include it, but we still need to skip it next iteration will handle page skip
        # So len(group) is number of data rows, next i will be at next row after group, which may be page -> will be skipped
        # So do:
        # Find actual consumed: we looked at i+1,i+2, but we didn't handle page offset correctly for len
        # Let's just increment i by 1 and let next iteration detect date? That would cause double counting
        # We need to properly advance
        # For now, advance by len(group) if group was contiguous, but our group building with offset check for page may have gaps
        # Simpler: we built group by looking at i+1,i+2 directly, not skipping page offset correctly for indexing
        # Let's just advance i by len(group) if no page, else need to handle
        # Quick: compute next_i = i + len(group) ; but if there was a page row at i+1, our group may have taken i+2 as second row, so next_i should be i+3?
        # Let's instead just increment i by 1 and check if next row col0 is date-like -> but then grouping logic will treat continuation rows as not date-like and they'd be skipped as not transaction start?
        # Let's implement proper while with index pointer that handles page
        # For now use simple: i += len(group)  # may miss page but page will be handled as not date-like and skipped
        # For 3-row case, len=3, i jumps 3, next will be next date
        i+=len(group)
        # But need to handle case where group==1 (single row transaction like row22) -> i+=1 correct
        # For 2-row, i+=2
        # Let's do that
        # However our group building for 3 rows used i+1 and i+2, so len 3 means we consumed 3 rows
        # For case where i+1 was page, we skipped adding it but still i+2 is group[1], so len 2 but we consumed 3 physical rows (including page)
        # So our i increment would be 2, would land on page row again? Better to handle page explicitly
        # Let's just handle page before: if next row is page, we skip it by incrementing extra
        # For now, keep i as len(group) and also skip any immediate page rows next loop will skip anyway, so double skip not needed
        # We'll keep i+=len(group) and let next loop's page check skip
        # But for group that included page skip, we already skipped page not in group, so i+=2 would land on row after page? Actually if i=81 page, we would have skipped it via initial page check, not as group, so not in group
        # So for group starting at 82, no page, len 3, i becomes 85, next row is 85 which is date, good
        # For case where page is between transactions, e.g., after group at 78-80, next is page 81, our next i will be 81, page check will skip it
        pass
    else:
        # not date-like, skip metadata? For generic, header row contains "Date" but not date-like, so will be skipped until first date
        # But for metadata before header, also skipped
        # However for single-row transaction where col0 empty but col2 etc has data? No, transaction start always has date in col0
        # So just skip
        # But what about row20 where col0 empty but col1 empty col2 S97007464 - this row is already consumed as part of previous group, but if we advance by group len, we won't see it again
        # If we are here and col0 not date-like, it means we either already consumed it as continuation, or it's metadata that should be skipped
        # So just i+=1
        i+=1

print(f"detected {len(detected)}")
for d in detected[:5]:
    print(d)
print("--- last 5 ---")
for d in detected[-5:]:
    print(d)

# Check duplicates and sample
# Check date parsing
from collections import Counter
print(Counter([d['transaction_type'] for d in detected]))
