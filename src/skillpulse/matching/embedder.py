"""Turn text into embeddings: 384 numbers that capture its meaning.

Texts with similar meaning get similar numbers, so "Junior Data Analyst, SQL and
Power BI" lands close to a resume that talks about SQL dashboards, even if the
words differ. We compare two embeddings with cosine similarity
(1 = same meaning, 0 = unrelated).

Model: all-MiniLM-L6-v2: small (~90 MB), fast on a normal CPU, free.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DIM = 384
MAX_RESUME_CHARS = 4000   # the model reads ~256 words at a time; keep the meaningful start


@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer  # heavy import, only when needed

    return SentenceTransformer(MODEL_NAME)


def embed(texts: list[str], batch_size: int = 64) -> np.ndarray:
    """Normalised embeddings (so a dot product = cosine similarity)."""
    vecs = get_model().encode(texts, batch_size=batch_size, normalize_embeddings=True,
                              show_progress_bar=False)
    return np.asarray(vecs, dtype=np.float32)


def embed_resume(text: str) -> np.ndarray:
    """Long resumes are split into chunks; we average the chunk embeddings."""
    text = text[:MAX_RESUME_CHARS]
    chunks = [text[i:i + 1000] for i in range(0, len(text), 1000)] or [""]
    v = embed(chunks).mean(axis=0)
    return v / (np.linalg.norm(v) or 1.0)


def to_pgvector(vec: np.ndarray) -> str:
    """Format for PostgreSQL's vector type: '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
