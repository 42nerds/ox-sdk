"""Contexts API for OXCloud provisioning."""

from .exceptions import raise_for_status


class ContextsAPI:
    """Provides methods for managing OXCloud contexts.

    Args:
        session: An authenticated ``requests.Session``.
        base_api_url: The API base URL, e.g. ``https://host/cloudapi/v2``.
    """

    def __init__(self, session, base_api_url):
        self._session = session
        self._base_url = base_api_url

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def list(self):
        """List all contexts.

        Returns:
            A list of context dicts as returned by the API.
        """
        response = self._session.get(f"{self._base_url}/contexts")
        raise_for_status(response)
        return response.json()

    def get(self, name_or_id):
        """Get a single context by name or numeric ID.

        Args:
            name_or_id: Context name or ID.

        Returns:
            A dict representing the context.
        """
        response = self._session.get(f"{self._base_url}/contexts/{name_or_id}")
        raise_for_status(response)
        return response.json()

    def create(
        self,
        name,
        *,
        max_quota=None,
        admin_login=None,
        admin_password=None,
        admin_email=None,
        theme=None,
        max_user=None,
    ):
        """Create a new context.

        Args:
            name: Context name (required).
            max_quota: Maximum quota in MB.
            admin_login: Context admin login.
            admin_password: Context admin password.
            admin_email: Context admin email address.
            theme: Theme definition as a dict.
            max_user: Maximum number of users.

        Returns:
            A dict representing the newly created context.
        """
        payload = {"name": name}
        if max_quota is not None:
            payload["maxQuota"] = max_quota
        if admin_login is not None:
            payload["adminLogin"] = admin_login
        if admin_password is not None:
            payload["adminPassword"] = admin_password
        if admin_email is not None:
            payload["adminEmail"] = admin_email
        if theme is not None:
            payload["theme"] = theme
        if max_user is not None:
            payload["maxUser"] = max_user

        response = self._session.post(f"{self._base_url}/contexts", json=payload)
        raise_for_status(response)
        return response.json()

    def update(self, name_or_id, *, max_quota=None, theme=None, max_user=None):
        """Update an existing context.

        Only the supplied fields will be changed; omitted fields remain
        unchanged on the server.

        Args:
            name_or_id: Context name or ID.
            max_quota: New maximum quota in MB.
            theme: New theme definition as a dict.
            max_user: New maximum number of users.

        Returns:
            A dict representing the updated context, or an empty dict if the
            API returned no body.
        """
        payload = {}
        if max_quota is not None:
            payload["maxQuota"] = max_quota
        if theme is not None:
            payload["theme"] = theme
        if max_user is not None:
            payload["maxUser"] = max_user

        response = self._session.put(f"{self._base_url}/contexts/{name_or_id}", json=payload)
        raise_for_status(response)

        if response.content and response.content.strip():
            try:
                return response.json()
            except ValueError:
                return {}
        return {}

    def delete(self, name_or_id):
        """Delete a context.

        Args:
            name_or_id: Context name or ID.
        """
        response = self._session.delete(f"{self._base_url}/contexts/{name_or_id}")
        raise_for_status(response)
