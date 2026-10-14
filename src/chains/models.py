"""LangChain-only model/embedding factories. No raw SDK calls elsewhere."""
from __future__ import annotations
from functools import lru_cache
from langchain_core.runnables import RunnableLambda
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config.settings import get_settings


def _openrouter_chat(model: str, temperature: float, max_tokens: int | None = None):
    """OpenRouter via its OpenAI-compatible endpoint (ChatOpenAI is a LangChain class).

    Free-tier (`:free`) ids are rate-limited, so retries are generous and the
    timeout is long enough for a cold start behind a cold cache.
    """
    s = get_settings()
    return ChatOpenAI(model=model, temperature=temperature,
                      base_url=s.OPEN_ROUTER_BASE_URL,
                      api_key=s.OPEN_ROUTER_API_KEY or "sk-or-placeholder",
                      max_tokens=max_tokens or 2048, max_retries=3, request_timeout=300)


def _flatten_any(x) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        out = []
        for b in x:
            if isinstance(b, dict):
                t = b.get("text") or b.get("content") or ""
                if t:
                    out.append(str(t))
            elif isinstance(b, str):
                out.append(b)
        return "\n".join(out)
    return ""


class FailoverChat:
    """Invoke across several models until one answers.

    OpenRouter's `:free` ids are rate-limited per model, and a 429 or an empty
    completion is common on a shared pool. Without this, a single unlucky call
    returns a blank answer in the middle of a live demo.
    """

    def __init__(self, models: list[str], temperature: float, max_tokens: int | None = None):
        self.models = [m for m in models if m]
        self.temperature = temperature
        self.max_tokens = max_tokens

    def invoke(self, *a, **kw):
        last = None
        for model in self.models:
            try:
                r = _openrouter_chat(model, self.temperature, self.max_tokens).invoke(*a, **kw)
                # a 200 with an empty body is common on the free pool — treat it
                # as a miss, otherwise the caller silently gets a blank answer
                content = getattr(r, "content", "")
                if isinstance(content, list):
                    content = " ".join(b.get("text", "") for b in content
                                       if isinstance(b, dict))
                extra = (getattr(r, "additional_kwargs", {}) or {}).get("reasoning_content", "")
                if (isinstance(content, str) and content.strip()) or \
                   (isinstance(extra, str) and extra.strip()):
                    # OpenRouter reasoning models return `content` as a block list
                    # and put the visible answer in `reasoning_content`. Rebuild a
                    # plain-text message so downstream extraction can't miss it.
                    from langchain_core.messages import AIMessage
                    return AIMessage(content=_flatten_any(content) or _flatten_any(extra))
                print(f"[llm] {model} returned an empty completion; trying next")
            except Exception as e:          # rate limit, 404, timeout…
                last = e
                print(f"[llm] {model} unavailable ({type(e).__name__}); trying next")
                continue
        if last:
            raise last
        raise RuntimeError("no model produced a response")


def get_generator():
    """Primary answering / generation chat model (LangChain)."""
    s = get_settings()
    if s.GENERATOR_PROVIDER == "openrouter":
        chain = [s.GENERATOR_MODEL] + [m.strip() for m in s.GENERATOR_FALLBACKS.split(",") if m.strip()]
        return RunnableLambda(FailoverChat(list(dict.fromkeys(chain)), 0.2).invoke)
    if s.GENERATOR_PROVIDER == "openai":
        return ChatOpenAI(model=s.GENERATOR_MODEL, temperature=0.2)
    if s.GENERATOR_PROVIDER == "nim":
        return ChatOpenAI(model=s.NIM_MODEL, base_url=s.NVIDIA_NIM_BASE_URL,
                          api_key=s.NVIDIA_NIM_API_KEY, temperature=0.2)
    return ChatGoogleGenerativeAI(model=s.GENERATOR_MODEL, temperature=0.2)


def get_verifier():
    """MUST be a different vendor/model from generator (cross-model validation)."""
    s = get_settings()
    if s.VERIFIER_PROVIDER == "openrouter":
        chain = [s.VERIFIER_MODEL] + [m.strip() for m in s.VERIFIER_FALLBACKS.split(",") if m.strip()]
        return RunnableLambda(FailoverChat(list(dict.fromkeys(chain)), 0.0).invoke)
    if s.VERIFIER_PROVIDER == "openai":
        return ChatOpenAI(model=s.VERIFIER_MODEL, temperature=0.0)
    if s.VERIFIER_PROVIDER == "nim":
        return ChatOpenAI(model=s.NIM_MODEL, base_url=s.NVIDIA_NIM_BASE_URL,
                          api_key=s.NVIDIA_NIM_API_KEY, temperature=0.0)
    return ChatGoogleGenerativeAI(model=s.VERIFIER_MODEL, temperature=0.0)


def get_vision():
    """Vision-capable chat model for describing images/diagrams (G0 image branch).

    Defaults to the generator when the provider's model is already multimodal.
    Never raises here — callers must treat failure as "describe me later" and fall
    back to a filename-only stub so an image upload can never break ingestion.
    """
    s = get_settings()
    # OpenRouter's free tier is text-only, so a vision model must come from
    # elsewhere: prefer an explicit override, then OpenAI, then Gemini.
    if s.VISION_MODEL:
        provider, model = (s.VISION_PROVIDER or "openrouter").lower(), s.VISION_MODEL
    elif s.OPENAI_API_KEY:
        provider, model = "openai", "gpt-4o-mini"
    elif s.GOOGLE_API_KEY:
        provider, model = "google", "gemini-2.0-flash"
    else:
        provider, model = (s.VISION_PROVIDER or s.GENERATOR_PROVIDER).lower(), s.GENERATOR_MODEL
    if provider == "openrouter":
        return _openrouter_chat(model, 0.0, max_tokens=s.VLM_MAX_TOKENS)
    if provider == "openai":
        return ChatOpenAI(model=model, temperature=0.0, max_tokens=s.VLM_MAX_TOKENS)
    if provider == "nim":
        return ChatOpenAI(model=model, base_url=s.NVIDIA_NIM_BASE_URL,
                          api_key=s.NVIDIA_NIM_API_KEY, temperature=0.0)
    return ChatGoogleGenerativeAI(model=model, temperature=0.0)


@lru_cache
def get_embeddings():
    """Nomic-Embed-Text v1.5 via sentence-transformers, GPU if VRAM allows else CPU.

    Priority: (1) local Nomic on GPU when >= ~1.5GB free, else CPU;
    (2) HF MiniLM fallback; (3) LM Studio server embeddings (needs the nomic
    model loaded there). OpenAI is last and requires a real API key.
    """
    import torch
    s = get_settings()
    try:
        from sentence_transformers import SentenceTransformer
        from langchain_huggingface import HuggingFaceEmbeddings  # noqa: reimport
        free_mb = 0
        if torch.cuda.is_available():
            try:
                free_mb = torch.cuda.mem_get_info()[0] / 1024**2
            except Exception:
                free_mb = 0
        device = f"cuda:{torch.cuda.current_device()}" if free_mb > 1500 else "cpu"
        print(f"[embed] Nomic-Embed-Text v1.5 on {device} (GPU free: {free_mb:.0f} MB)")
        model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5",
                                    device=device, trust_remote_code=True)
        return HuggingFaceEmbeddings(model_name="nomic-ai/nomic-embed-text-v1.5",
                                     model_kwargs={"device": device},
                                     encode_kwargs={"normalize_embeddings": True})
    except Exception as e:
        print(f"[embed] Nomic failed ({e}); trying MiniLM fallback")
    try:
        return HuggingFaceEmbeddings(model_name=s.HF_EMBEDDING_MODEL)
    except Exception as e:
        print(f"[embed] MiniLM failed ({e}); trying OpenRouter embeddings")
    if s.EMBEDDING_PROVIDER in ("openrouter", "auto"):
        try:
            return OpenAIEmbeddings(model=s.EMBEDDING_MODEL, base_url=s.OPEN_ROUTER_BASE_URL,
                                    api_key=s.OPEN_ROUTER_API_KEY,
                                    check_embedding_ctx_length=False)
        except Exception as e:
            print(f"[embed] LM Studio embeddings failed ({e})")
    raise RuntimeError(
        "No embedding backend available. Set OPENAI_API_KEY for cloud embeddings, "
        "or load text-embedding-nomic-embed-text-v1.5 in LM Studio.")
