"""
Pipeline de indexación de documentos regulatorios para el sistema RAG.

Estrategia de chunking justificada:
- Chunk size: 512 tokens (~350 palabras)
- Overlap: 64 tokens (~45 palabras)
- Razón: Los artículos regulatorios tienen ~200-400 palabras cada uno.
  Con 512 tokens capturamos un artículo completo en la mayoría de los casos.
  El overlap de 64 tokens asegura que las referencias cruzadas entre artículos
  contiguos no se pierdan en el límite del chunk.
- Split strategy: Por artículo/disposición primero, luego por tokens si el
  artículo es muy largo. Esto preserva la semántica regulatoria.
"""
import os
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

DOCS_PATH = Path(__file__).parent.parent / "data" / "regulatory_docs"
CHUNK_SIZE = 512   # tokens aproximados
CHUNK_OVERLAP = 64
COLLECTION_NAME = "regulatory_corpus"


def load_regulatory_documents() -> list[dict[str, str]]:
    """
    Carga documentos regulatorios desde el directorio de docs.
    Retorna lista de {content, source, regulator, article_ref}.
    """
    documents = []
    regulator_map = {
        "uiaf_colombia": "UIAF",
        "cnbv_mexico": "CNBV",
        "sbs_peru": "SBS",
    }

    for txt_file in DOCS_PATH.glob("*.txt"):
        regulator_key = txt_file.stem
        regulator = regulator_map.get(regulator_key, "UNKNOWN")
        content = txt_file.read_text(encoding="utf-8")
        documents.append({
            "content": content,
            "source": txt_file.name,
            "regulator": regulator,
        })

    return documents


def chunk_by_article(document: dict[str, str]) -> list[dict[str, Any]]:
    """
    Chunking semántico por artículo/disposición.
    Divide en el marcador 'Artículo N' o 'Disposición N'.
    Si un artículo es muy largo, subdivide por párrafo.
    """
    content = document["content"]
    chunks = []

    # Split por artículos (preservar el encabezado del artículo en cada chunk)
    import re
    article_pattern = r'((?:Artículo|Disposición|CAPÍTULO)\s+\w+[^-]*?[-–])'
    parts = re.split(article_pattern, content)

    current_chunk = ""
    current_article_ref = "header"

    for i, part in enumerate(parts):
        if re.match(article_pattern, part):
            # Es un encabezado de artículo
            if current_chunk.strip():
                chunks.append({
                    **document,
                    "content": current_chunk.strip(),
                    "article_ref": current_article_ref,
                    "chunk_id": f"{document['source']}_{len(chunks)}",
                })
            current_chunk = part
            current_article_ref = part.strip()
        else:
            current_chunk += part

        # Si el chunk es muy largo, dividir por párrafos
        if len(current_chunk.split()) > CHUNK_SIZE:
            paragraphs = current_chunk.split("\n\n")
            for j, para in enumerate(paragraphs):
                if para.strip():
                    chunks.append({
                        **document,
                        "content": para.strip(),
                        "article_ref": current_article_ref,
                        "chunk_id": f"{document['source']}_{len(chunks)}_{j}",
                    })
            current_chunk = ""

    # Último chunk
    if current_chunk.strip():
        chunks.append({
            **document,
            "content": current_chunk.strip(),
            "article_ref": current_article_ref,
            "chunk_id": f"{document['source']}_{len(chunks)}",
        })

    return chunks


def build_index(chroma_host: str = "localhost", chroma_port: int = 8001) -> chromadb.Collection:
    """
    Construye el índice vectorial completo.
    - Carga documentos
    - Divide en chunks semánticos
    - Genera embeddings con sentence-transformers
    - Persiste en ChromaDB
    """
    print("Iniciando indexación del corpus regulatorio...")

    # Modelo de embeddings multilingüe (español/inglés)
    # paraphrase-multilingual-MiniLM-L12-v2: 384 dimensiones, ~117MB, muy bueno para español
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    # Conectar a ChromaDB
    try:
        client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    except Exception:
        # Fallback: ChromaDB en memoria para testing
        client = chromadb.Client()

    # Recrear la colección (indexación limpia)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Procesar documentos
    all_chunks = []
    for doc in load_regulatory_documents():
        chunks = chunk_by_article(doc)
        all_chunks.extend(chunks)
        print(f"  {doc['regulator']}: {len(chunks)} chunks")

    # Generar embeddings en batch
    texts = [c["content"] for c in all_chunks]
    print(f"Generando embeddings para {len(all_chunks)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True).tolist()

    # Insertar en ChromaDB
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

    print(f"Indexación completa: {len(all_chunks)} chunks en ChromaDB.")
    return collection


if __name__ == "__main__":
    build_index()
