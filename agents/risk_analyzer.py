"""
Agente 2: Analizador de Riesgo
Responsabilidad: recibe el contexto del Agente Investigador y:
  (a) clasifica nivel de riesgo 1-10 con justificación explícita
  (b) identifica patrones de comportamiento anómalo vs. histórico
  (c) produce resumen en lenguaje natural para el analista humano
"""
import json

from data.models import CaseContext, RiskAnalysis, AnomalousPattern, AuditStep
from tools.llm_client import get_llm_client

SYSTEM_PROMPT = """Eres un experto en análisis de riesgo financiero y compliance regulatorio
para América Latina (UIAF Colombia, CNBV México, SBS Perú).

Tu tarea es analizar el contexto de una alerta de compliance y producir un análisis
estructurado en formato JSON con exactamente estos campos:
- risk_score: integer 1-10 (1=mínimo riesgo, 10=máximo riesgo)
- risk_justification: string con justificación explícita del score
- anomalous_patterns: lista de objetos {pattern_type, description, severity}
- analyst_summary: string con resumen claro para analista humano (máx. 200 palabras)

CRITERIOS DE EVALUACIÓN:
- Score 8-10: Indicadores claros de lavado de dinero, estructuración, o cliente PEP con actividad inusual
- Score 5-7: Patrones sospechosos que requieren investigación adicional
- Score 1-4: Actividad dentro de parámetros normales, probable falso positivo

Responde ÚNICAMENTE con el JSON, sin texto adicional."""


def run(context: CaseContext, audit_trail: list[AuditStep]) -> tuple[RiskAnalysis, list[AuditStep]]:
    """
    Ejecuta el análisis de riesgo sobre el contexto del caso.
    """
    llm = get_llm_client()

    # Construir el mensaje con el contexto relevante (sin datos que identifiquen directamente al cliente
    # para minimizar exposición en el prompt — datos anonimizados internamente)
    user_message = f"""
ALERTA ID: {context.alert_id}
TIPO DE ALERTA: {context.alert_type}
SCORE XGBOOST: {context.xgboost_score}
REGULADOR: {context.regulator.value}
PAIS: {context.country}
ES PEP: {context.is_pep}
CATEGORIA PEP: {context.pep_category or 'N/A'}

HISTORIAL TRANSACCIONAL (últimos 90 días):
- Total transacciones: {context.transaction_count}
- Volumen total: ${context.total_volume_usd:,.2f} USD
- Transacciones flaggeadas: {len(context.flagged_transactions)}

TRANSACCIONES SOSPECHOSAS DETECTADAS:
{json.dumps(context.flagged_transactions, indent=2, default=str) if context.flagged_transactions else 'Ninguna'}

RESUMEN DE DOCUMENTOS DEL CLIENTE:
{chr(10).join([f"- {d['type']}: {d['content_summary']}" for d in context.documents])}
"""

    # Llamar al LLM para análisis
    raw_response = llm.complete_json(SYSTEM_PROMPT, user_message)

    audit_trail.append(AuditStep(
        step=len(audit_trail) + 1,
        agent="risk_analyzer",
        action="llm_risk_assessment",
        reasoning=f"LLM asignó score de riesgo {raw_response['risk_score']}/10. "
                  f"Patrones detectados: {len(raw_response.get('anomalous_patterns', []))}.",
    ))

    # Construir objeto tipado
    patterns = [
        AnomalousPattern(**p) for p in raw_response.get("anomalous_patterns", [])
    ]

    analysis = RiskAnalysis(
        alert_id=context.alert_id,
        risk_score=raw_response["risk_score"],
        risk_justification=raw_response["risk_justification"],
        anomalous_patterns=patterns,
        analyst_summary=raw_response["analyst_summary"],
    )

    return analysis, audit_trail
