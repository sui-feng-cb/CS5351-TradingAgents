"""QUA-01/GOV-01 repository validation and local PR change checks."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "9fa1196fffbcfd9de5146d2dd2869df84ab99838"
REQUIRED = [
    "AGENTS.md", "Prompt.md", "Report.md", "architecture-blueprint.md",
    "docs/architecture/architecture-blueprint.md", "docs/architecture/invariants.md",
    "docs/architecture/trace-matrix.md", "docs/architecture/memory-design.md",
    "docs/architecture/permission-model.md", "docs/architecture/evaluation-table.md",
    "docs/architecture/runtime-policy-catalog.md", "docs/architecture/adr/001-layout-and-extension-boundaries.md",
    "docs/architecture/interface-contracts.md",
    "docs/code-governance/structural-constraints.md",
    "docs/code-governance/verification-constraints.md",
    "docs/code-governance/mcp-tool-manifest.md", "docs/ai-use-log.yaml",
    "docs/review-memo.md", "docs/debt-register.md", "docs/bug-diary.md",
    "docs/testing/test-approval-process.md",
    ".opencode/permissions.jsonc", ".opencode/rules.md", ".agent/rules.md",
    ".github/workflows/ci.yml", "transcripts/README.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".opencode/skills/session-artifacts/SKILL.md",
    ".opencode/skills/repository-initialization/SKILL.md",
    "docs/reference/project-requirements.md", "docs/reference/module-acceptance.md",
    "docs/verification/initialization.md",
]


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def validate() -> None:
    """QUA-01: verify registry, reference files and effective permission source."""
    registry = yaml.safe_load((ROOT / "docs/req/requirements.yaml").read_text())
    schema = yaml.safe_load((ROOT / "docs/req/req-schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(registry)
    ids = [entry["id"] for entry in registry["requirements"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate requirement IDs")
    for owner in "ABCD":
        for prefix in ("FR", "NFR"):
            entries = [r for r in registry["requirements"] if r["id"] == f"{prefix}-{owner}"]
            if len(entries) != 1 or entries[0]["owner"] != owner:
                raise ValueError(f"Missing/wrong owner for {prefix}-{owner}")
    for filename in [*REQUIRED, *registry["source_documents"]]:
        if not (ROOT / filename).is_file():
            raise ValueError(f"Missing required file: {filename}")
    config = json.loads((ROOT / ".opencode/opencode.json").read_text())
    artifact = json.loads((ROOT / ".opencode/permissions.jsonc").read_text())
    if config["permission"] != artifact["permission"]:
        raise ValueError("Course permission artifact differs from loaded OpenCode config")
    if config["permission"].get("*") != "deny":
        raise ValueError("Default permission must deny")
    for package in ("tradingagents", "cli"):
        if not (ROOT / "src" / package / "__init__.py").is_file():
            raise ValueError(f"Missing src package: {package}")
    print("Registry/schema, course layout and permission synchronization passed")


def is_application_path(path: str) -> bool:
    return path.startswith(("src/", "cli/", "tradingagents/")) or path == "main.py"


def changed_code(base: str, head: str = "HEAD") -> list[str]:
    """Ignore exact relocations of baseline code; detect substantive app changes."""
    names = changed_paths(base, head)
    changed = []
    for name in names:
        if not is_application_path(name):
            continue
        if name.startswith(("cli/", "tradingagents/")) and _blob_at(head, name) is None:
            old_blob = _blob_at(base, name)
            if old_blob and old_blob == _blob_at(head, f"src/{name}"):
                continue
        if name.startswith("src/") and _blob_at(base, name) is None:
            moved_blob = _blob_at(base, name.removeprefix("src/"))
            if moved_blob and moved_blob == _blob_at(head, name):
                continue
        if _blob_at(base, name) == _blob_at(head, name):
            continue
        changed.append(name)
    return changed


def changed_paths(base: str, head: str = "HEAD") -> list[str]:
    return list(filter(None, git("diff", "--no-renames", "--name-only", "-z", base, head).decode().split("\0")))


def merge_base(base: str, head: str) -> str:
    return git("merge-base", base, head).decode().strip()


def _blob_at(revision: str, filename: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", f"{revision}:{filename}"], cwd=ROOT,
        capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def pr_gates(base: str) -> None:
    """GOV-01: check local PR changes; safety reviews run separately in GitHub CI."""
    names = changed_paths(base)
    application = changed_code(base)
    test_changes = any(name.startswith("test/") for name in names)
    prompt_change = any(n.startswith("prompts/") and n != "prompts/README.md" for n in names)
    if (application or test_changes or prompt_change) and "docs/ai-use-log.yaml" not in names:
        raise ValueError("Code, test or prompt changes require an AI-use log update")
    if any(path.endswith("events.py") for path in application) or prompt_change:
        raise ValueError("Semantic changes are blocked until the approved evaluation is wired into CI")
    print("Local PR governance checks passed")


def scan() -> None:
    """SEC-01: basic credential-pattern scan; human artifact review still required."""
    # Scan tracked AND untracked nonignored text, including initial scaffolding.
    paths = git("ls-files", "--cached", "--others", "--exclude-standard", "-z").decode().split("\0")
    pattern = re.compile(r"(?:gh[pousr]_)[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{32,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----")
    for filename in filter(None, paths):
        path = ROOT / filename
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            continue
        if pattern.search(text):
            raise ValueError(f"Possible credential detected in {filename}; inspect locally")
    print("Basic credential-pattern scan passed (not a complete secret detector)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    args = parser.parse_args()
    validate()
    scan()
    if args.base:
        pr_gates(merge_base(args.base, "HEAD"))


if __name__ == "__main__":
    main()
