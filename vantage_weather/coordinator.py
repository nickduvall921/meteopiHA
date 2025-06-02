"""DataUpdateCoordinator for the Vantage Weather integration."""
import logging
from datetime import timedelta
import async_timeout
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession # Import directly

from .const import (
    DOMAIN,
    DEVICE_UNIT_TEMP,
    DEVICE_UNIT_WIND,
    DEVICE_UNIT_PRESSURE,
    DEVICE_UNIT_RAIN
)

_LOGGER = logging.getLogger(__name__)


class VantageWeatherDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Vantage Weather device."""

    def __init__(self, hass: HomeAssistant, host: str, name: str, update_interval: int):
        """Initialize."""
        self.host = host
        self.api_url = f"http://{self.host}/webrtd.json"
        self.device_name = name

        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(seconds=update_interval),
        )

    @property
    def device_temperature_unit(self) -> str | None:
        """Return the temperature unit reported by the device (e.g., 'C', 'F')."""
        return self.data.get("info", {}).get(DEVICE_UNIT_TEMP) if self.data else None

    @property
    def device_wind_speed_unit(self) -> str | None:
        """Return the wind speed unit reported by the device (e.g., 'km/h', 'mph')."""
        return self.data.get("info", {}).get(DEVICE_UNIT_WIND) if self.data else None

    @property
    def device_pressure_unit(self) -> str | None:
        """Return the pressure unit reported by the device (e.g., 'in', 'hPa')."""
        # The device sends 'in' for likely inHg. Mapping will handle this.
        return self.data.get("info", {}).get(DEVICE_UNIT_PRESSURE) if self.data else None

    @property
    def device_rain_unit(self) -> str | None:
        """Return the rain unit reported by the device (e.g., 'in', 'mm')."""
        return self.data.get("info", {}).get(DEVICE_UNIT_RAIN) if self.data else None


    async def _async_update_data(self):
        """Fetch data from API endpoint."""
        headers = {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Expires': '0',
        }
        try:
            session = async_get_clientsession(self.hass)
            async with async_timeout.timeout(10):
                async with session.get(self.api_url, headers=headers) as response:
                    if response.status == 401:
                        raise ConfigEntryAuthFailed("Authentication failed")
                    response.raise_for_status()
                    data = await response.json()
                    _LOGGER.debug("Successfully fetched data: %s", data) # Already present, good.
                    if "rtd" not in data or "info" not in data:
                        _LOGGER.error("Missing 'rtd' or 'info' in JSON response: %s", data)
                        raise UpdateFailed("Data missing 'rtd' or 'info' keys in response")
                    _LOGGER.debug(
                        "Device reported units: Temp=%s, Wind=%s, Pressure=%s, Rain=%s",
                        data.get("info", {}).get(DEVICE_UNIT_TEMP),
                        data.get("info", {}).get(DEVICE_UNIT_WIND),
                        data.get("info", {}).get(DEVICE_UNIT_PRESSURE),
                        data.get("info", {}).get(DEVICE_UNIT_RAIN),
                    )
                    return data
        except aiohttp.ClientConnectorError as err:
            _LOGGER.error("Error connecting to device at %s: %s", self.api_url, err)
            raise UpdateFailed(f"Error connecting to device: {err}")
        except aiohttp.ClientError as err:
            _LOGGER.error("Client error fetching data from %s: %s", self.api_url, err)
            raise UpdateFailed(f"Error communicating with API: {err}")
        except TimeoutError:
            _LOGGER.error("Timeout fetching data from %s", self.api_url)
            raise UpdateFailed("Timeout fetching data from API")
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching data from %s: %s", self.api_url, err)
            raise UpdateFailed(f"Unexpected error fetching data: {err}")

