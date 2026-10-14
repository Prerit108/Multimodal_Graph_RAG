"""Central settings. All secrets from env; models/embeddings chosen here."""
from __future__ import annotations
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- LLM providers (generator + distinct verifier) ---
    GOOGLE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    NVIDIA_NIM_API_KEY: str = ""
    NVIDIA_NIM_BASE_URL: str = "https://integrate.api.nvidia.com/v1"

    # OpenRouter (OpenAI-compatible gateway; `:free` model ids are free tier).
    OPEN_ROUTER_API_KEY: str = ""
    OPEN_ROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    # Free-tier ids are individually rate-limited. Each role tries these in
    # order, so a 429 on one model does not take down the demo.
    GENERATOR_FALLBACKS: str = ("nvidia/nemotron-3-super-120b-a12b:free,"
                                "nvidia/nemotron-3.5-lightning:free,"
                                "cohere/north-mini-code:free,"
                                "liquid/lfm-2.5-2.6b:free")
    VERIFIER_FALLBACKS: str = ("google/gemma-4-31b-it:free,"
                               "google/gemma-4-26b-a4b-it:free,"
                               "nvidia/nemotron-3-super-120b-a12b:free")

    GENERATOR_PROVIDER: str = "openrouter"  # openrouter | google | openai | nim
    GENERATOR_MODEL: str = "nvidia/nemotron-3-super-120b-a12b:free"
    VERIFIER_PROVIDER: str = "openrouter"   # different vendor = stronger cross-check
    VERIFIER_MODEL: str = "google/gemma-4-31b-it:free"
    NIM_MODEL: str = "meta/llama-3.1-70b-instruct"

    # --- Vision (G0 image / diagram descriptions) ---
    # OpenRouter's general free tier is text-only, but the Nemotron omni model is
    # multimodal on the free tier, so image/diagram description works with no
    # extra key. Falls back to a filename stub if it is unavailable.
    ENABLE_VLM: bool = True
    VISION_PROVIDER: str = "openrouter"
    VISION_MODEL: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    VISION_FALLBACKS: str = ("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free,"
                             "nvidia/nemotron-3-super-120b-a12b:free")
    VLM_MAX_TOKENS: int = 1024

    # --- Reranker (cross-encoder, CPU-safe) ---
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_DEVICE: str = "cpu"           # force cpu: GPU VRAM held by LM Studio
    RERANKER_TOPN: int = 12                # candidates scored, top TOP_K returned
    USE_BM25: bool = True

    # --- Embeddings / vector store ---
    # Nomic-Embed-Text v1.5 local (GPU if VRAM allows, else CPU). Chroma stores
    # whatever dim the embedder returns — wipe data/chroma_db when switching.
    EMBEDDING_PROVIDER: str = "nomic"  # nomic (local) | huggingface
    EMBEDDING_MODEL: str = "text-embedding-nomic-embed-text-v1.5"
    HF_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    NOMIC_MODEL: str = "nomic-ai/nomic-embed-text-v1.5"
    NOMIC_MIN_GPU_MB: int = 1500
    VECTOR_BACKEND: str = "chroma"       # chroma (installed) | qdrant (optional)
    CHROMA_DIR: str = "data/chroma_db"
    COLLECTION: str = "learning_companion"
    QDRANT_URL: str = "http://localhost:6333"

    # --- Retrieval / grounding ---
    TOP_K: int = 6
    GRADE_THRESHOLD: float = 0.35
    CHUNK_SIZE: int = 900
    CHUNK_OVERLAP: int = 135

    # --- Uploads ---
    UPLOAD_DIR: str = "data/uploads"

    # --- Persistence ---
    CHECKPOINT_DB: str = "data/checkpoints/graph.db"
    BKT_DB: str = "data/checkpoints/bkt.json"
    QUESTION_BANK: str = "data/checkpoints/questions.jsonl"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # map legacy NVIDIA_NIM key name in existing .env
    if not s.NVIDIA_NIM_API_KEY:
        s.NVIDIA_NIM_API_KEY = os.getenv("NVIDIA_NIM", "")
    return s
