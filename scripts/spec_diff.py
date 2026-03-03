#!/usr/bin/env python3
"""Diff two versions of the OXCloud Provisioning API spec.

By default compares the last committed version (via ``git show``) against the
current file on disk at ``specs/current.yml``.
"""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

SPECS_DIR = Path(__file__).resolve().parent.parent / "specs"
REPO_ROOT = Path(__file__).resolve().parent.parent
V2_PREFIX = "/cloudapi/v2/"

# ANSI helpers ---------------------------------------------------------------

_IS_TTY = sys.stdout.isatty()
GREEN = "\033[32m" if _IS_TTY else ""
RED = "\033[31m" if _IS_TTY else ""
YELLOW = "\033[33m" if _IS_TTY else ""
BOLD = "\033[1m" if _IS_TTY else ""
RESET = "\033[0m" if _IS_TTY else ""


# Helpers --------------------------------------------------------------------


def _load_from_git(rel_path):
    """Load a file from the last git commit.  Returns *None* on failure."""
    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:{rel_path}"],
            capture_output=True,
            text=True,
            check=True,
            cwd=REPO_ROOT,
        )
        return yaml.safe_load(result.stdout)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


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


def _schemas(spec):
    """Return ``{name: {prop_name: prop_def}}``."""
    out = {}
    for name, defn in spec.get("components", {}).get("schemas", {}).items():
        out[name] = defn.get("properties", {})
    return out


def _params(operation):
    """Return a set of query-parameter names from an operation dict."""
    return {p["name"] for p in operation.get("parameters", []) if p.get("in") == "query"}


def _resolve_ref(spec, ref):
    """Follow a ``$ref`` string to the referenced dict."""
    parts = ref.lstrip("#/").split("/")
    node = spec
    for part in parts:
        node = node.get(part, {})
    return node


def _request_body_props(spec, operation):
    """Return the property dict for an operation's JSON request body (or ``{}``)."""
    rb = operation.get("requestBody", {})
    schema = rb.get("content", {}).get("application/json", {}).get("schema", {})
    if "$ref" in schema:
        schema = _resolve_ref(spec, schema["$ref"])
    return schema.get("properties", {})


# Diff sections --------------------------------------------------------------


def _diff_version(old_spec, new_spec):
    old_v = old_spec.get("info", {}).get("version", "?")
    new_v = new_spec.get("info", {}).get("version", "?")
    if old_v != new_v:
        print(f"Version: {old_v} -> {YELLOW}{new_v}{RESET}")
    else:
        print(f"Version: {old_v} (unchanged)")
    print()


def _diff_endpoints(old_eps, new_eps):
    old_keys = set(old_eps)
    new_keys = set(new_eps)
    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)

    if not added and not removed:
        print("  (no endpoint changes)")
        print()
        return

    for path, method in added:
        print(f"  {GREEN}+ {method:6s} {path}{RESET}")
    for path, method in removed:
        print(f"  {RED}- {method:6s} {path}{RESET}")
    print()


def _diff_schemas(old_schemas, new_schemas):
    old_names = set(old_schemas)
    new_names = set(new_schemas)
    has_output = False

    for name in sorted(new_names - old_names):
        print(f"  {GREEN}+ {name}{RESET}  (new schema)")
        has_output = True
    for name in sorted(old_names - new_names):
        print(f"  {RED}- {name}{RESET}  (removed schema)")
        has_output = True

    for name in sorted(old_names & new_names):
        old_props = set(old_schemas[name])
        new_props = set(new_schemas[name])
        added = sorted(new_props - old_props)
        removed = sorted(old_props - new_props)
        if added or removed:
            print(f"  {YELLOW}~ {name}:{RESET}")
            for p in added:
                ptype = new_schemas[name][p].get("type", new_schemas[name][p].get("$ref", "?"))
                print(f"    {GREEN}+ {p} ({ptype}){RESET}")
            for p in removed:
                print(f"    {RED}- {p}{RESET}")
            has_output = True

    if not has_output:
        print("  (no schema changes)")
    print()


def _diff_parameters(old_eps, new_eps, old_spec, new_spec):
    common = set(old_eps) & set(new_eps)
    has_output = False

    for key in sorted(common):
        path, method = key
        old_params = _params(old_eps[key])
        new_params = _params(new_eps[key])
        added = sorted(new_params - old_params)
        removed = sorted(old_params - new_params)
        if added or removed:
            print(f"  {YELLOW}~ {method} {path}:{RESET}")
            for p in added:
                print(f"    {GREEN}+ {p}{RESET}")
            for p in removed:
                print(f"    {RED}- {p}{RESET}")
            has_output = True

    # Also check request body field changes
    for key in sorted(common):
        path, method = key
        old_body = _request_body_props(old_spec, old_eps[key])
        new_body = _request_body_props(new_spec, new_eps[key])
        if not old_body and not new_body:
            continue
        old_fields = set(old_body)
        new_fields = set(new_body)
        added = sorted(new_fields - old_fields)
        removed = sorted(old_fields - new_fields)
        if added or removed:
            print(f"  {YELLOW}~ {method} {path} (body):{RESET}")
            for f in added:
                ftype = new_body[f].get("type", new_body[f].get("$ref", "?"))
                print(f"    {GREEN}+ {f} ({ftype}){RESET}")
            for f in removed:
                print(f"    {RED}- {f}{RESET}")
            has_output = True

    if not has_output:
        print("  (no parameter/body changes)")
    print()


# Main -----------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Diff OXCloud API specs")
    parser.add_argument("--old", type=Path, help="Path to old spec (default: git HEAD version)")
    parser.add_argument(
        "--new",
        type=Path,
        default=SPECS_DIR / "current.yml",
        help="Path to new spec (default: specs/current.yml)",
    )
    args = parser.parse_args()

    if not args.new.exists():
        print("No current spec found. Run 'make fetch-spec' first.", file=sys.stderr)
        sys.exit(1)
    new_spec = yaml.safe_load(args.new.read_text())

    if args.old:
        old_spec = yaml.safe_load(args.old.read_text())
    else:
        rel = args.new.resolve().relative_to(REPO_ROOT)
        old_spec = _load_from_git(str(rel))
        if old_spec is None:
            print("No previous spec in git history. Nothing to diff.")
            sys.exit(0)

    print(f"{BOLD}=== OXCloud API Spec Diff ==={RESET}")
    _diff_version(old_spec, new_spec)

    old_eps = _v2_endpoints(old_spec)
    new_eps = _v2_endpoints(new_spec)

    print(f"{BOLD}--- Endpoints ---{RESET}")
    _diff_endpoints(old_eps, new_eps)

    print(f"{BOLD}--- Schemas ---{RESET}")
    _diff_schemas(_schemas(old_spec), _schemas(new_spec))

    print(f"{BOLD}--- Parameters & Request Bodies ---{RESET}")
    _diff_parameters(old_eps, new_eps, old_spec, new_spec)

    # Summary
    old_keys = set(old_eps)
    new_keys = set(new_eps)
    added_count = len(new_keys - old_keys)
    removed_count = len(old_keys - new_keys)
    unchanged_count = len(old_keys & new_keys)
    print(f"{BOLD}=== Summary ==={RESET}")
    print(f"Endpoints: {added_count} added, {removed_count} removed, {unchanged_count} unchanged")


if __name__ == "__main__":
    main()
