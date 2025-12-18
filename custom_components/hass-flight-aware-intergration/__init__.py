# __init__.py

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .sensor import FlightAwareDataUpdateCoordinator, FlightAwarePredictedArrivalSensor
# from .sensor import FlightAwareDataUpdateCoordinator, FlightAwarePredictedArrivalSensor, FlightAwarePredictedFlightInput

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FlightAware Tracker from a config entry."""
    # Store the Config Entry object so other platforms can access data/options
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry

    # Set up all platforms (in this case, just 'sensor')
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload integration when options are updated
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms first
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
