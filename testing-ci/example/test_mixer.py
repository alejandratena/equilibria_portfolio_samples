from example.mixer import check_energy_balance, outlet_temperature
from known_failures import KNOWN_EQUAL_CP_MIXING

# Liquid specific heat capacities near 298 K, J/(kg K), held constant over 290–350 K.
# Water and toluene are practically immiscible, so there is no heat of mixing and the outlet
# enthalpy is the sum of the two streams' sensible heats.
CP_WATER, CP_TOLUENE = 4180.0, 1710.0


def test_equal_streams_mix_to_the_average():
    assert outlet_temperature(1.0, 300.0, 1.0, 340.0) == 320.0


def test_balance_closes_for_two_streams_of_the_same_fluid():
    t = outlet_temperature(2.0, 290.0, 1.0, 350.0)
    check_energy_balance([(2.0, CP_WATER, 290.0), (1.0, CP_WATER, 350.0)], (3.0, CP_WATER, t))


@KNOWN_EQUAL_CP_MIXING
def test_balance_closes_for_water_and_toluene():
    # Outlet cp taken as the mass-weighted value of the two phases.
    t = outlet_temperature(1.0, 290.0, 1.0, 350.0)
    cp_out = (CP_WATER + CP_TOLUENE) / 2
    check_energy_balance([(1.0, CP_WATER, 290.0), (1.0, CP_TOLUENE, 350.0)], (2.0, cp_out, t))
