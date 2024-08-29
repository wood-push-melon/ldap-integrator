# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from typing import Generator

import pytest
from ops.testing import Harness

from charm import LdapIntegratorCharm


@pytest.fixture
def harness() -> Generator[Harness, None, None]:
    harness = Harness(LdapIntegratorCharm)
    harness.set_model_name("unit-test")
    harness.set_leader(True)

    harness.begin_with_initial_hooks()
    yield harness
    harness.cleanup()
