"""Users API for OXCloud provisioning."""

from .exceptions import raise_for_status

# Mapping from Python snake_case keyword arguments to camelCase API field names.
_FIELD_MAP = {
    "password": "password",
    "given_name": "givenName",
    "sur_name": "surName",
    "mail": "mail",
    "display_name": "displayName",
    "class_of_service": "classOfService",
    "language": "language",
    "aliases": "aliases",
    "timezone": "timezone",
    "spam_level": "spamLevel",
    "unified_quota": "unifiedQuota",
    "mail_quota": "mailQuota",
    "file_quota": "fileQuota",
    "user_admin_enabled": "userAdminEnabled",
    "email_backup_enabled": "emailBackupEnabled",
}


def _validate_quotas(fields):
    """Raise ``ValueError`` if both unified and split quotas are specified."""
    unified = fields.get("unified_quota") if "unified_quota" in fields else None
    mail_q = fields.get("mail_quota") if "mail_quota" in fields else None
    file_q = fields.get("file_quota") if "file_quota" in fields else None

    if unified is not None and (mail_q is not None or file_q is not None):
        raise ValueError("Either unified_quota OR mail_quota/file_quota may be set, not both at the same time.")


def _build_payload(fields):
    """Convert snake_case *fields* dict to a camelCase API payload.

    Only keys whose values are not ``None`` are included.  List-typed values
    (``aliases``, ``class_of_service``) are converted to plain lists.
    """
    payload = {}
    for key, value in fields.items():
        if value is None:
            continue
        api_key = _FIELD_MAP.get(key)
        if api_key is None:
            raise ValueError(f"Unknown user field: {key!r}")
        if isinstance(value, tuple):
            value = list(value)
        payload[api_key] = value
    return payload


class UsersAPI:
    """Provides methods for managing OXCloud users.

    Args:
        session: An authenticated ``requests.Session``.
        base_api_url: The API base URL, e.g. ``https://host/cloudapi/v2``.
    """

    def __init__(self, session, base_api_url):
        self._session = session
        self._base_url = base_api_url

    # ------------------------------------------------------------------
    # List / Get
    # ------------------------------------------------------------------

    def list(
        self,
        context,
        *,
        pattern="*",
        include_guests=False,
        include_id=False,
        include_weblogin_enabled=False,
        include_image=False,
        include_user_admin_enabled=False,
    ):
        """List users in a context.

        Args:
            context: Context name or ID.
            pattern: Search pattern (default ``"*"``).
            include_guests: Include guest accounts.
            include_id: Include user IDs in results.
            include_weblogin_enabled: Include weblogin status.
            include_image: Include user image data.
            include_user_admin_enabled: Include user-admin flag.

        Returns:
            A list of user dicts.
        """
        params = {"name": context, "pattern": pattern}

        # Only add boolean flags that are True.
        if include_guests:
            params["includeguests"] = "true"
        if include_id:
            params["includeid"] = "true"
        if include_weblogin_enabled:
            params["includewebloginenabled"] = "true"
        if include_image:
            params["includeimage"] = "true"
        if include_user_admin_enabled:
            params["includeuseradminenabled"] = "true"

        response = self._session.get(f"{self._base_url}/users", params=params)
        raise_for_status(response)
        return response.json()

    def get(
        self,
        login,
        context,
        *,
        include_id=False,
        include_weblogin_enabled=False,
        include_image=False,
        include_permissions=False,
        include_user_admin_enabled=False,
    ):
        """Get a single user.

        Args:
            login: User login name.
            context: Context name or ID.
            include_id: Include user ID.
            include_weblogin_enabled: Include weblogin status.
            include_image: Include user image data.
            include_permissions: Include user permissions.
            include_user_admin_enabled: Include user-admin flag.

        Returns:
            A dict representing the user.
        """
        params = {"name": context}
        if include_id:
            params["includeid"] = "true"
        if include_weblogin_enabled:
            params["includewebloginenabled"] = "true"
        if include_image:
            params["includeimage"] = "true"
        if include_permissions:
            params["includepermissions"] = "true"
        if include_user_admin_enabled:
            params["includeuseradminenabled"] = "true"

        response = self._session.get(f"{self._base_url}/users/{login}", params=params)
        raise_for_status(response)
        return response.json()

    # ------------------------------------------------------------------
    # Create / Update / Delete
    # ------------------------------------------------------------------

    def create(
        self,
        login,
        context,
        *,
        password,
        given_name,
        sur_name,
        mail,
        display_name=None,
        class_of_service=None,
        language=None,
        aliases=None,
        timezone=None,
        spam_level=None,
        unified_quota=None,
        mail_quota=None,
        file_quota=None,
        user_admin_enabled=None,
    ):
        """Create a new user in a context.

        Args:
            login: User login name (required).
            context: Context name or ID (required).
            password: User password (required).
            given_name: First name (required).
            sur_name: Last name (required).
            mail: Primary email address (required).
            display_name: Display name.
            class_of_service: Class-of-service list.
            language: Language code, e.g. ``"en_US"``.
            aliases: List of alias email addresses.
            timezone: Timezone, e.g. ``"Europe/Berlin"``.
            spam_level: One of ``"low"``, ``"medium"``, ``"high"``.
            unified_quota: Unified quota in MB (mutually exclusive with
                *mail_quota* / *file_quota*).
            mail_quota: Mail quota in MB.
            file_quota: File quota in MB.
            user_admin_enabled: Whether the user has admin privileges.

        Returns:
            A dict representing the newly created user.

        Raises:
            ValueError: If both *unified_quota* and *mail_quota*/*file_quota*
                are supplied.
        """
        _validate_quotas(
            {
                "unified_quota": unified_quota,
                "mail_quota": mail_quota,
                "file_quota": file_quota,
            }
        )

        payload = {
            "name": login,
            "password": password,
            "givenName": given_name,
            "surName": sur_name,
            "mail": mail,
        }
        if display_name is not None:
            payload["displayName"] = display_name
        if class_of_service is not None:
            payload["classOfService"] = (
                list(class_of_service) if not isinstance(class_of_service, list) else class_of_service
            )
        if language is not None:
            payload["language"] = language
        if aliases is not None:
            payload["aliases"] = list(aliases) if not isinstance(aliases, list) else aliases
        if timezone is not None:
            payload["timezone"] = timezone
        if spam_level is not None:
            payload["spamLevel"] = spam_level
        if unified_quota is not None:
            payload["unifiedQuota"] = unified_quota
        if mail_quota is not None:
            payload["mailQuota"] = mail_quota
        if file_quota is not None:
            payload["fileQuota"] = file_quota
        if user_admin_enabled is not None:
            payload["userAdminEnabled"] = user_admin_enabled

        params = {"name": context}
        response = self._session.post(f"{self._base_url}/users", params=params, json=payload)
        raise_for_status(response)
        return response.json()

    def update(self, login, context, **fields):
        """Update an existing user.

        Only the supplied keyword arguments will be sent to the API. Field
        names use Python snake_case and are mapped to camelCase for the
        request payload automatically.

        Supported fields:
            password, given_name, sur_name, mail, display_name,
            class_of_service, language, aliases, timezone, spam_level,
            unified_quota, mail_quota, file_quota, user_admin_enabled,
            email_backup_enabled.

        Args:
            login: User login name.
            context: Context name or ID.
            **fields: Keyword arguments for the fields to update.

        Returns:
            A dict representing the updated user, or an empty dict if the
            API returned no body.

        Raises:
            ValueError: If both *unified_quota* and *mail_quota*/*file_quota*
                are supplied, or if an unknown field name is given.
        """
        _validate_quotas(fields)
        payload = _build_payload(fields)

        params = {"name": context}
        response = self._session.put(f"{self._base_url}/users/{login}", params=params, json=payload)
        raise_for_status(response)

        if response.content and response.content.strip():
            try:
                return response.json()
            except ValueError:
                return {}
        return {}

    def delete(self, login, context, *, reassign_user=None):
        """Delete a user.

        Args:
            login: User login name.
            context: Context name or ID.
            reassign_user: Optional login of a user to reassign shared data to.
        """
        params = {"name": context}
        if reassign_user is not None:
            params["reassignuser"] = reassign_user

        response = self._session.delete(f"{self._base_url}/users/{login}", params=params)
        raise_for_status(response)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def count(self, context):
        """Return the number of users in a context.

        Args:
            context: Context name or ID.

        Returns:
            An int with the user count.
        """
        params = {"name": context}
        response = self._session.get(f"{self._base_url}/users/amount", params=params)
        raise_for_status(response)
        data = response.json()
        return data.get("amount", data)

    def check_login(self, login, context):
        """Check whether a login exists in a context.

        Args:
            login: User login name.
            context: Context name or ID.

        Returns:
            ``True`` if the user exists (HTTP 200), ``False`` if not found
            (HTTP 404).

        Raises:
            OXCloudError: On any status code other than 200 or 404.
        """
        params = {"name": context}
        response = self._session.get(f"{self._base_url}/users/{login}", params=params)
        if response.status_code == 404:
            return False
        raise_for_status(response)
        return True

    # ------------------------------------------------------------------
    # Permissions
    # ------------------------------------------------------------------

    def get_permissions(self, login, context):
        """Get user permissions.

        Args:
            login: User login name.
            context: Context name or ID.

        Returns:
            A dict of permission flags.
        """
        params = {"name": context}
        response = self._session.get(f"{self._base_url}/users/{login}/permissions", params=params)
        raise_for_status(response)
        return response.json()

    def update_permissions(
        self,
        login,
        context,
        *,
        send=None,
        receive=None,
        maillogin=None,
        weblogin=None,
        edit_password=None,
    ):
        """Update user permissions.

        Only the supplied keyword arguments will be included in the request
        payload.

        Args:
            login: User login name.
            context: Context name or ID.
            send: Allow or deny sending.
            receive: Allow or deny receiving.
            maillogin: Allow or deny mail login.
            weblogin: Allow or deny web login.
            edit_password: Allow or deny password changes.
        """
        payload = {}
        if send is not None:
            payload["send"] = send
        if receive is not None:
            payload["receive"] = receive
        if maillogin is not None:
            payload["maillogin"] = maillogin
        if weblogin is not None:
            payload["weblogin"] = weblogin
        if edit_password is not None:
            payload["editPassword"] = edit_password

        params = {"name": context}
        response = self._session.put(
            f"{self._base_url}/users/{login}/permissions",
            params=params,
            json=payload,
        )
        raise_for_status(response)
