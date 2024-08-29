# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import ops
import ops.testing

from charm import LdapIntegratorCharm


def test_pebble_ready(harness: ops.testing.Harness[LdapIntegratorCharm]) -> None:
    assert harness.model.unit.status == ops.ActiveStatus()
