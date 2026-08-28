from collections import defaultdict

def recommend_budget(transactions: list, income: float = None):
    if not transactions or len(transactions) < 5:
        return {"status":"insufficient_data", "message":"More transaction history is required to recommend budgets."}
    # group expense by category
    cat_totals = defaultdict(float)
    cat_counts = defaultdict(int)
    total_expense = 0
    for t in transactions:
        if t.get("type") == "expense":
            cat = t.get("category") or "Other"
            amt = float(t.get("amount",0))
            cat_totals[cat] += amt
            cat_counts[cat] += 1
            total_expense += amt
    if total_expense == 0:
        return {"status":"insufficient_data", "message":"No expense data found."}
    # ideal 50/30/20 style: compute avg monthly
    # estimate months from data
    recommendations = {}
    explanations = {}
    for cat, total in cat_totals.items():
        avg = total / max(1, len(set([t.get("date","")[:7] for t in transactions if t.get("type")=="expense"])))
        # suggest 10% reduction if high variance category, else avg
        # Simple: recommend = avg * 0.9 for Shopping/Entertainment, avg otherwise
        if cat in ["Shopping","Entertainment","Food"]:
            rec = round(avg * 0.9, 2)
            explanations[cat] = f"Based on avg monthly spend {avg:.2f}, suggested 10% reduction for discretionary category."
        else:
            rec = round(avg,2)
            explanations[cat] = f"Based on avg monthly spend for {cat}."
        recommendations[cat] = rec
    # If income provided, ensure sum < income*0.8
    if income and sum(recommendations.values()) > income*0.8:
        scale = (income*0.8)/sum(recommendations.values())
        for k in recommendations:
            recommendations[k] = round(recommendations[k]*scale,2)
            explanations[k] += " Scaled to fit 80% of income."
    return {"status":"success", "recommendations": recommendations, "explanations": explanations, "total_recommended": round(sum(recommendations.values()),2)}
