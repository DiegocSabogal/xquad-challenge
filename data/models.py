"""
Modelos Pydantic compartidos por todos los agentes y la API.
Definen el contrato de datos del sistema.
"""
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class DecisionType(str, Enum):
    ESCALATE = "escalate"        # Escalar al humano
    DISCARD = "discard"          # Descartar la alerta
    REQUEST_INFO = "request_info"  # Solicitar información adicional


class RegulatoryBody(str, Enum):
    UIAF = "UIAF"   # Colombia
    CNBV = "CNBV"   # Mexico
    SBS = "SBS"     # Peru


# ---------------------------------------------------------------------------
# Salida del Agente Investigador
# ---------------------------------------------------------------------------

class CaseContext(BaseModel):
    alert_id: str
    client_id: str
    is_pep: bool = False
    pep_category: str | None = None
    regulator: RegulatoryBody
    country: str
    xgboost_score: float
    alert_type: str
    transactions_last_90d: list[dict[str, Any]]
    transaction_count: int
    total_volume_usd: float
    flagged_transactions: list[dict[str, Any]]
    documents: list[dict[str, str]]
    context_built_at: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Salida del Agente de Análisis de Riesgo
# ---------------------------------------------------------------------------

class AnomalousPattern(BaseModel):
    pattern_type: str
    description: str
    severity: str  # low | medium | high


class RiskAnalysis(BaseModel):
    alert_id: str
    risk_score: int = Field(ge=1, le=10, description="Nivel de riesgo 1-10")
    risk_justification: str
    anomalous_patterns: list[AnomalousPattern]
    analyst_summary: str  # Resumen en lenguaje natural para el analista humano
    analyzed_at: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Salida del Agente de Decisión (con audit trail completo)
# ---------------------------------------------------------------------------

class RegulatoryReference(BaseModel):
    article: str
    body: RegulatoryBody
    description: str
    retrieved_via: str  # "rag_dense" | "rag_sparse" | "graph_rag"


class AuditStep(BaseModel):
    step: int
    agent: str
    action: str
    reasoning: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ComplianceDecision(BaseModel):
    alert_id: str
    decision: DecisionType
    confidence: float = Field(ge=0.0, le=1.0)
    regulatory_references: list[RegulatoryReference]
    reasoning_chain: list[AuditStep]  # Audit trail paso a paso
    is_pep_override: bool = False  # True si se escalo por ser PEP independientemente del riesgo
    final_summary: str
    decided_at: datetime = Field(default_factory=datetime.now)
    pipeline_duration_ms: float | None = None


# ---------------------------------------------------------------------------
# Estado global del grafo LangGraph
# ---------------------------------------------------------------------------

class PipelineState(BaseModel):
    alert_id: str
    case_context: CaseContext | None = None
    risk_analysis: RiskAnalysis | None = None
    decision: ComplianceDecision | None = None
    error: str | None = None
    audit_trail: list[AuditStep] = Field(default_factory=list)
