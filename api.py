"""
Prospect Assist AI - Backend API
Endpoints:
  GET  /api/leads          -> all leads, scored + reasoned, ranked by score desc
  GET  /api/leads/{lead_id} -> single lead detail
  POST /api/leads           -> submit a new lead, returns scored + reasoned result
"""

import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scorecard import score_lead
from reasoning import get_reasoning

app = FastAPI(title="Prospect Assist AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "leads.json")


class LeadInput(BaseModel):
    lead_id: str
    name: str
    monthly_income: float
    existing_emi: float
    employment_type: str  # salaried_govt | salaried_private | business_owner | self_employed
    repayment_history: str  # good | average | poor | none
    requested_loan_amount: float
    tenure_months: int
    relationship_years: float


def _process(lead: dict) -> dict:
    scored = score_lead(lead)
    reasoning = get_reasoning(scored)
    return {**scored, "reasoning": reasoning}


def _load_leads() -> list:
    with open(DATA_PATH) as f:
        return json.load(f)


@app.get("/api/leads")
def get_all_leads():
    leads = _load_leads()
    results = [_process(lead) for lead in leads]
    results.sort(key=lambda r: r["total_score"], reverse=True)
    return results


@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: str):
    leads = _load_leads()
    match = next((l for l in leads if l["lead_id"] == lead_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _process(match)


@app.post("/api/leads")
def submit_lead(lead: LeadInput):
    return _process(lead.dict())


@app.get("/")
def health():
    return {"status": "ok", "service": "Prospect Assist AI"}
