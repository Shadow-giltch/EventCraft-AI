import pytest

from eventcraft.llm.parsing import JSONRepairFailedError, parse_and_repair_json


def test_parse_valid_json():
    raw = '{"status": "ok", "count": 42}'
    data = parse_and_repair_json(raw)
    assert data["status"] == "ok"
    assert data["count"] == 42


def test_parse_markdown_fenced_json():
    raw = '```json\n{\n  "items": [1, 2, 3]\n}\n```'
    data = parse_and_repair_json(raw)
    assert data["items"] == [1, 2, 3]


def test_parse_repaired_trailing_comma():
    raw = '{\n  "key": "value",\n}'
    data = parse_and_repair_json(raw)
    assert data["key"] == "value"


def test_parse_invalid_json_raises():
    with pytest.raises(JSONRepairFailedError):
        parse_and_repair_json("This is definitely not json")

    with pytest.raises(JSONRepairFailedError):
        parse_and_repair_json("")


def test_parse_non_dict_root_raises():
    with pytest.raises(JSONRepairFailedError, match="not a dictionary"):
        parse_and_repair_json("[1, 2, 3]")

    with pytest.raises(JSONRepairFailedError):
        parse_and_repair_json("```json\n[1, 2, 3]\n```")


def test_parse_assistant_response_json_wrapped():
    from eventcraft.llm.parsing import parse_assistant_response

    raw = '{"response": "For your wedding, secure the ceremony and reception venue first."}'
    result = parse_assistant_response(raw)
    assert result == "For your wedding, secure the ceremony and reception venue first."


def test_parse_assistant_response_plain_text():
    from eventcraft.llm.parsing import parse_assistant_response

    raw = "For your wedding, secure the ceremony and reception venue first."
    result = parse_assistant_response(raw)
    assert result == "For your wedding, secure the ceremony and reception venue first."


def test_parse_assistant_response_fenced():
    from eventcraft.llm.parsing import parse_assistant_response

    raw = '```json\n{\n  "response": "For your wedding, secure the ceremony and reception venue first."\n}\n```'
    result = parse_assistant_response(raw)
    assert result == "For your wedding, secure the ceremony and reception venue first."


def test_parse_assistant_response_empty_raises():
    from eventcraft.llm.parsing import AssistantResponseParsingError, parse_assistant_response

    with pytest.raises(AssistantResponseParsingError):
        parse_assistant_response("")

    with pytest.raises(AssistantResponseParsingError):
        parse_assistant_response("   ")

    with pytest.raises(AssistantResponseParsingError):
        parse_assistant_response("{}")


def test_parse_assistant_response_length_cap():
    from eventcraft.llm.parsing import AssistantResponseParsingError, parse_assistant_response

    long_text = "a" * 1501
    with pytest.raises(AssistantResponseParsingError):
        parse_assistant_response(long_text, max_length=1500)
