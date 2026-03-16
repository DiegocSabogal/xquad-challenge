"""
Herramientas de Google Cloud Storage para extracción de documentos PDF.

En producción: usa google-cloud-storage para descargar PDFs de gs://finserv-docs/
y pypdf para extraer texto. Toda la operación permanece en us-central1.
En desarrollo/challenge: retorna resúmenes sintéticos pre-generados.
"""
from typing import Any

from data.mock_data import MOCK_GCS_DOCUMENTS


def list_client_documents(client_id: str) -> list[dict[str, str]]:
    """
    Lista los documentos PDF disponibles para un cliente en GCS.
    Simula: storage_client.list_blobs(bucket, prefix=f"{client_id}/")
    """
    return MOCK_GCS_DOCUMENTS.get(client_id, [])


def extract_document_content(gcs_path: str, client_id: str) -> str:
    """
    Extrae el contenido de texto de un PDF almacenado en GCS.
    Simula: download_blob() + PdfReader(bytes_io).pages[i].extract_text()

    NOTA: En producción, los datos NO salen de GCP (restricción regulatoria).
    El procesamiento con pypdf ocurre dentro del Cloud Run en us-central1.
    """
    docs = MOCK_GCS_DOCUMENTS.get(client_id, [])
    for doc in docs:
        if doc["gcs_path"] == gcs_path:
            return doc["content_summary"]
    return f"[Documento no encontrado: {gcs_path}]"


def get_all_client_documents_content(client_id: str) -> list[dict[str, Any]]:
    """
    Descarga y extrae el contenido de todos los documentos de un cliente.
    Retorna lista con metadatos + contenido extraído.
    """
    documents = list_client_documents(client_id)
    enriched = []
    for doc in documents:
        content = extract_document_content(doc["gcs_path"], client_id)
        enriched.append({
            **doc,
            "extracted_content": content,
        })
    return enriched
