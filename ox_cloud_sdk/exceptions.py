"""Exception classes for the OXCloud SDK."""


class OXCloudError(Exception):
    """Base exception for OXCloud API errors.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code from the API response, if available.
        error_code: OXCloud-specific error code from the API response, if available.
    """

    def __init__(self, message, status_code=None, error_code=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"status_code={self.status_code!r}, "
            f"error_code={self.error_code!r})"
        )


class OXNotFoundError(OXCloudError):
    """Raised when the requested resource is not found (HTTP 404)."""

    pass


class OXConflictError(OXCloudError):
    """Raised on conflict or validation errors (HTTP 409)."""

    pass


class OXAuthError(OXCloudError):
    """Raised when authentication fails (HTTP 401)."""

    pass


_STATUS_CODE_MAP = {
    401: OXAuthError,
    404: OXNotFoundError,
    409: OXConflictError,
}


def raise_for_status(response):
    """Inspect an API response and raise a typed exception on error.

    For non-2xx responses the function attempts to extract the OXCloud error
    body (JSON API error format) and raises the appropriate exception subclass.
    2xx responses pass through without raising.

    Args:
        response: A ``requests.Response`` object.

    Raises:
        OXAuthError: On HTTP 401.
        OXNotFoundError: On HTTP 404.
        OXConflictError: On HTTP 409.
        OXCloudError: On any other non-2xx status code.
    """
    if response.ok:
        return

    status_code = response.status_code
    error_code = None
    message = response.text

    # Attempt to parse the OXCloud JSON-API error envelope.
    try:
        body = response.json()
        errors = body.get("errors")
        if errors and isinstance(errors, list) and len(errors) > 0:
            err = errors[0]
            error_code = err.get("code")
            message = err.get("title", message)
    except (ValueError, KeyError, AttributeError):
        pass

    exc_class = _STATUS_CODE_MAP.get(status_code, OXCloudError)
    raise exc_class(message, status_code=status_code, error_code=error_code)
