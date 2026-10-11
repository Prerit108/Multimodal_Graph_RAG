"""Shared typed schemas: CitationUnit, graph States, quiz models."""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


class CitationUnit(BaseModel):
    course: str = "general"
    topic: str
    subtopic: str = ""
    concept: str = ""
    content_type: Literal["textbook", "slide", "video", "figure"] = "textbook"
    source_file: str
    page: Optional[int] = None
    slide: Optional[int] = None
    t_start: Optional[float] = None
    t_end: Optional[float] = None
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    figure_caption: Optional[str] = None

    def deep_link(self) -> str:
        if self.page is not None:
            return f"{self.source_file}#page={self.page}"
        if self.slide is not None:
            return f"{self.source_file}#slide={self.slide}"
        if self.t_start is not None:
            return f"{self.source_file}?t={self.t_start:.0f}s"
        return self.source_file

    def cite(self) -> str:
        if self.page is not None:
            return f"[{self.source_file}, p.{self.page}]"
        if self.slide is not None:
            return f"[{self.source_file}, slide {self.slide}]"
        if self.t_start is not None:
            m, s = divmod(int(self.t_start), 60)
            return f"[{self.source_file}, {m:02d}:{s:02d}]"
        return f"[{self.source_file}]"


# --- LangGraph States (as TypedDicts in graphs; pydantic mirrors here) ---
class TutorState(BaseModel):
    student_id: str = "anon"
    question: str = ""
    topic_filter: Optional[str] = None
    docs: list = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    answer: str = ""
    verdict: Literal["answer", "refuse"] = "answer"


class QuizQuestion(BaseModel):
    qtype: Literal["mcq", "short", "numerical"]
    stem: str
    options: list[str] = Field(default_factory=list)
    answer_key: str
    topic: str
    source: str = ""          # deep link
    difficulty: str = "medium"
    explanation: str = ""
    qhash: str = ""


class QuizState(BaseModel):
    student_id: str = "anon"
    scope: str = ""
    difficulty_target: str = "medium"
    n_questions: int = 5
    questions: list[QuizQuestion] = Field(default_factory=list)
    results: list[dict] = Field(default_factory=list)
    weak_topics: list[str] = Field(default_factory=list)
