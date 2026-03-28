import os

NEBIUS_API_KEY = os.environ.get("NEBIUS_API_KEY", "")
NEBIUS_BASE_URL = "https://api.studio.nebius.ai/v1"

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
EVO2_URL = "https://health.api.nvidia.com/v1/biology/arc/evo2-40b/generate"

LLM_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
