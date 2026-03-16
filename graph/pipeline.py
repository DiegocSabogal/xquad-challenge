"""
Orquestación del pipeline de compliance usando LangGraph.

Grafo de estados:
  START
    └─> investigador_node
          └─> risk_analyzer_node
                └─> [conditional] ─> decision_node ─> END
                                  └─> (PEP fast-track) ─> END

Los nodos trabajan en secuencia. El sistema está diseñado para:
- Paralelismo futuro: investigador y búsqueda RAG pueden correr en paralelo
- Human-in-the-loop: el nodo 'decision' puede pausar en espera de revisión humana
"""
from typing import Any

from langgraph.graph import StateGraph, START, END

from data.models import AuditStep
from agents import investigador, risk_analyzer, decision_agent
from observability.langfuse_config import get_tracer


# ---------------------------------------------------------------------------
# Nodos del grafo
# ---------------------------------------------------------------------------

def investigador_node(state: dict[str, Any]) -> dict[str, Any]:
    """Nodo 1: construye el contexto del caso."""
    tracer = get_tracer()

    with tracer.span("investigador") as span:
        try:
            context, steps = investigador.run(state["alert_id"])
            span.update(output={"client_id": context.client_id, "is_pep": context.is_pep})
            return {
                **state,
                "case_context": context,
                "audit_trail": steps,
                "error": None,
            }
        except Exception as e:
            span.update(level="ERROR", status_message=str(e))
            return {**state, "error": str(e)}


def risk_analyzer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Nodo 2: analiza el riesgo del caso."""
    if state.get("error"):
        return state

    tracer = get_tracer()

    with tracer.span("risk_analyzer") as span:
        analysis, updated_trail = risk_analyzer.run(
            state["case_context"],
            state.get("audit_trail", []),
        )
        span.update(output={"risk_score": analysis.risk_score})
        return {
            **state,
            "risk_analysis": analysis,
            "audit_trail": updated_trail,
        }


def decision_node(state: dict[str, Any]) -> dict[str, Any]:
    """Nodo 3: toma la decisión final con contexto regulatorio (RAG)."""
    if state.get("error"):
        return state

    tracer = get_tracer()

    with tracer.span("decision_agent") as span:
        # Importar aquí para evitar circular import con RAG
        try:
            from rag.retriever import HybridRetriever
            retriever = HybridRetriever()
            context = state["case_context"]
            regulatory_context = retriever.retrieve(
                query=f"{context.alert_type} {context.country} {context.regulator.value}",
                regulator=context.regulator.value,
                top_k=3,
            )
            rag_text = "\n".join([r["content"] for r in regulatory_context])
        except Exception:
            rag_text = ""  # Si RAG falla, continúa sin contexto regulatorio

        decision, updated_trail = decision_agent.run(
            state["case_context"],
            state["risk_analysis"],
            state.get("audit_trail", []),
            regulatory_context=rag_text,
        )

        span.update(output={
            "decision": decision.decision.value,
            "confidence": decision.confidence,
            "is_pep_override": decision.is_pep_override,
        })

        return {
            **state,
            "decision": decision,
            "audit_trail": updated_trail,
        }


def should_continue(state: dict[str, Any]) -> str:
    """Routing condicional: si hay error, termina sin decisión."""
    if state.get("error"):
        return END
    return "risk_analyzer"


# ---------------------------------------------------------------------------
# Construccion del grafo
# ---------------------------------------------------------------------------

def build_pipeline() -> Any:
    """
    Construye y compila el grafo de compliance.
    Retorna el grafo compilado listo para invocar.
    """
    graph = StateGraph(dict)

    # Registrar nodos
    graph.add_node("investigador", investigador_node)
    graph.add_node("risk_analyzer", risk_analyzer_node)
    graph.add_node("decision", decision_node)

    # Definir edges
    graph.add_edge(START, "investigador")
    graph.add_conditional_edges(
        "investigador",
        should_continue,
        {"risk_analyzer": "risk_analyzer", END: END},
    )
    graph.add_edge("risk_analyzer", "decision")
    graph.add_edge("decision", END)

    return graph.compile()


# Instancia singleton del pipeline
_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline


async def run_pipeline(alert_id: str) -> dict[str, Any]:
    """
    Ejecuta el pipeline completo para una alerta.
    Entry point principal para la API.
    """
    pipeline = get_pipeline()
    initial_state = {
        "alert_id": alert_id,
        "case_context": None,
        "risk_analysis": None,
        "decision": None,
        "error": None,
        "audit_trail": [],
    }
    result = await pipeline.ainvoke(initial_state)
    return result
