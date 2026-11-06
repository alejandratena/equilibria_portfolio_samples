# Pipe-flow API

A FastAPI endpoint for pressure-drop calculations using the Hagen–Poiseuille equation. The sample includes input validation, Reynolds-number classification, and explicit model assumptions and limitations.

## Model and API

For steady, fully developed, laminar flow of an incompressible Newtonian fluid in a rigid circular pipe:

- Mean velocity: `V = 4Q/(πD²)`
- Pressure drop: `Δp = 128μLQ/(πD⁴)`
- Reynolds number: `Re = ρVD/μ`
- Wall shear stress: `τw = 8μV/D`

`Q` is volumetric flow rate, `D` is inside diameter, `L` is pipe length, `ρ` is density, and `μ` is dynamic viscosity. All inputs and outputs use SI units.

`POST /pipe/pressure-drop` accepts finite, positive JSON numbers and rejects missing fields, unknown fields, strings, and booleans with HTTP 422. Units are specified in field names but cannot be verified independently of the submitted values.

| Reynolds number | Reported regime | Result status |
|---|---|---|
| `Re < 2000` | `laminar` | `calculated` |
| `2000 ≤ Re < 4000` | `transitional` | `calculated_outside_model_validity` |
| `Re ≥ 4000` | `above_transitional` | `calculated_outside_model_validity` |

The solver returns the laminar-equation result above the defined laminar band, but marks it as extrapolated rather than treating it as a validated prediction. The 2000 and 4000 thresholds are provisional teaching-tool settings, not independently established boundaries.

The response also lists model assumptions and identifies unassessed effects, including entrance-region losses and fluid-property applicability. Intermediate floating-point failures and invalid derived values are returned as HTTP 422 with `type: not_representable`.

## Files

- `laminar_pipe.py` — request/result schemas, solver, regime classification, and numerical checks
- `api.py` — FastAPI endpoint and validation/error responses
- `test_laminar_pipe.py` — equation-based, boundary, and API tests
- `example_request.json` — sample inputs

## Verification

The 31 tests cover a hand-calculated reference (`Δp = 12,800 Pa`, `Re = 18`, `τw = 16 Pa`), pressure-drop scaling laws, a dimensionless consistency identity, Reynolds-number boundaries, extreme floating-point inputs, and HTTP validation.

The example request represents 0.9 L/min through a 5 m pipe with a 20 mm inside diameter. It produces approximately `Δp = 19.1 Pa` and `Re = 953`. An estimated laminar entrance length of 0.95 m indicates that the fully developed assumption requires separate assessment; entrance-region pressure losses are not calculated.

An internal comparison against the private application covered 162 input combinations for pressure drop, velocity, Reynolds number, wall shear stress, and regime. The reference implementation and comparison data are not included in this repository.

## Run

```bash
pip install -r requirements.txt
python -m pytest -q
# Optional: install uvicorn, then serve the API
uvicorn api:app --port 8001
```

## Limitations

- The model has not undergone independent scientific review or comparison with a published reference example.
- The calculation assumes steady, fully developed flow in a horizontal, rigid, circular pipe. Fittings, elevation changes, entrance losses, and turbulence are excluded.
- Density and viscosity are caller-supplied constants, without validated property ranges.
- The numerical checks identify failures of the implemented double-precision computation. Intermediate overflow or underflow can trigger `not_representable` even when an algebraically equivalent calculation could produce a finite result; rounding error short of these failures is not evaluated.
