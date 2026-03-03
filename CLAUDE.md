# OXCloud Python SDK (ox-cloud-sdk)

Standalone Python SDK for the OXCloud Provisioning REST API v2.

## Structure

```
ox-sdk/
├── ox_cloud_sdk/
│   ├── __init__.py         # Exports OXCloudClient and exceptions
│   ├── client.py           # OXCloudClient main class
│   ├── contexts.py         # ContextsAPI (list, get, create, update, delete)
│   ├── users.py            # UsersAPI (list, get, create, update, delete, count, check_login, permissions)
│   └── exceptions.py       # OXCloudError, OXNotFoundError, OXConflictError, OXAuthError
├── setup.py
└── pyproject.toml
```

## Usage

```python
from ox_cloud_sdk import OXCloudClient

client = OXCloudClient("https://provisioning.eu.appsuite.cloud", "user", "pass")
contexts = client.contexts.list()
user = client.users.get("john", "my_context")
```

## API Reference

All API logic was extracted from the original `/ox-cli/main.py`.
The OpenAPI spec is at `/ox-cli/cloud-provisioning-rest-api-2.3.0.yml`.

### Key design decisions:
- Uses `requests.Session` with basic auth for connection reuse
- `users.update()` accepts `**fields` with snake_case names, auto-mapped to camelCase
- `users.check_login()` returns bool (True if exists, False if 404)
- `users.count()` returns int directly
- Custom exceptions map HTTP status codes: 401→OXAuthError, 404→OXNotFoundError, 409→OXConflictError
- No CLI dependency — this is a pure library

## Dependencies

- `requests>=2.28`
