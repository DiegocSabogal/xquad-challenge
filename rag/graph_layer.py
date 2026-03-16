"""
Graph layer para el sistema GraphRAG.

Modela relaciones entre artículos regulatorios:
- "Artículo 15 hace referencia al Artículo 8"
- "Esta circular deroga la disposición anterior"
- "Artículo 20 complementa el Artículo 18"

Tecnología: NetworkX para el challenge (simple, sin dependencias externas).
En producción: Neo4j o FalkorDB en GCP para escalar a miles de artículos
con queries Cypher complejas.

El grafo mejora la precisión cuando una consulta requiere razonamiento sobre
múltiples artículos relacionados (ej: "¿Qué aplica para una transferencia
internacional de $50,000 desde una persona jurídica en Panamá?")
"""
import re
from pathlib import Path
from typing import Any

import networkx as nx

DOCS_PATH = Path(__file__).parent.parent / "data" / "regulatory_docs"


def build_regulatory_graph() -> nx.DiGraph:
    """
    Construye el grafo de relaciones regulatorias.
    Nodos: artículos individuales.
    Edges: referencias cruzadas entre artículos.

    En producción con Neo4j, estos edges se modelarían como:
    (:Article {id: "UIAF-Art15"})-[:REFERENCES]->(:Article {id: "UIAF-Art8"})
    """
    G = nx.DiGraph()

    # -----------------------------------------------------------------------
    # Nodos: artículos del corpus regulatorio
    # -----------------------------------------------------------------------
    articles = {
        # UIAF Colombia
        "UIAF-Art1": {"regulator": "UIAF", "title": "Objeto y Alcance", "topic": "general"},
        "UIAF-Art5": {"regulator": "UIAF", "title": "Reporte de Operaciones Sospechosas", "topic": "ros"},
        "UIAF-Art8": {"regulator": "UIAF", "title": "Umbral de Reporte Efectivo", "topic": "threshold"},
        "UIAF-Art15": {"regulator": "UIAF", "title": "Estructuración (Smurfing)", "topic": "structuring"},
        "UIAF-Art18": {"regulator": "UIAF", "title": "Transferencias Internacionales", "topic": "international"},
        "UIAF-Art20": {"regulator": "UIAF", "title": "Debida Diligencia Reforzada", "topic": "enhanced_dd"},
        "UIAF-Art25": {"regulator": "UIAF", "title": "Definición de PEP", "topic": "pep"},
        "UIAF-Art26": {"regulator": "UIAF", "title": "Obligaciones para Clientes PEP", "topic": "pep"},
        # CNBV México
        "CNBV-D100": {"regulator": "CNBV", "title": "Marco General", "topic": "general"},
        "CNBV-D105": {"regulator": "CNBV", "title": "Avisos de Operaciones Relevantes", "topic": "threshold"},
        "CNBV-D110": {"regulator": "CNBV", "title": "Operaciones Inusuales", "topic": "unusual"},
        "CNBV-D115": {"regulator": "CNBV", "title": "Operaciones Preocupantes", "topic": "ros"},
        "CNBV-D115B": {"regulator": "CNBV", "title": "PEPs", "topic": "pep"},
        "CNBV-D120": {"regulator": "CNBV", "title": "Lista de Cargos PEP México", "topic": "pep"},
        "CNBV-D130": {"regulator": "CNBV", "title": "Transferencias Internacionales", "topic": "international"},
        # SBS Perú
        "SBS-Art1": {"regulator": "SBS", "title": "Objetivo", "topic": "general"},
        "SBS-Art5": {"regulator": "SBS", "title": "Sistema de Detección Automática", "topic": "ai_limits"},
        "SBS-Art8": {"regulator": "SBS", "title": "Umbrales de Reporte Perú", "topic": "threshold"},
        "SBS-Art15": {"regulator": "SBS", "title": "Transacciones Fraccionadas", "topic": "structuring"},
        "SBS-Art18": {"regulator": "SBS", "title": "PEPs", "topic": "pep"},
        "SBS-Art22": {"regulator": "SBS", "title": "Beneficiario Final", "topic": "beneficial_owner"},
        "SBS-Art25": {"regulator": "SBS", "title": "Jurisdicciones de Alto Riesgo", "topic": "international"},
    }

    for node_id, attrs in articles.items():
        G.add_node(node_id, **attrs)

    # -----------------------------------------------------------------------
    # Edges: referencias cruzadas explícitas en el texto
    # -----------------------------------------------------------------------
    references = [
        # UIAF
        ("UIAF-Art15", "UIAF-Art8", "references"),       # Estructuración -> Umbrales
        ("UIAF-Art18", "UIAF-Art20", "references"),       # Internacionales -> DD Reforzada
        ("UIAF-Art20", "UIAF-Art25", "references"),       # DD Reforzada -> PEP definición
        ("UIAF-Art26", "UIAF-Art20", "extends"),          # PEP obligaciones extiende DD
        # CNBV
        ("CNBV-D115B", "CNBV-D120", "references"),       # PEPs -> Lista cargos PEP
        ("CNBV-D110", "CNBV-D115", "related_to"),        # Inusuales relacionado con Preocupantes
        ("CNBV-D130", "CNBV-D105", "references"),        # Internacionales -> Umbrales
        # SBS
        ("SBS-Art15", "SBS-Art8", "references"),         # Fraccionadas -> Umbrales
        ("SBS-Art18", "SBS-Art5", "references"),         # PEPs limita decisiones de IA
        ("SBS-Art25", "SBS-Art18", "extends"),           # Jurisdicciones + PEP
        ("SBS-Art22", "SBS-Art18", "related_to"),        # Beneficiario final + PEP
        # Relaciones cross-regulador (misma temática)
        ("UIAF-Art15", "CNBV-D130", "similar_concept"),  # Estructuración similar en MX
        ("UIAF-Art15", "SBS-Art15", "similar_concept"),  # Estructuración similar en PE
        ("UIAF-Art26", "CNBV-D115B", "similar_concept"), # PEPs Colombia ~ PEPs México
        ("UIAF-Art26", "SBS-Art18", "similar_concept"),  # PEPs Colombia ~ PEPs Perú
    ]

    for src, dst, rel_type in references:
        G.add_edge(src, dst, relationship=rel_type)

    return G


def find_related_articles(
    graph: nx.DiGraph,
    topic: str,
    regulator: str | None = None,
    depth: int = 2,
) -> list[dict[str, Any]]:
    """
    Encuentra artículos relacionados a un tema, siguiendo referencias cruzadas
    hasta una profundidad N en el grafo.

    Esto permite responder preguntas como:
    "¿Qué aplica para estructuración en Colombia?"
    -> UIAF-Art15 (directo) + UIAF-Art8 (referenciado) + UIAF-Art5 (relacionado)
    """
    # Encontrar nodos semilla por tema
    seed_nodes = [
        n for n, attrs in graph.nodes(data=True)
        if topic.lower() in attrs.get("topic", "").lower()
        and (regulator is None or attrs.get("regulator") == regulator)
    ]

    # BFS hasta depth N para encontrar artículos relacionados
    related = set(seed_nodes)
    for _ in range(depth):
        new_related = set()
        for node in related:
            # Artículos que este referencia
            new_related.update(graph.successors(node))
            # Artículos que referencian a este
            new_related.update(graph.predecessors(node))
        related.update(new_related)

    return [
        {
            "article_id": node,
            "regulator": graph.nodes[node].get("regulator"),
            "title": graph.nodes[node].get("title"),
            "topic": graph.nodes[node].get("topic"),
            "is_seed": node in seed_nodes,
        }
        for node in related
    ]


# Instancia singleton del grafo
_graph: nx.DiGraph | None = None


def get_graph() -> nx.DiGraph:
    global _graph
    if _graph is None:
        _graph = build_regulatory_graph()
    return _graph
