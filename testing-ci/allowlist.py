"""Pytest plugin: with --runxfail, allow only the declared known failures.

Run:  pytest example --runxfail -p allowlist

--runxfail ignores the xfail markers, so known failures fail visibly again. This plugin then
passes the run only if the failing tests are exactly the tests carrying a marker from
known_failures.py, and each one fails in its test body with the exception that marker names.
Anything else fails the run: an unlisted failure, a known failure with a different exception, or a
known failure that no longer fails.

It checks bookkeeping only. It does not validate any model.
"""

import pytest

import known_failures


def _declared_marks():
    return [v.mark for v in vars(known_failures).values() if isinstance(v, pytest.MarkDecorator)]


class Allowlist:
    def __init__(self):
        self.declared = {}  # nodeid -> exception type the marker names
        self.failed = {}  # nodeid -> (phase, exception type)
        self.problems = []

    def pytest_collection_modifyitems(self, items):
        marks = _declared_marks()
        for item in items:
            for mark in item.iter_markers("xfail"):
                if mark in marks:
                    self.declared[item.nodeid] = mark.kwargs["raises"]

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_makereport(self, item, call):
        report = yield
        if report.failed:
            self.failed[item.nodeid] = (report.when, call.excinfo.type if call.excinfo else None)
        return report

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session):
        for nodeid, (phase, exc) in self.failed.items():
            raises = self.declared.get(nodeid)
            if raises is None:
                self.problems.append(f"unlisted failure: {nodeid}")
            elif phase != "call" or exc is None or not issubclass(exc, raises):
                name = exc.__name__ if exc else "unknown"
                self.problems.append(f"fails differently than declared ({phase}, {name}): {nodeid}")
        for nodeid in sorted(self.declared.keys() - self.failed.keys()):
            self.problems.append(f"known failure no longer fails; remove its marker: {nodeid}")
        if session.exitstatus in (pytest.ExitCode.OK, pytest.ExitCode.TESTS_FAILED):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED if self.problems else pytest.ExitCode.OK

    def pytest_terminal_summary(self, terminalreporter):
        terminalreporter.section("known-failure allowlist")
        for problem in self.problems or ["OK: failures match the declared known failures exactly"]:
            terminalreporter.write_line(problem)


def pytest_configure(config):
    if not config.option.runxfail:
        raise pytest.UsageError("the allowlist plugin needs --runxfail")
    config.pluginmanager.register(Allowlist(), "known-failure-allowlist")
