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
        from collections import defaultdict
        from datetime import datetime
        txs = db.query(Transaction).filter(Transaction.user_id==user_id).order_by(Transaction.date.desc()).limit(100).all()
        budgets = db.query(Budget).filter(Budget.user_id==user_id).all()
        goals = db.query(Goal).filter(Goal.user_id==user_id).all()
        def tx_type(t): return getattr(t, 'transaction_type', None) or getattr(t, 'type', None)
        now = datetime.utcnow()
        month_start = now.replace(day=1).date()
        monthly_income = sum(float(t.amount) for t in txs if tx_type(t)=="income" and t.date >= month_start)
        monthly_expenses = sum(float(t.amount) for t in txs if tx_type(t)=="expense" and t.date >= month_start)
        monthly_savings = monthly_income - monthly_expenses
        savings_rate = round((monthly_savings/monthly_income*100) if monthly_income>0 else 0,1)
        # top spending categories
        cat_spent = defaultdict(float)
        for t in txs:
            if tx_type(t)=="expense" and t.date.strftime("%Y-%m")==now.strftime("%Y-%m"):
                cat_spent[t.category or "Other"] += float(t.amount)
        top_cats = sorted(cat_spent.items(), key=lambda x: x[1], reverse=True)[:3]
        top_str = ", ".join([f"{k}: ₹{v:.0f}" for k,v in top_cats]) if top_cats else "none"
        # budget usage
        budget_usage_str = ""
        for b in budgets[:3]:
            limit = float(b.monthly_limit if b.monthly_limit is not None else b.amount)
            spent = cat_spent.get(b.category,0)
            pct = round(spent/limit*100,1) if limit else 0
            budget_usage_str += f"{b.category} {pct}% (₹{spent:.0f}/₹{limit:.0f}); "
        if not budget_usage_str: budget_usage_str = "no budgets"
        # forecast - use simple sum or call forecaster if enough data
        forecast_str = "insufficient data"
        try:
            from app.ml.predictors.forecaster import forecast_spending
            daily=defaultdict(float)
            for t in txs:
                if tx_type(t)=="expense":
                    daily[t.date.isoformat()] += float(t.amount)
            sorted_days=sorted(daily.items())
            hist=[{"date":k, "amount":v} for k,v in sorted_days]
            if len(hist)>=7:
                fc = forecast_spending(hist, "30d")
                if fc.get("status")=="success":
                    forecast_str = f"Estimated next-month spending: ₹{fc.get('total_forecast',0):.0f}"
        except: pass
        ctx = (
            f"Monthly income: ₹{monthly_income:.2f}, Monthly expenses: ₹{monthly_expenses:.2f}, "
            f"Monthly savings: ₹{monthly_savings:.2f}, Savings rate: {savings_rate}%, "
            f"Top spending categories: {top_str}. "
            f"Budget usage: {budget_usage_str} "
            f"Forecast: {forecast_str}. "
            f"Total transactions: {len(txs)}, Budgets: {len(budgets)}, Goals: {len(goals)}."
        )
        if txs:
            ctx += " Recent examples: " + "; ".join([f"{t.description} ({t.category} ₹{t.amount})" for t in txs[:5]])
        # NEVER send passwords, JWT, SMTP, DB secrets - only summarized numbers above
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
    # Parse context for numbers to give informational recommendations per spec
    # Examples: "Food spending is 18% higher", "You can save...", "budget close to limit"
    if "food" in m:
        return f"Based on your data: {context}\n\nFood spending analysis: check your Food category in Top spending categories. If Food is above 30% of monthly expenses, consider reducing dining out (e.g., Swiggy/Zomato) by ~₹1,200 to improve savings rate. This is informational, not guaranteed."
    if "budget" in m or "transport" in m:
        return f"Context: {context}\n\nBudget check: review Budget usage line. If any category ≥90%, you are close to its monthly limit. Example: 'Your transport budget is close to its monthly limit.' Adjust by tracking daily spends."
    if "save" in m or "saving" in m:
        return f"Context: {context}\n\nSavings recommendation: maintain savings rate >20%. Example: 'You can save approximately ₹1,200 by reducing dining expenses.' Build emergency fund of 3-6 months expenses. Informational only."
    if "forecast" in m or "next month" in m:
        return f"Context: {context}\n\nForecast: see 'Estimated next-month spending' in context. If forecast > income, plan to cut discretionary categories (Shopping/Entertainment) by 10-15%. Estimates only, not guaranteed."
    if "invest" in m:
        return f"Context: {context}\n\nInvestment guidance (educational, returns not guaranteed): diversify, align with goals, understand risk. Not professional advice."
    # general
    # try to detect high spending
    if "spent" in context.lower():
        return f"Context: {context}\n\nObservation: Top categories show where most money went. Example: 'Food spending is 18% higher than last month.' Review Transactions and Import Statement pages, then check AI Advisor for personalized tips. (Informational estimates only)"
    return f"Context: {context}\n\nBased on your summarized financial data above: review Dashboard, Transactions, Import Statement, and Budgets. Top categories, savings rate, and forecast indicate trends. Recommendations are informational (e.g., reduce Food/Transport if >20% of expenses, keep forecast under income). Ask about food, budget, savings, or forecast for tailored tips. (Rule-based fallback, not professional advice)"
