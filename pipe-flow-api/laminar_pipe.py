"""
Laminar pressure drop in a straight circular pipe (Hagen–Poiseuille), with
typed inputs and outputs, explicit units and a model-applicability check.

All quantities are SI: m, m^3/s, kg/m^3, Pa·s, Pa, m/s.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Regime boundaries. These are product settings for a teaching tool, not
# universal thresholds, and they are still awaiting independent review.
LAMINAR_RE_LIMIT = 2000.0  # laminar band is Re < 2000
TRANSITIONAL_RE_LIMIT = 4000.0  # 2000 <= Re < 4000 is transitional

Regime = Literal["laminar", "transitional", "above_transitional"]
Outcome = Literal["calculated", "calculated_outside_model_validity"]

ASSUMPTIONS = (
    "Horizontal, rigid, circular pipe",
    "Steady, fully developed, laminar flow",
    "Incompressible Newtonian fluid with constant viscosity",
    "No slip at the wall",
    "No fittings, minor losses, elevation change or wall roughness",
    "Density and viscosity are the constant values supplied in the request",
)
ENTRANCE_LENGTH = "Entrance-length effects are not assessed."
PROPERTY_RANGE = "No validity range is claimed for the supplied fluid properties."
EXTRAPOLATED = "Re is outside the laminar band: these numbers extrapolate the laminar equation and are not validated predictions."


class NotRepresentable(ValueError):
    """The inputs pass validation but a derived quantity cannot be represented in double precision.

    Raised when an intermediate or result underflows to zero or overflows to infinity, so that a
    finite, positive request such as diameter_m = 1e-100 fails with a clear message instead of a
    ZeroDivisionError or an infinite pressure drop. This is a numerical limit, not a statement
    about the model's physical validity; that is reported separately through `regime`.
    """


class PipeFlowRequest(BaseModel):
    """Inputs. Every value must be a JSON number (not a string or boolean), finite and strictly positive."""

    # strict=True: "5.0" and true are rejected for float fields; 5 and 5.0 are accepted.
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    flow_rate_m3_s: float = Field(gt=0, description="Volumetric flow rate Q, m^3/s")
    diameter_m: float = Field(gt=0, description="Inside diameter D, m")
    length_m: float = Field(gt=0, description="Pipe length L, m")
    density_kg_m3: float = Field(gt=0, description="Fluid density rho, kg/m^3 (declared constant)")
    dynamic_viscosity_pa_s: float = Field(gt=0, description="Dynamic viscosity mu, Pa·s (declared constant)")


class PipeFlowResult(BaseModel):
    """Outputs, with the conditions under which they hold."""

    pressure_drop_pa: float = Field(description="Pressure drop p_in - p_out, Pa")
    mean_velocity_m_s: float = Field(description="Mean velocity V = 4Q/(pi D^2), m/s")
    reynolds_number: float = Field(description="Re = rho V D / mu, dimensionless")
    wall_shear_stress_pa: float = Field(description="Wall shear stress magnitude 8 mu V / D, Pa")
    regime: Regime
    outcome: Outcome
    extrapolated: bool = Field(description="True when Re is outside the laminar band")
    assumptions: list[str]
    limitations: list[str]


def classify_reynolds(re: float) -> Regime:
    """Regime for an exact Reynolds number. No tolerance is applied at the boundaries."""
    if not math.isfinite(re) or re < 0:
        raise ValueError(f"Reynolds number must be finite and >= 0, got {re!r}")
    if re < LAMINAR_RE_LIMIT:
        return "laminar"
    if re < TRANSITIONAL_RE_LIMIT:
        return "transitional"
    return "above_transitional"


def solve(req: PipeFlowRequest) -> PipeFlowResult:
    """Hagen–Poiseuille: dp = 128 mu L Q / (pi D^4) = 32 mu L V / D^2."""
    mu, d, length = req.dynamic_viscosity_pa_s, req.diameter_m, req.length_m
    try:
        velocity = 4.0 * req.flow_rate_m3_s / (math.pi * d**2)
        dp = 128.0 * mu * length * req.flow_rate_m3_s / (math.pi * d**4)
        re = req.density_kg_m3 * velocity * d / mu
        tau_w = 8.0 * mu * velocity / d
    except (ZeroDivisionError, OverflowError) as exc:
        kind = "division by zero after underflow" if isinstance(exc, ZeroDivisionError) else "overflow"
        raise NotRepresentable(f"a derived quantity underflowed or overflowed in double precision ({kind})") from exc
    derived = {"mean_velocity_m_s": velocity, "pressure_drop_pa": dp, "reynolds_number": re, "wall_shear_stress_pa": tau_w}
    bad = [k for k, v in derived.items() if not math.isfinite(v) or v <= 0.0]
    if bad:
        raise NotRepresentable(f"{', '.join(bad)} not representable in double precision for these inputs: "
                               + ", ".join(f"{k}={derived[k]!r}" for k in bad))
    regime = classify_reynolds(re)
    laminar = regime == "laminar"
    limitations = [ENTRANCE_LENGTH, PROPERTY_RANGE] + ([] if laminar else [EXTRAPOLATED])
    return PipeFlowResult(
        pressure_drop_pa=dp,
        mean_velocity_m_s=velocity,
        reynolds_number=re,
        wall_shear_stress_pa=tau_w,
        regime=regime,
        outcome="calculated" if laminar else "calculated_outside_model_validity",
        extrapolated=not laminar,
        assumptions=list(ASSUMPTIONS),
        limitations=limitations,
    )
