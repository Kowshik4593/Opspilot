import os
import json
import typing
from pathlib import Path
import requests

VECTORS_FILE = Path(__file__).resolve().parent / 'vectors_store.json'

def _load_vectors():
    if not VECTORS_FILE.exists():
        return {}
    try:
        return json.loads(VECTORS_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}

def _save_vectors(d: dict):
    VECTORS_FILE.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')

def get_embedding(text: str) -> typing.List[float]:
    # Try Azure OpenAI embeddings if configured, otherwise return a simple fallback vector.
    base = os.environ.get('AZURE_OPENAI_API_BASE')
    deployment = os.environ.get('AZURE_OPENAI_EMBEDDING_DEPLOYMENT')
    key = os.environ.get('AZURE_OPENAI_API_KEY') or os.environ.get('AZURE_OPENAI_API_KEY')
    if base and deployment and key:
        try:
            url = f"{base}/openai/deployments/{deployment}/embeddings?api-version=2023-10-01-preview"
            headers = {'Content-Type': 'application/json', 'api-key': key}
            payload = {"input": text}
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            r.raise_for_status()
            j = r.json()
            emb = j.get('data', [{}])[0].get('embedding')
            if emb:
                return emb
        except Exception:
            pass

    # Fallback: simple character-level normalized vector (deterministic but low-quality)
    vec = [0.0] * 128
    for i, ch in enumerate(text[:1024]):
        vec[i % 128] += ord(ch) / 1000.0
    # normalize
    norm = sum(x * x for x in vec) ** 0.5
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec

def upsert_vector(doc_id: str, text: str, metadata: dict = None):
    d = _load_vectors()
    emb = get_embedding(text)
    d[doc_id] = {"embedding": emb, "text": text, "metadata": metadata or {}}
    _save_vectors(d)

def search_vectors(query: str, k: int = 5):
    qv = get_embedding(query)
    d = _load_vectors()
    results = []
    for doc_id, doc in d.items():
        v = doc.get('embedding')
        if not v:
            continue
        # cosine similarity
        dot = sum(a * b for a, b in zip(qv, v))
        results.append((dot, doc_id, doc))
    results.sort(key=lambda t: t[0], reverse=True)
    out = []
    for score, doc_id, doc in results[:k]:
        out.append({"id": doc_id, "score": score, "text": doc.get('text'), "metadata": doc.get('metadata')})
    return out
