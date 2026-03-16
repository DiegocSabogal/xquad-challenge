"""
Herramientas de BigQuery para el Agente Investigador.

En producción: usa google-cloud-bigquery para consultar el dataset real en us-central1.
En desarrollo/challenge: retorna datos sintéticos del módulo mock_data.
"""
from datetime import datetime, timedelta
from typing import Any

from data.mock_data import MOCK_TRANSACTIONS, MOCK_ALERTS


def get_alert_by_id(alert_id: str) -> dict[str, Any] | None:
    """
    Recupera los metadatos de una alerta del sistema XGBoost.
    Simula: SELECT * FROM `finserv.compliance.alerts` WHERE alert_id = @alert_id
    """
    return MOCK_ALERTS.get(alert_id)


def get_transaction_history(client_id: str, days: int = 90) -> list[dict[str, Any]]:
    """
    Recupera el historial de transacciones de los últimos N días.
    Simula: SELECT * FROM `finserv.transactions.history`
            WHERE client_id = @client_id
            AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
            ORDER BY timestamp DESC
    """
    transactions = MOCK_TRANSACTIONS.get(client_id, [])
    cutoff = datetime.now() - timedelta(days=days)

    return [
        txn for txn in transactions
        if datetime.fromisoformat(txn["timestamp"]) >= cutoff
    ]


def get_flagged_transactions(client_id: str, days: int = 90) -> list[dict[str, Any]]:
    """Filtra únicamente las transacciones marcadas como sospechosas."""
    all_txns = get_transaction_history(client_id, days)
    return [txn for txn in all_txns if txn.get("flagged", False)]


def calculate_transaction_volume_usd(transactions: list[dict[str, Any]]) -> float:
    """
    Calcula el volumen total en USD.
    En producción usaría tasas de cambio de BigQuery. Aquí usa factores fijos.
    """
    fx_rates = {"USD": 1.0, "COP": 0.00025, "MXN": 0.052, "PEN": 0.27}
    total = 0.0
    for txn in transactions:
        rate = fx_rates.get(txn.get("currency", "USD"), 1.0)
        total += txn.get("amount", 0.0) * rate
    return round(total, 2)
