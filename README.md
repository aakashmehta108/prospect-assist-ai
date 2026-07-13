# Prospect Assist AI — Team Green Galaxy

**IDBI Innovate 2026 — Problem Statement 2: Prospect Assist AI**
(AI-powered loan lead generation and repayment capacity prediction)

## What this is

A decision-support tool for bank loan officers. It scores incoming leads using a
transparent, rule-based weighted scorecard (income adequacy, obligation ratio,
repayment history, employment stability, relationship tenure), then uses an AI
reasoning layer (Claude API) to explain *why* each lead scored the way it did and
recommend a specific next action — not just a number.

**Flow:** Lead Data → Scorecard Engine → Risk Band → AI Reasoning (explanation +
recommended action) → Officer Dashboard.

## Project structure

```
.
├── api.py            # FastAPI backend — REST endpoints
├── scorecard.py       # Rule-based scoring engine (transparent, explainable)
├── reasoning.py        # Claude API integration — structured JSON reasoning output
├── index.html          # Frontend — single static file, no build step
├── requirements.txt
├── data/
│   └── leads.json      # Synthetic sample leads for demo
└── assets/             # Diagrams and screenshots used in the submission deck
```

## Run locally

```bash
pip install -r requirements.txt
uvicorn api:app --reload
```

Backend runs at `http://localhost:8000`. Open `index.html` directly in a browser
(the `API_BASE` constant near the top of the `<script>` tag already points to
`http://localhost:8000` by default).

## Environment variable

Set `ANTHROPIC_API_KEY` to enable live AI-generated reasoning. Without it, the
app automatically falls back to a deterministic offline reasoning stub, so the
demo still runs end-to-end even without API access.

```bash
export ANTHROPIC_API_KEY=your_key_here
```

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/leads` | All leads, scored + reasoned, ranked by score descending |
| GET | `/api/leads/{lead_id}` | Single lead detail |
| POST | `/api/leads` | Submit a new lead, returns scored + reasoned result |
| GET | `/` | Health check |

## Deployment

- **Backend:** Render (free tier) — Build: `pip install -r requirements.txt`,
  Start: `uvicorn api:app --host 0.0.0.0 --port $PORT`
- **Frontend:** Vercel/Netlify — static file, no build step. Update `API_BASE`
  in `index.html` to your deployed backend URL before deploying.

## Why rule-based scoring, not a trained ML model

Scorecard weights are transparent business rules, not a black-box classifier.
This is intentional: it keeps every score fully explainable and auditable,
aligning with RBI fair-lending expectations — a deliberate design choice, not
a shortcut. See `assets/performance.png` for the full reasoning.

## Team

Green Galaxy — Aakash Mehta, Priyansh Vala
