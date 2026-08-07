"""
Unit tests for the LangGraph nodes with mocked GitHub and Groq dependencies.

Run with:  pytest tests/test_langgraph_nodes.py -v
"""

import sys
import os
import json
from unittest.mock import MagicMock, patch, PropertyMock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.langgraph_agent import (
    AgentState,
    fetch_codebase,
    score_risk,
    identify_gaps,
    generate_tests,
    detect_defects,
    explain_and_score,
    generate_fixes,
    apply_and_verify_fixes,
    dispatch_results,
    _post_autofix_audit,
    _extract_features,
    _consistency_score,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------
def _make_state(**overrides) -> AgentState:
    base: AgentState = {
        "run_id": "unit-test-run-001",
        "project_id": 42,
        "repo_url": "https://github.com/testorg/myrepo",
        "github_token": "ghp_fake_token",
        "commit_sha": "deadbeef1234",
        "file_list": [],
        "risk_scores": [],
        "coverage_gaps": [],
        "generated_tests": [],
        "defects": [],
        "explained_defects": [],
        "generated_fixes": [],
        "pr_results": [],
        "dispatch_results": {},
        "error": "",
        "status": "QUEUED",
    }
    base.update(overrides)
    return base


def _make_groq_response(text: str) -> MagicMock:
    """Build a mock that looks like a Groq ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = text
    response = MagicMock()
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# Node 1 — fetch_codebase
# ---------------------------------------------------------------------------
class TestFetchCodebase:
    def _mock_github_commit(self, files_data: list[dict]):
        """
        files_data: [{"filename": str, "patch": str, "additions": int,
                       "deletions": int, "status": str, "content": bytes}]
        """
        mock_files = []
        for fd in files_data:
            mf = MagicMock()
            mf.filename = fd["filename"]
            mf.patch = fd.get("patch", "@@ -1 +1 @@ changed")
            mf.additions = fd.get("additions", 5)
            mf.deletions = fd.get("deletions", 2)
            mf.status = fd.get("status", "modified")
            mock_files.append(mf)

        parent = MagicMock()
        parent.sha = "parentsha"

        commit = MagicMock()
        commit.files = mock_files
        commit.parents = [parent]

        # Repo content mock
        def get_contents_side_effect(path, ref=None):
            for fd in files_data:
                if fd["filename"] == path:
                    content_obj = MagicMock()
                    content_obj.decoded_content = fd.get("content", b"file content")
                    return content_obj
            raise Exception(f"File not found: {path}")

        repo = MagicMock()
        repo.get_commit.return_value = commit
        repo.get_contents.side_effect = get_contents_side_effect

        gh = MagicMock()
        gh.get_repo.return_value = repo

        return gh

    @patch("agents.langgraph_agent.Github")
    def test_fetch_populates_file_list(self, mock_gh_class):
        files_data = [
            {
                "filename": "src/auth.py",
                "patch": "@@ -0,0 +1,10 @@ ...",
                "additions": 10,
                "deletions": 0,
                "status": "added",
                "content": b"def login(): pass",
            },
            {
                "filename": "src/utils.py",
                "patch": "@@ -5,3 +5,5 @@ ...",
                "additions": 2,
                "deletions": 0,
                "status": "modified",
                "content": b"def helper(): pass",
            },
        ]
        mock_gh_class.return_value = self._mock_github_commit(files_data)

        state = _make_state()
        result = fetch_codebase(state)

        assert result["error"] == "", f"Unexpected error: {result['error']}"
        assert len(result["file_list"]) == 2
        paths = [f["path"] for f in result["file_list"]]
        assert "src/auth.py" in paths
        assert "src/utils.py" in paths

    @patch("agents.langgraph_agent.Github")
    def test_fetch_sets_status_fetching(self, mock_gh_class):
        mock_gh_class.return_value = self._mock_github_commit([])
        state = _make_state()
        result = fetch_codebase(state)
        # Status should remain FETCHING_CODE (not FAILED) for successful fetch
        assert result["status"] in ("FETCHING_CODE",)

    @patch("agents.langgraph_agent.Github")
    def test_fetch_file_content_decoded(self, mock_gh_class):
        files_data = [
            {
                "filename": "app/models.py",
                "status": "modified",
                "additions": 3,
                "deletions": 1,
                "content": b"class User:\n    pass",
            }
        ]
        mock_gh_class.return_value = self._mock_github_commit(files_data)
        state = _make_state()
        result = fetch_codebase(state)

        assert result["file_list"][0]["content"] == "class User:\n    pass"

    @patch("agents.langgraph_agent.Github")
    def test_fetch_lines_changed_calculated(self, mock_gh_class):
        files_data = [
            {
                "filename": "src/main.py",
                "additions": 15,
                "deletions": 7,
                "status": "modified",
                "content": b"x=1",
            }
        ]
        mock_gh_class.return_value = self._mock_github_commit(files_data)
        state = _make_state()
        result = fetch_codebase(state)
        assert result["file_list"][0]["lines_changed"] == 22  # 15+7

    @patch("agents.langgraph_agent.Github")
    def test_fetch_github_error_sets_failed(self, mock_gh_class):
        mock_gh_class.side_effect = Exception("GitHub API unavailable")
        state = _make_state()
        result = fetch_codebase(state)
        assert result["status"] == "FAILED"
        assert "fetch_codebase" in result["error"]

    @patch("agents.langgraph_agent.Github")
    def test_fetch_skips_deleted_file_content(self, mock_gh_class):
        files_data = [
            {
                "filename": "old_module.py",
                "status": "removed",
                "additions": 0,
                "deletions": 50,
                "content": b"",
            }
        ]
        mock_gh = self._mock_github_commit(files_data)
        mock_gh_class.return_value = mock_gh

        state = _make_state()
        result = fetch_codebase(state)

        assert result["file_list"][0]["content"] == ""


# ---------------------------------------------------------------------------
# Node 2 — score_risk
# ---------------------------------------------------------------------------
class TestScoreRisk:
    def _file_list_with_mix(self) -> list[dict]:
        simple = [
            {"path": f"src/util_{i}.py", "content": "def f(): pass\n", "diff": "", "lines_changed": 3}
            for i in range(7)
        ]
        complex_auth = {
            "path": "src/auth_service.py",
            "content": (
                "import jwt\nimport requests\n"
                "def authenticate(token, password, login):\n    pass\n" * 20
                + "SELECT * FROM users\n"
            ),
            "diff": "",
            "lines_changed": 300,
        }
        return simple + [complex_auth]

    def test_score_risk_returns_scores_for_all_files(self):
        file_list = self._file_list_with_mix()
        state = _make_state(file_list=file_list)
        result = score_risk(state)

        assert len(result["risk_scores"]) == len(file_list)

    def test_score_risk_values_in_range(self):
        state = _make_state(file_list=self._file_list_with_mix())
        result = score_risk(state)
        for rs in result["risk_scores"]:
            assert 0.0 <= rs["score"] <= 1.0

    def test_score_risk_sorted_descending(self):
        state = _make_state(file_list=self._file_list_with_mix())
        result = score_risk(state)
        scores = [r["score"] for r in result["risk_scores"]]
        assert scores == sorted(scores, reverse=True)

    def test_score_risk_empty_file_list(self):
        state = _make_state(file_list=[])
        result = score_risk(state)
        assert result["risk_scores"] == []
        assert result["error"] == ""

    def test_score_risk_anomaly_flag_is_bool(self):
        state = _make_state(file_list=self._file_list_with_mix())
        result = score_risk(state)
        for rs in result["risk_scores"]:
            assert isinstance(rs["anomaly_flag"], bool)


# ---------------------------------------------------------------------------
# Node 3 — identify_gaps
# ---------------------------------------------------------------------------
class TestIdentifyGaps:
    def _risk_scores_for(self, paths: list[str], score: float = 0.8) -> list[dict]:
        return [{"file_path": p, "score": score, "anomaly_flag": True} for p in paths]

    def test_identifies_untested_files(self):
        file_list = [
            {"path": "src/payment.py", "content": "def pay(): pass", "diff": "", "lines_changed": 20},
            {"path": "src/utils.py", "content": "def util(): pass", "diff": "", "lines_changed": 5},
        ]
        risk_scores = self._risk_scores_for(["src/payment.py", "src/utils.py"])
        state = _make_state(file_list=file_list, risk_scores=risk_scores)
        result = identify_gaps(state)

        gap_paths = [g["file_path"] for g in result["coverage_gaps"]]
        assert "src/payment.py" in gap_paths

    def test_skips_files_with_test_counterpart(self):
        file_list = [
            {"path": "src/auth.py", "content": "def login(): pass", "diff": "", "lines_changed": 20},
            {"path": "tests/test_auth.py", "content": "def test_login(): pass", "diff": "", "lines_changed": 15},
        ]
        risk_scores = self._risk_scores_for(["src/auth.py"])
        state = _make_state(file_list=file_list, risk_scores=risk_scores)
        result = identify_gaps(state)

        gap_paths = [g["file_path"] for g in result["coverage_gaps"]]
        assert "src/auth.py" not in gap_paths, "auth.py has test_auth.py so should not be in gaps"

    def test_skips_low_risk_files(self):
        file_list = [
            {"path": "src/config.py", "content": "DEBUG = True", "diff": "", "lines_changed": 1},
        ]
        risk_scores = [{"file_path": "src/config.py", "score": 0.1, "anomaly_flag": False}]
        state = _make_state(file_list=file_list, risk_scores=risk_scores)
        result = identify_gaps(state)

        # risk_score <= 0.3 should be excluded
        assert result["coverage_gaps"] == []

    def test_max_10_gaps_returned(self):
        file_list = [
            {"path": f"src/module_{i}.py", "content": "def f(): pass", "diff": "", "lines_changed": 30}
            for i in range(20)
        ]
        risk_scores = self._risk_scores_for([f"src/module_{i}.py" for i in range(20)], score=0.9)
        state = _make_state(file_list=file_list, risk_scores=risk_scores)
        result = identify_gaps(state)

        assert len(result["coverage_gaps"]) <= 10

    def test_gaps_sorted_by_priority_descending(self):
        file_list = [
            {"path": "src/a.py", "content": "def a(): pass", "diff": "", "lines_changed": 5},
            {"path": "src/b.py", "content": "def b(): pass", "diff": "", "lines_changed": 5},
        ]
        risk_scores = [
            {"file_path": "src/a.py", "score": 0.5, "anomaly_flag": False},
            {"file_path": "src/b.py", "score": 0.9, "anomaly_flag": True},
        ]
        state = _make_state(file_list=file_list, risk_scores=risk_scores)
        result = identify_gaps(state)

        if len(result["coverage_gaps"]) == 2:
            assert result["coverage_gaps"][0]["file_path"] == "src/b.py"

    def test_spec_file_recognised_as_test(self):
        file_list = [
            {"path": "src/auth.service.ts", "content": "export class AuthService {}", "diff": "", "lines_changed": 30},
            {"path": "src/auth.service.spec.ts", "content": "describe('AuthService', () => {})", "diff": "", "lines_changed": 20},
        ]
        risk_scores = self._risk_scores_for(["src/auth.service.ts"])
        state = _make_state(file_list=file_list, risk_scores=risk_scores)
        result = identify_gaps(state)

        gap_paths = [g["file_path"] for g in result["coverage_gaps"]]
        assert "src/auth.service.ts" not in gap_paths

    def test_test_file_itself_not_added_to_gaps(self):
        file_list = [
            {"path": "tests/test_auth.py", "content": "def test_login(): pass", "diff": "", "lines_changed": 20},
        ]
        risk_scores = self._risk_scores_for(["tests/test_auth.py"])
        state = _make_state(file_list=file_list, risk_scores=risk_scores)
        result = identify_gaps(state)
        assert result["coverage_gaps"] == []


# ---------------------------------------------------------------------------
# Node 4 — generate_tests
# ---------------------------------------------------------------------------
class TestGenerateTests:
    def _coverage_gap(self, path: str, priority: float = 0.8) -> dict:
        return {"file_path": path, "has_test": False, "priority": priority, "risk_score": priority}

    def _file_info(self, path: str, content: str = "def foo(): pass") -> dict:
        return {"path": path, "content": content, "diff": "", "lines_changed": 10}

    @patch("agents.langgraph_agent.Groq")
    def test_generate_tests_calls_groq(self, mock_groq_class):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_groq_response(
            "import { test, expect } from '@playwright/test';\ntest('should work', async ({page}) => {});"
        )
        mock_groq_class.return_value = mock_client

        gaps = [self._coverage_gap("src/payment.py")]
        file_list = [self._file_info("src/payment.py")]
        state = _make_state(coverage_gaps=gaps, file_list=file_list)
        result = generate_tests(state)

        mock_client.chat.completions.create.assert_called_once()
        assert len(result["generated_tests"]) == 1

    @patch("agents.langgraph_agent.Groq")
    def test_generate_tests_uses_correct_model(self, mock_groq_class):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_groq_response("test code")
        mock_groq_class.return_value = mock_client

        gaps = [self._coverage_gap("src/auth.py")]
        file_list = [self._file_info("src/auth.py", "import jwt\ndef verify(t): pass")]
        state = _make_state(coverage_gaps=gaps, file_list=file_list)
        generate_tests(state)

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "llama-3.3-70b-versatile"

    @patch("agents.langgraph_agent.Groq")
    def test_generate_tests_includes_file_path_in_prompt(self, mock_groq_class):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_groq_response("// test")
        mock_groq_class.return_value = mock_client

        gaps = [self._coverage_gap("src/orders/checkout.ts")]
        file_list = [self._file_info("src/orders/checkout.ts", "export function checkout() {}")]
        state = _make_state(coverage_gaps=gaps, file_list=file_list)
        generate_tests(state)

        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        user_msg = next(m["content"] for m in messages if m["role"] == "user")
        assert "src/orders/checkout.ts" in user_msg

    @patch("agents.langgraph_agent.Groq")
    def test_generate_tests_respects_top_5_limit(self, mock_groq_class):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_groq_response("// test")
        mock_groq_class.return_value = mock_client

        gaps = [self._coverage_gap(f"src/module_{i}.py") for i in range(10)]
        file_list = [self._file_info(f"src/module_{i}.py") for i in range(10)]
        state = _make_state(coverage_gaps=gaps, file_list=file_list)
        result = generate_tests(state)

        assert mock_client.chat.completions.create.call_count == 5
        assert len(result["generated_tests"]) == 5

    @patch("agents.langgraph_agent.Groq")
    def test_generate_tests_handles_llm_failure_gracefully(self, mock_groq_class):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        mock_groq_class.return_value = mock_client

        gaps = [self._coverage_gap("src/service.py")]
        file_list = [self._file_info("src/service.py")]
        state = _make_state(coverage_gaps=gaps, file_list=file_list)
        result = generate_tests(state)

        # Should not crash; should still have 1 entry with an error comment
        assert len(result["generated_tests"]) == 1
        assert "LLM generation failed" in result["generated_tests"][0]["test_code"]
        assert result["error"] == ""

    @patch("agents.langgraph_agent.Groq")
    def test_generate_tests_output_language_is_typescript(self, mock_groq_class):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_groq_response("test('x', async () => {})")
        mock_groq_class.return_value = mock_client

        gaps = [self._coverage_gap("src/api.ts")]
        file_list = [self._file_info("src/api.ts")]
        state = _make_state(coverage_gaps=gaps, file_list=file_list)
        result = generate_tests(state)

        assert result["generated_tests"][0]["language"] == "typescript"

    @patch("agents.langgraph_agent.Groq")
    def test_generate_tests_no_gaps_returns_empty(self, mock_groq_class):
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        state = _make_state(coverage_gaps=[], file_list=[])
        result = generate_tests(state)

        mock_client.chat.completions.create.assert_not_called()
        assert result["generated_tests"] == []

    @patch("agents.langgraph_agent.Groq")
    def test_generate_tests_truncates_content_to_3000(self, mock_groq_class):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_groq_response("// test")
        mock_groq_class.return_value = mock_client

        long_content = "x = 1\n" * 1000  # well over 3000 chars
        gaps = [self._coverage_gap("src/big.py")]
        file_list = [self._file_info("src/big.py", long_content)]
        state = _make_state(coverage_gaps=gaps, file_list=file_list)
        generate_tests(state)

        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        user_msg = next(m["content"] for m in messages if m["role"] == "user")
        # The prompt uses content[:3000] so should not contain more than ~3000 content chars
        assert len(user_msg) < len(long_content) + 200  # padding for the template text


# ---------------------------------------------------------------------------
# Node 5 — detect_defects (spot checks)
# ---------------------------------------------------------------------------
class TestDetectDefects:
    def _risk_scores(self, path: str, score: float = 0.8, has_auth: bool = False, has_db: bool = False) -> list[dict]:
        return [
            {
                "file_path": path,
                "score": score,
                "anomaly_flag": True,
                "features": {
                    "lines_changed": 100,
                    "file_size_kb": 5.0,
                    "import_count": 5,
                    "function_count": 10,
                    "has_auth_code": has_auth,
                    "has_db_code": has_db,
                },
            }
        ]

    def test_detects_sql_injection(self):
        content = 'result = db.execute(f"SELECT * FROM users WHERE name = {user_input}")'
        file_list = [{"path": "src/user.py", "content": content, "diff": "", "lines_changed": 5}]
        state = _make_state(file_list=file_list, risk_scores=self._risk_scores("src/user.py"))
        result = detect_defects(state)

        titles = [d["title"] for d in result["defects"]]
        assert any("SQL injection" in t or "sql injection" in t.lower() for t in titles)

    def test_detects_todo_in_high_risk_file(self):
        content = "def process_payment():\n    # TODO: validate card number\n    pass"
        file_list = [{"path": "src/payment.py", "content": content, "diff": "", "lines_changed": 20}]
        state = _make_state(file_list=file_list, risk_scores=self._risk_scores("src/payment.py", score=0.9))
        result = detect_defects(state)

        severities = [d["severity"] for d in result["defects"]]
        assert "P3" in severities

    def test_clean_file_no_defects(self):
        content = "def add(a, b):\n    return a + b\n"
        file_list = [{"path": "src/math.py", "content": content, "diff": "", "lines_changed": 2}]
        state = _make_state(
            file_list=file_list,
            risk_scores=[{"file_path": "src/math.py", "score": 0.1, "anomaly_flag": False, "features": {
                "lines_changed": 2, "file_size_kb": 0.1, "import_count": 0,
                "function_count": 1, "has_auth_code": False, "has_db_code": False,
            }}],
        )
        result = detect_defects(state)
        # No SQL injection, no auth issues, no bad comments, no DB issues
        assert len(result["defects"]) == 0


# ---------------------------------------------------------------------------
# Node 6 — explain_and_score (consistency scoring)
# ---------------------------------------------------------------------------
class TestExplainAndScore:
    def test_consistency_score_full(self):
        explanation = (
            "1. What broke: The login function fails.\n"
            "2. Why it matters: Users cannot authenticate.\n"
            "3. Root cause hypothesis: Missing null check.\n"
            "4. Steps to reproduce: Call login with empty string.\n"
            "5. Suggested fix: Add guard clause at top of function."
        )
        assert _consistency_score(explanation) == 1.0

    def test_consistency_score_partial(self):
        explanation = "What broke: The function crashes. Why it matters: data loss."
        score = _consistency_score(explanation)
        assert 0.3 <= score <= 0.5

    def test_consistency_score_empty(self):
        assert _consistency_score("") == 0.0

    @patch("agents.langgraph_agent.Groq")
    def test_explain_calls_groq_for_each_defect(self, mock_groq_class):
        explanation = (
            "1. What broke: auth.\n2. Why it matters: security.\n"
            "3. Root cause hypothesis: bad code.\n4. Steps to reproduce: run it.\n"
            "5. Suggested fix: patch it."
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_groq_response(explanation)
        mock_groq_class.return_value = mock_client

        defects = [
            {"title": "Auth bug", "severity": "P0", "description": "Token not validated", "stack_trace": "", "file_path": "src/auth.py"},
            {"title": "DB bug", "severity": "P1", "description": "Missing rollback", "stack_trace": "", "file_path": "src/db.py"},
        ]
        state = _make_state(defects=defects)
        result = explain_and_score(state)

        # At least 2 calls (one per defect, may be more if consistency < 0.85 triggers retry)
        assert mock_client.chat.completions.create.call_count >= 2
        assert len(result["explained_defects"]) == 2

    @patch("agents.langgraph_agent.Groq")
    def test_explain_adds_ai_explanation_field(self, mock_groq_class):
        explanation = (
            "What broke: crash.\nWhy it matters: bad.\n"
            "Root cause hypothesis: bug.\nSteps to reproduce: run.\nSuggested fix: fix."
        )
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_groq_response(explanation)
        mock_groq_class.return_value = mock_client

        defects = [
            {"title": "Bug", "severity": "P1", "description": "Desc", "stack_trace": "", "file_path": "f.py"},
        ]
        state = _make_state(defects=defects)
        result = explain_and_score(state)

        assert "ai_explanation" in result["explained_defects"][0]
        assert "consistency_score" in result["explained_defects"][0]

    @patch("agents.langgraph_agent.Groq")
    def test_explain_handles_groq_failure(self, mock_groq_class):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Connection timeout")
        mock_groq_class.return_value = mock_client

        defects = [
            {"title": "Bug", "severity": "P2", "description": "Issue", "stack_trace": "", "file_path": "f.py"},
        ]
        state = _make_state(defects=defects)
        result = explain_and_score(state)

        assert result["error"] == ""
        assert result["explained_defects"][0]["consistency_score"] == 0.0


# ---------------------------------------------------------------------------
# Node 6.5 — generate_fixes (CodegenerateAgent)
# ---------------------------------------------------------------------------
class TestGenerateFixes:
    def _defect(self, path: str, severity: str = "P0", title: str = "SQL injection") -> dict:
        return {
            "title": title,
            "severity": severity,
            "description": "Bad query",
            "stack_trace": "",
            "file_path": path,
            "ai_explanation": "String interpolation used directly in SQL query.",
            "consistency_score": 0.8,
        }

    def _file_info(self, path: str, content: str = "def foo(): pass") -> dict:
        return {"path": path, "content": content, "diff": "", "lines_changed": 10}

    @patch("agents.langgraph_agent.Groq")
    def test_generate_fixes_calls_groq_for_high_severity(self, mock_groq_class):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_groq_response(
            "--- a/src/db.py\n+++ b/src/db.py\n@@ -1 +1 @@\n-bad\n+good"
        )
        mock_groq_class.return_value = mock_client

        defects = [self._defect("src/db.py", severity="P0")]
        file_list = [self._file_info("src/db.py", "result = db.execute(query)")]
        state = _make_state(explained_defects=defects, file_list=file_list)
        result = generate_fixes(state)

        mock_client.chat.completions.create.assert_called_once()
        assert len(result["generated_fixes"]) == 1
        assert result["generated_fixes"][0]["file_path"] == "src/db.py"

    @patch("agents.langgraph_agent.Groq")
    def test_generate_fixes_skips_low_severity(self, mock_groq_class):
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        defects = [self._defect("src/notes.py", severity="P3")]
        file_list = [self._file_info("src/notes.py")]
        state = _make_state(explained_defects=defects, file_list=file_list)
        result = generate_fixes(state)

        mock_client.chat.completions.create.assert_not_called()
        assert result["generated_fixes"] == []

    @patch("agents.langgraph_agent.Groq")
    def test_generate_fixes_respects_top_5_limit(self, mock_groq_class):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_groq_response("diff")
        mock_groq_class.return_value = mock_client

        defects = [self._defect(f"src/mod_{i}.py", severity="P1") for i in range(10)]
        file_list = [self._file_info(f"src/mod_{i}.py") for i in range(10)]
        state = _make_state(explained_defects=defects, file_list=file_list)
        result = generate_fixes(state)

        assert mock_client.chat.completions.create.call_count == 5
        assert len(result["generated_fixes"]) == 5

    @patch("agents.langgraph_agent.Groq")
    def test_generate_fixes_skips_defect_with_no_file_content(self, mock_groq_class):
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        defects = [self._defect("src/missing.py", severity="P0")]
        state = _make_state(explained_defects=defects, file_list=[])
        result = generate_fixes(state)

        mock_client.chat.completions.create.assert_not_called()
        assert result["generated_fixes"] == []

    @patch("agents.langgraph_agent.Groq")
    def test_generate_fixes_handles_llm_failure_gracefully(self, mock_groq_class):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        mock_groq_class.return_value = mock_client

        defects = [self._defect("src/service.py", severity="P0")]
        file_list = [self._file_info("src/service.py")]
        state = _make_state(explained_defects=defects, file_list=file_list)
        result = generate_fixes(state)

        assert len(result["generated_fixes"]) == 1
        assert "Fix generation failed" in result["generated_fixes"][0]["fix_diff"]
        assert result["error"] == ""


# ---------------------------------------------------------------------------
# Node 6.6 — apply_and_verify_fixes (CodegenerateAgent: clone/patch/retest/PR)
# ---------------------------------------------------------------------------
class TestApplyAndVerifyFixes:
    def _fix(self, path="ai-engine/foo.py", title="SQL injection", severity="P0", diff="--- a\n+++ b\n"):
        return {"file_path": path, "defect_title": title, "severity": severity, "fix_diff": diff}

    def test_no_fixes_returns_empty(self):
        state = _make_state(generated_fixes=[])
        result = apply_and_verify_fixes(state)
        assert result["pr_results"] == []

    @patch("agents.langgraph_agent._clone_repo")
    def test_skips_failed_generation_placeholder(self, mock_clone):
        fixes = [self._fix(diff="// Fix generation failed for x.py: boom")]
        state = _make_state(generated_fixes=fixes)
        result = apply_and_verify_fixes(state)

        assert result["pr_results"] == []
        mock_clone.assert_not_called()

    @patch("agents.langgraph_agent._open_pr")
    @patch("agents.langgraph_agent._run_tests")
    @patch("agents.langgraph_agent._apply_diff")
    @patch("agents.langgraph_agent._clone_repo")
    @patch("agents.langgraph_agent.subprocess.run")
    @patch("agents.langgraph_agent.Github")
    def test_opens_pr_when_tests_pass(self, mock_gh_class, mock_run, mock_clone, mock_apply, mock_tests, mock_pr):
        mock_gh_class.return_value.get_repo.return_value.default_branch = "main"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_apply.return_value = (True, "")
        mock_tests.return_value = (True, "ok")
        mock_pr.return_value = "https://github.com/bkumars22/QA-Intelligent-Platform/pull/1"

        fixes = [self._fix()]
        state = _make_state(
            generated_fixes=fixes,
            explained_defects=[{"title": "SQL injection", "ai_explanation": "bad query"}],
        )
        result = apply_and_verify_fixes(state)

        assert len(result["pr_results"]) == 1
        entry = result["pr_results"][0]
        assert entry["status"] == "pr_opened"
        assert entry["pr_url"] == "https://github.com/bkumars22/QA-Intelligent-Platform/pull/1"
        assert entry["why"] == "bad query"
        assert entry["tests_passed"] is True

    @patch("agents.langgraph_agent._open_pr")
    @patch("agents.langgraph_agent._run_tests")
    @patch("agents.langgraph_agent._apply_diff")
    @patch("agents.langgraph_agent._clone_repo")
    @patch("agents.langgraph_agent.subprocess.run")
    @patch("agents.langgraph_agent.Github")
    def test_skips_pr_when_tests_fail(self, mock_gh_class, mock_run, mock_clone, mock_apply, mock_tests, mock_pr):
        mock_gh_class.return_value.get_repo.return_value.default_branch = "main"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_apply.return_value = (True, "")
        mock_tests.return_value = (False, "1 failed")

        state = _make_state(generated_fixes=[self._fix()])
        result = apply_and_verify_fixes(state)

        assert result["pr_results"][0]["status"] == "tests_failed"
        mock_pr.assert_not_called()

    @patch("agents.langgraph_agent._open_pr")
    @patch("agents.langgraph_agent._run_tests")
    @patch("agents.langgraph_agent._apply_diff")
    @patch("agents.langgraph_agent._clone_repo")
    @patch("agents.langgraph_agent.subprocess.run")
    @patch("agents.langgraph_agent.Github")
    def test_opens_pr_when_no_test_runner_mapped(self, mock_gh_class, mock_run, mock_clone, mock_apply, mock_tests, mock_pr):
        mock_gh_class.return_value.get_repo.return_value.default_branch = "main"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_apply.return_value = (True, "")
        mock_tests.return_value = (None, "no runner mapped")
        mock_pr.return_value = "https://github.com/bkumars22/QA-Intelligent-Platform/pull/2"

        state = _make_state(generated_fixes=[self._fix(path="frontend/src/App.tsx")])
        result = apply_and_verify_fixes(state)

        assert result["pr_results"][0]["status"] == "pr_opened"
        assert result["pr_results"][0]["tests_passed"] is None

    @patch("agents.langgraph_agent._apply_diff")
    @patch("agents.langgraph_agent._clone_repo")
    @patch("agents.langgraph_agent.subprocess.run")
    @patch("agents.langgraph_agent.Github")
    def test_apply_failure_skips_tests(self, mock_gh_class, mock_run, mock_clone, mock_apply):
        mock_gh_class.return_value.get_repo.return_value.default_branch = "main"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_apply.return_value = (False, "patch does not apply")

        with patch("agents.langgraph_agent._run_tests") as mock_tests:
            state = _make_state(generated_fixes=[self._fix()])
            result = apply_and_verify_fixes(state)
            mock_tests.assert_not_called()

        assert result["pr_results"][0]["status"] == "apply_failed"

    @patch("agents.langgraph_agent._clone_repo", side_effect=Exception("network down"))
    @patch("agents.langgraph_agent.Github")
    def test_clone_failure_reports_status(self, mock_gh_class, mock_clone):
        mock_gh_class.return_value.get_repo.return_value.default_branch = "main"
        state = _make_state(generated_fixes=[self._fix()])
        result = apply_and_verify_fixes(state)
        assert result["pr_results"][0]["status"] == "clone_failed"


# ---------------------------------------------------------------------------
# _post_autofix_audit (persists pr_results to the backend audit table)
# ---------------------------------------------------------------------------
class TestPostAutofixAudit:
    def test_skips_when_no_pr_results(self, monkeypatch):
        import agents.langgraph_agent as agent_module
        called = []
        monkeypatch.setattr(agent_module.requests, "post", lambda *a, **k: called.append(1))

        state = _make_state(pr_results=[])
        result = _post_autofix_audit(state)

        assert called == []
        assert result["autofix_audit"] == "skipped — no fix attempts this run"

    def test_posts_camel_case_payload(self, monkeypatch):
        import agents.langgraph_agent as agent_module
        captured = {}

        def fake_post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            return MagicMock(status_code=200)

        monkeypatch.setattr(agent_module.requests, "post", fake_post)

        pr_results = [{
            "file_path": "ai-engine/foo.py", "defect_title": "SQL injection", "severity": "P0",
            "branch": "auto-fix/abc-sql", "why": "bad query", "tests_passed": True,
            "status": "pr_opened", "pr_url": "https://github.com/x/y/pull/1", "detail": "",
        }]
        state = _make_state(pr_results=pr_results)
        result = _post_autofix_audit(state)

        assert result["autofix_audit"] == "ok"
        assert captured["url"].endswith("/api/autofix-audit")
        entry = captured["json"]["entries"][0]
        assert entry["filePath"] == "ai-engine/foo.py"
        assert entry["testsPassed"] is True
        assert entry["prUrl"] == "https://github.com/x/y/pull/1"

    def test_handles_request_failure_gracefully(self, monkeypatch):
        import agents.langgraph_agent as agent_module

        def fake_post(*a, **k):
            raise Exception("connection refused")

        monkeypatch.setattr(agent_module.requests, "post", fake_post)

        state = _make_state(pr_results=[{"file_path": "f.py", "defect_title": "t", "status": "pr_opened"}])
        result = _post_autofix_audit(state)

        assert "failed" in result["autofix_audit"]


# ---------------------------------------------------------------------------
# Node 7 — dispatch_results
# ---------------------------------------------------------------------------
class TestDispatchResults:
    def _full_state(self) -> AgentState:
        return _make_state(
            explained_defects=[
                {
                    "title": "SQL injection",
                    "severity": "P0",
                    "description": "Bad query",
                    "stack_trace": "",
                    "file_path": "src/db.py",
                    "ai_explanation": "It's bad.",
                    "consistency_score": 0.8,
                }
            ],
            risk_scores=[{"file_path": "src/db.py", "score": 0.95, "anomaly_flag": True}],
            coverage_gaps=[],
            generated_tests=[],
        )

    def test_dispatch_saves_report_file(self, tmp_path, monkeypatch):
        import agents.langgraph_agent as agent_module

        saved_path = [None]

        def mock_save(s):
            path = str(tmp_path / f"testmind_report_{s['run_id']}.json")
            with open(path, "w") as fh:
                json.dump({"run_id": s["run_id"]}, fh)
            saved_path[0] = path
            return path

        monkeypatch.setattr(agent_module, "_save_report", mock_save)
        monkeypatch.setattr(agent_module, "_create_jira_tickets", lambda s: {"jira": "skipped"})
        monkeypatch.setattr(agent_module, "_post_slack", lambda s: {"slack": "skipped"})
        monkeypatch.setattr(agent_module, "_callback_backend", lambda s: {"backend": "skipped"})

        state = self._full_state()
        result = dispatch_results(state)

        assert saved_path[0] is not None
        assert os.path.exists(saved_path[0])

    def test_dispatch_sets_status_completed(self, monkeypatch):
        import agents.langgraph_agent as agent_module

        monkeypatch.setattr(agent_module, "_save_report", lambda s: "/tmp/report.json")
        monkeypatch.setattr(agent_module, "_create_jira_tickets", lambda s: {"jira": "skipped"})
        monkeypatch.setattr(agent_module, "_post_slack", lambda s: {"slack": "skipped"})
        monkeypatch.setattr(agent_module, "_callback_backend", lambda s: {"backend": "skipped"})

        state = self._full_state()
        result = dispatch_results(state)

        assert result["status"] == "COMPLETED"
        assert result["error"] == ""

    def test_dispatch_jira_skipped_when_no_env(self, monkeypatch):
        import agents.langgraph_agent as agent_module

        monkeypatch.setattr(agent_module, "_save_report", lambda s: "/tmp/r.json")
        monkeypatch.setattr(agent_module, "_post_slack", lambda s: {"slack": "skipped"})
        monkeypatch.setattr(agent_module, "_callback_backend", lambda s: {"backend": "skipped"})
        monkeypatch.delenv("JIRA_URL", raising=False)
        monkeypatch.delenv("JIRA_API_TOKEN", raising=False)

        state = self._full_state()
        result = dispatch_results(state)

        assert "skipped" in str(result["dispatch_results"].get("jira", ""))
