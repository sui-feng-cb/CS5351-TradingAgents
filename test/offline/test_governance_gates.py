"""Tests for repository governance bootstrap and fail-closed PR checks."""

from unittest.mock import patch

import pytest

from scripts import check_governance


def test_initialized_requirements_and_permissions_validate():
    check_governance.validate()


def test_feature_code_cannot_self_approve_test_and_implementation_in_one_pr():
    paths = b"docs/ai-use-log.yaml\0src/tradingagents/enhancements/comparison.py\0"
    def git_result(*args):
        return b'{"approvals": []}' if args[0] == "show" else paths

    with patch.object(check_governance, "git", side_effect=git_result), patch.object(
        check_governance, "changed_code",
        return_value=["src/tradingagents/enhancements/comparison.py"],
    ), pytest.raises(ValueError, match="test-only PR"):
        check_governance.pr_gates("base-commit")


def test_test_change_without_ai_use_record_is_blocked():
    paths = b"test/offline/test_comparison.py\0"
    with patch.object(check_governance, "git", return_value=paths), patch.object(
        check_governance, "changed_code", return_value=[]
    ), patch.object(check_governance, "_blob_at", side_effect=[None, "new-test-blob"]), pytest.raises(
        ValueError, match="AI-use log"
    ):
        check_governance.pr_gates("base-commit")
