import load_env  # noqa: F401 — must be first to populate env before config
import asyncio
import logging
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pipeline import run_pipeline
from evo2 import call_evo2, get_sequence_for_gene, apply_mutation, MUTATION_DESCRIPTIONS

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="BioReason-lite")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        result = await run_pipeline(req.message)
        return result
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


class AnalyzeRequest(BaseModel):
    gene: str
    mutation_type: str


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    gene = req.gene.upper()
    mutation_type = req.mutation_type

    sequence = get_sequence_for_gene(gene)
    if not sequence:
        raise HTTPException(status_code=404, detail=f"Gene '{gene}' not found")

    if mutation_type not in MUTATION_DESCRIPTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown mutation type '{mutation_type}'")

    try:
        mutated_seq, change_desc = apply_mutation(sequence, mutation_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Score original and mutated sequences in parallel
    original_result, mutated_result = await asyncio.gather(
        call_evo2(gene, sequence),
        call_evo2(gene, mutated_seq),
    )

    score_delta = None
    if original_result.get("score") is not None and mutated_result.get("score") is not None:
        score_delta = round(mutated_result["score"] - original_result["score"], 4)

    return {
        "gene": gene,
        "mutation_type": mutation_type,
        "mutation_label": MUTATION_DESCRIPTIONS[mutation_type],
        "change": change_desc,
        "original": {
            "sequence": sequence,
            "score": original_result.get("score"),
            "mutation_effect": original_result.get("mutation_effect"),
        },
        "mutated": {
            "sequence": mutated_seq,
            "score": mutated_result.get("score"),
            "mutation_effect": mutated_result.get("mutation_effect"),
        },
        "score_delta": score_delta,
    }


@app.get("/health")
def health():
    return {"status": "ok"}
