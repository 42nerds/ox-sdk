#!/usr/bin/env python3
"""Download the latest OXCloud Provisioning API spec from the OX documentation site."""

import hashlib
import re
import sys
from pathlib import Path

import requests
import yaml

DOCS_URL = "https://documentation.open-xchange.com/components/cloud-api/latest/"
SPECS_DIR = Path(__file__).resolve().parent.parent / "specs"
CURRENT_LINK = SPECS_DIR / "current.yml"

# Regex to extract the spec YAML filename from the Redoc.init() call in the HTML.
SPEC_PATTERN = re.compile(r"cloud-provisioning-rest-api-[\d.]+\.ya?ml")


def fetch_spec_filename():
    """Scrape the documentation page to discover the current spec filename."""
    resp = requests.get(DOCS_URL, timeout=30)
    resp.raise_for_status()
    match = SPEC_PATTERN.search(resp.text)
    if not match:
        print("ERROR: Could not find spec filename in page HTML.", file=sys.stderr)
        print(f"Check {DOCS_URL} manually.", file=sys.stderr)
        sys.exit(1)
    return match.group(0)


def file_hash(path):
    """Return SHA-256 hex digest of a file, or None if the file does not exist."""
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    SPECS_DIR.mkdir(exist_ok=True)

    # 1. Discover the filename
    filename = fetch_spec_filename()
    spec_url = DOCS_URL + filename
    print(f"Found spec: {filename}")

    # 2. Download
    resp = requests.get(spec_url, timeout=60)
    resp.raise_for_status()
    content = resp.content

    # 3. Validate YAML
    try:
        spec = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        print(f"ERROR: Downloaded file is not valid YAML: {exc}", file=sys.stderr)
        sys.exit(1)

    version = spec.get("info", {}).get("version", "unknown")
    print(f"API version: {version}")

    # 4. Write to specs/
    target = SPECS_DIR / filename
    old_hash = file_hash(target)
    new_hash = hashlib.sha256(content).hexdigest()

    target.write_bytes(content)

    # 5. Update symlink
    if CURRENT_LINK.is_symlink() or CURRENT_LINK.exists():
        CURRENT_LINK.unlink()
    CURRENT_LINK.symlink_to(filename)

    if old_hash == new_hash:
        print(f"Spec unchanged ({len(content):,} bytes).")
    elif old_hash is None:
        print(f"New spec saved ({len(content):,} bytes).")
    else:
        print(f"Spec UPDATED ({len(content):,} bytes). Run 'make spec-diff' to see changes.")


if __name__ == "__main__":
    main()
