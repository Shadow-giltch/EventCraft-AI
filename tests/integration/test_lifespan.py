from fastapi.testclient import TestClient

from eventcraft.config import AppSettings
from eventcraft.main import create_app


def test_lifespan_startup_and_shutdown():
    app = create_app(AppSettings())
    with TestClient(app) as client:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
