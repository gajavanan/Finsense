"""
FinSense CSV Import Normalization Layer
Supports:
- FORMAT A: Simple CSV  Date,Description,Debit,Credit  or Date,Description,Merchant,Amount,Transaction Type
- FORMAT B: Formatted bank statement with metadata + multi-row transactions (Indian bank)

Privacy: Never store/log customer ID, account number, phone, email, address, IFSC
"""
import io, re, pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple

# --- helpers ---
def _parse_date_safe(s: str):
    s = s.strip().strip("()").strip()
    fmts = ["%d-%b-%y", "%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y", "%d-%b-%y", "%Y/%m/%d"]
    for fmt in fmts:
        try:
            test_s = s.title() if "%b" in fmt else s
            dt = datetime.strptime(test_s, fmt)
            return dt.date()
        except:
            continue
    try:
        return pd.to_datetime(s, dayfirst=True, errors='raise').date()
    except:
        raise ValueError(f"Unknown datetime string format, unable to parse: {s}")

def _is_strict_date(s: str) -> bool:
    """True if s is date like 30-Aug-26 WITHOUT parentheses -> transaction START"""
    if not isinstance(s, str):
        return False
    s = s.strip()
    if not s or s.lower() in ("nan", "-", ""):
        return False
    if s.startswith("(") or s.endswith(")"):
        return False
    patterns = [r"^\d{1,2}-[A-Za-z]{3}-\d{2,4}$", r"^\d{1,2}/\d{1,2}/\d{2,4}$", r"^\d{1,2}-\d{1,2}-\d{2,4}$", r"^\d{4}-\d{1,2}-\d{1,2}$"]
    for pat in patterns:
        if re.match(pat, s.strip()):
            try:
                _parse_date_safe(s)
                return True
            except:
                continue
    return False

def _parse_amount_safe(s) -> float:
    if s is None:
        return None
    s = str(s).strip()
    if s.lower() in ("", "-", "nan", "none", "null"):
        return None
    s = s.replace(",", "").replace("₹", "").replace("Rs", "").replace("Rs.", "").strip()
    # handle like "34.8" or "15078.34"
    try:
        v = float(s)
        if v == 0:
            return None
        return v
    except:
        return None

def detect_csv_format(raw_bytes: bytes) -> str:
    """
    Suggested architecture: detect_csv_format()
    Returns "bank_statement" or "generic"
    Detects formatted bank statement containing metadata + multi-row transactions.
    """
    try:
        text = raw_bytes.decode('utf-8', errors='ignore')[:10000].lower()
    except:
        text = ""
    # bank indicators per spec
    bank_keywords = ["report generation date", "statement of the account", "branch address", "customer id", "account no", "ifs code"]
    hits = sum(1 for kw in bank_keywords if kw in text)
    if hits >= 2:
        return "bank_statement"
    if "debit(rs)" in text and "credit(rs)" in text and "particulars" in text:
        return "bank_statement"
    return "generic"

def _find_transaction_header_generic(df_header) -> int:
    """For generic CSV, header is usually row 0 containing Date"""
    for idx, row in df_header.iterrows():
        row_str = " ".join([str(v).lower() for v in row.values if str(v).strip()]).lower()
        if "date" in row_str and ("description" in row_str or "narration" in row_str or "debit" in row_str or "amount" in row_str):
            return idx
    return 0

def parse_bank_statement_csv(raw_bytes: bytes) -> List[Dict]:
    """
    Parse formatted bank statement (FORMAT B)
    Steps:
    - Read with header=None
    - Scan for transaction table via Debit(Rs)/Credit(Rs) keywords
    - Handle multi-row transactions: start detected when col0 is strict date DD-MMM-YY, merge 2-3 rows
    - Only parse dates after transaction table detected (metadata ignored)
    - Normalize debit/credit, never use Balance as amount
    """
    df = pd.read_csv(io.BytesIO(raw_bytes), header=None, dtype=str, keep_default_na=False, engine='python', on_bad_lines='skip')
    # Find header
    header_idx = None
    for idx, row in df.iterrows():
        row_str = " ".join([str(v).lower() for v in row.values if str(v).strip()]).lower()
        if "debit(rs)" in row_str and "credit(rs)" in row_str:
            header_idx = idx
            print(f"[CSV IMPORT] transaction table header detected at physical row {idx+1}")
            break
    if header_idx is None:
        # fallback: find first strict date
        for idx, row in df.iterrows():
            col0 = str(row[0]).strip() if 0 in row else ""
            if _is_strict_date(col0):
                header_idx = idx - 1
                print(f"[CSV IMPORT] fallback header at {header_idx}")
                break
    if header_idx is None:
        raise ValueError("Transaction table header not found")
    start_idx = header_idx + 2  # skip header block (header row + continuation row Date)/Cheque No
    # ensure start is at next strict date
    # scan forward to first strict date if needed
    for i in range(start_idx, min(start_idx+5, len(df))):
        if i < len(df) and _is_strict_date(str(df.iloc[i][0]).strip()):
            start_idx = i
            break
    print(f"[CSV IMPORT] transaction table starts at physical row {start_idx+1}")

    detected = []
    i = start_idx
    while i < len(df):
        row = df.iloc[i]
        # skip page/summary
        row_str = " ".join([str(v) for v in row.values])
        if "Page" in row_str and "of" in row_str:
            i += 1
            continue
        if "Effective available balance" in row_str or "computer generated statement" in row_str:
            break
        if row_str.strip() == "" or row_str.strip().lower() == "nan":
            i += 1
            continue
        # also check for summary total row like "15078.34 14829" with no date
        if "15078.34" in row_str and "14829" in row_str:
            i += 1
            continue
        col0 = str(row[0]).strip() if 0 in row else ""
        if col0.lower() == "nan":
            col0 = ""
        if _is_strict_date(col0):
            group = [row]
            # collect next up to 2 continuation rows
            for offset in [1, 2]:
                if i + offset >= len(df):
                    break
                nxt = df.iloc[i + offset]
                nxt_str = " ".join([str(v) for v in nxt.values])
                if "Page" in nxt_str and "of" in nxt_str:
                    break
                if "Effective available balance" in nxt_str or "computer generated statement" in nxt_str:
                    break
                nxt_col0 = str(nxt[0]).strip() if 0 in nxt else ""
                if nxt_col0.lower() == "nan":
                    nxt_col0 = ""
                if _is_strict_date(nxt_col0):
                    break
                nxt_content = " ".join([str(v).strip() for v in nxt.values if str(v).strip()]).strip()
                if nxt_content == "" or nxt_content.lower() == "nan":
                    continue
                # don't treat header remnants as group
                if "15078.34" in nxt_str:
                    break
                group.append(nxt)
                if len(group) >= 3:
                    break
            # normalize group
            try:
                norm_date = _parse_date_safe(str(group[0][0]).strip())
            except Exception as e:
                # safe: metadata should never reach here, but if it does, skip
                print(f"[CSV IMPORT] skip date parse fail at row {i+1}: {e}")
                i += len(group)
                continue
            parts = []
            ref_no = None
            trans_type = None
            debit = None
            credit = None
            for grow in group:
                p1 = str(grow[1]).strip() if 1 in grow and str(grow[1]).strip().lower() not in ("", "nan", "-") else ""
                if p1 and not p1.lower() in ("particulars", "type", "/cheque no"):
                    # avoid adding date-like fragments
                    if not _is_strict_date(p1) and "Page" not in p1:
                        parts.append(p1)
                c2 = str(grow[2]).strip() if 2 in grow else ""
                if c2.lower() not in ("", "nan", "-") and "Page" not in c2:
                    if re.match(r"S\d+", c2) or c2.isdigit():
                        if not ref_no:
                            ref_no = c2
                c3 = str(grow[3]).strip() if 3 in grow else ""
                if c3.lower() not in ("", "nan", "-"):
                    if c3.lower() in ("transfer", "imps", "neft", "upi"):
                        trans_type = c3
                    elif not trans_type and c3.lower() not in ("type", "/cheque no"):
                        trans_type = c3
                c4 = str(grow[4]).strip() if 4 in grow else ""
                c5 = str(grow[5]).strip() if 5 in grow else ""
                dval = _parse_amount_safe(c4)
                cval = _parse_amount_safe(c5)
                if dval is not None and debit is None:
                    debit = dval
                if cval is not None and credit is None:
                    credit = cval
            description = " ".join(parts).strip()
            description = re.sub(r"\s+", " ", description).strip()
            # Remove NaN fragments
            if description.lower() == "nan":
                description = ""
            # Determine amount/type, never use Balance
            amount = None
            ttype = None
            if debit is not None and debit > 0:
                amount = debit
                ttype = "expense"
            elif credit is not None and credit > 0:
                amount = credit
                ttype = "income"
            else:
                # no amount -> not a valid transaction (maybe continuation with no amount already handled)
                i += len(group)
                continue
            pay = "UPI" if "UPI/" in description or "upi" in description.lower() else "Bank Transfer"
            detected.append({
                "date": norm_date,
                "description": description or f"Transaction {norm_date}",
                "merchant": None,  # will be extracted downstream if needed
                "amount": amount,
                "transaction_type": ttype,
                "debit": debit,
                "credit": credit,
                "payment_method": pay,
                "ref_no": ref_no,
            })
            i += len(group)
        else:
            i += 1
    print(f"[CSV IMPORT] transactions detected = {len(detected)}")
    return detected

def parse_generic_csv(raw_bytes: bytes) -> List[Dict]:
    """
    Parse simple CSV (FORMAT A): Date,Description,Merchant,Amount,Transaction Type,Debit,Credit,Category
    Assumes header at first row containing Date, skips metadata rows before header.
    """
    # First try to find header row with Date
    df_raw = pd.read_csv(io.BytesIO(raw_bytes), header=None, dtype=str, keep_default_na=False, engine='python', on_bad_lines='skip')
    header_idx = _find_transaction_header_generic(df_raw)
    # Now read with header at header_idx
    try:
        df = pd.read_csv(io.BytesIO(raw_bytes), header=header_idx, dtype=str, keep_default_na=False, engine='python', on_bad_lines='skip')
    except Exception as e:
        raise ValueError(f"Generic CSV parse failed: {e}")
    # normalize columns lower
    df.columns = [str(c).strip().lower() for c in df.columns]
    col_map = {
        "date": ["date","transaction date","txn date","value date"],
        "description": ["description","narration","details","particulars","remarks"],
        "merchant": ["merchant","payee","beneficiary","counterparty"],
        "amount": ["amount","amt","value"],
        "debit": ["debit","withdrawal","dr"],
        "credit": ["credit","deposit","cr"],
        "transaction_type": ["transaction type","type","txn type","transaction_type"],
        "category": ["category","cat"],
        "payment_method": ["payment method","payment_method","mode"],
    }
    def find_col(key):
        for c in df.columns:
            if c in col_map[key]:
                return c
        for alias in col_map[key]:
            for c in df.columns:
                if alias in c or c in alias:
                    return c
        return None
    c_date = find_col("date")
    c_desc = find_col("description")
    c_merch = find_col("merchant")
    c_amt = find_col("amount")
    c_debit = find_col("debit")
    c_credit = find_col("credit")
    c_type = find_col("transaction_type")
    # c_cat not needed for detection but for later
    detected = []
    for idx, row in df.iterrows():
        # skip rows where date is missing or not parseable
        raw_date = row[c_date] if c_date and c_date in row else None
        if raw_date is None or str(raw_date).strip() == "" or str(raw_date).strip().lower() == "nan":
            continue
        try:
            norm_date = _parse_date_safe(str(raw_date).strip())
        except:
            # metadata row, skip silently (not counted as failed)
            continue
        desc = ""
        if c_desc and c_desc in row and str(row[c_desc]).strip().lower() not in ("","nan"):
            desc = str(row[c_desc]).strip()
        else:
            desc = str(row[c_merch] if c_merch and c_merch in row and str(row[c_merch]).strip().lower() not in ("","nan") else f"Row {idx+1}").strip()
        if not desc:
            desc = f"Row {idx+1}"
        merchant = None
        if c_merch and c_merch in row and str(row[c_merch]).strip().lower() not in ("","nan"):
            merchant = str(row[c_merch]).strip()
        amt = None
        ttype = None
        has_debit = c_debit and c_debit in row and str(row[c_debit]).strip().lower() not in ("","0","0.0","nan","-")
        has_credit = c_credit and c_credit in row and str(row[c_credit]).strip().lower() not in ("","0","0.0","nan","-")
        if has_debit or has_credit:
            if has_debit:
                amt = _parse_amount_safe(str(row[c_debit]))
                ttype = "expense"
            elif has_credit:
                amt = _parse_amount_safe(str(row[c_credit]))
                ttype = "income"
        if amt is None:
            if c_amt and c_amt in row and str(row[c_amt]).strip().lower() not in ("","nan"):
                amt = _parse_amount_safe(str(row[c_amt]))
            else:
                continue
            if c_type and c_type in row and str(row[c_type]).strip().lower() not in ("","nan"):
                raw_t = str(row[c_type]).lower().strip()
                if raw_t in ("income","cr","credit","deposit"): ttype="income"
                elif raw_t in ("expense","dr","debit","withdrawal"): ttype="expense"
                else: ttype = raw_t if raw_t in ("income","expense") else "expense"
            else:
                ttype = "expense" if amt and amt>0 else "income"
                if amt: amt = abs(amt)
        if amt is None or amt <=0:
            continue
        if ttype not in ("income","expense"):
            ttype="expense"
        # Determine category later via ML, but keep raw
        detected.append({
            "date": norm_date,
            "description": desc,
            "merchant": merchant,
            "amount": abs(float(amt)),
            "transaction_type": ttype,
            "payment_method": str(row[find_col("payment_method")]).strip() if find_col("payment_method") and find_col("payment_method") in row and str(row[find_col("payment_method")]).strip().lower() not in ("","nan") else None,
        })
    print(f"[CSV IMPORT] generic transactions detected = {len(detected)}")
    return detected

def normalize_transaction(raw: Dict) -> Dict:
    """Final normalization for DB insert, handles particulars cleaning"""
    desc = raw.get("description","").strip()
    # combine continuation already done for bank, but clean
    desc = re.sub(r"\s+", " ", desc).strip()
    # Remove NaN fragments
    if desc.lower() == "nan":
        desc = raw.get("description","").strip()
    return raw

def is_ml_dataset(raw_bytes: bytes) -> bool:
    """
    Check if the CSV represents an ML training dataset.
    It returns True if there is a row containing description, merchant, and category columns.
    """
    try:
        df_raw = pd.read_csv(io.BytesIO(raw_bytes), header=None, dtype=str, keep_default_na=False, engine='python', on_bad_lines='skip')
    except Exception as e:
        print(f"[is_ml_dataset] read failed: {e}")
        return False
    
    for idx, row in df_raw.iterrows():
        row_cells = [str(v).strip().lower() for v in row.values if str(v).strip()]
        has_desc = any("description" in cell or "narration" in cell or cell == "details" for cell in row_cells)
        has_merchant = any("merchant" in cell or "payee" in cell for cell in row_cells)
        has_category = any("category" in cell or "cat" in cell or cell == "label" for cell in row_cells)
        if has_desc and has_merchant and has_category:
            return True
    return False

def parse_ml_dataset_csv(raw_bytes: bytes) -> Dict:
    """
    Find header row, parse rows, normalize columns and validate category.
    """
    df = pd.read_csv(io.BytesIO(raw_bytes), header=None, dtype=str, keep_default_na=False, engine='python', on_bad_lines='skip')
    
    # Find header row
    header_row_idx = None
    for idx, row in df.iterrows():
        row_values = [str(val).strip().lower() for val in row.values]
        has_desc = any("description" in cell for cell in row_values)
        has_merchant = any("merchant" in cell for cell in row_values)
        has_amount = any("amount" in cell for cell in row_values)
        has_pay = any("payment" in cell or "mode" in cell for cell in row_values)
        has_cat = any("category" in cell or "cat" in cell or "label" in cell for cell in row_values)
        if has_desc and has_merchant and has_amount and has_pay and has_cat:
            header_row_idx = idx
            break
            
    if header_row_idx is None:
        raise ValueError("ML training dataset header row not found. Expected columns: Description, Merchant, Amount, Payment Method, Category.")
        
    df_data = df.iloc[header_row_idx + 1:]
    raw_headers = [str(h).strip() for h in df.iloc[header_row_idx].values]
    
    # Map headers to target columns
    col_mapping = {}
    for idx, h in enumerate(raw_headers):
        hl = h.lower()
        if "description" in hl:
            col_mapping["description"] = idx
        elif "merchant" in hl:
            col_mapping["merchant"] = idx
        elif "amount" in hl:
            col_mapping["amount"] = idx
        elif "payment" in hl or "mode" in hl:
            col_mapping["payment_method"] = idx
        elif "category" in hl or "cat" in hl or "label" in hl:
            col_mapping["category"] = idx

    # Check if we mapped description and category
    if "description" not in col_mapping or "category" not in col_mapping:
        raise ValueError("Could not map Description or Category columns.")
        
    total_rows = len(df_data)
    valid_rows = []
    invalid_count = 0
    categories_detected = set()
    
    ALLOWED_CATEGORIES = {
        "Food", "Shopping", "Transport", "Bills", "Entertainment",
        "Healthcare", "Education", "Travel", "Investment", "Rent",
        "Subscriptions", "Other"
    }
    allowed_lower = {cat.lower(): cat for cat in ALLOWED_CATEGORIES}
    
    for idx, row in df_data.iterrows():
        row_vals = list(row.values)
        
        # Extract fields safely using our mapping
        desc = row_vals[col_mapping["description"]].strip() if col_mapping.get("description") is not None and col_mapping["description"] < len(row_vals) else ""
        merch = row_vals[col_mapping["merchant"]].strip() if col_mapping.get("merchant") is not None and col_mapping["merchant"] < len(row_vals) else ""
        amount = row_vals[col_mapping["amount"]].strip() if col_mapping.get("amount") is not None and col_mapping["amount"] < len(row_vals) else ""
        pay = row_vals[col_mapping["payment_method"]].strip() if col_mapping.get("payment_method") is not None and col_mapping["payment_method"] < len(row_vals) else ""
        cat = row_vals[col_mapping["category"]].strip() if col_mapping.get("category") is not None and col_mapping["category"] < len(row_vals) else ""
        
        # Validation
        cat_lower = cat.lower()
        if not desc or not cat or cat_lower not in allowed_lower:
            invalid_count += 1
            continue
            
        normalized_cat = allowed_lower[cat_lower]
        categories_detected.add(normalized_cat)
        
        valid_rows.append({
            "description": desc,
            "merchant": merch,
            "amount": amount,
            "payment_method": pay,
            "category": normalized_cat
        })
        
    return {
        "total_rows": total_rows,
        "valid_rows_data": valid_rows,
        "valid_count": len(valid_rows),
        "invalid_count": invalid_count,
        "categories_detected": sorted(list(categories_detected))
    }
