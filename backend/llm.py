import httpx
from config import NEBIUS_API_KEY, NEBIUS_BASE_URL, LLM_MODEL

_client = httpx.AsyncClient(timeout=60.0)


async def call_llm(messages: list[dict], max_tokens: int = 512) -> str:
    resp = await _client.post(
        f"{NEBIUS_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {NEBIUS_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": LLM_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
        },
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
