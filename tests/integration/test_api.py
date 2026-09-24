import sqlite3

import pytest


def test_health(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_contact_persists_and_response_excludes_personal_data(
    client, database_url, payload
) -> None:
    response = client.post("/api/v1/contacts", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "new"
    assert isinstance(body["id"], int)
    assert "created_at" in body
    assert "email" not in body and "message" not in body

    path = database_url.removeprefix("sqlite+pysqlite:///")
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT first_name, last_name, email, message, status FROM contacts WHERE id = ?",
            (body["id"],),
        ).fetchone()
    assert row == ("Ana", "Silva", "ana@example.com", "Gostaria de saber mais.", "new")


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"email": "invalid"}, "email"),
        ({"first_name": ""}, "first_name"),
        ({"message": "x" * 5001}, "message"),
        ({"first_name": 42}, "first_name"),
        ({"address": []}, "address"),
        ({"unknown": "value"}, "unknown"),
    ],
)
def test_invalid_contact_returns_422(client, payload, change, field) -> None:
    payload.update(change)
    response = client.post("/api/v1/contacts", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert any(item["field"].endswith(field) for item in response.json()["error"]["details"])


def test_missing_required_field(client, payload) -> None:
    del payload["last_name"]
    response = client.post("/api/v1/contacts", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "body.last_name"


@pytest.mark.parametrize(
    ("field", "length"),
    [("first_name", 101), ("last_name", 101), ("phone", 41), ("address", 256), ("message", 5001)],
)
def test_contact_field_length_limits(client, payload, field, length) -> None:
    payload[field] = "x" * length
    response = client.post("/api/v1/contacts", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_idempotency_key_returns_same_contact_on_retry(client, payload) -> None:
    headers = {"Idempotency-Key": "retry-key-1"}
    first = client.post("/api/v1/contacts", json=payload, headers=headers)
    second = client.post("/api/v1/contacts", json=payload, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json() == second.json()


def test_idempotency_key_with_different_payload_still_returns_original(client, payload) -> None:
    headers = {"Idempotency-Key": "retry-key-2"}
    first = client.post("/api/v1/contacts", json=payload, headers=headers)
    payload["message"] = "Uma mensagem completamente diferente."
    second = client.post("/api/v1/contacts", json=payload, headers=headers)
    assert first.json()["id"] == second.json()["id"]


def test_missing_idempotency_key_creates_separate_contacts(client, payload) -> None:
    first = client.post("/api/v1/contacts", json=payload)
    second = client.post("/api/v1/contacts", json=payload)
    assert first.json()["id"] != second.json()["id"]


def test_different_idempotency_keys_create_separate_contacts(client, payload) -> None:
    first = client.post("/api/v1/contacts", json=payload, headers={"Idempotency-Key": "key-a"})
    second = client.post("/api/v1/contacts", json=payload, headers={"Idempotency-Key": "key-b"})
    assert first.json()["id"] != second.json()["id"]


def test_malformed_idempotency_key_returns_422(client, payload) -> None:
    response = client.post(
        "/api/v1/contacts", json=payload, headers={"Idempotency-Key": "has a space"}
    )
    assert response.status_code == 422


def test_openapi_and_documentation(client) -> None:
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/api/v1/contacts" in schema["paths"]
    assert schema["paths"]["/api/v1/contacts"]["post"]["responses"]["201"]
