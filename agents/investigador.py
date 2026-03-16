"""
Agente 1: Investigador
Responsabilidad: dado un alert_id, construye el contexto completo del caso
consultando BigQuery (historial transaccional) y GCS (documentos PDF del cliente).
"""
from datetime import datetime

from data.models import CaseContext, AuditStep, RegulatoryBody
from tools.bigquery_tools import (
    get_alert_by_id,
    get_transaction_history,
    get_flagged_transactions,
    calculate_transaction_volume_usd,
)
from tools.gcs_tools import get_all_client_documents_content


def run(alert_id: str) -> tuple[CaseContext, list[AuditStep]]:
    """
    Ejecuta el agente investigador.
    Retorna el contexto estructurado del caso y el audit trail de sus pasos.
    """
    audit_steps: list[AuditStep] = []

    # --- Paso 1: Recuperar metadatos de la alerta ---
    alert = get_alert_by_id(alert_id)
    if not alert:
        raise ValueError(f"Alerta {alert_id} no encontrada en el sistema.")

    audit_steps.append(AuditStep(
        step=1,
        agent="investigador",
        action="fetch_alert_metadata",
        reasoning=f"Alerta {alert_id} recuperada. Cliente: {alert['client_id']}. "
                  f"Score XGBoost: {alert['xgboost_score']:.2f}. "
                  f"Tipo: {alert['alert_type']}. Regulador: {alert['regulator']}.",
    ))

    client_id = alert["client_id"]

    # --- Paso 2: Consultar historial transaccional (BigQuery) ---
    transactions = get_transaction_history(client_id, days=90)
    flagged = get_flagged_transactions(client_id, days=90)
    total_volume = calculate_transaction_volume_usd(transactions)

    audit_steps.append(AuditStep(
        step=2,
        agent="investigador",
        action="query_bigquery_history",
        reasoning=f"Recuperadas {len(transactions)} transacciones de los últimos 90 días. "
                  f"Volumen total: ${total_volume:,.2f} USD. "
                  f"Transacciones flaggeadas: {len(flagged)}.",
    ))

    # --- Paso 3: Extraer documentos PDF de GCS ---
    documents = get_all_client_documents_content(client_id)

    audit_steps.append(AuditStep(
        step=3,
        agent="investigador",
        action="extract_gcs_documents",
        reasoning=f"Extraídos {len(documents)} documentos de GCS para el cliente {client_id}. "
                  f"Tipos: {[d['type'] for d in documents]}.",
    ))

    # --- Paso 4: Construir contexto estructurado ---
    is_pep = alert.get("is_pep", False)
    if is_pep:
        audit_steps.append(AuditStep(
            step=4,
            agent="investigador",
            action="flag_pep_status",
            reasoning=f"ALERTA: Cliente identificado como PEP ({alert.get('pep_category', 'no especificado')}). "
                      f"Aplicará normativa de monitoreo reforzado según regulación "
                      f"{alert['regulator']}.",
        ))

    context = CaseContext(
        alert_id=alert_id,
        client_id=client_id,
        is_pep=is_pep,
        pep_category=alert.get("pep_category"),
        regulator=RegulatoryBody(alert["regulator"]),
        country=alert["country"],
        xgboost_score=alert["xgboost_score"],
        alert_type=alert["alert_type"],
        transactions_last_90d=transactions,
        transaction_count=len(transactions),
        total_volume_usd=total_volume,
        flagged_transactions=flagged,
        documents=documents,
    )

    return context, audit_steps
