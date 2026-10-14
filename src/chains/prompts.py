"""LangChain prompt templates + structured chains (tag/answer/verify/quiz)."""
from __future__ import annotations
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from src.chains.models import get_generator, get_verifier
from src.schemas.models import CitationUnit


def _content(msg) -> str:
    """Extract text from a chat response, never returning blank when text exists.

    Reasoning models (the OpenRouter `:free` tier in particular) are inconsistent:
    they may answer in `content`, in `reasoning_content`, or as a list of content
    blocks, and a 200 response can arrive with an empty body. Try each shape.
    """
    def _flatten(x) -> str:
        if isinstance(x, str):
            return x
        if isinstance(x, list):
            parts = []
            for b in x:
                if isinstance(b, dict):
                    t = b.get("text") or b.get("content") or ""
                    if t:
                        parts.append(str(t))
                elif isinstance(b, str):
                    parts.append(b)
            return "\n".join(parts)
        return ""

    c = _flatten(getattr(msg, "content", "") or "")
    if c.strip():
        return c.strip()

    extra = getattr(msg, "additional_kwargs", {}) or {}
    rc = _flatten(extra.get("reasoning_content", "") or "")
    if rc.strip():
        # strip leaked chain-of-thought preambles, keep the answer
        for marker in ("\n\nA:", "\nA:"):
            if marker in rc and ("Thinking Process" in rc or "Thinking" in rc):
                rc = rc.split(marker, 1)[-1]
        return rc.strip()
    return ""

TAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Tag the chunk into course/topic/subtopic/concept with difficulty. "
               "Figures: content_type=figure + one-line figure_caption."),
    ("human", "SOURCE: {source_file} (page={page} slide={slide} t={t_start}-{t_end})\n\n{content}"),
])

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Answer ONLY from the context. Write clean, flowing prose in your own words. "
               "Do NOT insert bracketed markers, page numbers or file names anywhere in the "
               "answer — citations are appended for you afterwards. "
               "If context is insufficient, say so explicitly."),
    ("human", "CONTEXT:\n{context}\n\nQUESTION: {question}"),
])

VERIFY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Decide if the ANSWER is fully supported by the CONTEXT. "
               "Reply with exactly SUPPORTED or NOT_SUPPORTED plus one-line reason."),
    ("human", "CONTEXT:\n{context}\n\nANSWER:\n{answer}"),
])

QUIZ_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Write {n} questions ({types}) on scope '{scope}' at {difficulty} level. "
               "Each: stem, options (MCQ), answer_key, topic, explanation. "
               "Ground every question in the context; include source ref."),
    ("human", "CONTEXT:\n{context}"),
])


def get_tag_chain():
    return TAG_PROMPT | get_generator().with_structured_output(CitationUnit)


def get_answer_chain():
    return ANSWER_PROMPT | get_generator() | RunnableLambda(_content)


def get_verify_chain():
    return VERIFY_PROMPT | get_verifier() | RunnableLambda(_content)


def get_quiz_chain():
    return QUIZ_PROMPT | get_generator() | RunnableLambda(_content)
