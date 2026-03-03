"""Shared test fixtures for the OXCloud SDK test suite."""

import pytest

from ox_cloud_sdk import OXCloudClient

BASE_URL = "https://cloud.example.com"
API_URL = f"{BASE_URL}/cloudapi/v2"


@pytest.fixture
def client():
    """Return an OXCloudClient pointed at the test base URL."""
    return OXCloudClient(BASE_URL, "admin", "secret")
