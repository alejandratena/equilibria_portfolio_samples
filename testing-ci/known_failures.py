"""Known scientific failures, contained in CI. Not validated.

Each marker contains one documented failure:

- strict=True: if a contained test starts passing, the run fails, so the marker has to be removed
  in the same change that fixes the model;
- raises=...: only the known failure mode is contained; any other exception is a normal failure.

A marker is never added to make CI pass. It is added when a test exposes a real model defect
that can't be fixed yet, with the reason stated.
"""

import pytest

from example.mixer import BalanceError

KNOWN_EQUAL_CP_MIXING = pytest.mark.xfail(
    strict=True,
    raises=BalanceError,
    reason="Mixer assumes equal specific heat capacities, so the energy balance cannot close for fluids with different cp.",
)
