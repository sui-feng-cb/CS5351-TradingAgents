"""Verify that feature-test and approval-registry PRs predate implementation."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from check_governance import changed_code

ROOT = Path(__file__).resolve().parents[1]


def api(path: str) -> Any:
    repository = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GITHUB_TOKEN"]
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/{path}",
        headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
                 "X-GitHub-Api-Version": "2022-11-28"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to verify GitHub approval evidence for {path}") from exc


def approved_merged_pr(number: int, base_ref: str) -> dict[str, Any]:
    pr = api(f"pulls/{number}")
    if not isinstance(pr, dict) or not pr.get("merged_at") or pr["base"]["ref"] != base_ref:
        raise ValueError(f"PR #{number} is not merged into the implementation target branch")
    reviews = api(f"pulls/{number}/reviews")
    if not isinstance(reviews, list):
        raise ValueError(f"Cannot read reviews for PR #{number}")
    eligible = [
        review for review in reviews
        if review.get("state") == "APPROVED"
        and review.get("user", {}).get("login") != pr["user"]["login"]
        and review.get("commit_id") == pr["head"]["sha"]
        and review.get("submitted_at")
        and review["submitted_at"] <= pr["merged_at"]
    ]
    if not eligible:
        raise ValueError(f"PR #{number} lacks a human approval of its merged head commit")
    return pr


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    application = changed_code(args.base)
    if not application:
        print("No application source changes; prior test PR verification not required")
        return

    current_pr_number = int(os.environ["PR_NUMBER"])
    current_pr = api(f"pulls/{current_pr_number}")
    base_ref = current_pr["base"]["ref"]
    base_sha = args.base
    current_files = api(f"pulls/{current_pr_number}/files?per_page=100")
    if not isinstance(current_files, list):
        raise ValueError("Cannot read current PR file list")
    current_names = {item["filename"] for item in current_files}
    safety_paths = [
        path for path in current_names
        if path.startswith(("src/tradingagents/graph/", "src/tradingagents/agents/"))
        or path.endswith("/eligibility.py")
    ]
    if safety_paths:
        if not any(path.startswith("docs/architecture/adr/") for path in current_names):
            raise ValueError("Safety-critical PR must include a corresponding ADR")
        reviews = api(f"pulls/{current_pr_number}/reviews?per_page=100")
        head_sha = current_pr["head"]["sha"]
        author = current_pr["user"]["login"]
        if not isinstance(reviews, list) or not any(
            review.get("state") == "APPROVED"
            and review.get("user", {}).get("login") != author
            and review.get("commit_id") == head_sha
            for review in reviews
        ):
            raise ValueError("Safety-critical PR requires human approval of its current head")
    approvals = json.loads(subprocess.check_output(
        ["git", "show", f"{base_sha}:docs/test-approvals.json"], cwd=ROOT
    ))["approvals"]

    covered: set[str] = set()
    verified: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for record in approvals:
        test_paths = set(record.get("test_blobs", {}))
        code_patterns = record.get("implementation_paths", [])
        if (not test_paths or not code_patterns or not record.get("requirement_ids")
                or not all(path.startswith(("test/offline/", "test/live/")) for path in test_paths)):
            continue
        test_pr_number = int(record["test_pr_number"])
        registry_pr_number = int(record["registry_pr_number"])
        test_pr = approved_merged_pr(test_pr_number, base_ref)
        registry_pr = approved_merged_pr(registry_pr_number, base_ref)
        if test_pr["merged_at"] > registry_pr["merged_at"]:
            raise ValueError("Test PR must be merged before the approval-registry PR")
        if not _ancestor(test_pr["merge_commit_sha"], base_sha):
            raise ValueError("Approved test PR is not contained in the feature PR base")
        if not _ancestor(registry_pr["merge_commit_sha"], base_sha):
            raise ValueError("Approval-registry PR is not contained in the feature PR base")
        registry_files = api(f"pulls/{registry_pr_number}/files?per_page=100")
        if not isinstance(registry_files, list) or not any(
            item["filename"] == "docs/test-approvals.json" for item in registry_files
        ) or any(
            item["filename"] not in {"docs/test-approvals.json", "docs/ai-use-log.yaml"}
            for item in registry_files
        ):
            raise ValueError("Approval-registry PR may only update the approval registry and AI-use log")
        test_reviews = api(f"pulls/{test_pr_number}/reviews?per_page=100")
        if not isinstance(test_reviews, list) or not any(
            review.get("state") == "APPROVED"
            and review.get("user", {}).get("login") == record.get("approved_by")
            and review.get("user", {}).get("login") != test_pr["user"]["login"]
            and review.get("commit_id") == test_pr["head"]["sha"]
            and review.get("submitted_at") == record.get("approved_at")
            for review in test_reviews
        ):
            raise ValueError("Approval reviewer/time must match the earlier independent test PR review")
        if record.get("approval_commit") != test_pr.get("merge_commit_sha"):
            raise ValueError("Approval commit must identify the previously merged test PR")
        test_files = api(f"pulls/{test_pr_number}/files?per_page=100")
        if not isinstance(test_files, list):
            raise ValueError("Cannot read approved test PR file list")
        changed = {item["filename"] for item in test_files}
        if not test_paths.issubset(changed):
            raise ValueError("Approved test PR did not introduce every frozen test path")
        if any(not path.startswith(("test/offline/", "test/live/", "docs/ai-use-log.yaml")) for path in changed):
            raise ValueError("Prior test-approval PR may contain only tests and its AI-use log entry")
        actual = {
            path: subprocess.check_output(["git", "rev-parse", f"{base_sha}:{path}"], cwd=ROOT).decode().strip()
            for path in test_paths
        }
        if actual != record["test_blobs"]:
            raise ValueError("Approved tests changed after their approval")
        covered.update(path for path in application
                       if any(fnmatch.fnmatchcase(path, pattern) for pattern in code_patterns))
        verified.append((record, test_pr))
    if set(application) - covered:
        raise ValueError(f"No prior human-approved frozen tests cover: {sorted(set(application) - covered)}")
    for record, _test_pr in verified:
        print(f"Prior human-approved test PR #{record['test_pr_number']} verified for {record['requirement_ids']}")


def _ancestor(commit: str, base: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", commit, base], cwd=ROOT,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          check=False).returncode == 0


if __name__ == "__main__":
    main()
