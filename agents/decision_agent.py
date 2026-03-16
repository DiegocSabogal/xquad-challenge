"""
Agente 3: Agente de Decisión
Responsabilidad: con base en el análisis de riesgo y el corpus regulatorio (RAG),
decide si escalar al humano, descartar la alerta, o solicitar información adicional.

REGLA CRÍTICA: Clientes PEP siempre escalan, independientemente del score de riesgo.
Esta regla es hardcoded — no delegada al LLM — para garantizar compliance regulatorio.
"""
import json
from datetime import datetime

from config import settings
from data.models import (
    CaseContext,
    RiskAnalysis,
    ComplianceDecision,
    DecisionType,
    AuditStep,
    RegulatoryReference,
)
from tools.llm_client import get_llm_client

SYSTEM_PROMPT = """Eres el agente de decisión de un sistema de compliance financiero regulado
(UIAF Colombia, CNBV México, SBS Perú).

Tu tarea es generar una decisión final estructurada en JSON con estos campos:
- decision: "escalate" | "discard" | "request_info"
- confidence: float 0.0-1.0
- regulatory_references: lista de artículos relevantes con {article, body, description, retrieved_via}
- reasoning_chain: lista de pasos de razonamiento {step, agent, action, reasoning}
- is_pep_override: boolean
- final_summary: string resumen de la decisión

REGLAS OBLIGATORIAS (no negociables):
1. Si el cliente es PEP (persona políticamente expuesta): decision = "escalate" SIEMPRE
2. Si risk_score >= 7: decision = "escalate"
3. Si risk_score <= 3: decision = "discard"
4. Si 4 <= risk_score <= 6: decision = "request_info"

El audit trail debe ser detallado suficiente para satisfacer una auditoría regulatoria.
Responde ÚNICAMENTE con el JSON."""


def run(
    context: CaseContext,
    analysis: RiskAnalysis,
    audit_trail: list[AuditStep],
    regulatory_context: str = "",
) -> tuple[ComplianceDecision, list[AuditStep]]:
    """
    Ejecuta el agente de decisión.

    Args:
        context: Contexto del caso (del Agente Investigador)
        analysis: Análisis de riesgo (del Agente Analizador)
        audit_trail: Trail de pasos previos
        regulatory_context: Artículos regulatorios recuperados via RAG
    """
    start_time = datetime.now()

    # -----------------------------------------------------------------------
    # REGLA CRÍTICA: PEP override — hardcoded, no delegado al LLM
    # Garantiza compliance regulatorio independientemente de la respuesta del modelo
    # -----------------------------------------------------------------------
    if context.is_pep:
        audit_trail.append(AuditStep(
            step=len(audit_trail) + 1,
            agent="decision_agent",
            action="pep_mandatory_escalation",
            reasoning=f"Cliente identificado como PEP ({context.pep_category}). "
                      f"Normativa {context.regulator.value} exige escalación obligatoria "
                      f"para todas las alertas de PEPs, independientemente del score de riesgo "
                      f"({analysis.risk_score}/10). Esta regla NO es delegada al LLM.",
        ))

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        return ComplianceDecision(
            alert_id=context.alert_id,
            decision=DecisionType.ESCALATE,
            confidence=1.0,
            regulatory_references=[
                RegulatoryReference(
                    article=_get_pep_article(context.regulator.value),
                    body=context.regulator,
                    description="Monitoreo reforzado obligatorio para Personas Políticamente Expuestas.",
                    retrieved_via="hardcoded_rule",
                )
            ],
            reasoning_chain=audit_trail,
            is_pep_override=True,
            final_summary=(
                f"ESCALACIÓN OBLIGATORIA: Cliente PEP ({context.pep_category}). "
                f"Normativa {context.regulator.value} exige revisión humana para todas "
                f"las alertas de personas políticamente expuestas sin excepción."
            ),
            pipeline_duration_ms=duration_ms,
        ), audit_trail

    # -----------------------------------------------------------------------
    # Flujo normal: el LLM toma la decisión con contexto regulatorio
    # -----------------------------------------------------------------------
    llm = get_llm_client()

    user_message = f"""
CONTEXTO DEL CASO:
- Alert ID: {context.alert_id}
- Tipo de alerta: {context.alert_type}
- Regulador: {context.regulator.value}
- País: {context.country}
- Es PEP: {context.is_pep}

ANÁLISIS DE RIESGO:
- Score: {analysis.risk_score}/10
- Justificación: {analysis.risk_justification}
- Patrones anómalos: {len(analysis.anomalous_patterns)}
- Resumen para analista: {analysis.analyst_summary}

ARTÍCULOS REGULATORIOS RELEVANTES (del sistema RAG):
{regulatory_context if regulatory_context else "No se recuperaron artículos específicos."}

UMBRALES DE DECISIÓN CONFIGURADOS:
- Escalación: score >= {settings.risk_threshold_escalate}
- Descarte: score <= {settings.risk_threshold_discard}
"""

    raw_response = llm.complete_json(SYSTEM_PROMPT, user_message)

    audit_trail.append(AuditStep(
        step=len(audit_trail) + 1,
        agent="decision_agent",
        action="llm_decision",
        reasoning=f"Decisión: {raw_response['decision']}. "
                  f"Confianza: {raw_response['confidence']:.0%}. "
                  f"Referencias regulatorias: {len(raw_response.get('regulatory_references', []))}.",
    ))

    # Normalizar body: Claude puede devolver texto largo como "CIRCULAR BASICA - UIAF COLOMBIA"
    # Extraemos el codigo del regulador (UIAF, CNBV, SBS) buscando en el string
    _body_map = {"UIAF": "UIAF", "CNBV": "CNBV", "SBS": "SBS"}

    def _normalize_ref(r: dict) -> dict:
        body_raw = str(r.get("body", "UIAF")).upper()
        body_code = next((k for k in _body_map if k in body_raw), "UIAF")
        return {**r, "body": body_code}

    refs = [
        RegulatoryReference(**_normalize_ref(r))
        for r in raw_response.get("regulatory_references", [])
    ]

    duration_ms = (datetime.now() - start_time).total_seconds() * 1000

    decision = ComplianceDecision(
        alert_id=context.alert_id,
        decision=DecisionType(raw_response["decision"]),
        confidence=raw_response["confidence"],
        regulatory_references=refs,
        reasoning_chain=audit_trail,
        is_pep_override=False,
        final_summary=raw_response["final_summary"],
        pipeline_duration_ms=duration_ms,
    )

    return decision, audit_trail


def _get_pep_article(regulator: str) -> str:
    """Retorna el artículo específico del regulador para PEPs."""
    articles = {
        "UIAF": "Circular Básica Jurídica - Capítulo XI: Personas Expuestas Políticamente",
        "CNBV": "Disposición 115 Bis - Identificación de PEPs en el Sistema Financiero Mexicano",
        "SBS": "Resolución SBS N°2660-2015 - Artículo 18: Clientes PEP",
    }
    return articles.get(regulator, f"Normativa PEP - {regulator}")
