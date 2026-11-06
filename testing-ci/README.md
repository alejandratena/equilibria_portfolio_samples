# Testing and CI: known failures

A pytest setup for tracking a documented model defect while continuing to detect new regressions. The sample combines strict expected-failure markers with a separate check of the known-failure list.

## Test policy

Each known failure is defined in `known_failures.py` using `pytest.mark.xfail` with `strict=True`, an expected exception (`raises=`), and a reason.

The [GitHub Actions workflow](../.github/workflows/ci.yml) performs two checks:

1. **Regression gate:** Run the full suite with strict expected failures enabled. A previously failing test that starts passing, or fails with an unexpected exception, fails the gate.
2. **Known-failure check:** Rerun the example suite with `--runxfail` and the `allowlist.py` plugin. The plugin requires the actual failures to match the declared tests and exception types, with failures occurring during the test body.

| Condition | Result |
|---|---|
| Only documented failures occur as expected | Pass |
| A new test fails | Fail |
| A documented failure starts passing | Fail |
| A documented failure raises a different exception | Fail |

The allowlist verifies test outcomes, not scientific correctness.

## Files

- `known_failures.py` — declared expected failures
- `allowlist.py` — pytest plugin for checking failure identity, exception type, and execution phase
- `example/mixer.py` and `example/test_mixer.py` — illustrative model and known defect
- `test_allowlist.py` — five isolated tests of the plugin and strict-xfail behavior

The illustrative adiabatic mixer computes outlet temperature using a mass-weighted average, which assumes equal specific heat capacities. A test using unequal heat capacities demonstrates the resulting sensible-energy imbalance. The model and defect were created for this repository; they are not production incidents.

## Run

```bash
pip install -r requirements.txt
python -m pytest -q -rxX
python -m pytest example -q --runxfail -p allowlist
```

The first command is expected to report seven passing tests and one expected failure. The second reports the known failure but exits successfully when the failure matches its declaration.

## Limitations

- The workflow does not itself enforce branch protection or required status checks; those are repository settings.
- Skipped or deselected declared tests are treated as no longer failing.
- The production plugin additionally generates CI summaries and links to a known-failure ledger. Those features are excluded, and the simplified plugin was not directly compared with production.
