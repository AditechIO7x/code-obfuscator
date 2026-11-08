import subprocess
import sys
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from api import index


LANGUAGES = (
    "python", "javascript", "html", "php", "ruby", "java", "csharp", "cpp",
    "typescript", "kotlin", "swift", "go",
)


@pytest.fixture
def client():
    with TestClient(index.app) as client:
        yield client


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("level,anti_hooking", [(1, False), (15, True)])
def test_dispatch_and_response_metadata(client, monkeypatch, language, level, anti_hooking):
    code = 'print("héllo 🌍")\n'
    output = "generated ✓"
    obfuscator = Mock(return_value=output)
    monkeypatch.setattr(index, f"obfuscate_{language}", obfuscator)

    response = client.post("/api/obfuscate", json={
        "code": code, "language": language, "level": level,
        "anti_hooking": anti_hooking,
    })

    assert response.status_code == 200
    obfuscator.assert_called_once_with(code, level, anti_hooking)
    assert response.json() == {
        "obfuscated_code": output, "original_size": len(code),
        "obfuscated_size": len(output), "language": language, "level": level,
    }


def test_anti_hooking_defaults_to_false(client, monkeypatch):
    obfuscator = Mock(return_value="output")
    monkeypatch.setattr(index, "obfuscate_python", obfuscator)
    response = client.post("/api/obfuscate", json={
        "code": "print(42)", "language": "python", "level": 1,
    })
    assert response.status_code == 200
    obfuscator.assert_called_once_with("print(42)", 1, False)


@pytest.mark.parametrize("overrides,detail", [
    ({"level": 0}, "Level must be between 1 and 15"),
    ({"level": 16}, "Level must be between 1 and 15"),
    ({"language": "unsupported"}, "Unsupported language: unsupported"),
])
def test_invalid_options_rejected_before_transform(client, monkeypatch, overrides, detail):
    obfuscator = Mock(side_effect=AssertionError("must not transform invalid input"))
    monkeypatch.setattr(index, "obfuscate_python", obfuscator)
    payload = {"code": "print(42)", "language": "python", "level": 1}
    response = client.post("/api/obfuscate", json=payload | overrides)
    assert response.status_code == 400
    assert response.json() == {"detail": detail}
    obfuscator.assert_not_called()


@pytest.mark.parametrize("field,value", [
    ("code", None), ("language", None), ("level", "invalid"),
])
def test_invalid_request_schema(client, monkeypatch, field, value):
    obfuscator = Mock()
    monkeypatch.setattr(index, "obfuscate_python", obfuscator)
    payload = {"code": "print(42)", "language": "python", "level": 1}
    payload[field] = value
    response = client.post("/api/obfuscate", json=payload)
    assert response.status_code == 422
    assert any(error["loc"] == ["body", field] for error in response.json()["detail"])
    obfuscator.assert_not_called()


def test_transform_failure_returns_json_error(client, monkeypatch):
    obfuscator = Mock(side_effect=ValueError("transform failed"))
    monkeypatch.setattr(index, "obfuscate_python", obfuscator)
    response = client.post("/api/obfuscate", json={
        "code": "print(42)", "language": "python", "level": 1,
    })
    assert response.status_code == 500
    assert response.json() == {"detail": "Obfuscation error: transform failed"}
    obfuscator.assert_called_once_with("print(42)", 1, False)


def test_advertised_languages_match_dispatch_contract(client):
    response = client.get("/api/languages")
    assert response.status_code == 200
    languages = response.json()["languages"]
    assert len(languages) == len(LANGUAGES)
    assert {language["id"] for language in languages} == set(LANGUAGES)
    assert all(language["max_level"] == 15 for language in languages)


def test_real_python_request_returns_executable_code(client):
    source = 'value = 6\nprint("result", value * 7)\n'
    response = client.post("/api/obfuscate", json={
        "code": source, "language": "python", "level": 10,
    })
    assert response.status_code == 200
    data = response.json()
    result = subprocess.run(
        [sys.executable, "-I", "-c", data["obfuscated_code"]],
        capture_output=True, text=True, timeout=5,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "result 42\n"
    assert result.stderr == ""
    assert data["original_size"] == len(source)
    assert data["obfuscated_size"] == len(data["obfuscated_code"])
