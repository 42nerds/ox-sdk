# ox-cloud-sdk

Python SDK for the OXCloud Provisioning REST API v2.

## Requirements

- Python 3.10+

## Installation

```bash
pip install git+https://github.com/42nerds/ox-sdk.git
```

Pin to a specific version tag:

```bash
pip install git+https://github.com/42nerds/ox-sdk.git@v1.0.0
```

In `requirements.txt`:

```
ox-cloud-sdk @ git+https://github.com/42nerds/ox-sdk.git@v1.0.0
```

## Usage

```python
from ox_cloud_sdk import OXCloudClient

client = OXCloudClient(
    base_url="https://provisioning.eu.appsuite.cloud",
    username="admin",
    password="secret",
)

# Contexts
contexts = client.contexts.list()
ctx = client.contexts.get("my_context")
client.contexts.create("new_context", max_quota=2048)
client.contexts.update("my_context", max_user=100)
client.contexts.delete("old_context")

# Users
users = client.users.list("my_context")
user = client.users.get("john", "my_context")
client.users.create(
    "jane", "my_context",
    password="s3cret",
    given_name="Jane",
    sur_name="Doe",
    mail="jane@example.com",
)
client.users.update("jane", "my_context", display_name="Jane D.")
client.users.delete("jane", "my_context")

# Helpers
count = client.users.count("my_context")
exists = client.users.check_login("john", "my_context")
perms = client.users.get_permissions("john", "my_context")
```

## Exception Handling

```python
from ox_cloud_sdk import OXCloudError, OXNotFoundError, OXAuthError, OXConflictError

try:
    client.users.get("unknown", "my_context")
except OXNotFoundError as e:
    print(f"Not found: {e.message} (code={e.error_code})")
except OXAuthError:
    print("Authentication failed")
except OXConflictError:
    print("Conflict / validation error")
except OXCloudError as e:
    print(f"API error {e.status_code}: {e.message}")
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Lint
ruff check .

# Format
ruff format .

# Install pre-commit hooks
pre-commit install
```
