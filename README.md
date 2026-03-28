# BioReason-lite: Chat with DNA

A chat app that answers biology questions using **Evo 2** for DNA-level insight and an **LLM** for step-by-step reasoning — powered by [Nebius AI Studio](https://studio.nebius.ai).

## How it works

```
User question
     ↓
LLM (parse + plan)        — extracts gene, mutation, reasoning plan
     ↓
Evo 2 (biological signal) — scores DNA sequence for mutation effect
     ↓
LLM (reasoning)           — reasons step-by-step using plan + Evo2 output
     ↓
Final answer + reasoning trace
```

## Setup

### 1. Get a Nebius API key

1. Go to [studio.nebius.ai](https://studio.nebius.ai)
2. Profile → **API Keys** → create a new key

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and set your key:
# NEBIUS_API_KEY=your_key_here
```

> ⚠️ Never commit `.env` — it's in `.gitignore`

### 3. Run

```bash
./start.sh
```

Then open `frontend/index.html` in your browser.

Requires **Python 3.12 or 3.13** (not 3.14 — pydantic-core doesn't support it yet).

## Project structure

```
explain_dna/
├── start.sh                  # one-command startup
├── frontend/
│   └── index.html            # chat UI
└── backend/
    ├── main.py               # FastAPI app
    ├── pipeline.py           # 3-step reasoning pipeline
    ├── llm.py                # Nebius LLM calls
    ├── evo2.py               # Evo 2 scoring + gene→sequence lookup
    ├── cache.py              # in-memory response cache
    ├── config.py             # model name, API base URL
    ├── load_env.py           # .env loader
    ├── requirements.txt
    └── .env.example          # safe to commit — no secrets
```

## API

```
POST /chat
{ "message": "What happens if BRCA1 mutates?" }
```

Response:
```json
{
  "gene": "BRCA1",
  "mutation": "loss_of_function",
  "plan": ["step 1", "..."],
  "evo2": { "function": "DNA repair", "mutation_effect": "..." },
  "final_answer": "...",
  "reasoning": ["Step 1: ...", "Step 2: ...", "..."]
}
```

## Supported genes (built-in sequences)

BRCA1, BRCA2, TP53, EGFR, KRAS, PTEN, MYC, APC

## Cost tips

- Responses are cached in memory — same question costs nothing twice
- Evo 2 is only called when a gene is detected in the question
- Prompts kept under ~500 tokens
