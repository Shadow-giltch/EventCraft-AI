from fastapi import FastAPI
from fastapi.testclient import TestClient

from eventcraft.errors import (
    EventCraftError,
    PayloadTooLargeError,
    RateLimitExceededError,
    create_problem_response,
    register_error_handlers,
)


def test_custom_exception_hierarchy():
    e1 = RateLimitExceededError()
    assert e1.status_code == 429
    assert e1.error_type == "rate-limit-exceeded"

    e2 = PayloadTooLargeError()
    assert e2.status_code == 413
    assert e2.error_type == "payload-too-large"

    resp = create_problem_response(400, "Bad Request", "Detail msg", "bad-request")
    assert resp.status_code == 400
    assert resp.headers["content-type"] == "application/problem+json"


def test_exception_handlers_catch_errors():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/trigger-eventcraft-error")
    def trigger_ec():
        raise EventCraftError("Custom failure", status_code=400, error_type="custom-err")

    @app.get("/trigger-unhandled")
    def trigger_unhandled():
        raise RuntimeError("Unexpected boom")

    client = TestClient(app, raise_server_exceptions=False)

    r1 = client.get("/trigger-eventcraft-error")
    assert r1.status_code == 400
    assert r1.headers["content-type"] == "application/problem+json"
    assert "Custom failure" in r1.json()["detail"]

    r2 = client.get("/trigger-unhandled")
    assert r2.status_code == 500
    assert r2.headers["content-type"] == "application/problem+json"
