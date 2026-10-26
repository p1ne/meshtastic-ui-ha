"""Tests for Meshtastic UI config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.meshtastic_ui.const import (
    CONF_CONNECTION_TYPE,
    CONF_SERIAL_DEV_PATH,
    CONF_TCP_HOSTNAME,
    CONF_TCP_PORT,
    DEFAULT_TCP_PORT,
    DOMAIN,
)


async def test_user_step_shows_form(hass: HomeAssistant):
    """Test the initial user step shows connection type selector."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_tcp_step_success(hass: HomeAssistant):
    """Test TCP step with valid input creates config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.meshtastic_ui.config_flow.MeshtasticUiConfigFlow._test_tcp_connection",
        return_value="!aabbccdd",
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "tcp"},
        )
        assert result["step_id"] == "tcp"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TCP_HOSTNAME: "192.168.1.100", CONF_TCP_PORT: DEFAULT_TCP_PORT},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_CONNECTION_TYPE] == "tcp"
        assert result["data"][CONF_TCP_HOSTNAME] == "192.168.1.100"
        assert result["data"][CONF_TCP_PORT] == DEFAULT_TCP_PORT


async def test_tcp_step_failure(hass: HomeAssistant):
    """Test TCP step shows error on connection failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.meshtastic_ui.config_flow.MeshtasticUiConfigFlow._test_tcp_connection",
        side_effect=Exception("Connection refused"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "tcp"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TCP_HOSTNAME: "192.168.1.100", CONF_TCP_PORT: DEFAULT_TCP_PORT},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"


async def test_serial_step_success(hass: HomeAssistant):
    """Test serial step with valid input creates config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.meshtastic_ui.config_flow.MeshtasticUiConfigFlow._test_serial_connection"
        ),
        patch(
            "custom_components.meshtastic_ui.config_flow.MeshtasticUiConfigFlow._find_serial_ports",
            return_value=["/dev/ttyUSB0"],
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "serial"},
        )
        assert result["step_id"] == "serial"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_SERIAL_DEV_PATH: "/dev/ttyUSB0"},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_CONNECTION_TYPE] == "serial"
        assert result["data"][CONF_SERIAL_DEV_PATH] == "/dev/ttyUSB0"


async def test_serial_step_failure(hass: HomeAssistant):
    """Test serial step shows error on connection failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with (
        patch(
            "custom_components.meshtastic_ui.config_flow.MeshtasticUiConfigFlow._test_serial_connection",
            side_effect=Exception("Device not found"),
        ),
        patch(
            "custom_components.meshtastic_ui.config_flow.MeshtasticUiConfigFlow._find_serial_ports",
            return_value=[],
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "serial"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_SERIAL_DEV_PATH: "/dev/ttyUSB0"},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"


async def test_duplicate_tcp_aborts(hass: HomeAssistant):
    """Test adding the same TCP host twice aborts as already_configured."""
    with patch(
        "custom_components.meshtastic_ui.config_flow.MeshtasticUiConfigFlow._test_tcp_connection",
        return_value="!aabbccdd",
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "tcp"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TCP_HOSTNAME: "192.168.1.100", CONF_TCP_PORT: DEFAULT_TCP_PORT},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY

        result2 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {CONF_CONNECTION_TYPE: "tcp"},
        )
        result2 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {CONF_TCP_HOSTNAME: "192.168.1.100", CONF_TCP_PORT: DEFAULT_TCP_PORT},
        )
        assert result2["type"] is FlowResultType.ABORT
        assert result2["reason"] == "already_configured"


async def test_tcp_entry_keyed_on_node_id(hass: HomeAssistant):
    """Test a TCP entry's unique_id is the radio's node ID, not its IP."""
    with patch(
        "custom_components.meshtastic_ui.config_flow.MeshtasticUiConfigFlow._test_tcp_connection",
        return_value="!aabbccdd",
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "tcp"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TCP_HOSTNAME: "192.168.1.100", CONF_TCP_PORT: DEFAULT_TCP_PORT},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.unique_id == "!aabbccdd"


async def test_readd_after_ip_change_updates_host(hass: HomeAssistant):
    """Test re-adding the same radio at a new IP updates the existing entry."""
    with patch(
        "custom_components.meshtastic_ui.config_flow.MeshtasticUiConfigFlow._test_tcp_connection",
        return_value="!aabbccdd",
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "tcp"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TCP_HOSTNAME: "192.168.1.100", CONF_TCP_PORT: DEFAULT_TCP_PORT},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY

        # Same radio, new DHCP address.
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {CONF_CONNECTION_TYPE: "tcp"},
        )
        result2 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {CONF_TCP_HOSTNAME: "192.168.1.200", CONF_TCP_PORT: DEFAULT_TCP_PORT},
        )
        assert result2["type"] is FlowResultType.ABORT
        assert result2["reason"] == "already_configured"

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.data[CONF_TCP_HOSTNAME] == "192.168.1.200"


async def test_zeroconf_rediscovery_updates_host(hass: HomeAssistant):
    """Test zeroconf discovery at a new IP updates the existing entry's host."""
    from ipaddress import ip_address

    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

    with patch(
        "custom_components.meshtastic_ui.config_flow.MeshtasticUiConfigFlow._test_tcp_connection",
        return_value="!aabbccdd",
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_CONNECTION_TYPE: "tcp"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TCP_HOSTNAME: "192.168.1.100", CONF_TCP_PORT: DEFAULT_TCP_PORT},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY

    discovery = ZeroconfServiceInfo(
        ip_address=ip_address("192.168.1.200"),
        ip_addresses=[ip_address("192.168.1.200")],
        hostname="meshtastic-ccdd.local.",
        name="Meshtastic-ccdd._meshtastic._tcp.local.",
        port=DEFAULT_TCP_PORT,
        properties={"id": "!aabbccdd", "shortname": "CCDD"},
        type="_meshtastic._tcp.local.",
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.data[CONF_TCP_HOSTNAME] == "192.168.1.200"


# --- Meshtastic integration TCP proxy -------------------------------------

_PATCH_TCP = (
    "custom_components.meshtastic_ui.config_flow.MeshtasticUiConfigFlow._test_tcp_connection"
)


def _add_meshtastic_entry(hass: HomeAssistant, *, host: str, proxy: bool, port: int = 4403):
    """Add a config entry of the Meshtastic integration (domain "meshtastic")."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain="meshtastic",
        title="MiFi3860",
        unique_id="2410035296",
        data={"connection_type": "tcp", "tcp_host": host, "tcp_port": 4403},
        options={"tcp_proxy": {"enable": proxy, "port": port}},
    )
    entry.add_to_hass(hass)
    return entry


def _zeroconf(host: str, node_id: str = "!aabbccdd"):
    from ipaddress import ip_address

    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

    return ZeroconfServiceInfo(
        ip_address=ip_address(host),
        ip_addresses=[ip_address(host)],
        hostname="meshtastic-ccdd.local.",
        name="Meshtastic-ccdd._meshtastic._tcp.local.",
        port=DEFAULT_TCP_PORT,
        properties={"id": node_id},
        type="_meshtastic._tcp.local.",
    )


_PROXY_DISCOVERY = {"host": "127.0.0.1", "port": 4403, "name": "MiFi3860", "node_id": "!AABBCCDD"}


async def test_integration_discovery_proxy_creates_entry(hass: HomeAssistant):
    """A proxy announced by the Meshtastic integration is offered and set up."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data=_PROXY_DISCOVERY,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "proxy_confirm"
    assert result["description_placeholders"]["host"] == "127.0.0.1"

    with patch(_PATCH_TCP, return_value="!aabbccdd") as test_tcp:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    test_tcp.assert_called_once_with("127.0.0.1", 4403)
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Meshtastic (MiFi3860 via proxy)"
    assert result["data"] == {
        CONF_CONNECTION_TYPE: "tcp",
        CONF_TCP_HOSTNAME: "127.0.0.1",
        CONF_TCP_PORT: 4403,
    }
    assert result["result"].unique_id == "!aabbccdd"


async def test_integration_discovery_switches_direct_entry_to_proxy(hass: HomeAssistant):
    """An entry connected directly to the radio is moved to the proxy."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="!aabbccdd",
        data={CONF_CONNECTION_TYPE: "tcp", CONF_TCP_HOSTNAME: "192.168.1.66", CONF_TCP_PORT: 4403},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data=_PROXY_DISCOVERY,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_TCP_HOSTNAME] == "127.0.0.1"


async def test_integration_discovery_already_on_proxy_address(hass: HomeAssistant):
    """An entry already pointing at the proxy address is not offered again."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    MockConfigEntry(
        domain=DOMAIN,
        unique_id="tcp:127.0.0.1",
        data={CONF_CONNECTION_TYPE: "tcp", CONF_TCP_HOSTNAME: "127.0.0.1", CONF_TCP_PORT: 4403},
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data=_PROXY_DISCOVERY,
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_zeroconf_radio_served_by_proxy_is_not_offered(hass: HomeAssistant):
    """mDNS discovery of a radio the Meshtastic integration proxies is suppressed."""
    _add_meshtastic_entry(hass, host="192.168.1.66", proxy=True)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_zeroconf("192.168.1.66"),
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "served_by_meshtastic_proxy"


async def test_zeroconf_radio_without_proxy_is_offered(hass: HomeAssistant):
    """Without the proxy enabled (or for another radio) direct discovery still works."""
    _add_meshtastic_entry(hass, host="192.168.1.66", proxy=False)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_zeroconf("192.168.1.66"),
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=_zeroconf("192.168.1.77", node_id="!11223344"),
    )
    assert result["type"] is FlowResultType.FORM
