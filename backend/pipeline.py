"""
BioReason-lite pipeline:
  Step 1 — LLM parses user question → structured plan
  Step 2 — Evo2 scores the gene sequence (only if a gene is identified)
  Step 3 — LLM reasons step-by-step using the plan + Evo2 output
  Step 4 — Return final answer + reasoning trace
"""

import json
import cache
from llm import call_llm
from evo2 import call_evo2, get_sequence_for_gene

# ---------------------------------------------------------------------------
# Step 1: Parse + Plan
# ---------------------------------------------------------------------------

PARSE_SYSTEM = """You are a molecular biology expert assistant.
Given a biology question, extract structured information and create a reasoning plan.

Reply ONLY with valid JSON in exactly this shape:
{
  "gene": "<gene symbol or null>",
  "mutation": "<mutation type or null>",
  "topic": "<one-line topic summary>",
  "plan": ["step 1", "step 2", "step 3", "step 4"]
}

Keep each plan step short (≤ 10 words). Output nothing outside the JSON."""


async def step1_parse(question: str) -> dict:
    raw = await call_llm(
        [
            {"role": "system", "content": PARSE_SYSTEM},
            {"role": "user", "content": question},
        ],
        max_tokens=300,
    )
    try:
        # Strip possible markdown fences
        text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except json.JSONDecodeError:
        return {"gene": None, "mutation": None, "topic": question, "plan": []}


# ---------------------------------------------------------------------------
# Step 2: Evo2 (conditional)
# ---------------------------------------------------------------------------

async def step2_evo2(parsed: dict) -> dict | None:
    gene = parsed.get("gene")
    if not gene:
        return None
    sequence = get_sequence_for_gene(gene)
    if not sequence:
        return None
    return await call_evo2(gene, sequence)


# ---------------------------------------------------------------------------
# Step 3: Reasoning
# ---------------------------------------------------------------------------

REASON_SYSTEM = """You are a molecular biology expert.
Use the structured plan and biological evidence to reason step-by-step, then give a final answer.

Reply ONLY with valid JSON in exactly this shape:
{
  "final_answer": "<2–3 sentence plain-language answer>",
  "reasoning": ["Step 1: ...", "Step 2: ...", "Step 3: ...", "Step 4: ..."]
}

Be scientifically accurate but accessible. Output nothing outside the JSON."""


async def step3_reason(question: str, parsed: dict, evo2_result: dict | None) -> dict:
    bio_evidence = (
        json.dumps(evo2_result, indent=2) if evo2_result
        else "No Evo2 data available — reason from general knowledge."
    )

    plan_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(parsed.get("plan", [])))

    prompt = f"""Question: {question}

Reasoning plan:
{plan_text}

Biological evidence from Evo2:
{bio_evidence}

Now reason through the plan and give your answer."""

    raw = await call_llm(
        [
            {"role": "system", "content": REASON_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        max_tokens=600,
    )
    try:
        text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except json.JSONDecodeError:
        return {"final_answer": raw, "reasoning": []}


# ---------------------------------------------------------------------------
# Main pipeline entry point
# ---------------------------------------------------------------------------

async def run_pipeline(question: str) -> dict:
    cached = cache.get(question)
    if cached:
        return {**cached, "cached": True}

    parsed = await step1_parse(question)
    evo2_result = await step2_evo2(parsed)
    answer = await step3_reason(question, parsed, evo2_result)

    result = {
        "question": question,
        "gene": parsed.get("gene"),
        "mutation": parsed.get("mutation"),
        "plan": parsed.get("plan", []),
        "evo2": evo2_result,
        "final_answer": answer.get("final_answer", ""),
        "reasoning": answer.get("reasoning", []),
        "cached": False,
    }
    cache.set(question, result)
    return result
