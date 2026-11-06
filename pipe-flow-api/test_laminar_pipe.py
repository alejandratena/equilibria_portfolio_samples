"""Checks for the pipe-flow example. Run: python -m pytest -q

Expected values are literals derived by hand (shown in comments); none is
computed with the code under test.
"""
import math

import pytest
from fastapi.testclient import TestClient

from api import app
from laminar_pipe import NotRepresentable, PipeFlowRequest, classify_reynolds, solve

# Synthetic case, not a real fluid: mu = 0.1 Pa·s, rho = 900 kg/m^3, D = 0.01 m, L = 2 m, V = 0.2 m/s.
# Q = V * pi D^2 / 4 = pi * 5e-6 m^3/s
# dp = 32 mu L V / D^2 = 32 * 0.1 * 2 * 0.2 / 1e-4 = 12800 Pa
# Re = rho V D / mu = 900 * 0.2 * 0.01 / 0.1 = 18
# tau_w = 8 mu V / D = 8 * 0.1 * 0.2 / 0.01 = 16 Pa
CASE = dict(flow_rate_m3_s=math.pi * 5e-6, diameter_m=0.01, length_m=2.0,
            density_kg_m3=900.0, dynamic_viscosity_pa_s=0.1)


def run(**overrides):
    return solve(PipeFlowRequest(**{**CASE, **overrides}))


def test_hand_derived_reference_case():
    r = run()
    assert r.mean_velocity_m_s == pytest.approx(0.2, rel=1e-12)
    assert r.pressure_drop_pa == pytest.approx(12800.0, rel=1e-12)
    assert r.reynolds_number == pytest.approx(18.0, rel=1e-12)
    assert r.wall_shear_stress_pa == pytest.approx(16.0, rel=1e-12)
    assert (r.regime, r.outcome, r.extrapolated) == ("laminar", "calculated", False)


def test_scaling_laws_and_density_independence():
    # dp is linear in mu, L and Q, scales as D^-4 at fixed Q, and does not depend on rho.
    assert run(dynamic_viscosity_pa_s=0.2).pressure_drop_pa == pytest.approx(25600.0, rel=1e-12)
    assert run(length_m=4.0).pressure_drop_pa == pytest.approx(25600.0, rel=1e-12)
    assert run(diameter_m=0.02).pressure_drop_pa == pytest.approx(800.0, rel=1e-12)  # 12800 / 16
    r = run(density_kg_m3=1800.0)
    assert r.pressure_drop_pa == pytest.approx(12800.0, rel=1e-12) and r.reynolds_number == pytest.approx(36.0, rel=1e-12)


def test_dimensionless_identity():
    # Hagen–Poiseuille in dimensionless form: dp D^2 / (mu V L) = 32 for any valid input.
    for over in ({}, {"diameter_m": 0.037}, {"flow_rate_m3_s": 3e-3, "dynamic_viscosity_pa_s": 0.004}):
        r = run(**over)
        req = {**CASE, **over}
        group = r.pressure_drop_pa * req["diameter_m"] ** 2 / (req["dynamic_viscosity_pa_s"] * r.mean_velocity_m_s * req["length_m"])
        assert group == pytest.approx(32.0, rel=1e-12)


@pytest.mark.parametrize("re, regime", [
    (math.nextafter(2000.0, -math.inf), "laminar"),
    (2000.0, "transitional"),
    (math.nextafter(4000.0, -math.inf), "transitional"),
    (4000.0, "above_transitional"),
])
def test_regime_boundaries_on_exact_values(re, regime):
    # Boundaries are tested on the classifier directly: Re computed from geometry
    # can land one rounding step either side of 2000 depending on operation order.
    assert classify_reynolds(re) == regime


def test_outside_laminar_band_still_returns_numbers_but_flags_them():
    r = run(flow_rate_m3_s=math.pi * 5e-6 * 200)  # Re = 3600
    assert r.regime == "transitional" and r.outcome == "calculated_outside_model_validity"
    assert r.extrapolated and any("not validated" in s for s in r.limitations)
    assert r.pressure_drop_pa == pytest.approx(12800.0 * 200, rel=1e-12)


def test_entrance_length_limitation_is_reported_for_every_run():
    for q in (math.pi * 5e-6, math.pi * 5e-6 * 300):
        assert any("Entrance-length" in s for s in run(flow_rate_m3_s=q).limitations)


@pytest.mark.parametrize("override, reason", [
    ({"diameter_m": 1e-100}, "D^4 underflows to 0"),
    ({"diameter_m": 1e100}, "D^4 overflows"),
    ({"flow_rate_m3_s": 1e308, "diameter_m": 1e-3}, "every derived quantity is inf"),
    ({"dynamic_viscosity_pa_s": 5e-324}, "dp underflows to 0 and Re is inf"),
    ({"length_m": 1e308, "dynamic_viscosity_pa_s": 1e3}, "dp alone is inf"),
])
def test_valid_but_unrepresentable_inputs_raise_a_named_error(override, reason):
    # These pass validation (finite, positive) but cannot be computed in double precision.
    # They must fail with NotRepresentable, never with ZeroDivisionError, OverflowError or an
    # infinite result. This is separate from the regime check: a representable result far outside
    # the laminar band is still returned, flagged.
    with pytest.raises(NotRepresentable):
        run(**override)


def test_extreme_but_representable_inputs_are_computed():
    r = run(diameter_m=1e-6, flow_rate_m3_s=1e-15)  # a capillary; Re ~ 1e-5
    assert math.isfinite(r.pressure_drop_pa) and r.regime == "laminar"
    r = run(diameter_m=10.0, flow_rate_m3_s=1e3, dynamic_viscosity_pa_s=1e-5)  # Re ~ 1e10
    assert math.isfinite(r.pressure_drop_pa) and r.regime == "above_transitional" and r.extrapolated


client = TestClient(app)


@pytest.mark.parametrize("field, value", [("diameter_m", 0.0), ("length_m", -1.0)])
def test_api_rejects_invalid_inputs_before_calculating(field, value):
    resp = client.post("/pipe/pressure-drop", json={**CASE, field: value})
    assert resp.status_code == 422
    assert field in {loc for err in resp.json()["detail"] for loc in err["loc"]}


def post_raw(body_text):
    # A raw body, because these values can't be produced by a JSON encoder.
    return client.post("/pipe/pressure-drop", content=body_text, headers={"content-type": "application/json"})


@pytest.mark.parametrize("field, literal", [
    ("dynamic_viscosity_pa_s", "NaN"),
    ("flow_rate_m3_s", "Infinity"),
    ("length_m", "-Infinity"),
    ("diameter_m", "1e400"),  # valid JSON, but parses to inf
])
def test_api_rejects_non_finite_numbers_with_422_not_500(field, literal):
    body = ", ".join(f'"{k}": {literal if k == field else repr(v)}' for k, v in CASE.items())
    resp = post_raw("{" + body + "}")
    assert resp.status_code == 422
    assert field in {loc for err in resp.json()["detail"] for loc in err["loc"]}


def test_api_error_response_stays_valid_json_when_the_body_holds_nan():
    # A missing field makes the whole body the echoed input; it contains NaN in another field.
    body = ", ".join(f'"{k}": {"NaN" if k == "length_m" else repr(v)}' for k, v in CASE.items() if k != "diameter_m")
    resp = post_raw("{" + body + "}")
    assert resp.status_code == 422
    assert {"diameter_m", "length_m"} <= {loc for err in resp.json()["detail"] for loc in err["loc"]}


@pytest.mark.parametrize("field, value", [
    ("length_m", True), ("length_m", False), ("length_m", "5.0"), ("diameter_m", "0.02"), ("density_kg_m3", "998"),
])
def test_api_rejects_booleans_and_numeric_strings(field, value):
    # Strict types: a float field takes a JSON number only. Without strict mode, Pydantic would
    # read true as 1.0 and "5.0" as 5.0 and the request would compute.
    resp = client.post("/pipe/pressure-drop", json={**CASE, field: value})
    assert resp.status_code == 422
    assert field in {loc for err in resp.json()["detail"] for loc in err["loc"]}


def test_api_accepts_integer_and_float_json_numbers():
    body = client.post("/pipe/pressure-drop", json={**CASE, "length_m": 2, "density_kg_m3": 900}).json()
    assert body["pressure_drop_pa"] == pytest.approx(12800.0, rel=1e-12)
    with pytest.raises(ValueError):
        PipeFlowRequest(**{**CASE, "length_m": True})
    with pytest.raises(ValueError):
        PipeFlowRequest(**{**CASE, "length_m": "2.0"})


def test_api_returns_422_not_500_for_unrepresentable_inputs():
    resp = client.post("/pipe/pressure-drop", json={**CASE, "diameter_m": 1e-100})
    assert resp.status_code == 422
    assert resp.json()["detail"][0]["type"] == "not_representable"
    assert "underflowed or overflowed" in resp.json()["detail"][0]["msg"]


def test_api_rejects_missing_and_unknown_fields():
    missing = {k: v for k, v in CASE.items() if k != "length_m"}
    assert client.post("/pipe/pressure-drop", json=missing).status_code == 422
    assert client.post("/pipe/pressure-drop", json={**CASE, "length_ft": 3}).status_code == 422


def test_api_round_trip_matches_the_library():
    body = client.post("/pipe/pressure-drop", json=CASE).json()
    assert body["pressure_drop_pa"] == pytest.approx(12800.0, rel=1e-12)
    assert body["regime"] == "laminar" and len(body["assumptions"]) == 6
