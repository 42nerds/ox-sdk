"""Tests for OXCloudClient initialization and sub-API accessors."""

from ox_cloud_sdk import OXCloudClient
from ox_cloud_sdk.contexts import ContextsAPI
from ox_cloud_sdk.users import UsersAPI


def test_url_construction_strips_trailing_slash():
    client = OXCloudClient("https://cloud.example.com/", "u", "p")
    assert client._api_url == "https://cloud.example.com/cloudapi/v2"


def test_url_construction_without_trailing_slash():
    client = OXCloudClient("https://cloud.example.com", "u", "p")
    assert client._api_url == "https://cloud.example.com/cloudapi/v2"


def test_session_auth():
    client = OXCloudClient("https://cloud.example.com", "admin", "secret")
    assert client._session.auth == ("admin", "secret")


def test_contexts_returns_contexts_api():
    client = OXCloudClient("https://cloud.example.com", "u", "p")
    assert isinstance(client.contexts, ContextsAPI)


def test_users_returns_users_api():
    client = OXCloudClient("https://cloud.example.com", "u", "p")
    assert isinstance(client.users, UsersAPI)


def test_contexts_is_singleton():
    client = OXCloudClient("https://cloud.example.com", "u", "p")
    assert client.contexts is client.contexts


def test_users_is_singleton():
    client = OXCloudClient("https://cloud.example.com", "u", "p")
    assert client.users is client.users
