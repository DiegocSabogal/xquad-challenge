"""
API FastAPI — Capa de exposición del pipeline de compliance.

Endpoints:
  POST /alerts/{alert_id}/process  -> Ejecuta el pipeline completo
  GET  /alerts/{alert_id}/status   -> Estado de una alerta procesada
  GET  /health                     -> Health check para Cloud Run / Docker
"""
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from data.mock_data import MOCK_ALERTS
from graph.pipeline import run_pipeline

app = FastAPI(
    title="FinServ LATAM Compliance Agent",
    description="Sistema multi-agente para análisis automático de alertas de compliance "
                "(UIAF Colombia · CNBV México · SBS Perú)",
    version="1.0.0",
)

# Cache en memoria (en producción: Redis o Firestore)
_processed_alerts: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Schemas de respuesta
# ---------------------------------------------------------------------------

class ProcessAlertResponse(BaseModel):
    alert_id: str
    decision: str
    confidence: float
    risk_score: int
    is_pep_override: bool
    final_summary: str
    pipeline_duration_ms: float | None
    processed_at: str
    audit_trail_steps: int


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["Sistema"])
async def health_check():
    """Health check para orquestadores (Cloud Run, Docker Compose)."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
    )


@app.get("/alerts", tags=["Alertas"])
async def list_available_alerts():
    """Lista las alertas disponibles en el sistema (mock)."""
    return {
        "alerts": list(MOCK_ALERTS.values()),
        "total": len(MOCK_ALERTS),
        "note": "Datos sintéticos. En producción: query a Elasticsearch.",
    }


@app.post(
    "/alerts/{alert_id}/process",
    response_model=ProcessAlertResponse,
    tags=["Alertas"],
    summary="Procesa una alerta a través del pipeline multi-agente",
)
async def process_alert(alert_id: str):
    """
    Ejecuta el pipeline completo para una alerta:
    1. Agente Investigador: construye contexto del caso
    2. Agente de Riesgo: clasifica riesgo 1-10
    3. Agente de Decisión: decide con contexto regulatorio (RAG)

    Retorna la decisión con audit trail completo (requerimiento UIAF/CNBV/SBS).
    """
    if alert_id not in MOCK_ALERTS:
        raise HTTPException(
            status_code=404,
            detail=f"Alerta {alert_id} no encontrada. "
                   f"Alertas disponibles: {list(MOCK_ALERTS.keys())}",
        )

    # Ejecutar pipeline
    result = await run_pipeline(alert_id)

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    decision = result["decision"]
    analysis = result["risk_analysis"]

    # Guardar en cache
    _processed_alerts[alert_id] = result

    return ProcessAlertResponse(
        alert_id=alert_id,
        decision=decision.decision.value,
        confidence=decision.confidence,
        risk_score=analysis.risk_score,
        is_pep_override=decision.is_pep_override,
        final_summary=decision.final_summary,
        pipeline_duration_ms=decision.pipeline_duration_ms,
        processed_at=decision.decided_at.isoformat(),
        audit_trail_steps=len(decision.reasoning_chain),
    )


@app.get(
    "/alerts/{alert_id}/audit",
    tags=["Alertas"],
    summary="Retorna el audit trail completo de una alerta procesada",
)
async def get_audit_trail(alert_id: str):
    """
    Retorna el audit trail completo requerido por reguladores.
    Cada paso documenta qué agente actuó, qué acción tomó y por qué.
    """
    if alert_id not in _processed_alerts:
        raise HTTPException(
            status_code=404,
            detail=f"Alerta {alert_id} no ha sido procesada aún. "
                   f"Usar POST /alerts/{alert_id}/process primero.",
        )

    result = _processed_alerts[alert_id]
    decision = result["decision"]

    return {
        "alert_id": alert_id,
        "decision": decision.decision.value,
        "regulatory_references": [r.model_dump() for r in decision.regulatory_references],
        "audit_trail": [step.model_dump() for step in decision.reasoning_chain],
        "compliance_note": "Este audit trail cumple los requisitos de trazabilidad "
                           "UIAF (Colombia), CNBV (México) y SBS (Perú).",
    }
