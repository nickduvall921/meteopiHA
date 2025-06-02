"""Config flow for Vantage Weather integration."""
import logging
import voluptuous as vol
import aiohttp
import async_timeout

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    CONF_NAME,
    DEVICE_STATION_NAME_KEY,
    DEVICE_WIFI_LOGGER_ID_KEY,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA_USER = vol.Schema({
    vol.Required(CONF_HOST): str,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
})

async def validate_host_connection(host: str, hass) -> dict:
    """
    Validate the user input allows us to connect to the device
    and retrieve basic information.
    Returns a dictionary with 'title' and 'unique_id' for the device.
    Raises ConnectionError on failure.
    """
    api_url = f"http://{host}/webrtd.json"
    session = async_get_clientsession(hass)
    device_info = {}
    headers = { # Add headers to try and prevent caching on the device side
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Expires': '0',
    }

    try:
        _LOGGER.debug("Attempting to connect to %s", api_url)
        async with async_timeout.timeout(10): # 10-second timeout for the connection attempt
            async with session.get(api_url, headers=headers) as response:
                response.raise_for_status() # Raises an exception for 4XX/5XX errors
                data = await response.json()
                _LOGGER.debug("Successfully connected and received data: %s", data)

                info_data = data.get("info", {})
                unique_id_val = info_data.get(DEVICE_WIFI_LOGGER_ID_KEY)
                if unique_id_val:
                    device_info["unique_id"] = str(unique_id_val)
                else:
                    device_info["unique_id"] = f"vantage_weather_{host}"
                    _LOGGER.warning("WID not found in device info, using host for unique_id: %s", device_info["unique_id"])

                title_val = info_data.get(DEVICE_STATION_NAME_KEY)
                if title_val:
                    device_info["title"] = str(title_val)
                else:
                    device_info["title"] = host
                    _LOGGER.debug("Station name not found, using host for title: %s", host)

                return device_info
    except (aiohttp.ClientConnectorError, TimeoutError) as ex:
        _LOGGER.error("Failed to connect to %s: %s", api_url, ex)
        raise ConnectionError(f"Cannot connect to device at {host}. Ensure it's reachable and the IP is correct.")
    except aiohttp.ClientResponseError as ex:
        _LOGGER.error("HTTP error connecting to %s: %s (status: %s)", api_url, ex.message, ex.status)
        raise ConnectionError(f"HTTP error: {ex.message} (status: {ex.status}). Check device logs if possible.")
    except aiohttp.ContentTypeError as ex:
        _LOGGER.error("Invalid content type received from %s: %s. Expected JSON.", api_url, ex)
        raise ConnectionError(f"Device returned non-JSON data. Content type: {ex.actual_content_type}")
    except Exception as ex: # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception validating host %s: %s", api_url, ex)
        raise ConnectionError(f"An unexpected error occurred: {ex}")


class VantageWeatherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vantage Weather."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step where the user provides connection details."""
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            name = user_input.get(CONF_NAME, DEFAULT_NAME)

            try:
                device_info = await validate_host_connection(host, self.hass)

                await self.async_set_unique_id(device_info["unique_id"])
                self._abort_if_unique_id_configured()

                entry_title = device_info.get("title", name)

                return self.async_create_entry(
                    title=entry_title,
                    data={
                        CONF_HOST: host,
                        CONF_NAME: name,
                    }
                )
            except ConnectionError: # Error message is set by validate_host_connection for specifics
                errors["base"] = "cannot_connect"
                _LOGGER.debug("Connection error during user step")
            except config_entries.AbortFlow as e:
                _LOGGER.debug("Aborting flow: %s", e.reason)
                return self.async_abort(reason=e.reason)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in user step")
                errors["base"] = "unknown"

        # Show the form to the user
        return self.async_show_form( # Corrected: async_show_form
            step_id="user",
            data_schema=DATA_SCHEMA_USER,
            errors=errors,
            description_placeholders={"docs_url": "https://www.home-assistant.io/integrations/http/"}
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return VantageWeatherOptionsFlowHandler(config_entry)


class VantageWeatherOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Vantage Weather options."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options for the integration."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema({
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10,
                    max=3600,
                    step=1,
                    mode=selector.NumberSelectorMode.SLIDER,
                    unit_of_measurement="seconds",
                )
            ),
            # **Future Enhancement: Entity Selection**
            # from .const import SENSOR_TYPES
            # for sensor_key, (name_suffix, _, _, _, _, _) in SENSOR_TYPES.items():
            #     options_schema = options_schema.extend({
            #         vol.Optional(
            #             f"enable_{sensor_key}",
            #             default=self.config_entry.options.get(f"enable_{sensor_key}", True)
            #         ): bool,
            #     })
        })

        return self.async_show_form( # Corrected: async_show_form
            step_id="init",
            data_schema=options_schema,
            description_placeholders={"device_name": self.config_entry.title}
        )

