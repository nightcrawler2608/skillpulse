# SkillPulse web app for Hugging Face Spaces (Docker SDK, free CPU basic: 2 vCPU, 16 GB RAM).
# Built by scripts/deploy_space.py, which uploads only the files the app needs.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.hf-cache

# Hugging Face runs containers as user 1000
RUN useradd -m -u 1000 user
WORKDIR /app

# Dependencies first (cached between builds). CPU-only PyTorch keeps the image ~1 GB smaller.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -e ".[nlp,app]"

# Download the embedding model at build time, so the first visitor doesn't wait for it.
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY app ./app
COPY data/skills ./data/skills
COPY .streamlit ./.streamlit
RUN chown -R user:user /app
USER user

EXPOSE 7860
CMD ["streamlit", "run", "app/main.py", "--server.port=7860", "--server.address=0.0.0.0"]
