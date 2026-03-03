"""Tests for ContextsAPI."""

import json

import pytest
import responses

from ox_cloud_sdk.exceptions import OXNotFoundError

from .conftest import API_URL


@responses.activate
def test_list(client):
    responses.get(f"{API_URL}/contexts", json=[{"name": "ctx1"}, {"name": "ctx2"}])
    result = client.contexts.list()
    assert len(result) == 2
    assert result[0]["name"] == "ctx1"
    assert result[1]["name"] == "ctx2"


@responses.activate
def test_get(client):
    responses.get(f"{API_URL}/contexts/ctx1", json={"name": "ctx1", "maxQuota": 1024})
    result = client.contexts.get("ctx1")
    assert result["name"] == "ctx1"
    assert result["maxQuota"] == 1024


@responses.activate
def test_create_minimal(client):
    responses.post(f"{API_URL}/contexts", json={"name": "new_ctx"}, status=201)
    result = client.contexts.create("new_ctx")
    assert result["name"] == "new_ctx"
    payload = json.loads(responses.calls[0].request.body)
    assert payload == {"name": "new_ctx"}


@responses.activate
def test_create_with_all_fields(client):
    responses.post(f"{API_URL}/contexts", json={"name": "new_ctx"}, status=201)
    client.contexts.create(
        "new_ctx",
        max_quota=2048,
        admin_login="ctxadmin",
        admin_password="pass123",
        admin_email="admin@example.com",
        theme={"logo": "https://example.com/logo.png"},
        max_user=100,
    )
    payload = json.loads(responses.calls[0].request.body)
    assert payload["name"] == "new_ctx"
    assert payload["maxQuota"] == 2048
    assert payload["adminLogin"] == "ctxadmin"
    assert payload["adminPassword"] == "pass123"
    assert payload["adminEmail"] == "admin@example.com"
    assert payload["theme"] == {"logo": "https://example.com/logo.png"}
    assert payload["maxUser"] == 100


@responses.activate
def test_update(client):
    responses.put(f"{API_URL}/contexts/ctx1", json={"name": "ctx1", "maxQuota": 4096})
    result = client.contexts.update("ctx1", max_quota=4096)
    assert result["maxQuota"] == 4096
    payload = json.loads(responses.calls[0].request.body)
    assert payload == {"maxQuota": 4096}


@responses.activate
def test_update_empty_response(client):
    responses.put(f"{API_URL}/contexts/ctx1", body=b"", status=200)
    result = client.contexts.update("ctx1", max_quota=4096)
    assert result == {}


@responses.activate
def test_update_non_json_response(client):
    responses.put(f"{API_URL}/contexts/ctx1", body=b"OK", status=200, content_type="text/plain")
    result = client.contexts.update("ctx1", max_quota=4096)
    assert result == {}


@responses.activate
def test_delete(client):
    responses.delete(f"{API_URL}/contexts/ctx1", status=204)
    client.contexts.delete("ctx1")
    assert len(responses.calls) == 1


@responses.activate
def test_get_not_found_raises(client):
    error_body = {"errors": [{"code": "3", "title": "Context not found", "status": "404"}]}
    responses.get(f"{API_URL}/contexts/missing", json=error_body, status=404)
    with pytest.raises(OXNotFoundError):
        client.contexts.get("missing")
