#!/usr/bin/env python3
"""Validate SDK coverage against the OXCloud API spec.

Parses ``specs/current.yml`` and checks which endpoints and fields are
implemented in the hand-written SDK code.
"""

import re
import sys
from pathlib import Path

import yaml

SPECS_DIR = Path(__file__).resolve().parent.parent / "specs"
SDK_DIR = Path(__file__).resolve().parent.parent / "ox_cloud_sdk"
V2_PREFIX = "/cloudapi/v2/"

# ANSI helpers ---------------------------------------------------------------

_IS_TTY = sys.stdout.isatty()
GREEN = "\033[32m" if _IS_TTY else ""
RED = "\033[31m" if _IS_TTY else ""
YELLOW = "\033[33m" if _IS_TTY else ""
BOLD = "\033[1m" if _IS_TTY else ""
RESET = "\033[0m" if _IS_TTY else ""

# ---------------------------------------------------------------------------
# Endpoint mapping: (spec_path, HTTP_method) -> (module, class, method)
#
# This mapping is intentionally hand-maintained.  When the spec adds new
# endpoints, this script will report them as MISSING so a developer can
# decide whether to add SDK support and update this mapping.
# ---------------------------------------------------------------------------
ENDPOINT_MAP = {
    # Contexts
    ("/cloudapi/v2/contexts", "GET"): ("contexts", "ContextsAPI", "list"),
    ("/cloudapi/v2/contexts", "POST"): ("contexts", "ContextsAPI", "create"),
    ("/cloudapi/v2/contexts/{nameOrId}", "GET"): ("contexts", "ContextsAPI", "get"),
    ("/cloudapi/v2/contexts/{nameOrId}", "PUT"): ("contexts", "ContextsAPI", "update"),
    ("/cloudapi/v2/contexts/{nameOrId}", "DELETE"): ("contexts", "ContextsAPI", "delete"),
    # Users
    ("/cloudapi/v2/users", "GET"): ("users", "UsersAPI", "list"),
    ("/cloudapi/v2/users", "POST"): ("users", "UsersAPI", "create"),
    ("/cloudapi/v2/users/count", "GET"): ("users", "UsersAPI", "count"),
    ("/cloudapi/v2/users/{login}", "GET"): ("users", "UsersAPI", "get"),
    ("/cloudapi/v2/users/{login}", "PUT"): ("users", "UsersAPI", "update"),
    ("/cloudapi/v2/users/{login}", "DELETE"): ("users", "UsersAPI", "delete"),
    ("/cloudapi/v2/users/{login}/exists", "HEAD"): ("users", "UsersAPI", "check_login"),
    ("/cloudapi/v2/users/{login}/permissions", "GET"): ("users", "UsersAPI", "get_permissions"),
    ("/cloudapi/v2/users/{login}/permissions", "PUT"): ("users", "UsersAPI", "update_permissions"),
}


# ---------------------------------------------------------------------------
# Spec helpers
# ---------------------------------------------------------------------------


def _load_spec():
    spec_path = SPECS_DIR / "current.yml"
    if not spec_path.exists():
        print("No spec found. Run 'make fetch-spec' first.", file=sys.stderr)
        sys.exit(1)
    return yaml.safe_load(spec_path.read_text())


def _v2_endpoints(spec):
    """Return ``{(path, METHOD): operation}`` for all v2 paths."""
    endpoints = {}
    for path, methods in spec.get("paths", {}).items():
        if not path.startswith(V2_PREFIX):
            continue
        for method, op in methods.items():
            if method in {"get", "post", "put", "delete", "head", "patch"}:
                endpoints[(path, method.upper())] = op
    return endpoints


def _resolve_ref(spec, ref):
    parts = ref.lstrip("#/").split("/")
    node = spec
    for part in parts:
        node = node.get(part, {})
    return node


def _request_body_fields(spec, operation):
    """Return ``{field_name: field_def}`` for an operation's JSON body."""
    rb = operation.get("requestBody", {})
    schema = rb.get("content", {}).get("application/json", {}).get("schema", {})
    if "$ref" in schema:
        schema = _resolve_ref(spec, schema["$ref"])
    return schema.get("properties", {})


def _query_params(operation):
    """Return ``{param_name: param_def}`` for query parameters."""
    return {p["name"]: p for p in operation.get("parameters", []) if p.get("in") == "query"}


# ---------------------------------------------------------------------------
# SDK source parsing
# ---------------------------------------------------------------------------


def _sdk_user_fields():
    """Extract known camelCase field names from ``users.py``."""
    source = (SDK_DIR / "users.py").read_text()

    # Values from _FIELD_MAP
    field_map_match = re.search(r"_FIELD_MAP\s*=\s*\{(.+?)\}", source, re.DOTALL)
    camel_fields = set()
    if field_map_match:
        camel_fields = set(re.findall(r'"(\w+)"', field_map_match.group(1)))
        # _FIELD_MAP contains both keys and values; keep only the values (camelCase).
        # The values are the even-indexed matches in each "key": "value" pair.
        pairs = re.findall(r'"(\w+)"\s*:\s*"(\w+)"', field_map_match.group(1))
        camel_fields = {v for _, v in pairs}

    # Hard-coded fields in create() payload (payload["fieldName"] = ...)
    camel_fields.update(re.findall(r'payload\["(\w+)"\]', source))

    # The 'name' field is set as payload key in create()
    camel_fields.add("name")

    return camel_fields


def _sdk_context_fields():
    """Extract known camelCase field names from ``contexts.py``."""
    source = (SDK_DIR / "contexts.py").read_text()
    fields = set(re.findall(r'payload\["(\w+)"\]', source))
    fields.add("name")
    return fields


def _sdk_permission_fields():
    """Extract known camelCase field names from the permissions methods in ``users.py``."""
    source = (SDK_DIR / "users.py").read_text()
    # Look for payload["fieldName"] in the update_permissions section
    perm_start = source.find("def update_permissions")
    if perm_start == -1:
        return set()
    perm_source = source[perm_start:]
    return set(re.findall(r'payload\["(\w+)"\]', perm_source))


def _sdk_query_params(module_file, method_name):
    """Extract query parameter names used in a specific method of an SDK module."""
    source = (SDK_DIR / f"{module_file}.py").read_text()
    method_start = source.find(f"def {method_name}")
    if method_start == -1:
        return set()

    # Find the next method or end of class
    next_def = source.find("\n    def ", method_start + 1)
    method_source = source[method_start:next_def] if next_def != -1 else source[method_start:]

    # Extract params["key"] = ... assignment patterns
    params = set(re.findall(r'params\["(\w+)"\]', method_source))
    # Extract dict literal keys: params = {"key": ..., "key2": ...}
    dict_match = re.search(r"params\s*=\s*\{([^}]+)\}", method_source)
    if dict_match:
        params.update(re.findall(r'"(\w+)"\s*:', dict_match.group(1)))
    return params


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------


def _report_endpoints(spec_endpoints):
    """Print endpoint coverage and return (covered_count, missing_count)."""
    covered = 0
    missing = 0

    for key in sorted(spec_endpoints):
        path, method = key
        if key in ENDPOINT_MAP:
            mod, cls, meth = ENDPOINT_MAP[key]
            print(f"  {GREEN}[COVERED]{RESET}  {method:6s} {path}  -> {mod}.{cls}.{meth}()")
            covered += 1
        else:
            print(f"  {RED}[MISSING]{RESET}  {method:6s} {path}")
            missing += 1

    return covered, missing


def _report_fields(spec, spec_endpoints):
    """Print field coverage for endpoints with request bodies.

    Returns ``(covered, missing)`` totals.
    """
    total_covered = 0
    total_missing = 0

    # Group checks by SDK module
    checks = [
        # (spec_key, label, sdk_fields_fn)
        (("/cloudapi/v2/users", "POST"), "CreateUser", _sdk_user_fields),
        (("/cloudapi/v2/users/{login}", "PUT"), "ChangeUser", _sdk_user_fields),
        (("/cloudapi/v2/contexts", "POST"), "CreateContext", _sdk_context_fields),
        (("/cloudapi/v2/contexts/{nameOrId}", "PUT"), "UpdateContext", _sdk_context_fields),
        (
            ("/cloudapi/v2/users/{login}/permissions", "PUT"),
            "UpdatePermissions",
            _sdk_permission_fields,
        ),
    ]

    for spec_key, label, fields_fn in checks:
        if spec_key not in spec_endpoints:
            continue

        spec_fields = _request_body_fields(spec, spec_endpoints[spec_key])
        if not spec_fields:
            continue

        sdk_fields = fields_fn()
        print(f"\n  {BOLD}{label} ({spec_key[1]} {spec_key[0]}):{RESET}")

        for field_name in sorted(spec_fields):
            if field_name in sdk_fields:
                print(f"    {GREEN}[OK]{RESET}      {field_name}")
                total_covered += 1
            else:
                ftype = spec_fields[field_name].get("type", spec_fields[field_name].get("$ref", "?"))
                print(f"    {RED}[MISSING]{RESET}  {field_name} ({ftype})")
                total_missing += 1

    return total_covered, total_missing


def _report_query_params(spec, spec_endpoints):
    """Print query parameter coverage.

    Returns ``(covered, missing)`` totals.
    """
    total_covered = 0
    total_missing = 0
    has_output = False

    for spec_key in sorted(spec_endpoints):
        if spec_key not in ENDPOINT_MAP:
            continue

        spec_params = _query_params(spec_endpoints[spec_key])
        if not spec_params:
            continue

        mod, _cls, meth = ENDPOINT_MAP[spec_key]
        sdk_params = _sdk_query_params(mod, meth)

        path, method = spec_key
        missing = []
        covered = []
        for pname in sorted(spec_params):
            if pname in sdk_params:
                covered.append(pname)
                total_covered += 1
            else:
                missing.append(pname)
                total_missing += 1

        if missing:
            has_output = True
            print(f"  {YELLOW}~ {method} {path}:{RESET}")
            for p in covered:
                print(f"    {GREEN}[OK]{RESET}      {p}")
            for p in missing:
                print(f"    {RED}[MISSING]{RESET}  {p}")

    if not has_output:
        print("  (all query parameters covered)")

    return total_covered, total_missing


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    spec = _load_spec()
    spec_endpoints = _v2_endpoints(spec)
    version = spec.get("info", {}).get("version", "?")

    print(f"{BOLD}=== SDK Coverage Report ==={RESET}")
    print(f"Spec version: {version}")
    print(f"Spec endpoints (v2): {len(spec_endpoints)}")
    print(f"SDK-mapped endpoints: {len(ENDPOINT_MAP)}")
    print()

    print(f"{BOLD}--- Endpoint Coverage ---{RESET}")
    ep_covered, ep_missing = _report_endpoints(spec_endpoints)
    print()

    print(f"{BOLD}--- Field Coverage ---{RESET}")
    f_covered, f_missing = _report_fields(spec, spec_endpoints)
    print()

    print(f"{BOLD}--- Query Parameter Coverage ---{RESET}")
    qp_covered, qp_missing = _report_query_params(spec, spec_endpoints)
    print()

    # Summary
    print(f"{BOLD}=== Summary ==={RESET}")

    def _pct(c, m):
        total = c + m
        return f"{c}/{total} ({c / total * 100:.1f}%)" if total > 0 else "n/a"

    print(f"Endpoints:        {_pct(ep_covered, ep_missing)}")
    print(f"Request fields:   {_pct(f_covered, f_missing)}")
    print(f"Query parameters: {_pct(qp_covered, qp_missing)}")


if __name__ == "__main__":
    main()
