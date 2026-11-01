import json

import pytest

from eventcraft.llm.offline import OfflineClient


@pytest.mark.asyncio
async def test_offline_client_budget():
    client = OfflineClient()
    resp = await client.generate("suggest realistic percentage weights for budget categories")
    assert resp.source == "template"
    parsed = json.loads(resp.content)
    assert "weights" in parsed


@pytest.mark.asyncio
async def test_offline_client_ideas():
    client = OfflineClient()
    resp = await client.generate("recommendations for activities/entertainment and keepsakes")
    assert resp.source == "template"
    parsed = json.loads(resp.content)
    assert "ideas" in parsed
    assert len(parsed["ideas"]) == 5


@pytest.mark.asyncio
async def test_offline_client_assistant():
    client = OfflineClient()
    resp = await client.generate("What is my budget total?")
    assert resp.source == "template"
    assert "event plan" in resp.content
