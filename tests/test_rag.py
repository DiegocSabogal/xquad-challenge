"""
Tests para el sistema RAG + GraphRAG.
"""
import pytest
from rag.graph_layer import build_regulatory_graph, find_related_articles
from rag.retriever import HybridRetriever
from rag.indexer import load_regulatory_documents, chunk_by_article


class TestDocumentLoading:
    def test_loads_three_regulators(self):
        docs = load_regulatory_documents()
        regulators = {d["regulator"] for d in docs}
        assert "UIAF" in regulators
        assert "CNBV" in regulators
        assert "SBS" in regulators

    def test_chunks_have_content(self):
        docs = load_regulatory_documents()
        all_chunks = []
        for doc in docs:
            all_chunks.extend(chunk_by_article(doc))
        assert len(all_chunks) >= 5  # Mínimo 5 documentos según el challenge
        assert all(len(c["content"]) > 50 for c in all_chunks)


class TestGraphRAG:
    def setup_method(self):
        self.graph = build_regulatory_graph()

    def test_graph_has_nodes(self):
        assert self.graph.number_of_nodes() > 0

    def test_graph_has_edges(self):
        assert self.graph.number_of_edges() > 0

    def test_pep_articles_exist(self):
        pep_nodes = [n for n, d in self.graph.nodes(data=True) if d.get("topic") == "pep"]
        assert len(pep_nodes) >= 3  # Al menos uno por regulador

    def test_find_related_structuring_articles(self):
        related = find_related_articles(self.graph, "structuring", "UIAF")
        article_ids = [r["article_id"] for r in related]
        assert "UIAF-Art15" in article_ids  # Artículo de estructuración UIAF

    def test_graph_references_propagate(self):
        """UIAF-Art15 debería traer UIAF-Art8 (referencia cruzada)."""
        related = find_related_articles(self.graph, "structuring", "UIAF", depth=2)
        article_ids = [r["article_id"] for r in related]
        assert "UIAF-Art8" in article_ids

    def test_cross_regulator_relations_exist(self):
        """Debe haber edges de tipo similar_concept entre reguladores."""
        edges = [(u, v, d) for u, v, d in self.graph.edges(data=True)
                 if d.get("relationship") == "similar_concept"]
        assert len(edges) > 0


class TestHybridRetriever:
    def setup_method(self):
        self.retriever = HybridRetriever()

    def test_retrieve_returns_results(self):
        results = self.retriever.retrieve("transferencia internacional estructuración")
        assert len(results) > 0

    def test_retrieve_with_regulator_filter(self):
        results = self.retriever.retrieve("PEP persona políticamente expuesta", regulator="UIAF")
        regulators = {r["regulator"] for r in results}
        assert "UIAF" in regulators

    def test_results_have_required_fields(self):
        results = self.retriever.retrieve("reporte de operaciones sospechosas")
        for r in results:
            assert "content" in r
            assert "regulator" in r
            assert "retrieved_via" in r
            assert "hybrid_score" in r

    def test_results_sorted_by_score(self):
        results = self.retriever.retrieve("PEP escalar compliance")
        scores = [r["hybrid_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_pep_query_retrieves_pep_articles(self):
        """Una query sobre PEPs debe recuperar artículos sobre PEPs."""
        results = self.retriever.retrieve("persona políticamente expuesta PEP obligaciones")
        has_pep_content = any(
            "PEP" in r["content"] or "políticamente" in r["content"].lower()
            for r in results
        )
        assert has_pep_content
