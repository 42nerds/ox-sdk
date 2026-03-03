"""Main client entry point for the OXCloud SDK."""

import requests

from .contexts import ContextsAPI
from .users import UsersAPI


class OXCloudClient:
    """High-level client for the OXCloud Provisioning REST API v2.

    Usage::

        from ox_cloud_sdk import OXCloudClient

        client = OXCloudClient(
            base_url="https://cloud.example.com",
            username="admin",
            password="secret",
        )

        contexts = client.contexts.list()
        user = client.users.get("john", "my_context")

    Args:
        base_url: The base URL of the OXCloud instance (e.g.
            ``"https://cloud.example.com"``).  A trailing slash is stripped
            automatically.
        username: Username for HTTP Basic authentication.
        password: Password for HTTP Basic authentication.
    """

    def __init__(self, base_url, username, password):
        self._base_url = base_url.rstrip("/")
        self._api_url = f"{self._base_url}/cloudapi/v2"

        self._session = requests.Session()
        self._session.auth = (username, password)

        self._contexts = None
        self._users = None

    # ------------------------------------------------------------------
    # Sub-API accessors (lazy singletons)
    # ------------------------------------------------------------------

    @property
    def contexts(self):
        """Access the :class:`~ox_cloud_sdk.contexts.ContextsAPI`."""
        if self._contexts is None:
            self._contexts = ContextsAPI(self._session, self._api_url)
        return self._contexts

    @property
    def users(self):
        """Access the :class:`~ox_cloud_sdk.users.UsersAPI`."""
        if self._users is None:
            self._users = UsersAPI(self._session, self._api_url)
        return self._users
