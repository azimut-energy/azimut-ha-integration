"""Config flow for Azimut Energy integration."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_SERIAL, DOMAIN, MQTT_PORT, MQTT_USE_TLS
from .mqtt_client import AzimutMQTTClient

_LOGGER = logging.getLogger(__name__)

# Schema for manual configuration (host + serial only, port is always 8883)
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_SERIAL): str,
    }
)


def _extract_serial_from_name(name: str) -> str | None:
    """Extract serial number from mDNS name like 'azen-504589'."""
    # Match patterns like "azen-504589" or "Zephyr Azimut Broker on azen-504589"
    match = re.search(r"azen-(\d+)", name.lower())
    if match:
        return match.group(1)
    return None


class AzimutConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Azimut Energy."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_host: str | None = None
        self._discovered_serial: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return AzimutOptionsFlow()

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle zeroconf discovery."""
        _LOGGER.debug("Zeroconf discovery: %s", discovery_info)

        # Extract host from discovery
        self._discovered_host = str(discovery_info.host)

        # Extract serial from the name (e.g., "Zephyr Azimut Broker on azen-504589")
        self._discovered_serial = _extract_serial_from_name(discovery_info.name)

        if not self._discovered_serial:
            # Try properties
            self._discovered_serial = discovery_info.properties.get("serial")

        if not self._discovered_serial:
            _LOGGER.warning(
                "Could not extract serial from zeroconf discovery: %s",
                discovery_info.name,
            )
            return self.async_abort(reason="no_serial")

        # Set unique ID to prevent duplicate discoveries
        await self.async_set_unique_id(f"azimut_energy_{self._discovered_serial}")
        self._abort_if_unique_id_configured(updates={CONF_HOST: self._discovered_host})

        # Set the title for the discovery notification
        self.context["title_placeholders"] = {
            "name": f"Azimut Battery {self._discovered_serial}",
            "serial": self._discovered_serial,
            "host": self._discovered_host,
        }

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm zeroconf discovery."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate MQTT connection
            try:
                client = AzimutMQTTClient(
                    host=self._discovered_host,
                    port=MQTT_PORT,
                    serial=self._discovered_serial,
                    use_tls=MQTT_USE_TLS,
                )

                if not await client.connect():
                    errors["base"] = "cannot_connect"
                else:
                    await client.disconnect()
                    return self.async_create_entry(
                        title=f"Azimut Battery {self._discovered_serial}",
                        data={
                            CONF_HOST: self._discovered_host,
                            CONF_SERIAL: self._discovered_serial,
                        },
                    )

            except Exception as err:
                _LOGGER.exception("Failed to validate MQTT connection: %s", err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="zeroconf_confirm",
            description_placeholders={
                "serial": self._discovered_serial,
                "host": self._discovered_host,
            },
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            serial = user_input[CONF_SERIAL]
            host = user_input[CONF_HOST]

            # Set unique ID based on serial to prevent duplicates
            await self.async_set_unique_id(f"azimut_energy_{serial}")
            self._abort_if_unique_id_configured()

            # Validate MQTT connection
            try:
                client = AzimutMQTTClient(
                    host=host,
                    port=MQTT_PORT,
                    serial=serial,
                    use_tls=MQTT_USE_TLS,
                )

                if not await client.connect():
                    errors["base"] = "cannot_connect"
                else:
                    await client.disconnect()
                    return self.async_create_entry(
                        title=f"Azimut Battery {serial}",
                        data={
                            CONF_HOST: host,
                            CONF_SERIAL: serial,
                        },
                    )

            except Exception as err:
                _LOGGER.exception("Failed to validate MQTT connection: %s", err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration."""
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if entry is None:
            return self.async_abort(reason="reconfigure_failed")

        if user_input is not None:
            # Validate MQTT connection with new settings
            try:
                client = AzimutMQTTClient(
                    host=user_input[CONF_HOST],
                    port=MQTT_PORT,
                    serial=entry.data[CONF_SERIAL],
                    use_tls=MQTT_USE_TLS,
                )

                if not await client.connect():
                    errors["base"] = "cannot_connect"
                else:
                    await client.disconnect()
                    return self.async_update_reload_and_abort(
                        entry,
                        data={
                            CONF_HOST: user_input[CONF_HOST],
                            CONF_SERIAL: entry.data[CONF_SERIAL],
                        },
                    )

            except Exception as err:
                _LOGGER.exception("Failed to validate MQTT connection: %s", err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=entry.data.get(CONF_HOST, "")): str,
                }
            ),
            errors=errors,
            description_placeholders={"serial": entry.data.get(CONF_SERIAL, "")},
        )


class AzimutOptionsFlow(OptionsFlow):
    """Handle options flow for Azimut Energy."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate MQTT connection with new settings
            try:
                client = AzimutMQTTClient(
                    host=user_input[CONF_HOST],
                    port=MQTT_PORT,
                    serial=self.config_entry.data[CONF_SERIAL],
                    use_tls=MQTT_USE_TLS,
                )

                if not await client.connect():
                    errors["base"] = "cannot_connect"
                else:
                    await client.disconnect()
                    # Update the config entry
                    self.hass.config_entries.async_update_entry(
                        self.config_entry,
                        data={
                            CONF_HOST: user_input[CONF_HOST],
                            CONF_SERIAL: self.config_entry.data[CONF_SERIAL],
                        },
                    )
                    return self.async_create_entry(title="", data={})

            except Exception as err:
                _LOGGER.exception("Failed to validate MQTT connection: %s", err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST,
                        default=self.config_entry.data.get(CONF_HOST, ""),
                    ): str,
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
