"""Tests for RAG issues from Issues.txt."""
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document

# Test fixtures
@pytest.fixture
def sample_table_text():
    return """Name Type Description CreationDate DateTime This is the date of submission? [easy] Building Machine Learning Systems with Python - Second Edition.pdf#page=119
OwnerUserId Id This is a unique identifier of the poster? [easy] Building Machine Learning Systems with Python - Second Edition.pdf#page=119
Score Integer This is the score of the post? [easy] Building Machine Learning Systems with Python - Second Edition.pdf#page=119
com/qa: This Q&A site is laser-focused on machine learning topics? [easy] Building Machine Learning Systems with Python - Second Edition.pdf#page=26
com: This Q&A site is named Cross Validated, similar to MetaOptimize, but is focused more on statistical problems? [easy] Building Machine Learning Systems with Python - Second Edition.pdf#page=26
For almost every question, it contains above average answers from machine learning experts? [easy] Building Machine Learning Systems with Python - Second Edition.pdf#page=26"""

@pytest.fixture
def sample_good_text():
    return """Photosynthesis converts light energy into chemical energy in chloroplasts. Chlorophyll absorbs red and blue light. The Calvin cycle fixes carbon dioxide into glucose."""

def test_quiz_count_exact():
    """Quiz generator must return exactly n questions, never more."""
    from src.graphs.quiz_graph import build_quiz_graph
    from src.chains.prompts import QuizOutput, QuizQuestionItem
    
    # Mock the quiz chain to return 6 questions when n=4 (structured output)
    fake_questions = [
        QuizQuestionItem(
            stem=f"Question {i}?", qtype="short", options=[],
            answer_key=f"Answer {i}", topic="test", src="test.pdf",
            explanation=f"See test.pdf"
        )
        for i in range(1, 7)
    ]
    fake_output = QuizOutput(questions=fake_questions)
    
    def mock_invoke(inputs):
        return fake_output
    
    mock_chain = MagicMock()
    mock_chain.invoke = mock_invoke
    
    with patch("src.chains.prompts.get_quiz_chain", return_value=mock_chain):
        with patch("src.stores.vector.hybrid_search", return_value=[Document(page_content="test context", metadata={"source_file": "test.pdf"})]):
            app = build_quiz_graph()
            result = app.invoke({"student_id": "test", "scope": "test", "difficulty_target": "easy", "n_questions": 4, "questions": [], "results": [], "weak_topics": []})
            assert len(result["questions"]) == 4, f"Expected 4 questions, got {len(result['questions'])}"

def test_quiz_no_table_junk(sample_table_text):
    """Quiz must not generate questions from table/header/URL junk."""
    from src.graphs.quiz_graph import _quiz_worthy_sentences
    
    sentences = _quiz_worthy_sentences(sample_table_text)
    # Should reject all table/URL/header lines
    assert len(sentences) == 0, f"Expected 0 quiz-worthy sentences from table junk, got: {sentences}"

def test_tutor_no_raw_dump():
    """Tutor must not dump raw chunks when LLM returns empty."""
    from src.graphs.tutor_graph import n_generate
    
    # Mock LLM to return empty
    def mock_invoke(inputs):
        class MockMsg:
            content = ""
        return MockMsg()
    
    mock_chain = MagicMock()
    mock_chain.invoke = mock_invoke
    
    with patch("src.chains.prompts.get_answer_chain", return_value=mock_chain):
        with patch("src.stores.learner.get_mastery", return_value=0.5):
            state = {
                "verdict": "answer",
                "question": "What is photosynthesis?",
                "docs": [
                    Document(page_content="Photosynthesis is the process...", metadata={"source_file": "test.pdf", "page": 1}),
                    Document(page_content="Chlorophyll absorbs light...", metadata={"source_file": "test.pdf", "page": 2}),
                ],
                "context": "",
                "citations": [],
                "answer": "",
            }
            result = n_generate(state)
            # Should not contain raw "Based on your material:" + chunk dump
            assert "Based on your material:" not in result["answer"]
            assert "Photosynthesis is the process" not in result["answer"] or "[test.pdf, p.1]" in result["answer"]

def test_chunk_preserves_page():
    """Chunks must never mix pages; each must have page number."""
    from src.graphs.ingest_graph import n_split
    from src.config.settings import Settings
    from langchain_core.documents import Document
    
    # Create a mock document with 2 pages
    doc1 = Document(page_content="Page 1 content. " * 50, metadata={"source_file": "test.pdf", "page": 1, "content_type": "textbook"})
    doc2 = Document(page_content="Page 2 content. " * 50, metadata={"source_file": "test.pdf", "page": 2, "content_type": "textbook"})
    
    state = {"file": "test.pdf", "kind": "pdf", "raw_docs": [doc1, doc2], "units": [], "errors": []}
    
    # Patch settings
    with patch("src.graphs.ingest_graph.get_settings") as mock_settings:
        mock_settings.return_value = Settings(CHUNK_SIZE=900, CHUNK_OVERLAP=135)
        result = n_split(state)
        
        for unit in result["units"]:
            assert "page" in unit, "Every chunk must have page number"
            assert unit["page"] in (1, 2), f"Page must be 1 or 2, got {unit['page']}"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])