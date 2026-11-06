"""Adiabatic mixing of two liquid streams: a deliberately simplified example model.

Sensible heat only, with constant specific heat capacities and no heat of mixing.
"""


class BalanceError(Exception):
    """An energy balance does not close."""


def outlet_temperature(m1_kg_s, t1_k, m2_kg_s, t2_k):
    # Known defect: a mass-weighted average assumes both streams have the same specific heat
    # capacity (cp per kg).
    return (m1_kg_s * t1_k + m2_kg_s * t2_k) / (m1_kg_s + m2_kg_s)


def check_energy_balance(streams_in, stream_out, t_ref_k=298.15, rel_tol=1e-9):
    """Each stream is (mass flow kg/s, cp J/(kg K), T K). Raises BalanceError if in != out."""

    def enthalpy(m, cp, t):
        return m * cp * (t - t_ref_k)

    h_in = sum(enthalpy(*s) for s in streams_in)
    h_out = enthalpy(*stream_out)
    if abs(h_in - h_out) > rel_tol * max(abs(h_in), abs(h_out), 1.0):
        raise BalanceError(f"energy in {h_in:.6g} W != energy out {h_out:.6g} W")
