from datetime import date, timedelta

import httpx
import pytest

from eventcraft.config import AppSettings
from eventcraft.main import create_app


@pytest.fixture
def app_instance():
    settings = AppSettings(
        body_limit_bytes=4096,
        rate_limit_per_minute=20,
    )
    return create_app(settings)


@pytest.mark.asyncio
async def test_health_endpoint(app_instance):
    transport = httpx.ASGITransport(app=app_instance)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"


@pytest.mark.asyncio
@pytest.mark.parametrize("event_type", ["wedding", "birthday", "community"])
async def test_generate_plan_all_event_types(app_instance, event_type):
    future_date = (date.today() + timedelta(days=180)).isoformat()
    payload = {
        "event_type": event_type,
        "event_date": future_date,
        "guest_count": 80,
        "budget_total": "50000.00",
        "currency": "USD",
        "priorities": ["Food & Beverage"],
        "culture_or_tradition": "Family Celebration",
        "style": "Contemporary",
    }
    transport = httpx.ASGITransport(app=app_instance)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/plans/generate", json=payload)
        assert resp.status_code == 200
        plan = resp.json()

        # Check all 4 deliverables are present and working
        assert "budget" in plan
        assert "timeline" in plan
        assert "vendor_checklist" in plan
        assert "personalized_ideas" in plan

        assert plan["budget"]["total_amount"] == "50000.00"
        assert len(plan["budget"]["lines"]) > 0
        assert len(plan["timeline"]["milestones"]) > 0
        assert len(plan["vendor_checklist"]["items"]) > 0
        assert len(plan["personalized_ideas"]["ideas"]) == 5


@pytest.mark.asyncio
async def test_budget_rebalance_endpoint(app_instance):
    payload = {
        "event_type": "wedding",
        "budget_total": "75000.00",
        "currency": "INR",
        "guest_count": 120,
        "priorities": ["Catering & Bar"],
        "contingency_percent": "6.00",
    }
    transport = httpx.ASGITransport(app=app_instance)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/budget/rebalance", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_amount"] == "75000.00"
        assert data["meta"]["tokens_used"] == 0


@pytest.mark.asyncio
async def test_regenerate_ideas_endpoint(app_instance):
    future_date = (date.today() + timedelta(days=90)).isoformat()
    payload = {
        "brief": {
            "event_type": "birthday",
            "event_date": future_date,
            "guest_count": 30,
            "budget_total": "1500.00",
            "currency": "USD",
        },
        "steer": "vintage jazz lounge",
    }
    transport = httpx.ASGITransport(app=app_instance)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/plans/ideas", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["ideas"]) == 5
        assert data["steer"] == "vintage jazz lounge"


@pytest.mark.asyncio
async def test_assistant_ask_endpoint(app_instance):
    future_date = (date.today() + timedelta(days=120)).isoformat()
    payload = {
        "brief": {
            "event_type": "wedding",
            "event_date": future_date,
            "guest_count": 100,
            "budget_total": "20000.00",
            "currency": "USD",
        },
        "question": "What is my total budget and guest count?",
    }
    transport = httpx.ASGITransport(app=app_instance)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/assistant/ask", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert len(data["answer"]) > 0


@pytest.mark.asyncio
async def test_validation_error_rfc7807(app_instance):
    # Missing required fields
    payload = {"guest_count": -5}
    transport = httpx.ASGITransport(app=app_instance)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/plans/generate", json=payload)
        assert resp.status_code == 422
        assert resp.headers["content-type"] == "application/problem+json"
        body = resp.json()
        assert body["status"] == 422
        assert "type" in body
        assert "instance" in body


@pytest.mark.asyncio
async def test_unknown_fields_rejected_extra_forbid(app_instance):
    future_date = (date.today() + timedelta(days=60)).isoformat()
    payload = {
        "event_type": "birthday",
        "event_date": future_date,
        "guest_count": 20,
        "budget_total": "1000.00",
        "currency": "USD",
        "unknown_extra_field": "disallowed",
    }
    transport = httpx.ASGITransport(app=app_instance)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/plans/generate", json=payload)
        assert resp.status_code == 422
        assert resp.headers["content-type"] == "application/problem+json"
