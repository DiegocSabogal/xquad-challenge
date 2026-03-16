"""
Tests de integración para la API FastAPI.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_list_alerts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_process_alert_001():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/alerts/ALERT-001/process")
    assert response.status_code == 200
    data = response.json()
    assert data["alert_id"] == "ALERT-001"
    assert data["decision"] in ["escalate", "discard", "request_info"]
    assert 0.0 <= data["confidence"] <= 1.0
    assert 1 <= data["risk_score"] <= 10
    assert data["audit_trail_steps"] > 0


@pytest.mark.asyncio
async def test_pep_alert_always_escalates():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/alerts/ALERT-PEP-003/process")
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "escalate"
    assert data["is_pep_override"] is True
    assert data["confidence"] == 1.0


@pytest.mark.asyncio
async def test_process_nonexistent_alert_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/alerts/ALERT-FAKE-999/process")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_audit_trail_after_processing():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/alerts/ALERT-002/process")
        response = await client.get("/alerts/ALERT-002/audit")
    assert response.status_code == 200
    data = response.json()
    assert "audit_trail" in data
    assert len(data["audit_trail"]) > 0
    assert "compliance_note" in data
