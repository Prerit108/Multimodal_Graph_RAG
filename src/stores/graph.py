"""Concept/prerequisite graph via LangChain LLMGraphTransformer -> NetworkX."""
from __future__ import annotations
import networkx as nx

_graph = nx.DiGraph()


def add_topic_edge(concept: str, prereq: str = "", topic: str = "") -> None:
    _graph.add_node(concept, topic=topic)
    if prereq:
        _graph.add_node(prereq, topic=topic)
        _graph.add_edge(prereq, concept, kind="prerequisite")


def expand_prereqs(concepts: list[str], depth: int = 1) -> list[str]:
    out: list[str] = []
    for c in concepts:
        if c in _graph:
            out += list(_graph.predecessors(c))
    return out


def get_graph() -> nx.DiGraph:
    return _graph


def build_with_llm(texts: list[str]) -> int:
    """Lazy: uses LLMGraphTransformer (LangChain) only when called."""
    from langchain_experimental.graph_transformers import LLMGraphTransformer
    from langchain_core.documents import Document
    from src.chains.models import get_generator
    tr = LLMGraphTransformer(llm=get_generator())
    docs = [Document(page_content=t) for t in texts]
    gdocs = tr.convert_to_graph_documents(docs)
    n = 0
    for gd in gdocs:
        for node in gd.nodes:
            _graph.add_node(node.id, type=node.type)
        for e in gd.relationships:
            _graph.add_edge(e.source.id, e.target.id, kind=e.type); n += 1
    return n
