"""LangChain prompt templates + structured chains (tag/answer/verify/quiz/VLM)."""
from __future__ import annotations
from typing import List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, Field
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

# Structured output for quiz questions
class QuizQuestionItem(BaseModel):
    stem: str = Field(description="The question stem/text")
    qtype: str = Field(description="Question type: mcq, short, or numerical")
    options: List[str] = Field(default_factory=list, description="Options for MCQ (4 options)")
    answer_key: str = Field(description="Correct answer or answer key")
    topic: str = Field(description="Specific topic/concept this question tests")
    src: str = Field(description="Source reference from context (e.g., SOURCE: filename#page=3)")
    explanation: str = Field(description="Brief explanation of the answer")

class QuizOutput(BaseModel):
    questions: List[QuizQuestionItem] = Field(description="List of questions")

QUIZ_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Write EXACTLY {n} questions ({types}) on scope '{scope}' at {difficulty} level. "
               "Each question MUST follow this exact format:\n"
               "Q1: <stem> | TYPE: <mcq|short|numerical> | A: <answer_key> | TOPIC: <topic> | SRC: <source_ref>\n"
               "For MCQ, include 4 options in the stem (A, B, C, D).\n"
               "Rules:\n"
               "1. Ground every question in the provided context\n"
               "2. Use ONLY the SOURCE references from context (e.g., [SOURCE: file#page=3])\n"
               "3. NO table headers, NO URL fragments, NO code, NO 'com/qa' or 'com:' lines\n"
               "4. Questions must be conceptual, test understanding not memorization of IDs\n"
               "5. Mix question types: MCQ, short answer, numerical\n"
               "6. Stop after EXACTLY {n} questions"),
    ("human", "CONTEXT:\n{context}"),
])

# VLM prompt for image/slide/figure captioning
VLM_CAPTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are a precise visual analyst for educational content. "
               "Describe the image/figure/slide in one clear sentence focusing on the educational concept shown. "
               "Include: what type of diagram (flowchart, graph, table, photo, equation), "
               "the main subject, key labels/data visible, and the educational purpose. "
               "Output format: CAPTION: <one-sentence description>"),
    ("human", [
        {"type": "text", "text": "Context: This is from a {content_type} (page={page}, slide={slide}, topic={topic}). Describe the educational content."},
        {"type": "image_url", "image_url": {"url": "data:image/{image_format};base64,{image_b64}"}}
    ]),
])


def get_tag_chain():
    return TAG_PROMPT | get_generator().with_structured_output(CitationUnit)


def get_answer_chain():
    return ANSWER_PROMPT | get_generator() | RunnableLambda(_content)


def get_verify_chain():
    return VERIFY_PROMPT | get_verifier() | RunnableLambda(_content)


def get_quiz_chain():
    # Use structured output for reliable parsing and exact count
    return QUIZ_PROMPT | get_generator().with_structured_output(QuizOutput)


def get_vlm_caption_chain():
    """VLM chain for captioning images/figures/slides. Uses vision-capable model."""
    return VLM_CAPTION_PROMPT | get_generator() | RunnableLambda(_content)