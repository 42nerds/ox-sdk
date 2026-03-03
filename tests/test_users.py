"""Tests for UsersAPI."""

import json

import pytest
import responses

from ox_cloud_sdk.exceptions import OXConflictError
from ox_cloud_sdk.users import _build_payload, _validate_quotas

from .conftest import API_URL

# ---------------------------------------------------------------------------
# _validate_quotas
# ---------------------------------------------------------------------------


class TestValidateQuotas:
    def test_unified_only(self):
        _validate_quotas({"unified_quota": 1024})

    def test_split_only(self):
        _validate_quotas({"mail_quota": 512, "file_quota": 512})

    def test_empty(self):
        _validate_quotas({})

    def test_conflict_raises(self):
        with pytest.raises(ValueError, match="unified_quota OR"):
            _validate_quotas({"unified_quota": 1024, "mail_quota": 512})

    def test_conflict_with_file_quota(self):
        with pytest.raises(ValueError, match="unified_quota OR"):
            _validate_quotas({"unified_quota": 1024, "file_quota": 256})


# ---------------------------------------------------------------------------
# _build_payload
# ---------------------------------------------------------------------------


class TestBuildPayload:
    def test_snake_to_camel(self):
        result = _build_payload({"given_name": "John", "sur_name": "Doe"})
        assert result == {"givenName": "John", "surName": "Doe"}

    def test_skips_none_values(self):
        result = _build_payload({"given_name": "John", "sur_name": None})
        assert result == {"givenName": "John"}

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown user field"):
            _build_payload({"nonexistent": "value"})

    def test_tuple_converted_to_list(self):
        result = _build_payload({"aliases": ("a@b.com", "c@d.com")})
        assert result == {"aliases": ["a@b.com", "c@d.com"]}

    def test_list_stays_list(self):
        result = _build_payload({"aliases": ["a@b.com"]})
        assert result == {"aliases": ["a@b.com"]}

    def test_empty_fields(self):
        assert _build_payload({}) == {}


# ---------------------------------------------------------------------------
# UsersAPI.list
# ---------------------------------------------------------------------------


@responses.activate
def test_list_default(client):
    responses.get(f"{API_URL}/users", json=[{"name": "john"}])
    result = client.users.list("ctx1")
    assert result == [{"name": "john"}]
    url = responses.calls[0].request.url
    assert "name=ctx1" in url


@responses.activate
def test_list_with_include_flags(client):
    responses.get(f"{API_URL}/users", json=[])
    client.users.list("ctx1", include_guests=True, include_id=True)
    url = responses.calls[0].request.url
    assert "includeguests=true" in url
    assert "includeid=true" in url


@responses.activate
def test_list_without_include_flags(client):
    responses.get(f"{API_URL}/users", json=[])
    client.users.list("ctx1")
    url = responses.calls[0].request.url
    assert "includeguests" not in url
    assert "includeid" not in url


# ---------------------------------------------------------------------------
# UsersAPI.get
# ---------------------------------------------------------------------------


@responses.activate
def test_get(client):
    responses.get(f"{API_URL}/users/john", json={"name": "john", "mail": "john@example.com"})
    result = client.users.get("john", "ctx1")
    assert result["name"] == "john"
    assert "name=ctx1" in responses.calls[0].request.url


@responses.activate
def test_get_with_include_flags(client):
    responses.get(f"{API_URL}/users/john", json={"name": "john"})
    client.users.get("john", "ctx1", include_id=True, include_permissions=True)
    url = responses.calls[0].request.url
    assert "includeid=true" in url
    assert "includepermissions=true" in url


# ---------------------------------------------------------------------------
# UsersAPI.create
# ---------------------------------------------------------------------------


@responses.activate
def test_create_minimal(client):
    responses.post(f"{API_URL}/users", json={"name": "john"}, status=201)
    result = client.users.create(
        "john", "ctx1", password="s3cret", given_name="John", sur_name="Doe", mail="john@example.com"
    )
    assert result["name"] == "john"
    payload = json.loads(responses.calls[0].request.body)
    assert payload["name"] == "john"
    assert payload["password"] == "s3cret"
    assert payload["givenName"] == "John"
    assert payload["surName"] == "Doe"
    assert payload["mail"] == "john@example.com"


@responses.activate
def test_create_with_optional_fields(client):
    responses.post(f"{API_URL}/users", json={"name": "john"}, status=201)
    client.users.create(
        "john",
        "ctx1",
        password="p",
        given_name="J",
        sur_name="D",
        mail="j@x.com",
        display_name="John Doe",
        language="de_DE",
        aliases=["alias@x.com"],
        timezone="Europe/Berlin",
        unified_quota=2048,
        user_admin_enabled=True,
    )
    payload = json.loads(responses.calls[0].request.body)
    assert payload["displayName"] == "John Doe"
    assert payload["language"] == "de_DE"
    assert payload["aliases"] == ["alias@x.com"]
    assert payload["timezone"] == "Europe/Berlin"
    assert payload["unifiedQuota"] == 2048
    assert payload["userAdminEnabled"] is True


@responses.activate
def test_create_quota_conflict_raises(client):
    with pytest.raises(ValueError):
        client.users.create(
            "john",
            "ctx1",
            password="p",
            given_name="J",
            sur_name="D",
            mail="j@x.com",
            unified_quota=1024,
            mail_quota=512,
        )


@responses.activate
def test_create_conflict_raises_ox_error(client):
    error_body = {"errors": [{"code": "8", "title": "User already exists", "status": "409"}]}
    responses.post(f"{API_URL}/users", json=error_body, status=409)
    with pytest.raises(OXConflictError):
        client.users.create("john", "ctx1", password="p", given_name="J", sur_name="D", mail="j@x.com")


# ---------------------------------------------------------------------------
# UsersAPI.update
# ---------------------------------------------------------------------------


@responses.activate
def test_update(client):
    responses.put(f"{API_URL}/users/john", json={"name": "john"})
    result = client.users.update("john", "ctx1", given_name="Jane")
    payload = json.loads(responses.calls[0].request.body)
    assert payload == {"givenName": "Jane"}
    assert result["name"] == "john"


@responses.activate
def test_update_unknown_field_raises(client):
    with pytest.raises(ValueError, match="Unknown user field"):
        client.users.update("john", "ctx1", nonexistent="val")


@responses.activate
def test_update_quota_conflict_raises(client):
    with pytest.raises(ValueError):
        client.users.update("john", "ctx1", unified_quota=1024, file_quota=512)


@responses.activate
def test_update_empty_response(client):
    responses.put(f"{API_URL}/users/john", body=b"", status=200)
    result = client.users.update("john", "ctx1", given_name="Jane")
    assert result == {}


@responses.activate
def test_update_multiple_fields(client):
    responses.put(f"{API_URL}/users/john", json={"name": "john"})
    client.users.update("john", "ctx1", display_name="J. Doe", language="en_US", email_backup_enabled=True)
    payload = json.loads(responses.calls[0].request.body)
    assert payload["displayName"] == "J. Doe"
    assert payload["language"] == "en_US"
    assert payload["emailBackupEnabled"] is True


# ---------------------------------------------------------------------------
# UsersAPI.delete
# ---------------------------------------------------------------------------


@responses.activate
def test_delete(client):
    responses.delete(f"{API_URL}/users/john", status=204)
    client.users.delete("john", "ctx1")
    assert len(responses.calls) == 1


@responses.activate
def test_delete_with_reassign(client):
    responses.delete(f"{API_URL}/users/john", status=204)
    client.users.delete("john", "ctx1", reassign_user="jane")
    assert "reassignuser=jane" in responses.calls[0].request.url


# ---------------------------------------------------------------------------
# UsersAPI.count
# ---------------------------------------------------------------------------


@responses.activate
def test_count(client):
    responses.get(f"{API_URL}/users/amount", json={"amount": 42})
    result = client.users.count("ctx1")
    assert result == 42
    assert isinstance(result, int)


# ---------------------------------------------------------------------------
# UsersAPI.check_login
# ---------------------------------------------------------------------------


@responses.activate
def test_check_login_exists(client):
    responses.get(f"{API_URL}/users/john", json={"name": "john"})
    assert client.users.check_login("john", "ctx1") is True


@responses.activate
def test_check_login_not_found(client):
    responses.get(f"{API_URL}/users/john", status=404)
    assert client.users.check_login("john", "ctx1") is False


# ---------------------------------------------------------------------------
# UsersAPI.get_permissions / update_permissions
# ---------------------------------------------------------------------------


@responses.activate
def test_get_permissions(client):
    responses.get(f"{API_URL}/users/john/permissions", json={"send": True, "receive": True, "weblogin": True})
    result = client.users.get_permissions("john", "ctx1")
    assert result["send"] is True
    assert result["weblogin"] is True


@responses.activate
def test_update_permissions(client):
    responses.put(f"{API_URL}/users/john/permissions", status=204)
    client.users.update_permissions("john", "ctx1", send=True, edit_password=False)
    payload = json.loads(responses.calls[0].request.body)
    assert payload["send"] is True
    assert payload["editPassword"] is False


@responses.activate
def test_update_permissions_partial(client):
    responses.put(f"{API_URL}/users/john/permissions", status=204)
    client.users.update_permissions("john", "ctx1", weblogin=False)
    payload = json.loads(responses.calls[0].request.body)
    assert payload == {"weblogin": False}
