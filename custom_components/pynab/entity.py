"""Shared base entity for Nabaztag entities."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DEFAULT_PORT, DOMAIN
from .nabd import NabdClient


class NabaztagEntity:
    """Base class providing device info and connection-based availability."""

    _attr_has_entity_name = True

    def __init__(self, client: NabdClient, entry) -> None:
        self._client = client
        self._attr_available = client.connected
        client.add_connection_listener(self._on_connection)
        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{entry.data.get(CONF_HOST)}:{entry.data.get(CONF_PORT, DEFAULT_PORT)}",
                )
            },
            name="Nabaztag",
            manufacturer="Nabaztag2018",
            model="Pynab",
        )

    @callback
    def _on_connection(self, connected: bool) -> None:
        self._attr_available = connected
        if self.hass is not None:  # not yet added to the state machine
            self.async_write_ha_state()
