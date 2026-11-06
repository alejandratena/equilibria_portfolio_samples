# Frontend result identity

A small Zustand state store for keeping simulation results associated with the inputs and model fidelity that produced them. The example uses six inputs from a binary distillation-column simulation.

## Behavior

A run is identified by its model fidelity and normalized numeric inputs. Equivalent numeric text, such as `0.6` and `0.60`, produces the same identity; changing any input or the fidelity changes the identity.

| Status | Meaning |
|---|---|
| `none` | No result is available |
| `current` | The result matches the inputs and fidelity currently displayed |
| `stale` | The displayed inputs are invalid or differ from the result's request |
| `last-run-failed` | An existing result matches the inputs, but the latest run for them failed |

Each submitted request receives an increasing ID. Only the most recent request may update the stored result or failure state, so a delayed response or error cannot overwrite a newer outcome. Invalid inputs are rejected before submission without consuming a request ID or canceling an in-flight request.

## Files

- `src/requestIdentity.js` — request construction, numeric normalization, and identity generation
- `src/resultStatus.js` — result-status classification
- `src/runStore.js` — Zustand store and asynchronous run lifecycle
- `test/runStore.test.js` — state and request-ordering tests

This is a framework-independent state-store example; it does not render a React interface. The production application includes additional inputs and connects result status to the UI.

## Verification

Twelve Vitest tests cover equivalent numeric inputs, stale and restored results, fidelity changes, validation failures, failed runs, and late responses or errors. The tests also exercise behaviors affected by the request-ID guard, fidelity-dependent identity, and rejection of partially numeric strings.

An internal comparison with the private production status logic covered 54 input combinations. The production reference and comparison data are not included here.

## Run

```bash
npm ci
npm test
```

## Limitations

- Request identity is generated in the browser; the server does not independently identify the configuration associated with a result.
- Input parsing checks whether JavaScript can convert a value to a finite number. It is not strict decimal-format validation: values such as `"0x10"` or booleans can be coerced when passed programmatically.
- Tests exercise the store without a browser or live backend.
