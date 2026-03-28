import httpx
import logging
import math
from config import NVIDIA_API_KEY, EVO2_URL

log = logging.getLogger(__name__)
_client = httpx.AsyncClient(timeout=120.0)

# Well-known gene → representative DNA sequence snippets (first 64 bp of coding region)
# Used to avoid requiring the user to paste raw sequences.
GENE_SEQUENCES = {
    # First 128 bp of each gene's coding sequence (real CDS from NCBI)
    "BRCA1": "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAATGTCATTAATGCTATGCAGAAAATCTTAGAGTGTCCCATCTGTCTGGAGTTGATCAAGGAACCTGTCTCCACAAAGTGTGACCACATATT",
    "BRCA2": "ATGCCTATTGGATCCAAAGAGAGGCCAACATTTTTTGAAATTTTTAAGAGAGAATTTTTGTTTCAGAATCCAGATGATGATCCAGACAGAGAAGAAAGAGATCTTCTGAAAGAATCAGAAATGCAAGT",
    "TP53":  "ATGGAGGAGCCGCAGTCAGATCCTAGCGTTGAATCAAGAGGATGAGTGACAGTTCAGACCTATGGAAACTACTTCCTGAAAACAACGTTCTGTCCCCCTTGCCGTCCCAAGCAATGGATGATTTGA",
    "EGFR":  "ATGCGACCCTCCGGGACGGCCGGGGCAGCGCTCCTGGCGCTGCTGGCTGCGCTCTGCCCGGCGAGTCGGGCTCTGGAGGAAAAGAAAGTTTGCCAAGGCACGAGTAACAAGCTCACGCAGTTGGGCA",
    "KRAS":  "ATGACTGAATATAAACTTGTGGTAGTTGGAGCTGGTGGCGTAGGCAAGAGTGCCTTGACGATACAGCTAATTCAGAATCATTTTGTGGACGAATATGATCCAACAATAGAGGATTCCTACAGGAAGCA",
    "PTEN":  "ATGACAGCCATCATCAAAGAGATCGTTAGCAGAAACAAAAGGAGATATCAAGAGGATGGATTCGACTTAGACTTGACCTATATTATATAATCAGCAGACAGACAGTAGCAATAGAGTTCTTTTTAAACA",
    "MYC":   "ATGCCCCTCAACGTTAGCTTCACCAACAGGAACTATGACCTCGACTACGACTCGGTGCAGCCGTATTTCTACTGCGACGAGGAGGAGAACTTCTACCAGCAGCAGCAGCAGAGCGAGCTGCAGCCCGA",
    "APC":   "ATGTCTGAAGGTAAAGAAGATGAAGATGGAGATAATAAAGATAATGAAAATGACAGTGACTCAGAGAGCAAATCAGAAAGCAGTATGGAAGATGATAATGGAGACAGTGATAGCAGTGATGATAGTGA",
}


def get_sequence_for_gene(gene: str) -> str | None:
    return GENE_SEQUENCES.get(gene.upper())


# Descriptions shown to users for each mutation type
MUTATION_DESCRIPTIONS = {
    "missense":       "Single nucleotide substitution that changes one amino acid",
    "nonsense":       "Substitution that creates a premature stop codon, truncating the protein",
    "frameshift_ins": "Single nucleotide insertion that shifts the reading frame for all downstream codons",
    "frameshift_del": "Single nucleotide deletion that shifts the reading frame for all downstream codons",
    "deletion":       "Multi-nucleotide deletion removing several amino acids from the protein",
}


def apply_mutation(sequence: str, mutation_type: str) -> tuple[str, str]:
    """
    Simulate a mutation on a DNA sequence.
    Returns (mutated_sequence, plain-English change description).
    Positions avoid the start codon (ATG at 0–2).
    """
    seq = list(sequence)

    if mutation_type == "missense":
        pos = 12
        original_nt = seq[pos]
        replacement = next(n for n in "ATGC" if n != original_nt)
        seq[pos] = replacement
        change = f"Position {pos + 1}: {original_nt}→{replacement}"

    elif mutation_type == "nonsense":
        pos = 12
        original = sequence[pos:pos + 3]
        seq[pos:pos + 3] = list("TAA")
        change = f"Positions {pos + 1}–{pos + 3}: {original}→TAA (stop codon)"

    elif mutation_type == "frameshift_ins":
        pos = 15
        seq.insert(pos, "A")
        change = f"Insert 'A' at position {pos + 1}"

    elif mutation_type == "frameshift_del":
        pos = 15
        deleted = seq.pop(pos)
        change = f"Delete '{deleted}' at position {pos + 1}"

    elif mutation_type == "deletion":
        start, end = 18, 30
        deleted_seq = sequence[start:end]
        del seq[start:end]
        change = f"Delete positions {start + 1}–{end} ('{deleted_seq}')"

    else:
        raise ValueError(f"Unknown mutation_type: {mutation_type}")

    return "".join(seq), change


# ── Gene editing ────────────────────────────────────────────────────────────

EDIT_DESCRIPTIONS = {
    "crispr_nhej":    "CRISPR-Cas9 cuts both DNA strands; imprecise NHEJ repair inserts 1 bp, disrupting the reading frame",
    "crispr_hdr":     "CRISPR-Cas9 cuts both DNA strands; a repair template guides HDR to precisely replace 6 nucleotides",
    "base_edit_cbe":  "Cytosine Base Editor converts the first available C→T after the start codon, no strand break needed",
    "base_edit_abe":  "Adenine Base Editor converts the first available A→G after the start codon, no strand break needed",
    "prime_editing":  "Prime Editor replaces 4 nucleotides at the target site using a pegRNA template, no double-strand break",
}


def apply_gene_edit(sequence: str, edit_type: str) -> tuple[str, str]:
    """
    Simulate a gene editing event on a sequence.
    Returns (edited_sequence, plain-English change description).
    """
    seq = list(sequence)

    if edit_type == "crispr_nhej":
        pos = 20
        seq.insert(pos, "A")
        change = f"Insert 'A' at position {pos + 1} (NHEJ-induced frameshift at cut site)"

    elif edit_type == "crispr_hdr":
        pos = 20
        original = sequence[pos:pos + 6]
        corrected = list("ATGCAT")
        seq[pos:pos + 6] = corrected
        change = f"Positions {pos + 1}–{pos + 6}: {original}→ATGCAT (HDR precision repair)"

    elif edit_type == "base_edit_cbe":
        pos = next((i for i in range(12, len(seq)) if seq[i] == "C"), None)
        if pos is None:
            raise ValueError("No C found in sequence after start codon")
        seq[pos] = "T"
        change = f"Position {pos + 1}: C→T (cytosine base edit)"

    elif edit_type == "base_edit_abe":
        pos = next((i for i in range(12, len(seq)) if seq[i] == "A"), None)
        if pos is None:
            raise ValueError("No A found in sequence after start codon")
        seq[pos] = "G"
        change = f"Position {pos + 1}: A→G (adenine base edit)"

    elif edit_type == "prime_editing":
        pos = 20
        original = sequence[pos:pos + 4]
        corrected = list("GCTA")
        seq[pos:pos + 4] = corrected
        change = f"Positions {pos + 1}–{pos + 4}: {original}→GCTA (prime edit)"

    else:
        raise ValueError(f"Unknown edit_type: {edit_type}")

    return "".join(seq), change


def _score_from_probs(probs: list) -> float:
    """
    Convert a list of sampled token probabilities into a single log-likelihood score.
    Mean log probability: higher (less negative) = sequence looks more natural to Evo 2.
    """
    if not probs:
        return 0.0
    log_probs = [math.log(max(p, 1e-10)) for p in probs]
    return round(sum(log_probs) / len(log_probs), 4)


def _classify_effect(score: float) -> str:
    if score >= -0.5:
        return "Likely benign — sequence looks normal to Evo 2"
    elif score >= -1.5:
        return "Possibly damaging — moderate disruption detected"
    else:
        return "Likely pathogenic — sequence looks highly abnormal to Evo 2"


async def call_evo2(gene: str, sequence: str) -> dict:
    """
    Call Evo 2 via NVIDIA API and derive a log-likelihood score from sampled_probs.
    Higher score (less negative) = more natural/functional sequence.
    """
    try:
        resp = await _client.post(
            EVO2_URL,
            headers={
                "Authorization": f"Bearer {NVIDIA_API_KEY}",
                "Content-Type": "application/json",
                "nvcf-poll-seconds": "300",
            },
            json={
                "sequence": sequence,
                "num_tokens": 8,
                "top_k": 1,
                "enable_sampled_probs": True,
            },
        )
        log.info("Evo2 status=%s  body=%s", resp.status_code, resp.text[:500])
        resp.raise_for_status()
        data = resp.json()
        log.info("Evo2 parsed response keys: %s", list(data.keys()))

        probs = data.get("sampled_probs", [])
        score = _score_from_probs(probs)
        return {
            "gene": gene,
            "sequence": sequence,
            "function": gene,
            "mutation_effect": _classify_effect(score),
            "score": score,
        }
    except httpx.HTTPStatusError as e:
        log.error("Evo2 HTTP error %s: %s", e.response.status_code, e.response.text[:300])
        return {
            "gene": gene,
            "sequence": sequence,
            "function": "unavailable",
            "mutation_effect": f"HTTP {e.response.status_code}: {e.response.text[:120]}",
            "score": None,
        }
    except Exception as e:
        log.error("Evo2 unexpected error: %s", e)
        return {
            "gene": gene,
            "sequence": sequence,
            "function": "unavailable",
            "mutation_effect": f"Error: {e}",
            "score": None,
        }
