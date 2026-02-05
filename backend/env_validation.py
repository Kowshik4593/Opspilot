import os
from typing import Dict

REQUIRED = [
    "ENV",
]

def get_env_status() -> Dict[str, bool]:
    status = {}
    for k in REQUIRED:
        status[k] = k in os.environ and bool(os.environ.get(k))

    # Optional AI config
    status['azure_embeddings'] = all([os.environ.get('AZURE_OPENAI_API_BASE'), os.environ.get('AZURE_OPENAI_EMBEDDING_DEPLOYMENT'), os.environ.get('AZURE_OPENAI_API_KEY')])
    status['azure_models'] = all([os.environ.get('AZURE_OPENAI_API_BASE'), os.environ.get('AZURE_OPENAI_GPT4O_MINI_DEPLOYMENT'), os.environ.get('AZURE_OPENAI_API_KEY')])
    return status
