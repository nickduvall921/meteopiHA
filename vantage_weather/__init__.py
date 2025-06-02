"""The Vantage Weather integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform, CONF_HOST, CONF_SCAN_INTERVAL

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    CONF_NAME,
    DEFAULT_NAME  # Added DEFAULT_NAME to the import
)
from .coordinator import VantageWeatherDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vantage Weather from a config entry."""
    host = entry.data[CONF_HOST]
    # Now DEFAULT_NAME will be found because it's imported
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    coordinator = VantageWeatherDataUpdateCoordinator(
        hass,
        host=host,
        name=name,  # Pass the resolved name to the coordinator
        update_interval=scan_interval
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up options listener to allow runtime changes to scan_interval
    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def options_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle options update."""
    # This is called when options are updated via the UI.
    # We reload the config entry to apply the new options (e.g., scan_interval).
    _LOGGER.debug("Options updated, reloading entry %s", config_entry.entry_id)
    await hass.config_entries.async_reload(config_entry.entry_id)

