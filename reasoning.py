"""
Prospect Assist AI - Reasoning Layer
Takes the scorecard output and generates a human-readable explanation
and a specific recommended action, using Claude.

Output is constrained to strict JSON so the app never has to parse
free-form text - this is the key demo/judge talking point: the LLM
explains and recommends, it never re-scores or overrides the scorecard.
"""

import json
import os
import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"

ALLOWED_ACTIONS = [
    "Prioritize - Immediate Outreach",
    "Standard Follow-up",
    "Offer Restructured Terms",
    "Request Additional Documentation",
    "Deprioritize - High Risk",
]

SYSTEM_PROMPT = f"""You are a lending decision-support assistant for bank loan officers.
You will be given a lead's scorecard breakdown (already computed by a rule-based engine).
You do NOT change or second-guess the score. Your job is only to:
1. Explain in plain language why this lead scored the way it did (2-3 sentences).
2. List 1-3 key strengths (short phrases).
3. List 1-3 key risks or concerns (short phrases). If none, return an empty list.
4. Recommend exactly ONE action from this fixed list: {ALLOWED_ACTIONS}
5. Give a one-sentence rationale for that recommended action.

Respond with ONLY valid JSON, no markdown fences, no preamble, matching this schema:
{{
  "explanation": "string",
  "key_strengths": ["string", ...],
  "key_risks": ["string", ...],
  "recommended_action": "one of the fixed list above, exact match",
  "action_rationale": "string"
}}
"""


def build_user_prompt(scored_lead: dict) -> str:
    return f"""Lead scorecard data:
{json.dumps(scored_lead, indent=2)}

Generate the explanation, strengths, risks, and recommended action as per your instructions."""


def get_reasoning(scored_lead: dict, api_key: str = None) -> dict:
    """Calls Claude API. Falls back to a rule-based stub if no API key is set,
    so the pipeline is demoable even without live API access."""
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        return _fallback_reasoning(scored_lead)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": MODEL,
        "max_tokens": 500,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": build_user_prompt(scored_lead)}],
    }

    response = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    text = response.json()["content"][0]["text"]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # defensive: strip accidental markdown fences before giving up
        cleaned = text.strip().strip("```json").strip("```").strip()
        return json.loads(cleaned)


def _fallback_reasoning(scored_lead: dict) -> dict:
    """Deterministic stub used only if no API key is configured -
    keeps the demo runnable offline, e.g. during rehearsal without burning API calls."""
    band = scored_lead["risk_band"]
    breakdown = scored_lead["breakdown"]

    strengths = [k.replace("_", " ").title() for k, v in breakdown.items() if v["score"] / v["max"] >= 0.75]
    risks = [k.replace("_", " ").title() for k, v in breakdown.items() if v["score"] / v["max"] < 0.4]

    action_map = {
        "Low Risk": "Prioritize - Immediate Outreach",
        "Medium Risk": "Standard Follow-up",
        "High Risk": "Deprioritize - High Risk",
    }

    return {
        "explanation": f"{scored_lead['name']} scored {scored_lead['total_score']}/100, "
                        f"placing them in the {band} band based on the weighted pillar breakdown.",
        "key_strengths": strengths or ["No standout strengths"],
        "key_risks": risks or ["No major risk flags"],
        "recommended_action": action_map[band],
        "action_rationale": f"Action follows directly from the {band} classification.",
    }


if __name__ == "__main__":
    from scorecard import score_lead

    with open("data/leads.json") as f:
        leads = json.load(f)

    for lead in leads[:3]:
        scored = score_lead(lead)
        result = get_reasoning(scored)
        print(f"\n--- {scored['name']} ({scored['risk_band']}, {scored['total_score']}) ---")
        print(json.dumps(result, indent=2))
