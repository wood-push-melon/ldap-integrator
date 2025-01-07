# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Dict, Optional

import pytest
import pytest_asyncio
import yaml
from juju.application import Application
from pytest_operator.plugin import OpsTest

METADATA = yaml.safe_load(Path("./charmcraft.yaml").read_text())
APP_NAME = METADATA["name"]
GLAUTH_APP = "glauth-k8s"
CERTIFICATE_PROVIDER_APP = "self-signed-certificates"


async def get_secret(ops_test: OpsTest, secret_id: str) -> dict:
    show_secret_cmd = f"show-secret {secret_id} --reveal".split()
    _, stdout, _ = await ops_test.juju(*show_secret_cmd)
    cmd_output = yaml.safe_load(stdout)
    return cmd_output[secret_id]


async def get_unit_data(ops_test: OpsTest, unit_name: str) -> dict:
    show_unit_cmd = f"show-unit {unit_name}".split()
    _, stdout, _ = await ops_test.juju(*show_unit_cmd)
    cmd_output = yaml.safe_load(stdout)
    return cmd_output[unit_name]


async def get_integration_data(
    ops_test: OpsTest, app_name: str, integration_name: str, unit_num: int = 0
) -> Optional[dict]:
    data = await get_unit_data(ops_test, f"{app_name}/{unit_num}")
    return next(
        (
            integration
            for integration in data["relation-info"]
            if integration["endpoint"] == integration_name
        ),
        None,
    )


async def get_app_integration_data(
    ops_test: OpsTest,
    app_name: str,
    integration_name: str,
    unit_num: int = 0,
) -> Optional[dict]:
    data = await get_integration_data(ops_test, app_name, integration_name, unit_num)
    return data["application-data"] if data else None


async def get_unit_integration_data(
    ops_test: OpsTest,
    app_name: str,
    remote_app_name: str,
    integration_name: str,
) -> Optional[dict]:
    data = await get_integration_data(ops_test, app_name, integration_name)
    return data["related-units"][f"{remote_app_name}/0"]["data"] if data else None


@pytest.fixture
def ldap_integrator_application(ops_test: OpsTest) -> Application:
    return ops_test.model.applications[APP_NAME]


@pytest_asyncio.fixture(scope="module")
async def local_charm(ops_test: OpsTest) -> Path:
    return await ops_test.build_charm(".")


@pytest_asyncio.fixture
async def ldap_integrator_charm_config(ops_test: OpsTest) -> Dict:
    secrets = await ops_test.model.list_secrets({"label": "password"})
    if not secrets:
        password = await ops_test.model.add_secret("password", ["password=secret"])
    else:
        password = secrets[0].uri
    # await ops_test.model.grant_secret("password", APP_NAME)

    return {
        "urls": "ldap://ldap.com/path/to/somewhere",
        "base_dn": "dc=glauth,dc=com",
        "starttls": "True",
        "bind_dn": "cn=user,ou=group,dc=glauth,dc=com",
        "bind_password": password,
        "auth_method": "simple",
    }


@asynccontextmanager
async def remove_integration(
    ops_test: OpsTest, remote_app_name: str, integration_name: str
) -> AsyncGenerator[None, None]:
    remove_integration_cmd = (
        f"remove-relation {APP_NAME}:{integration_name} {remote_app_name}"
    ).split()
    await ops_test.juju(*remove_integration_cmd)
    await ops_test.model.wait_for_idle(
        apps=[remote_app_name],
        status="active",
    )

    try:
        yield
    finally:
        await ops_test.model.integrate(f"{APP_NAME}:{integration_name}", remote_app_name)
        await ops_test.model.wait_for_idle(
            apps=[APP_NAME, remote_app_name],
            status="active",
        )
