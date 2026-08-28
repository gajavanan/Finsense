import httpx
from app.core.config import settings
from sqlalchemy.orm import Session

SYSTEM_PROMPT = """You are FinSense AI, a helpful personal finance advisor.
You provide educational, informational insights based on the user's actual financial data provided in context.
Never invent numbers. If data is insufficient, say so. Always label predictions as estimates.
Do not claim professional financial advice. Be concise and helpful.
"""

async def get_user_financial_context(user_id: str, db: Session):
    try:
        from app.models import Transaction, Budget, Goal
        txs = db.query(Transaction).filter(Transaction.user_id==user_id).order_by(Transaction.date.desc()).limit(30).all()
        budgets = db.query(Budget).filter(Budget.user_id==user_id).all()
        goals = db.query(Goal).filter(Goal.user_id==user_id).all()
        total_exp = sum(float(t.amount) for t in txs if t.type=="expense")
        total_inc = sum(float(t.amount) for t in txs if t.type=="income")
        ctx = f"Recent transactions: {len(txs)} found. Total income (sample): {total_inc:.2f}, Total expense (sample): {total_exp:.2f}. Budgets: {len(budgets)} budgets. Goals: {len(goals)} goals."
        if txs:
            ctx += " Examples: " + "; ".join([f"{t.description} {t.category} {t.amount}" for t in txs[:5]])
        return ctx
    except Exception as e:
        return f"Context fetch error: {e}"

async def chat_with_advisor(user_id: str, message: str, history: list = None, db: Session = None):
    context = await get_user_financial_context(user_id, db) if db is not None else "No database."
    provider = settings.AI_PROVIDER.lower()
    prompt = f"User financial context:\n{context}\n\nUser question: {message}"
    if provider == "openai" and settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "dummy":
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post("https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type":"application/json"},
                    json={"model": settings.AI_MODEL, "messages":[{"role":"system","content": SYSTEM_PROMPT},{"role":"user","content": prompt}], "temperature":0.7})
                if r.status_code == 200:
                    data=r.json()
                    return {"response": data["choices"][0]["message"]["content"], "provider": "openai", "fallback": False}
        except Exception as e:
            print(f"OpenAI error {e}")
    if provider == "groq" and settings.GROQ_API_KEY and settings.GROQ_API_KEY != "dummy":
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type":"application/json"},
                    json={"model": settings.AI_MODEL, "messages":[{"role":"system","content": SYSTEM_PROMPT},{"role":"user","content": prompt}], "temperature":0.7})
                if r.status_code == 200:
                    data=r.json()
                    return {"response": data["choices"][0]["message"]["content"], "provider": "groq", "fallback": False}
        except Exception as e:
            print(f"Groq error {e}")
    fallback_response = rule_based_response(message, context)
    return {"response": fallback_response, "provider": "rule-based", "fallback": True, "note": "AI provider unavailable, using rule-based fallback."}

def rule_based_response(message: str, context: str):
    m = message.lower()
    if "food" in m:
        return f"Based on your data: {context}\n\nFor food spending, review your recent transactions in the Transactions page and check your Food budget usage. Consider setting a monthly Food budget if not already set."
    if "budget" in m:
        return f"Your context: {context}\n\nTo manage budgets, go to Budgets and review category spending. Aim to keep each category under 100%."
    if "save" in m or "saving" in m:
        return f"Context: {context}\n\nSavings tip: track income vs expense, maintain 20% savings rate, build emergency fund of 3-6 months expenses."
    if "invest" in m:
        return f"Context: {context}\n\nInvestment guidance (educational): diversify across asset types, understand risk, and align with goals. This is not professional advice."
    return f"Context: {context}\n\nI don't have live AI access right now, but based on your data: review Dashboard, Transactions, and Budgets for insights. Ask about food, budget, savings, or investments for tailored tips. (Rule-based fallback)"
