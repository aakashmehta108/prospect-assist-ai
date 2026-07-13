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
    OR if the API call fails/returns something unparseable for any reason,
    so the pipeline never crashes the endpoint mid-demo."""
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

    try:
        response = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        text = response.json()["content"][0]["text"]
        result = _parse_json_response(text)
        return _validate_and_clean(result, scored_lead)

    except Exception as e:
        # Any failure (network, API error, bad JSON, missing keys) -> safe fallback.
        # Logs to Render's Logs tab so you can see it happened, but never crashes the request.
        print(f"[reasoning.py] get_reasoning failed, using fallback: {e}")
        return _fallback_reasoning(scored_lead)


def _parse_json_response(text: str) -> dict:
    """Parses Claude's JSON output, tolerating accidental markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove a leading ```json or ``` line, and a trailing ``` line
        lines = cleaned.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return json.loads(cleaned)


def _validate_and_clean(result: dict, scored_lead: dict) -> dict:
    """Enforces the contract: recommended_action must be one of the allowed values.
    If Claude ever returns something outside the fixed list, we don't trust it -
    fall back to the deterministic action instead."""
    required_keys = {"explanation", "key_strengths", "key_risks", "recommended_action", "action_rationale"}
    if not required_keys.issubset(result.keys()):
        raise ValueError(f"Missing required keys in reasoning response: {result}")

    if result["recommended_action"] not in ALLOWED_ACTIONS:
        band = scored_lead["risk_band"]
        action_map = {
            "Low Risk": "Prioritize - Immediate Outreach",
            "Medium Risk": "Standard Follow-up",
            "High Risk": "Deprioritize - High Risk",
        }
        result["recommended_action"] = action_map.get(band, "Standard Follow-up")
        result["action_rationale"] += " (action corrected to match fixed policy list)"

    return result


def _fallback_reasoning(scored_lead: dict) -> dict:
    """Deterministic stub used if no API key is configured, or if the live call
    fails for any reason - keeps the demo runnable even if the API hiccups."""
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
