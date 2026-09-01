import re

KNOWN_BANK_CODES = {
    "YES", "CNR", "SBI", "ICICI", "HDFC", "AXIS", "KKBK", "BARB", "PUNB", 
    "IOBA", "UBIN", "UTIB", "PAYTM", "OKAXIS", "OKSBI", "OKHDFC", "OKICICI",
    "INDUS", "FEDERAL", "IDBI", "KOTAK", "PNB", "BOB", "CANARA", "UNION"
}

NON_MERCHANT_TOKENS = {
    "DR", "CR", "UPI", "REV", "RET", "P2P", "P2M", "NA", "XX", "XXX", "INB",
    "MOB", "MB", "TP", "IMPS", "NEFT", "RTGS", "POS", "ECOM", "ATM", "BIL"
}

def clean_text(s: str) -> str:
    if not s:
        return ""
    s = str(s).lower()
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def extract_merchant(description: str) -> str:
    """
    Extract the clean merchant / entity name from real bank/UPI descriptions.
    Examples:
      - UPI/660703068070/DR/DITTO COPIERS/YES/UPI -> DITTO COPIERS
      - UPI/624267626353/DR/Sathya Priya S/YES/UPI -> Sathya Priya S
      - UPI/658765476020/CR/DEVADARSAN/CNR/UPI -> DEVADARSAN
      - POS 1234567 SWIGGY BANGALORE -> SWIGGY BANGALORE
      - Swiggy food order -> Swiggy food order
    """
    if not description:
        return ""
    desc = str(description).strip()
    
    # 1. Handle UPI slash-delimited descriptions
    if "UPI" in desc.upper() and "/" in desc:
        parts = [p.strip() for p in desc.split("/") if p.strip()]
        candidates = []
        for p in parts:
            p_upper = p.upper()
            if p_upper in NON_MERCHANT_TOKENS:
                continue
            if p_upper in KNOWN_BANK_CODES:
                continue
            # Filter pure numeric reference numbers (e.g. 660703068070)
            if re.match(r'^\d+$', p):
                continue
            # Filter short alphanumeric reference codes like S1234567 or R123
            if re.match(r'^[A-Za-z]\d{5,}$', p) or re.match(r'^\d{4,}[A-Za-z0-9]*$', p):
                continue
            candidates.append(p)
        if candidates:
            # First clean non-reference candidate is the merchant/entity
            merchant = candidates[0]
            # Clean any trailing punctuation
            merchant = re.sub(r'\s+', ' ', merchant).strip()
            return merchant

    # 2. Handle POS / ECOM formats
    pos_match = re.search(r'(?:POS|ECOM|E-COM)\s+(?:\d+\s+)?([A-Za-z0-9\s\.\&\-]+)', desc, re.IGNORECASE)
    if pos_match:
        m = pos_match.group(1).strip()
        # Clean trailing location/city/codes if needed
        return re.sub(r'\s+', ' ', m)

    # 3. Handle NEFT / IMPS formats: IMPS-123456-MERCHANT-BANK
    imps_match = re.search(r'(?:IMPS|NEFT)[-\s/]+(?:\d+)[-\s/]+([A-Za-z0-9\s\.\&\-]+)', desc, re.IGNORECASE)
    if imps_match:
        m = imps_match.group(1).strip()
        return re.sub(r'\s+', ' ', m)

    return desc

def preprocess_bank_description(description: str) -> dict:
    """
    Normalize raw bank transaction descriptions by stripping UPI reference numbers,
    DR/CR direction, bank codes, and extra slashes.
    """
    if not description:
        return {"merchant": "", "clean_text": "", "payment_method": "", "direction": ""}

    raw = str(description).strip()
    is_upi = "UPI" in raw.upper()
    payment_method = "UPI" if is_upi else ""

    direction = ""
    if "/DR/" in raw.upper() or raw.upper().startswith("DR/"):
        direction = "DR"
    elif "/CR/" in raw.upper() or raw.upper().startswith("CR/"):
        direction = "CR"

    merchant = extract_merchant(raw)

    # Clean description for ML:
    # If merchant was extracted and is distinct from noisy raw text, use it as primary text
    if is_upi and merchant and merchant != raw:
        clean_desc = clean_text(merchant)
    else:
        # Strip long numeric tokens (ref numbers)
        cleaned = re.sub(r'\b\d{6,}\b', ' ', raw)
        # Strip UPI/DR/CR noise words
        tokens = [t for t in cleaned.split('/') if t.strip()]
        filtered_tokens = []
        for t in tokens:
            t_clean = t.strip()
            if t_clean.upper() not in NON_MERCHANT_TOKENS and t_clean.upper() not in KNOWN_BANK_CODES:
                filtered_tokens.append(t_clean)
        clean_desc = clean_text(" ".join(filtered_tokens))
        if not clean_desc:
            clean_desc = clean_text(raw)

    return {
        "merchant": merchant,
        "clean_text": clean_desc,
        "payment_method": payment_method,
        "direction": direction
    }

def combine_features(description: str, merchant: str = None, payment_method: str = None) -> str:
    """
    Produce clean, normalized input text for the TF-IDF vectorizer and ML model.
    Omits generic payment tokens (e.g. 'upi') to avoid noisy feature matches.
    """
    preprocessed = preprocess_bank_description(description)
    final_desc = preprocessed["clean_text"] or clean_text(description)
    final_merchant = clean_text(merchant or preprocessed["merchant"] or "")

    parts = []
    if final_desc:
        parts.append(final_desc)
    if final_merchant and final_merchant != final_desc:
        parts.append(final_merchant)

    return " ".join(parts).strip()

