# sensor.py

import logging
from datetime import timedelta
import requests

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.text import TextEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_API_KEY, CONF_SCAN_INTERVAL
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# --- Data Fetching Class (Centralized Logic) ---
class FlightAwareDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from FlightAware API."""

    def __init__(self, hass, api_key):
        """Initialize the coordinator."""
        self._api_key = api_key
        self.flight_input = ""
        # The update_interval will be set when the sensor is loaded from the Config Entry
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=1), # Temporary default, set by sensor later
        )
        self.flight_data = {}

    async def _async_update_data(self):
        """Fetch data from API."""
        # This function runs on the polling interval
        
        # In a real integration, the flight number would be a user option 
        # on the entity itself, or a service call, but for this simpler 
        # design, we'll keep the input_text dependency as before, 
        # passed into the coordinator on creation or via an update.
        # flight_number = self.hass.states.get("input_text.flight_number_to_track").state

        # flight_entity = self.hass.states.get("input_text.flight_number_to_track")
        
        # if flight_entity is None:
        #     _LOGGER.warning("Input text entity 'input_text.flight_number_to_track' not found")
        #     return UpdateFailed("Input text entity 'input_text.flight_number_to_track' not found") # Or raise UpdateFailed
        
        # flight_number = flight_entity.state
        flight_number = "BA825"
        
        if not flight_number or flight_number in ["unknown", "unavailable"]:
            _LOGGER.debug("Flight number is empty or unavailable")
            return UpdateFailed("Flight number is empty or unavailable")
        
        if not flight_number:
            raise UpdateFailed("Flight number input is empty.")

        url = f"https://aeroapi.flightaware.com/aeroapi/flights/{flight_number}"
        headers = {"x-apikey": self._api_key}

        try:
            # Use hass.async_add_executor_job for blocking network calls
            # response = await self.hass.async_add_executor_job(
            #     requests.get, url, headers=headers, timeout=10
            # )
            response = await self.hass.async_add_executor_job(
                lambda: requests.get(url, headers=headers, timeout=10)
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as err:
            raise UpdateFailed(f"Error fetching data from FlightAware API: {err}") from err

        predicted_arrival = None
        if data.get('flights'):
            flight_info = data['flights'][0]
            # Assumed key for demonstration
            predicted_arrival = flight_info.get('estimated_arrival_time') 

        if predicted_arrival:
            # Store the data
            self.flight_data = {"predicted_arrival": predicted_arrival}
            return self.flight_data
        else:
            raise UpdateFailed("Predicted arrival time not found in response.")


class FlightAwarePredictedFlightInput(TextEntity):
    # Implement one of these methods.
    def __init__(self, coordinator):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_name = "Predicted Flight Arrival Time"
        self._attr_unique_id = f"flightaware_flight_number_{coordinator.config_entry.entry_id}"
        self.unique_id = self._attr_unique_id
        self._attr_icon = "mdi:airplane-takeoff"

    async def async_set_value(self, value: str) -> None:
        """Set the text value."""
        

# --- Platform Setup ---
async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform."""
    
    # Get the configuration data from the Config Entry
    api_key = entry.data[CONF_API_KEY]
    # Get the polling interval from options (or use the initial default if not changed)
    interval_seconds = entry.options.get(CONF_SCAN_INTERVAL, 300) 
    
    # Create the coordinator and set the user-defined polling interval
    coordinator = FlightAwareDataUpdateCoordinator(hass, api_key)
    coordinator.update_interval = timedelta(seconds=interval_seconds)
    
    flight_intput = FlightAwarePredictedFlightInput(coordinator)
    coordinator.flight_input = flight_intput.unique_id

    # Initial fetch
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([
        FlightAwarePredictedArrivalSensor(coordinator)
    ], True)

# --- Sensor Entity ---
class FlightAwarePredictedArrivalSensor(SensorEntity):
    """Representation of a FlightAware Predicted Arrival Time sensor."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_name = "Predicted Flight Arrival Time"
        self._attr_unique_id = f"flightaware_predicted_arrival_{coordinator.config_entry.entry_id}"
        self._attr_icon = "mdi:airplane-landing"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # 1. Check if coordinator data exists at all
        if self.coordinator.data is None:
            return "unavailable"
    
        # 2. Safely get the value
        return self.coordinator.flight_data.get("predicted_arrival")
    
    @property
    def should_poll(self):
        """Return True if entity should be polled. Using coordinator, so False."""
        return False

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))
        
    async def async_update(self):
        """Update the entity's data from the coordinator."""
        await self.coordinator.async_request_refresh()
