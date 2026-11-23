"""Schema validation of the requirements registry (D1 / CI gate a).

Validates ``docs/req/requirements.yaml`` against
``docs/req/req-schema.json`` (JSON Schema draft 2020-12). This is the same check
CI runs before the offline suite, so a malformed registry fails fast.

Uses PyYAML + jsonschema; both are installed by the CI gate job
(``pip install pyyaml jsonschema``) and are not part of the B-module runtime path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REQUIREMENTS_PATH = REPO_ROOT / "docs" / "req" / "requirements.yaml"
SCHEMA_PATH = REPO_ROOT / "docs" / "req" / "req-schema.json"

# Required so `jsonschema` and `yaml` imports are local to this test module and do
# not leak onto the stdlib-only runtime path of ``src/event_merge``.
yaml = pytest.importorskip("yaml")
jsonschema = pytest.importorskip("jsonschema")


def _load_registry() -> dict:
    data = yaml.safe_load(REQUIREMENTS_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "requirements.yaml must be a YAML mapping"
    return data


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.mark.offline
def test_requirements_yaml_conforms_to_schema():
    """CI gate (a): docs/req/requirements.yaml validates against req-schema.json."""
    schema = _load_schema()
    registry = _load_registry()

    validator_cls = jsonschema.validators.validator_for(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(registry), key=lambda e: list(e.path))

    assert not errors, (
        "requirements.yaml violates req-schema.json:\n"
        + "\n".join(
            f"  - {'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors
        )
    )


@pytest.mark.offline
def test_registry_has_all_required_ids():
    """D1: FR-B-1..7, NFR-B-1..3 and INV-B-1..5 are all registered."""
    registry = _load_registry()
    ids = {req["id"] for req in registry["requirements"]}
    expected = (
        {f"FR-B-{i}" for i in range(1, 8)}
        | {f"NFR-B-{i}" for i in range(1, 4)}
        | {f"INV-B-{i}" for i in range(1, 6)}
    )
    assert expected <= ids


@pytest.mark.offline
def test_registry_types_are_from_allowed_taxonomy():
    """D1: every requirement's type is one of the allowed taxonomy values."""
    registry = _load_registry()
    schema = _load_schema()
    allowed = set(schema["properties"]["requirements"]["items"]["properties"]["type"]["enum"])
    for req in registry["requirements"]:
        assert req["type"] in allowed, f"{req['id']} has unknown type {req['type']!r}"
