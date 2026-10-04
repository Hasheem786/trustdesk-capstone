import pytest
from src.trustdesk.models.domain import KnowledgeDocument
from src.trustdesk.rag.retriever import KnowledgeRetriever
from src.trustdesk.rag.grounder import CitationGrounder

@pytest.fixture
def sample_kb_docs():
    return [
        KnowledgeDocument(
            doc_id="KB-REFUND-001",
            title="Returns Policy",
            category="refund",
            tags=["refund", "return", "30 days"],
            content="Returns accepted within 30 days of delivery.",
            is_active=True,
        ),
        KnowledgeDocument(
            doc_id="KB-WARRANTY-001",
            title="Hardware Warranty",
            category="warranty",
            tags=["warranty", "defect"],
            content="Hardware covered for 1 year.",
            is_active=True,
        ),
        KnowledgeDocument(
            doc_id="KB-SHIPPING-001",
            title="Shipping Timeline",
            category="shipping",
            tags=["shipping", "tracking"],
            content="Shipping takes 3-5 days.",
            is_active=True,
        ),
    ]

def test_retriever_preserves_document_ids(sample_kb_docs):
    retriever = KnowledgeRetriever(sample_kb_docs)
    results = retriever.retrieve("I want a refund for my item", top_k=2)
    assert len(results) > 0
    assert results[0].doc_id == "KB-REFUND-001"

def test_citation_extraction():
    grounder = CitationGrounder()
    text = "Per our policy [KB-REFUND-001] and warranty guidelines [KB-WARRANTY-001], returns are accepted."
    cits = grounder.extract_citations(text)
    assert cits == ["KB-REFUND-001", "KB-WARRANTY-001"]

def test_citation_grounding_verification(sample_kb_docs):
    grounder = CitationGrounder()
    # Case 1: valid citation in retrieved docs
    text_valid = "According to [KB-REFUND-001], items can be returned within 30 days."
    is_grounded, cited = grounder.verify_grounding(text_valid, sample_kb_docs)
    assert is_grounded is True
    assert cited == ["KB-REFUND-001"]

    # Case 2: hallucinated / invalid citation
    text_invalid = "According to our secret policy [KB-UNKNOWN-999], you get free money."
    is_grounded, cited = grounder.verify_grounding(text_invalid, sample_kb_docs)
    assert is_grounded is False
