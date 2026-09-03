"""
FinSense CSV Import Normalization Layer
Supports:
- FORMAT A: Simple CSV  Date,Description,Debit,Credit  or Date,Description,Merchant,Amount,Transaction Type
- FORMAT B: Formatted bank statement with metadata + multi-row transactions (Indian bank)

Privacy: Never store/log customer ID, account number, phone, email, address, IFSC
"""
import io, re, pandas as pd
from datetime import datetime
import math
from typing import List, Dict, Tuple, Optional, Any, Set

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

# ==============================================================================
# ML Training Dataset Normalization, Alias Mapping & Parsing
# ==============================================================================

ML_COLUMN_ALIASES: Dict[str, List[str]] = {
    "description": [
        "description",
        "transaction description",
        "transaction_description",
        "narration",
        "details",
        "transaction details",
        "transaction_details",
        "remarks",
        "remark",
        "particulars",
        "purpose",
        "note",
        "notes",
        "transaction note",
        "transaction type",
        "transaction_type",
        "type",
        "txn type",
    ],
    "merchant": [
        "merchant",
        "merchant name",
        "merchant_name",
        "payee",
        "payee name",
        "payee_name",
        "receiver",
        "receiver name",
        "receiver_name",
        "receiver bank",
        "receiver_bank",
        "beneficiary",
        "beneficiary name",
        "vendor",
        "vendor name",
        "store",
        "store name",
        "party",
        "party name",
    ],
    "amount": [
        "amount",
        "amount inr",
        "amount (inr)",
        "amount_inr",
        "transaction amount",
        "transaction_amount",
        "txn amount",
        "total amount",
        "debit",
        "debit amount",
        "inr",
    ],
    "payment_method": [
        "payment method",
        "payment_method",
        "paymentmethod",
        "mode",
        "payment mode",
        "payment_mode",
        "payment type",
        "payment_type",
        "txn mode",
        "device type",
        "device_type",
        "method",
        "channel",
        "payment channel",
        "network type",
        "network_type",
    ],
    "category": [
        "category",
        "transaction category",
        "transaction_category",
        "merchant category",
        "merchant_category",
        "expense category",
        "expense_category",
        "cat",
        "label",
        "classification",
        "tag",
    ],
}

ML_CANONICAL_NAMES: Dict[str, str] = {
    "description": "Description",
    "merchant": "Merchant",
    "amount": "Amount",
    "payment_method": "Payment Method",
    "category": "Category",
}

CATEGORY_SYNONYMS: Dict[str, str] = {
    "utilities": "Bills",
    "utility": "Bills",
    "bill": "Bills",
    "bills": "Bills",
    "grocery": "Food",
    "groceries": "Food",
    "fuel": "Transport",
    "petrol": "Transport",
    "diesel": "Transport",
    "dining": "Food",
    "restaurant": "Food",
    "restaurants": "Food",
    "e-commerce": "Shopping",
    "ecommerce": "Shopping",
    "medical": "Healthcare",
    "medicine": "Healthcare",
    "pharma": "Healthcare",
    "pharmacy": "Healthcare",
}

ALLOWED_CATEGORIES: Set[str] = {
    "Food", "Shopping", "Transport", "Bills", "Entertainment",
    "Healthcare", "Education", "Travel", "Investment", "Rent",
    "Subscriptions", "Other"
}


def normalize_header_name(header: Any) -> str:
    """
    Normalizes a CSV header string for robust alias matching:
    - Strips leading/trailing whitespace
    - Removes UTF-8 BOM (\ufeff)
    - Converts to lowercase
    - Replaces underscores with spaces
    - Collapses repeated whitespace
    """
    if header is None:
        return ""
    h = str(header).strip().lstrip("\ufeff").lower()
    h = h.replace("_", " ")
    h = re.sub(r"\s+", " ", h)
    return h.strip()


def match_ml_columns(headers: List[str]) -> Tuple[Dict[str, int], List[str]]:
    """
    Given a list of column headers from a CSV row or df.columns,
    maps each of the 5 required fields ('description', 'merchant', 'amount', 'payment_method', 'category')
    to a unique column index using ML_COLUMN_ALIASES.

    Returns:
        (col_mapping, missing_canonical_names)
        e.g. ({"description": 0, "merchant": 1, ...}, [])
    """
    normalized_headers = [normalize_header_name(h) for h in headers]
    # Punctuation-stripped version (e.g. "amount inr" from "amount (inr)")
    cleaned_headers = [re.sub(r'[\(\)\[\]\{\}]', '', nh).strip() for nh in normalized_headers]

    col_mapping: Dict[str, int] = {}
    used_indices: Set[int] = set()

    # Prioritize specific targets first so compound names like 'merchant_category'
    # match 'category' rather than generic 'merchant'
    target_priority = ["category", "amount", "merchant", "description", "payment_method"]

    for target in target_priority:
        aliases = ML_COLUMN_ALIASES[target]
        matched_idx = None

        # Pass 1: Exact normalized alias match
        for alias in aliases:
            norm_alias = normalize_header_name(alias)
            clean_alias = re.sub(r'[\(\)\[\]\{\}]', '', norm_alias).strip()
            for idx, (nh, ch) in enumerate(zip(normalized_headers, cleaned_headers)):
                if idx in used_indices:
                    continue
                if nh == norm_alias or ch == clean_alias or nh == clean_alias:
                    matched_idx = idx
                    break
            if matched_idx is not None:
                break

        # Pass 2: Substring / token match for multi-character aliases if no exact match
        if matched_idx is None:
            for alias in aliases:
                norm_alias = normalize_header_name(alias)
                if len(norm_alias) < 4:
                    continue
                for idx, nh in enumerate(normalized_headers):
                    if idx in used_indices:
                        continue
                    if re.search(r'\b' + re.escape(norm_alias) + r'\b', nh):
                        matched_idx = idx
                        break
                if matched_idx is not None:
                    break

        if matched_idx is not None:
            col_mapping[target] = matched_idx
            used_indices.add(matched_idx)

    missing_targets = [
        ML_CANONICAL_NAMES[target]
        for target in ["description", "merchant", "amount", "payment_method", "category"]
        if target not in col_mapping
    ]

    return col_mapping, missing_targets


def load_ml_dataframe(raw_bytes: bytes) -> pd.DataFrame:
    """
    Loads raw CSV bytes into a pandas DataFrame:
    - Tries utf-8-sig (for UTF-8 with BOM), utf-8, and latin1
    - Skips introductory metadata lines before the delimited table
    - Automatically detects delimiters (, ; \t)
    """
    encodings = ["utf-8-sig", "utf-8", "latin1"]
    last_exc = None

    for enc in encodings:
        try:
            text = raw_bytes.decode(enc)
            lines = text.splitlines()
            if not lines:
                continue

            # Scan up to the first 15 lines to locate where the tabular data begins
            start_line_idx = 0
            for idx, line in enumerate(lines[:15]):
                line_str = line.strip()
                if not line_str:
                    continue
                found_start = False
                for delim in [",", ";", "\t"]:
                    parts = [p.strip() for p in line_str.split(delim)]
                    if len(parts) >= 2:
                        mapping, _ = match_ml_columns(parts)
                        if len(mapping) >= 3 or len(parts) >= 4:
                            start_line_idx = idx
                            found_start = True
                            break
                if found_start:
                    break

            tabular_text = "\n".join(lines[start_line_idx:])

            # Try python engine automatic delimiter detection
            try:
                df = pd.read_csv(
                    io.StringIO(tabular_text),
                    sep=None,
                    engine="python",
                    dtype=str,
                    keep_default_na=False,
                    on_bad_lines="skip"
                )
                if df.shape[1] >= 2:
                    return df
            except Exception:
                pass

            # Fallback to standard delimiters
            for sep in [",", ";", "\t"]:
                try:
                    df = pd.read_csv(
                        io.StringIO(tabular_text),
                        sep=sep,
                        dtype=str,
                        keep_default_na=False,
                        on_bad_lines="skip"
                    )
                    if df.shape[1] >= 2:
                        return df
                except Exception:
                    continue
        except UnicodeDecodeError as ude:
            last_exc = ude
            continue

    # Final fallback directly with BytesIO
    try:
        return pd.read_csv(io.BytesIO(raw_bytes), dtype=str, keep_default_na=False, engine="python", on_bad_lines="skip")
    except Exception as e:
        raise ValueError(f"Failed to read CSV: {last_exc or e}")


def clean_amount_str(val: Any) -> Optional[str]:
    """
    Cleans and validates an amount value:
    - Removes currency symbols (₹, $, Rs., Rs, INR)
    - Removes commas and whitespace
    - Converts to numeric float
    - Returns formatted string e.g. "1250.50" or None if invalid
    """
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() == "nan":
        return None
    # Remove currency symbols and commas
    s = re.sub(r'[₹\$,]', '', s)
    s = re.sub(r'^(rs\.?|inr)\s*', '', s, flags=re.IGNORECASE).strip()
    s = re.sub(r'\s*(rs\.?|inr)$', '', s, flags=re.IGNORECASE).strip()
    try:
        num = float(s)
        if math.isnan(num) or math.isinf(num) or num <= 0:
            return None
        return f"{num:.2f}"
    except (ValueError, TypeError):
        return None


def is_ml_dataset(raw_bytes: bytes) -> bool:
    """
    Check if the CSV represents an ML training dataset.
    Returns True if at least Category and either Description or Merchant are detected.
    """
    try:
        df = load_ml_dataframe(raw_bytes)
        if df.empty:
            return False
        col_mapping, _ = match_ml_columns([str(c) for c in df.columns])
        if "category" in col_mapping and ("description" in col_mapping or "merchant" in col_mapping):
            return True
        for r_idx in range(min(5, len(df))):
            row_mapping, _ = match_ml_columns([str(v) for v in df.iloc[r_idx].values])
            if "category" in row_mapping and ("description" in row_mapping or "merchant" in row_mapping):
                return True
    except Exception as e:
        print(f"[is_ml_dataset] check error: {e}")
    return False


def parse_ml_dataset_csv(raw_bytes: bytes) -> Dict:
    """
    Find header row, parse rows, normalize columns, validate and clean data for ML training.
    Supports flexible column aliases, extra columns, encoding/delimiter detection,
    amount normalization, and category standardization.
    """
    df = load_ml_dataframe(raw_bytes)
    if df.empty:
        raise ValueError("The uploaded CSV file is empty.")

    # 1. Check df.columns first
    raw_headers = [str(c) for c in df.columns]
    col_mapping, missing = match_ml_columns(raw_headers)

    df_data = df
    if not missing:
        df_data = df
    else:
        # 2. Check introductory rows for a valid header row
        scan_limit = min(10, len(df))
        for r_idx in range(scan_limit):
            candidate_headers = [str(val) for val in df.iloc[r_idx].values]
            candidate_mapping, candidate_missing = match_ml_columns(candidate_headers)
            if not candidate_missing:
                col_mapping = candidate_mapping
                missing = []
                df_data = df.iloc[r_idx + 1:].reset_index(drop=True)
                raw_headers = candidate_headers
                break
            if len(candidate_missing) < len(missing):
                missing = candidate_missing

    if missing:
        missing_str = ", ".join(missing)
        raise ValueError(f"Missing required ML column: {missing_str}")

    total_rows = len(df_data)
    valid_rows = []
    invalid_count = 0
    categories_detected = set()

    allowed_lower = {cat.lower(): cat for cat in ALLOWED_CATEGORIES}

    desc_idx = col_mapping["description"]
    merch_idx = col_mapping["merchant"]
    amt_idx = col_mapping["amount"]
    pay_idx = col_mapping["payment_method"]
    cat_idx = col_mapping["category"]

    for _, row in df_data.iterrows():
        row_vals = list(row.values)

        desc_raw = row_vals[desc_idx] if desc_idx < len(row_vals) else ""
        merch_raw = row_vals[merch_idx] if merch_idx < len(row_vals) else ""
        amt_raw = row_vals[amt_idx] if amt_idx < len(row_vals) else ""
        pay_raw = row_vals[pay_idx] if pay_idx < len(row_vals) else ""
        cat_raw = row_vals[cat_idx] if cat_idx < len(row_vals) else ""

        # 1. Amount cleaning & validation
        clean_amt = clean_amount_str(amt_raw)
        if clean_amt is None:
            invalid_count += 1
            continue

        # 2. Category cleaning & validation (supervised ML target)
        cat_clean = str(cat_raw or "").strip()
        if not cat_clean or cat_clean.lower() == "nan":
            invalid_count += 1
            continue

        cat_lower = cat_clean.lower()
        if cat_lower in CATEGORY_SYNONYMS:
            normalized_cat = CATEGORY_SYNONYMS[cat_lower]
        elif cat_lower in allowed_lower:
            normalized_cat = allowed_lower[cat_lower]
        else:
            normalized_cat = cat_clean.title()

        categories_detected.add(normalized_cat)

        # 3. Description & Merchant cleaning
        desc_clean = str(desc_raw or "").strip()
        merch_clean = str(merch_raw or "").strip()
        pay_clean = str(pay_raw or "").strip()

        if desc_clean.lower() == "nan":
            desc_clean = ""
        if merch_clean.lower() == "nan":
            merch_clean = ""
        if pay_clean.lower() == "nan":
            pay_clean = ""

        # Ensure at least description or merchant has text
        if not desc_clean:
            if merch_clean:
                desc_clean = merch_clean
            elif pay_clean:
                desc_clean = f"Payment via {pay_clean}"
            else:
                invalid_count += 1
                continue

        if not pay_clean:
            pay_clean = "UPI"

        valid_rows.append({
            "description": desc_clean,
            "merchant": merch_clean,
            "amount": clean_amt,
            "payment_method": pay_clean,
            "category": normalized_cat
        })

    return {
        "total_rows": total_rows,
        "valid_rows_data": valid_rows,
        "valid_count": len(valid_rows),
        "invalid_count": invalid_count,
        "categories_detected": sorted(list(categories_detected))
    }

