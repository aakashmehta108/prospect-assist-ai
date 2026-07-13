"""
Prospect Assist AI - Scorecard Engine
Transparent, rule-based scoring (not a black-box ML model).
Weights are business-defined and fully explainable to a bank auditor.

Total score = 100 points across 5 pillars:
  1. Income Adequacy        - 25 pts
  2. Obligation Ratio        - 20 pts
  3. Repayment History       - 25 pts
  4. Employment Stability    - 15 pts
  5. Relationship Tenure     - 15 pts
"""

EMPLOYMENT_SCORES = {
    "salaried_govt": 15,
    "salaried_private": 11,
    "business_owner": 8,
    "self_employed": 6,
}

REPAYMENT_SCORES = {
    "good": 25,
    "average": 15,
    "poor": 5,
    "none": 10,  # no history != bad history, scored neutral-low
}


def score_income_adequacy(monthly_income: float, requested_loan_amount: float, tenure_months: int) -> float:
    """Checks if income comfortably supports the estimated EMI for the requested loan."""
    if tenure_months <= 0:
        return 0
    estimated_emi = requested_loan_amount / tenure_months
    ratio = estimated_emi / monthly_income if monthly_income > 0 else 1
    if ratio <= 0.15:
        return 25
    elif ratio <= 0.25:
        return 20
    elif ratio <= 0.35:
        return 12
    elif ratio <= 0.50:
        return 5
    return 0


def score_obligation_ratio(monthly_income: float, existing_emi: float) -> float:
    """Lower existing debt burden = higher score."""
    if monthly_income <= 0:
        return 0
    ratio = existing_emi / monthly_income
    if ratio <= 0.10:
        return 20
    elif ratio <= 0.25:
        return 15
    elif ratio <= 0.40:
        return 8
    return 2


def score_repayment_history(history: str) -> float:
    return REPAYMENT_SCORES.get(history, 10)


def score_employment_stability(employment_type: str) -> float:
    return EMPLOYMENT_SCORES.get(employment_type, 6)


def score_relationship_tenure(years: float) -> float:
    if years >= 5:
        return 15
    elif years >= 3:
        return 11
    elif years >= 1:
        return 7
    return 2


def compute_risk_band(total_score: float) -> str:
    if total_score >= 75:
        return "Low Risk"
    elif total_score >= 50:
        return "Medium Risk"
    return "High Risk"


def score_lead(lead: dict) -> dict:
    """Returns full breakdown - this dict is what gets passed to the LLM reasoning layer."""
    income_score = score_income_adequacy(
        lead["monthly_income"], lead["requested_loan_amount"], lead["tenure_months"]
    )
    obligation_score = score_obligation_ratio(lead["monthly_income"], lead["existing_emi"])
    repayment_score = score_repayment_history(lead["repayment_history"])
    employment_score = score_employment_stability(lead["employment_type"])
    tenure_score = score_relationship_tenure(lead["relationship_years"])

    total = income_score + obligation_score + repayment_score + employment_score + tenure_score

    return {
        "lead_id": lead["lead_id"],
        "name": lead["name"],
        "total_score": round(total, 1),
        "risk_band": compute_risk_band(total),
        "breakdown": {
            "income_adequacy": {"score": income_score, "max": 25},
            "obligation_ratio": {"score": obligation_score, "max": 20},
            "repayment_history": {"score": repayment_score, "max": 25},
            "employment_stability": {"score": employment_score, "max": 15},
            "relationship_tenure": {"score": tenure_score, "max": 15},
        },
        "raw_lead": lead,
    }


if __name__ == "__main__":
    import json

    with open("data/leads.json") as f:
        leads = json.load(f)

    for lead in leads:
        result = score_lead(lead)
        print(f"{result['lead_id']} | {result['name']:15s} | Score: {result['total_score']:5.1f} | {result['risk_band']}")
