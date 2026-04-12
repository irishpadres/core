"""Tests for the Proxmox VE sensor platform with missing data."""

from unittest.mock import MagicMock, patch

import pytest

from homeassistant.components.proxmoxve.const import DOMAIN
from homeassistant.const import STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant

from . import setup_integration

from tests.common import MockConfigEntry, load_json_array_fixture


async def test_sensors_missing_data(
    hass: HomeAssistant,
    mock_proxmox_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test sensors when data is missing from Proxmox API."""
    
    # Mock node data with missing fields
    all_nodes = load_json_array_fixture("nodes/nodes.json", DOMAIN)
    node1 = [n for n in all_nodes if n["node"] == "pve1"][0]
    # Remove some fields from node
    node1_incomplete = {k: v for k, v in node1.items() if k not in ["cpu", "mem", "maxmem", "disk", "maxdisk", "uptime"]}
    mock_proxmox_client.nodes.get.return_value = [node1_incomplete]

    # Mock storage with missing used_fraction and other fields
    storage_data = load_json_array_fixture("nodes/storage.json", DOMAIN)
    storage_incomplete = [
        {k: v for k, v in s.items() if k not in ["used_fraction", "used", "total", "avail"]}
        for s in storage_data
    ]
    # Add a zero-capacity storage pool
    storage_incomplete.append({
        "storage": "zero_pool",
        "total": 0,
        "used": 0,
        "avail": 0,
        "active": 1,
        "enabled": 1,
        "type": "nfs",
    })
    mock_proxmox_client._node_mock.storage.get.return_value = storage_incomplete

    # Malformed backup (missing starttime/endtime but entry exists)
    mock_proxmox_client._node_mock.tasks.get.return_value = [{"upid": "UPID:pve1:00000000:00000000:00000000:vzdump:100:root@pam:"}]

    # Mock VM/Container with missing fields
    qemu_data = load_json_array_fixture("nodes/qemu.json", DOMAIN)
    qemu_incomplete = [
        {k: v for k, v in vm.items() if k not in ["cpu", "mem", "maxmem", "disk", "maxdisk", "uptime", "netin", "netout"]}
        for vm in qemu_data
    ]
    mock_proxmox_client._node_mock.qemu.get.return_value = qemu_incomplete

    lxc_data = load_json_array_fixture("nodes/lxc.json", DOMAIN)
    lxc_incomplete = [
        {k: v for k, v in ct.items() if k not in ["cpu", "mem", "maxmem", "disk", "maxdisk", "uptime", "netin", "netout"]}
        for ct in lxc_data
    ]
    mock_proxmox_client._node_mock.lxc.get.return_value = lxc_incomplete

    with patch(
        "homeassistant.components.proxmoxve.PLATFORMS",
        [Platform.SENSOR],
    ):
        await setup_integration(hass, mock_config_entry)

    # Check that sensors are in unknown state instead of crashing the integration
    # Node sensors (Node CPU usage)
    state = hass.states.get("sensor.pve1")
    assert state.state == STATE_UNKNOWN
    
    # Backup sensors (Node backup last backup)
    state = hass.states.get("sensor.pve1_10")
    assert state.state == STATE_UNKNOWN

    # Storage sensors (Local storage usage percentage)
    state = hass.states.get("sensor.storage_local_4")
    assert state.state == STATE_UNKNOWN
    
    # Zero pool storage (Zero pool used storage)
    state = hass.states.get("sensor.storage_zero_pool")
    assert state.state == "0.0"
    # Zero pool usage percentage
    state = hass.states.get("sensor.storage_zero_pool_4")
    assert state.state == STATE_UNKNOWN

    # VM sensors (VM Web memory percentage)
    state = hass.states.get("sensor.vm_web_5")
    assert state.state == STATE_UNKNOWN

    # Container sensors (CT Nginx memory percentage)
    state = hass.states.get("sensor.ct_nginx_5")
    assert state.state == STATE_UNKNOWN
