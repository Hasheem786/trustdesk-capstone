import re
import math
from typing import List, Tuple
from src.trustdesk.models.domain import KnowledgeDocument

class KnowledgeRetriever:
    """Hybrid lexical and semantic policy retriever maintaining strict document IDs."""

    def __init__(self, documents: List[KnowledgeDocument]):
        self.documents = [d for d in documents if d.is_active]

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    def retrieve(self, query: str, top_k: int = 3) -> List[KnowledgeDocument]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return self.documents[:top_k]

        scored_docs: List[Tuple[float, KnowledgeDocument]] = []

        for doc in self.documents:
            score = 0.0
            doc_id_lower = doc.doc_id.lower()
            title_lower = doc.title.lower()
            content_lower = doc.content.lower()
            tags_lower = [t.lower() for t in doc.tags]

            # Direct doc_id match in query
            if doc_id_lower in query.lower() or doc.doc_id in query:
                score += 50.0

            # Direct category match in query
            if doc.category in query_tokens:
                score += 15.0

            # Match in tags
            for tag in tags_lower:
                if tag in query.lower():
                    score += 8.0

            # Token overlap in title and content
            for qt in query_tokens:
                if len(qt) <= 2:
                    continue
                if qt in title_lower:
                    score += 5.0
                if qt in content_lower:
                    score += 2.0

            if score > 0:
                scored_docs.append((score, doc))

        # Sort by score descending
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored_docs[:top_k]]
