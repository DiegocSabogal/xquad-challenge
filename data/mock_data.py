"""
Datos sintéticos que simulan BigQuery y GCS para el challenge.
En producción, estos serían reemplazados por clientes reales de GCP.
"""
from datetime import datetime, timedelta
import random
from typing import Any

# ---------------------------------------------------------------------------
# Mock: historial de transacciones (simula BigQuery)
# ---------------------------------------------------------------------------

MOCK_TRANSACTIONS: dict[str, list[dict[str, Any]]] = {
    "CLI-001": [
        {
            "transaction_id": f"TXN-{i:04d}",
            "client_id": "CLI-001",
            "amount": random.uniform(100, 5000),
            "currency": "COP",
            "type": random.choice(["transferencia", "retiro", "deposito"]),
            "counterparty": f"EMPRESA-{random.randint(1, 50)}",
            "country": random.choice(["CO", "MX", "PE"]),
            "timestamp": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
            "channel": random.choice(["app_movil", "banca_web", "sucursal"]),
            "flagged": False,
        }
        for i in range(45)
    ]
    + [
        # Transacciones sospechosas al final del periodo
        {
            "transaction_id": "TXN-9901",
            "client_id": "CLI-001",
            "amount": 48500.00,
            "currency": "USD",
            "type": "transferencia_internacional",
            "counterparty": "SHELL-CORP-PANAMA",
            "country": "PA",
            "timestamp": (datetime.now() - timedelta(days=2)).isoformat(),
            "channel": "banca_web",
            "flagged": True,
        },
        {
            "transaction_id": "TXN-9902",
            "client_id": "CLI-001",
            "amount": 49800.00,
            "currency": "USD",
            "type": "transferencia_internacional",
            "counterparty": "SHELL-CORP-PANAMA",
            "country": "PA",
            "timestamp": (datetime.now() - timedelta(days=1)).isoformat(),
            "channel": "banca_web",
            "flagged": True,
        },
    ],
    "CLI-002": [
        {
            "transaction_id": f"TXN-2{i:03d}",
            "client_id": "CLI-002",
            "amount": random.uniform(50, 1500),
            "currency": "MXN",
            "type": "compra",
            "counterparty": f"COMERCIO-{random.randint(1, 100)}",
            "country": "MX",
            "timestamp": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
            "channel": "tarjeta_debito",
            "flagged": False,
        }
        for i in range(60)
    ],
    "CLI-PEP-003": [
        # Cliente PEP (Persona Políticamente Expuesta) - debe SIEMPRE escalar
        {
            "transaction_id": f"TXN-3{i:03d}",
            "client_id": "CLI-PEP-003",
            "amount": random.uniform(1000, 20000),
            "currency": "PEN",
            "type": random.choice(["transferencia", "deposito"]),
            "counterparty": f"ENTIDAD-{random.randint(1, 20)}",
            "country": random.choice(["PE", "US", "CH"]),
            "timestamp": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
            "channel": "banca_web",
            "flagged": False,
        }
        for i in range(30)
    ],
}

# ---------------------------------------------------------------------------
# Mock: alertas (simula el modelo XGBoost que genera las alertas iniciales)
# ---------------------------------------------------------------------------

MOCK_ALERTS: dict[str, dict[str, Any]] = {
    "ALERT-001": {
        "alert_id": "ALERT-001",
        "client_id": "CLI-001",
        "xgboost_score": 0.87,
        "alert_type": "structuring",  # sospecha de fraccionamiento para evadir reporte
        "country": "CO",
        "regulator": "UIAF",
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        "is_pep": False,
    },
    "ALERT-002": {
        "alert_id": "ALERT-002",
        "client_id": "CLI-002",
        "xgboost_score": 0.42,
        "alert_type": "unusual_pattern",
        "country": "MX",
        "regulator": "CNBV",
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        "is_pep": False,
    },
    "ALERT-PEP-003": {
        "alert_id": "ALERT-PEP-003",
        "client_id": "CLI-PEP-003",
        "xgboost_score": 0.55,
        "alert_type": "high_value_transfer",
        "country": "PE",
        "regulator": "SBS",
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        "is_pep": True,  # Persona Politicamente Expuesta -> escalar SIEMPRE
        "pep_category": "funcionario_publico_nivel_1",
    },
}

# ---------------------------------------------------------------------------
# Mock: documentos PDF de GCS (simula metadatos + contenido extraído)
# ---------------------------------------------------------------------------

MOCK_GCS_DOCUMENTS: dict[str, list[dict[str, str]]] = {
    "CLI-001": [
        {
            "gcs_path": "gs://finserv-docs/CLI-001/kyc_2024.pdf",
            "type": "KYC",
            "content_summary": "Cliente persona jurídica. Actividad: importación de textiles. "
            "Ingresos declarados: $2.3M USD/año. Sin antecedentes. "
            "Actualización KYC: enero 2025.",
        },
        {
            "gcs_path": "gs://finserv-docs/CLI-001/due_diligence_2023.pdf",
            "type": "due_diligence",
            "content_summary": "Due diligence reforzado realizado en 2023. "
            "Estructura accionaria verificada. Beneficiario final identificado: "
            "Juan García Pérez (50% participación).",
        },
    ],
    "CLI-002": [
        {
            "gcs_path": "gs://finserv-docs/CLI-002/kyc_2024.pdf",
            "type": "KYC",
            "content_summary": "Cliente persona natural. Empleado sector privado. "
            "Ingresos: $85,000 MXN/mes. Comportamiento transaccional estable.",
        }
    ],
    "CLI-PEP-003": [
        {
            "gcs_path": "gs://finserv-docs/CLI-PEP-003/kyc_pep_2024.pdf",
            "type": "KYC_PEP",
            "content_summary": "Cliente identificado como PEP - Funcionario público nivel 1. "
            "Ex-ministro de economía Perú (2018-2022). "
            "Bajo régimen de monitoreo reforzado SBS. "
            "TODAS las alertas deben escalar al equipo de compliance senior.",
        },
        {
            "gcs_path": "gs://finserv-docs/CLI-PEP-003/enhanced_dd_2024.pdf",
            "type": "enhanced_due_diligence",
            "content_summary": "Due diligence reforzado PEP completado diciembre 2024. "
            "Fuente de fondos verificada. Patrimonio declarado consistente con cargo público.",
        },
    ],
}
