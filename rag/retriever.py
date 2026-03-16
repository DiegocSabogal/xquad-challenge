"""
Sistema de recuperación híbrido para el corpus regulatorio.

Combina tres estrategias:
1. Dense retrieval  : embeddings semánticos (sentence-transformers + ChromaDB)
2. Sparse retrieval : BM25 para coincidencia exacta de términos legales
3. Graph retrieval  : referencias cruzadas entre artículos (NetworkX / Neo4j en producción)

La combinación mejora la precisión para preguntas regulatorias que mezclan
conceptos semánticos ("transferencia sospechosa") con términos exactos
("Artículo 15", "UIAF", "$50,000 USD").

Scoring final: score = α*dense + β*sparse + γ*graph  (α=0.5, β=0.3, γ=0.2)
"""
from pathlib import Path
from typing import Any

import chromadb
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from rag.graph_layer import get_graph, find_related_articles
from rag.indexer import load_regulatory_documents, chunk_by_article, COLLECTION_NAME

DOCS_PATH = Path(__file__).parent.parent / "data" / "regulatory_docs"

# Pesos del retrieval híbrido
ALPHA = 0.5   # Dense (semántico)
BETA = 0.3    # Sparse (BM25)
GAMMA = 0.2   # Graph


class HybridRetriever:
    """
    Retriever híbrido: dense + sparse + graph.
    Se inicializa en el primer uso (lazy loading).
    """

    def __init__(self, chroma_host: str = "localhost", chroma_port: int = 8001):
        self._chroma_host = chroma_host
        self._chroma_port = chroma_port
        self._embedder: SentenceTransformer | None = None
        self._collection: chromadb.Collection | None = None
        self._bm25: BM25Okapi | None = None
        self._bm25_corpus: list[dict[str, Any]] = []

    def _init_dense(self) -> None:
        """Inicializa el modelo de embeddings y la conexión a ChromaDB."""
        if self._embedder is None:
            try:
                self._embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
            except Exception:
                # torch no compatible (ej: Python 3.13 Windows) — dense search deshabilitado
                # El sistema continúa con BM25 + graph search
                return

        if self._collection is None:
            try:
                client = chromadb.HttpClient(host=self._chroma_host, port=self._chroma_port)
                self._collection = client.get_collection(COLLECTION_NAME)
            except Exception:
                # ChromaDB no disponible: usar colección en memoria con docs pre-cargados
                self._collection = self._build_in_memory_collection()

    def _build_in_memory_collection(self) -> chromadb.Collection:
        """Fallback: ChromaDB en memoria para entornos sin Docker."""
        client = chromadb.Client()
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

        collection = client.create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
        all_chunks = []
        for doc in load_regulatory_documents():
            all_chunks.extend(chunk_by_article(doc))

        if not all_chunks:
            return collection

        texts = [c["content"] for c in all_chunks]
        embeddings = self._embedder.encode(texts).tolist()
        collection.add(
            ids=[c["chunk_id"] for c in all_chunks],
            embeddings=embeddings,
            documents=texts,
            metadatas=[{
                "source": c["source"],
                "regulator": c["regulator"],
                "article_ref": c["article_ref"],
            } for c in all_chunks],
        )
        return collection

    def _init_sparse(self) -> None:
        """Inicializa el índice BM25 con el corpus de documentos."""
        if self._bm25 is not None:
            return

        self._bm25_corpus = []
        for doc in load_regulatory_documents():
            for chunk in chunk_by_article(doc):
                self._bm25_corpus.append(chunk)

        tokenized = [c["content"].lower().split() for c in self._bm25_corpus]
        if tokenized:
            self._bm25 = BM25Okapi(tokenized)

    def _dense_search(self, query: str, regulator: str | None, top_k: int) -> list[dict[str, Any]]:
        """Búsqueda semántica por embeddings. Retorna [] si embedder no disponible."""
        self._init_dense()
        if self._embedder is None or self._collection is None:
            return []
        query_embedding = self._embedder.encode([query]).tolist()

        where_filter = {"regulator": regulator} if regulator else None

        results = self._collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k * 2, 10),
            where=where_filter,
        )

        hits = []
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            hits.append({
                "content": doc,
                "source": meta["source"],
                "regulator": meta["regulator"],
                "article_ref": meta["article_ref"],
                "dense_score": 1.0 - dist,  # Convertir distancia coseno a similaridad
                "retrieved_via": "rag_dense",
            })
        return hits

    def _sparse_search(self, query: str, regulator: str | None, top_k: int) -> list[dict[str, Any]]:
        """Búsqueda BM25 para coincidencia exacta de términos legales."""
        self._init_sparse()
        if not self._bm25:
            return []

        scores = self._bm25.get_scores(query.lower().split())
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k * 2]

        hits = []
        for idx in top_indices:
            chunk = self._bm25_corpus[idx]
            if regulator and chunk.get("regulator") != regulator:
                continue
            if scores[idx] > 0:
                hits.append({
                    **chunk,
                    "sparse_score": float(scores[idx]),
                    "retrieved_via": "rag_sparse",
                })
        return hits

    def _graph_search(self, query: str, regulator: str | None, top_k: int) -> list[dict[str, Any]]:
        """
        Recupera artículos relacionados via el grafo de referencias.
        Detecta el tema de la query para buscar en el grafo.
        """
        graph = get_graph()

        # Detectar tema según keywords en la query
        topic_keywords = {
            "structuring": ["estructur", "smurfing", "fraccion"],
            "pep": ["pep", "político", "exposit", "politic"],
            "international": ["internac", "transfer", "extran", "panama"],
            "threshold": ["umbral", "monto", "límite", "50000", "50,000"],
            "ros": ["sospech", "reporte", "ros"],
        }

        detected_topics = []
        query_lower = query.lower()
        for topic, keywords in topic_keywords.items():
            if any(kw in query_lower for kw in keywords):
                detected_topics.append(topic)

        if not detected_topics:
            return []

        all_related = []
        for topic in detected_topics:
            related = find_related_articles(graph, topic, regulator, depth=2)
            all_related.extend(related)

        # Convertir a formato estándar con contenido del corpus
        hits = []
        loaded_docs = {doc["regulator"]: doc["content"] for doc in load_regulatory_documents()}

        for article in all_related[:top_k]:
            reg = article["regulator"]
            doc_content = loaded_docs.get(reg, "")
            hits.append({
                "content": f"[{article['article_id']}] {article['title']}: {doc_content[:300]}...",
                "source": f"{reg.lower()}_graph",
                "regulator": reg,
                "article_ref": article["article_id"],
                "graph_score": 1.0 if article["is_seed"] else 0.7,
                "retrieved_via": "graph_rag",
            })

        return hits

    def retrieve(
        self,
        query: str,
        regulator: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Ejecuta el retrieval híbrido y combina scores.

        Args:
            query: Pregunta o descripción de la alerta
            regulator: Filtrar por regulador específico (UIAF/CNBV/SBS)
            top_k: Número de resultados finales

        Returns:
            Lista de chunks ordenados por score híbrido descendente
        """
        dense_hits = self._dense_search(query, regulator, top_k)
        sparse_hits = self._sparse_search(query, regulator, top_k)
        graph_hits = self._graph_search(query, regulator, top_k)

        # Combinar y normalizar scores por chunk_id / contenido
        combined: dict[str, dict[str, Any]] = {}

        for hit in dense_hits:
            key = hit["article_ref"]
            combined[key] = {**hit, "hybrid_score": ALPHA * hit.get("dense_score", 0)}

        for hit in sparse_hits:
            key = hit["article_ref"]
            max_sparse = max((h.get("sparse_score", 0) for h in sparse_hits), default=1)
            norm_score = hit.get("sparse_score", 0) / max_sparse if max_sparse > 0 else 0
            if key in combined:
                combined[key]["hybrid_score"] += BETA * norm_score
            else:
                combined[key] = {**hit, "hybrid_score": BETA * norm_score}

        for hit in graph_hits:
            key = hit["article_ref"]
            if key in combined:
                combined[key]["hybrid_score"] += GAMMA * hit.get("graph_score", 0)
            else:
                combined[key] = {**hit, "hybrid_score": GAMMA * hit.get("graph_score", 0)}

        # Ordenar por score híbrido
        sorted_hits = sorted(combined.values(), key=lambda x: x["hybrid_score"], reverse=True)
        return sorted_hits[:top_k]
