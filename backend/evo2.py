import httpx
from config import NEBIUS_API_KEY, NEBIUS_BASE_URL

_client = httpx.AsyncClient(timeout=120.0)

# Well-known gene → representative DNA sequence snippets (first 64 bp of coding region)
# Used to avoid requiring the user to paste raw sequences.
GENE_SEQUENCES = {
    "BRCA1": "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAATGTCATTAATGCTATGCAGAAAATCTT",
    "BRCA2": "ATGCCTATTGGATCCAAAGAGAGGCCAACATTTTTTGAAATTTTTAAGAGAGAATTTTTGTTTCA",
    "TP53":  "ATGGAGGAGCCGCAGTCAGATCCTAGCGTTGAATCAAGAGGATGAGTGACAGTTCAGACCTATGG",
    "EGFR":  "ATGCGACCCTCCGGGACGGCCGGGGCAGCGCTCCTGGCGCTGCTGGCTGCGCTCTGCCCGGCGAG",
    "KRAS":  "ATGACTGAATATAAACTTGTGGTAGTTGGAGCTGGTGGCGTAGGCAAGAGTGCCTTGACGATACA",
    "PTEN":  "ATGACAGCCATCATCAAAGAGATCGTTAGCAGAAACAAAAGGAGATATCAAGAGGATGGATTCGAC",
    "MYC":   "ATGCCCCTCAACGTTAGCTTCACCAACAGGAACTATGACCTCGACTACGACTCGGTGCAGCCGTAT",
    "APC":   "ATGTCTGAAGGTAAAGAAGATGAAGATGGAGATAATAAAGATAATGAAAATGACAGTGACTCAGAG",
}


def get_sequence_for_gene(gene: str) -> str | None:
    return GENE_SEQUENCES.get(gene.upper())


async def call_evo2(gene: str, sequence: str) -> dict:
    """
    Call Evo 2 on Nebius for mutation-effect scoring.
    Returns a dict with function summary and mutation_effect.
    """
    try:
        resp = await _client.post(
            f"{NEBIUS_BASE_URL}/evo2/score",
            headers={
                "Authorization": f"Bearer {NEBIUS_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "evo-2-40b",
                "sequence": sequence,
                "task": "mutation_effect",
                "gene": gene,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "function": data.get("function", "unknown"),
            "mutation_effect": data.get("mutation_effect", "unknown"),
            "score": data.get("score"),
        }
    except httpx.HTTPStatusError as e:
        # Graceful fallback if Evo2 endpoint format differs
        return {
            "function": "unavailable",
            "mutation_effect": f"Evo2 call failed: {e.response.status_code}",
            "score": None,
        }
