import json
from pathlib import Path

from eventcraft.main import create_app

OPENAPI_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "openapi.json"


def test_openapi_schema_matches_app_no_drift():
    assert OPENAPI_PATH.exists(), "docs/openapi.json must exist in repository"
    app = create_app()
    current_schema = app.openapi()
    stored_schema = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))

    # Verify no drift in endpoints or schemas
    assert current_schema["paths"].keys() == stored_schema["paths"].keys()
    assert current_schema["info"]["title"] == stored_schema["info"]["title"]
    assert current_schema["info"]["version"] == stored_schema["info"]["version"]
    assert (
        current_schema["components"]["schemas"].keys()
        == stored_schema["components"]["schemas"].keys()
    )
