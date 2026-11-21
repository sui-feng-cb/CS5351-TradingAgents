"""GOV-01: verify same-PR test reviews and independent safety review (INV-D)."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any

from scripts.check_governance import (
    changed_code,
    changed_paths,
    git,
    is_application_path,
    merge_base,
)

TEAM_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}
REVIEW_MARKER = "Test-Plan-Approved: "


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
        raise RuntimeError(f"Unable to verify GitHub review evidence for {path}") from exc


def pr_reviews(number: int) -> list[dict[str, Any]]:
    """Read the complete GitHub review history, including an early test review."""
    reviews: list[dict[str, Any]] = []
    page = 1
    while True:
        result = api(f"pulls/{number}/reviews?per_page=100&page={page}")
        if not isinstance(result, list) or not all(isinstance(review, dict) for review in result):
            raise ValueError("Cannot read GitHub PR reviews")
        reviews.extend(result)
        if len(result) < 100:
            return reviews
        page += 1


def reviewer_login(review: dict[str, Any], author: str) -> str | None:
    """Accept a human team member or collaborator other than the PR author."""
    user = review.get("user") or {}
    login = user.get("login")
    if (isinstance(login, str) and login and login.lower() != author.lower()
            and user.get("type") == "User" and review.get("author_association") in TEAM_ASSOCIATIONS):
        return login.lower()
    return None


def tests_only_commits(base: str, head: str) -> tuple[dict[str, set[str]], int]:
    """Find reviewable commits before application paths first changed on the branch."""
    candidates: dict[str, set[str]] = {}
    commits = git("rev-list", "--first-parent", "--reverse", f"{base}..{head}").decode().splitlines()
    for commit in commits:
        # An ordinary merge from current main should not look like new feature code.
        paths = changed_paths(merge_base(base, commit), commit)
        if any(is_application_path(path) for path in paths):
            return candidates, int(git("show", "-s", "--format=%ct", commit))
        if all(path.startswith(("test/", "docs/")) or path in {"README.md", "Report.md"} for path in paths):
            candidates[commit] = {path for path in paths if path.startswith("test/")}
    raise ValueError("Cannot establish the first application change in PR history")


def verify_test_review(base: str, head: str, paths: list[str], author: str, reviews: list[dict[str, Any]]) -> None:
    """GOV-01: require an independent, earlier review of the unchanged offline tests."""
    candidates, implementation_time = tests_only_commits(base, head)
    final_tests = {path for path in paths if path.startswith("test/")}
    if not any(path.startswith("test/offline/") and PurePosixPath(path).match("test_*.py")
               and git("ls-tree", head, "--", path) for path in final_tests):
        raise ValueError("Application PR must include an added or updated offline test")
    for review in reversed(reviews):
        login = reviewer_login(review, author)
        commit = review.get("commit_id")
        if not login or review.get("state") != "COMMENTED" or commit not in candidates:
            continue
        marker, _, rationale = (review.get("body") or "").strip().partition("\n")
        if marker.strip() != f"{REVIEW_MARKER}{commit}" or not rationale.strip():
            continue
        submitted_at = review.get("submitted_at")
        if not submitted_at:
            continue
        submitted = datetime.fromisoformat(submitted_at)
        if submitted.tzinfo is None or submitted.timestamp() > implementation_time:
            continue
        if candidates[commit] != final_tests or final_tests.intersection(changed_paths(commit, head)):
            continue
        print(f"Reviewed pre-implementation tests at {commit} by {login}")
        return
    raise ValueError("No independent, pre-implementation test review for the final test files. "
                     f"Request a GitHub Comment review starting with '{REVIEW_MARKER}<full SHA>'.")


def verify_safety_review(paths: list[str], head: str, author: str, reviews: list[dict[str, Any]]) -> None:
    """INV-D: retain the ADR and independent approval of the current safety change."""
    if not any(path.startswith(("src/tradingagents/graph/", "src/tradingagents/agents/"))
               or path.endswith("/eligibility.py") for path in paths):
        return
    if not any(path.startswith("docs/architecture/adr/") and git("ls-tree", head, "--", path) for path in paths):
        raise ValueError("Safety-critical PR must include a corresponding ADR")
    latest: dict[str, dict[str, Any]] = {}
    for review in reviews:
        login = reviewer_login(review, author)
        if login and review.get("state") in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}:
            latest[login] = review
    if not any(review["state"] == "APPROVED" and review.get("commit_id") == head
               for review in latest.values()):
        raise ValueError("Safety-critical PR requires independent approval of its current head")


def verify_pr(base: str, head: str, number: int) -> None:
    common = merge_base(base, head)
    if not changed_code(common, head):
        print("No application source changes; PR test review verification not required")
        return
    pr = api(f"pulls/{number}")
    if not isinstance(pr, dict) or pr.get("head", {}).get("sha") != head or not pr.get("user", {}).get("login"):
        raise ValueError("Cannot verify reviews for this PR head; run checks on the latest commit")
    paths = changed_paths(common, head)
    author = pr["user"]["login"]
    reviews = pr_reviews(number)
    verify_test_review(base, head, paths, author, reviews)
    verify_safety_review(paths, head, author, reviews)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    verify_pr(args.base, args.head, int(os.environ["PR_NUMBER"]))


if __name__ == "__main__":
    main()
