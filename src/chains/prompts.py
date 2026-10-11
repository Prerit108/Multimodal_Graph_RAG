"""LangChain prompt templates + structured chains (tag/answer/verify/quiz)."""
from __future__ import annotations
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from src.chains.models import get_generator, get_verifier
from src.schemas.models import CitationUnit


def _content(msg) -> str:
    """Extract text from a chat response. Reasoning models (e.g. ornith via LM
    Studio) may put the answer in reasoning_content, or return content as a
    list of blocks (text + reasoning), or cut content to '' on length limits."""
    c = getattr(msg, "content", "") or ""
    if isinstance(c, list):  # content blocks: [{type:text,...},{type:reasoning,...}]
        texts = [b.get("text", "") for b in c
                 if isinstance(b, dict) and b.get("type") == "text" and b.get("text")]
        if texts:
            return "\n".join(texts)
        c = ""
    if isinstance(c, str) and c.strip():
        return c
    extra = getattr(msg, "additional_kwargs", {}) or {}
    rc = extra.get("reasoning_content", "") or ""
    if isinstance(rc, list):
        rc = "\n".join(b.get("text", "") for b in rc if isinstance(b, dict))
    # strip leaked "Thinking Process:" preamble if present
    if "A:" in rc and "Thinking Process" in rc:
        rc = rc.split("A:", 1)[-1]
    return rc.strip() if isinstance(rc, str) else (c or "")

TAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Tag the chunk into course/topic/subtopic/concept with difficulty. "
               "Figures: content_type=figure + one-line figure_caption."),
    ("human", "SOURCE: {source_file} (page={page} slide={slide} t={t_start}-{t_end})\n\n{content}"),
])

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Answer ONLY from the context. Every factual claim needs an inline "
               "citation like [file, p.N] / [file, slide N] / [file, MM:SS]. "
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
