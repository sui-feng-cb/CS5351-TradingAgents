"""GOV-01/QUA-01: exercise local checks and the shared same-PR review gate."""

import os
import subprocess
from unittest.mock import patch

import pytest

from scripts import check_github_test_approvals as reviews_gate, check_governance

OFFLINE_TEST = "test/offline/test_feature.py"
TEST_FIXTURE = "test/fixtures/feature.txt"
NORMAL_SOURCE = "src/tradingagents/enhancements/comparison.py"
SAFETY_SOURCE = "src/tradingagents/enhancements/eligibility.py"
ADR = "docs/architecture/adr/002-eligibility.md"
AUTHOR = "feature-author"


def test_initialized_requirements_and_permissions_validate():
    check_governance.validate()


def test_test_change_without_ai_use_record_is_blocked():
    paths = b"test/offline/test_comparison.py\0"
    with patch.object(check_governance, "git", return_value=paths), patch.object(
        check_governance, "changed_code", return_value=[]
    ), pytest.raises(
        ValueError, match="AI-use log"
    ):
        check_governance.pr_gates("base-commit")


def test_event_semantic_gate_is_still_required():
    source = "src/tradingagents/enhancements/events.py"
    paths = ["docs/ai-use-log.yaml", source]
    with patch.object(check_governance, "changed_paths", return_value=paths), patch.object(
        check_governance, "changed_code", return_value=[source]
    ), pytest.raises(ValueError, match="Semantic changes are blocked"):
        check_governance.pr_gates("base-commit")


@pytest.fixture
def branch(tmp_path, monkeypatch):
    def git(*args, hour=9):
        timestamp = f"2026-11-22T{hour:02}:00:00Z"
        env = os.environ | {
            "GIT_AUTHOR_NAME": "Repository test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Repository test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
            "GIT_AUTHOR_DATE": timestamp,
            "GIT_COMMITTER_DATE": timestamp,
        }
        return subprocess.check_output(["git", *args], cwd=tmp_path, env=env)

    def commit(files, *, hour):
        for path, text in files.items():
            target = tmp_path / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        git("add", "--all")
        git("commit", "-qm", f"Change at {hour}", hour=hour)
        return git("rev-parse", "HEAD").decode().strip()

    git("init", "-q", "--initial-branch=main")
    base = commit({"README.md": "baseline"}, hour=9)
    git("switch", "-qc", "feature")
    monkeypatch.setattr(check_governance, "ROOT", tmp_path)
    return base, commit


def review_record(sha, *, login="peer", state="COMMENTED", user_type="User", association="MEMBER",
                  submitted_at="2026-11-22T11:00:00Z"):
    return {
        "user": {"login": login, "type": user_type},
        "author_association": association,
        "state": state,
        "commit_id": sha,
        "submitted_at": submitted_at,
        "body": f"Test-Plan-Approved: {sha}\n\nPositive and negative expectations reviewed.",
    }


def verify(monkeypatch, base, head, reviews):
    responses = {
        "pulls/42": {"head": {"sha": head}, "user": {"login": AUTHOR}},
        "pulls/42/reviews?per_page=100&page=1": reviews,
    }
    monkeypatch.setattr(reviews_gate, "api", responses.__getitem__)
    reviews_gate.verify_pr(base, head, 42)


def test_same_pr_accepts_independent_review_of_unchanged_tests(branch, monkeypatch):
    base, commit = branch
    tests = commit({OFFLINE_TEST: "def test_sample(): assert True\n", TEST_FIXTURE: "fixture"}, hour=10)
    head = commit({NORMAL_SOURCE: "feature = True\n"}, hour=12)
    verify(monkeypatch, base, head, [review_record(tests)])


def test_tests_only_draft_can_run_governance_without_prior_review(branch, monkeypatch):
    base, commit = branch
    tests = commit({OFFLINE_TEST: "def test_sample(): assert True\n"}, hour=10)
    monkeypatch.setattr(reviews_gate, "api", {}.__getitem__)
    reviews_gate.verify_pr(base, tests, 42)


@pytest.mark.parametrize("review_kwargs", [
    None, {"login": AUTHOR.upper()}, {"user_type": "Bot"}, {"association": "NONE"},
    {"submitted_at": "2026-11-22T13:00:00Z"},
])
def test_missing_self_bot_external_or_late_test_review_is_rejected(branch, monkeypatch, review_kwargs):
    base, commit = branch
    tests = commit({OFFLINE_TEST: "def test_sample(): assert True\n"}, hour=10)
    head = commit({NORMAL_SOURCE: "feature = True\n"}, hour=12)
    reviews = [review_record(tests, **review_kwargs)] if review_kwargs is not None else []
    with pytest.raises(ValueError, match="No independent, pre-implementation test review"):
        verify(monkeypatch, base, head, reviews)


def test_review_of_commit_already_containing_application_code_is_rejected(branch, monkeypatch):
    base, commit = branch
    combined = commit({OFFLINE_TEST: "def test_sample(): assert True\n", NORMAL_SOURCE: "feature = True\n"}, hour=10)
    head = commit({"Report.md": "Verification summary"}, hour=12)
    with pytest.raises(ValueError, match="No independent, pre-implementation test review"):
        verify(monkeypatch, base, head, [review_record(combined, submitted_at="2026-11-22T10:00:00Z")])


@pytest.mark.parametrize("path", [OFFLINE_TEST, TEST_FIXTURE, "test/offline/test_added.py"])
def test_approval_does_not_cover_modified_or_added_test_inputs(branch, monkeypatch, path):
    base, commit = branch
    tests = commit({OFFLINE_TEST: "def test_sample(): assert True\n", TEST_FIXTURE: "fixture"}, hour=10)
    head = commit({NORMAL_SOURCE: "feature = True\n", path: "unreviewed change\n"}, hour=12)
    with pytest.raises(ValueError, match="No independent, pre-implementation test review"):
        verify(monkeypatch, base, head, [review_record(tests)])


def test_safety_gate_requires_adr_and_current_independent_approval(branch, monkeypatch):
    base, commit = branch
    tests = commit({OFFLINE_TEST: "def test_sample(): assert True\n"}, hour=10)
    early = review_record(tests)
    head = commit({SAFETY_SOURCE: "gate = True\n"}, hour=12)
    with pytest.raises(ValueError, match="corresponding ADR"):
        verify(monkeypatch, base, head, [early])
    final = commit({ADR: "# Decision"}, hour=13)
    stale = review_record(head, state="APPROVED")
    with pytest.raises(ValueError, match="approval of its current head"):
        verify(monkeypatch, base, final, [early, stale])
    approved = review_record(final, state="APPROVED")
    verify(monkeypatch, base, final, [early, stale, approved])
    dismissed = review_record(final, state="DISMISSED")
    with pytest.raises(ValueError, match="approval of its current head"):
        verify(monkeypatch, base, final, [early, approved, dismissed])
