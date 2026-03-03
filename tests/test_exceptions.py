"""Tests for exception classes and raise_for_status."""

from unittest.mock import MagicMock

import pytest

from ox_cloud_sdk.exceptions import (
    OXAuthError,
    OXCloudError,
    OXConflictError,
    OXNotFoundError,
    raise_for_status,
)


def _make_response(status_code, json_body=None, text=""):
    """Create a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.text = text
    if json_body is not None:
        resp.json.return_value = json_body
        resp.text = str(json_body)
    else:
        resp.json.side_effect = ValueError("No JSON")
    return resp


class TestRaiseForStatus:
    def test_2xx_does_not_raise(self):
        raise_for_status(_make_response(200))
        raise_for_status(_make_response(201))
        raise_for_status(_make_response(204))

    def test_401_raises_auth_error(self):
        body = {"errors": [{"code": "2", "title": "Authentication failed", "status": "401"}]}
        with pytest.raises(OXAuthError) as exc_info:
            raise_for_status(_make_response(401, json_body=body))
        assert exc_info.value.status_code == 401
        assert exc_info.value.error_code == "2"
        assert exc_info.value.message == "Authentication failed"

    def test_404_raises_not_found_error(self):
        body = {"errors": [{"code": "1", "title": "User not found", "status": "404"}]}
        with pytest.raises(OXNotFoundError) as exc_info:
            raise_for_status(_make_response(404, json_body=body))
        assert exc_info.value.status_code == 404

    def test_409_raises_conflict_error(self):
        body = {"errors": [{"code": "8", "title": "Context already exists", "status": "409"}]}
        with pytest.raises(OXConflictError):
            raise_for_status(_make_response(409, json_body=body))

    def test_500_raises_base_error(self):
        with pytest.raises(OXCloudError) as exc_info:
            raise_for_status(_make_response(500, text="Internal Server Error"))
        assert exc_info.value.status_code == 500
        assert "Internal Server Error" in exc_info.value.message

    def test_non_json_body_falls_back_to_text(self):
        with pytest.raises(OXCloudError) as exc_info:
            raise_for_status(_make_response(400, text="Bad Request"))
        assert exc_info.value.message == "Bad Request"

    def test_json_without_errors_key_uses_text(self):
        resp = _make_response(400, json_body={"detail": "something"}, text="raw text")
        # json_body has no "errors" key, so message falls back to resp.text
        resp.text = "raw text"
        with pytest.raises(OXCloudError) as exc_info:
            raise_for_status(resp)
        assert exc_info.value.message == "raw text"


class TestExceptionRepr:
    def test_repr_includes_class_and_fields(self):
        err = OXCloudError("test msg", status_code=500, error_code="5")
        r = repr(err)
        assert "OXCloudError" in r
        assert "500" in r
        assert "test msg" in r
        assert "5" in r

    def test_subclass_repr(self):
        err = OXNotFoundError("not found", status_code=404, error_code="1")
        assert "OXNotFoundError" in repr(err)
