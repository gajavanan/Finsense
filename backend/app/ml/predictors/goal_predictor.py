import numpy as np
from datetime import date, timedelta

def predict_goal(target_amount: float, current_amount: float, monthly_contribution: float, historical_savings_rate: float = None):
    if monthly_contribution <= 0:
        return {"status":"insufficient_data", "message":"Monthly contribution must be greater than 0."}
    remaining = target_amount - current_amount
    if remaining <= 0:
        return {"status":"success", "months":0, "completion_date": str(date.today()), "on_track": True, "message":"Goal already achieved!"}
    months = remaining / monthly_contribution
    # Use linear regression style: if historical savings provided, adjust
    if historical_savings_rate:
        # historical_savings_rate is monthly avg savings
        if historical_savings_rate < monthly_contribution * 0.5:
            months = remaining / max(1, historical_savings_rate)
    months_ceil = int(np.ceil(months))
    completion = date.today() + timedelta(days=months_ceil*30)
    on_track = months_ceil <= 24  # arbitrary
    return {
        "status":"success",
        "months": months_ceil,
        "estimated_months": round(float(months),1),
        "completion_date": completion.isoformat(),
        "remaining": round(remaining,2),
        "monthly_required": round(remaining / max(1, months_ceil),2),
        "on_track": on_track
    }
