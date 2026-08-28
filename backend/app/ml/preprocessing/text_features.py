import re

def clean_text(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def combine_features(description, merchant, payment_method):
    parts = [clean_text(description), clean_text(merchant or ""), clean_text(payment_method or "")]
    return " ".join([p for p in parts if p])
