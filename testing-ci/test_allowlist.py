"""Tests for allowlist.py, each run in a fresh temporary project."""
import os
from pathlib import Path

import pytest

pytest_plugins = "pytester"
HERE = Path(__file__).parent

KNOWN = """
import pytest
class BalanceError(Exception): pass
KNOWN_BAD_BALANCE = pytest.mark.xfail(strict=True, raises=BalanceError, reason="known defect")
"""


@pytest.fixture
def project(pytester, monkeypatch):
    # The temporary project's known_failures.py must shadow the real one.
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([str(pytester.path), str(HERE)]))
    pytester.makepyfile(known_failures=KNOWN)
    return pytester


def run_full_suite(p):
    return p.runpytest_subprocess("-p", "allowlist", "--runxfail")


TESTS_HEADER = "from known_failures import KNOWN_BAD_BALANCE, BalanceError\n"


def test_passes_when_only_the_declared_failure_fails(project):
    project.makepyfile(test_model=TESTS_HEADER + """
def test_ok(): pass
@KNOWN_BAD_BALANCE
def test_known(): raise BalanceError("does not close")
""")
    result = run_full_suite(project)
    assert result.ret == 0
    result.stdout.fnmatch_lines(["*OK: failures match the declared known failures exactly*"])


def test_fails_on_an_unlisted_failure(project):
    project.makepyfile(test_model=TESTS_HEADER + """
@KNOWN_BAD_BALANCE
def test_known(): raise BalanceError("does not close")
def test_new_regression(): assert 1 == 2
""")
    result = run_full_suite(project)
    assert result.ret == 1
    result.stdout.fnmatch_lines(["unlisted failure: test_model.py::test_new_regression"])


def test_fails_when_a_known_failure_starts_passing(project):
    project.makepyfile(test_model=TESTS_HEADER + """
@KNOWN_BAD_BALANCE
def test_known(): pass
""")
    result = run_full_suite(project)
    assert result.ret == 1
    result.stdout.fnmatch_lines(["known failure no longer fails; remove its marker: *test_known"])


def test_fails_when_a_known_failure_fails_for_another_reason(project):
    project.makepyfile(test_model=TESTS_HEADER + """
@KNOWN_BAD_BALANCE
def test_known(): raise TypeError("unrelated bug")
""")
    result = run_full_suite(project)
    assert result.ret == 1
    result.stdout.fnmatch_lines(["fails differently than declared (call, TypeError): *test_known"])


def test_regression_gate_without_the_plugin_rejects_an_unexpected_pass(project):
    # The ordinary gate relies on strict=True: a contained test that passes fails the run.
    project.makepyfile(test_model=TESTS_HEADER + """
@KNOWN_BAD_BALANCE
def test_known(): pass
""")
    result = project.runpytest_subprocess()
    assert result.ret == 1
    result.stdout.fnmatch_lines(["*XPASS(strict)*"])
