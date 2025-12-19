# sensor.py

import logging
from datetime import timedelta, datetime, timezone
import requests

from homeassistant.components.sensor import SensorEntity
from homeassistant.components.text import TextEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, CoordinatorEntity
from homeassistant.const import CONF_API_KEY, CONF_SCAN_INTERVAL
from homeassistant.helpers.entity import DeviceInfo

from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.core import Event, EventStateChangedData, callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

FLIGHT_NUMBER_INPUT = "text.flight_number_to_track"

# --- Data Fetching Class (Centralized Logic) ---
class FlightAwareDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from FlightAware API."""

    def __init__(self, hass, api_key):
        """Initialize the coordinator."""
        self.hass = hass
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
        # This function runs on the polling interval or when the flight number is updated
        flight_entity = self.hass.states.get(FLIGHT_NUMBER_INPUT)
        
        if flight_entity is None:
            _LOGGER.warning(f"Input text entity '{FLIGHT_NUMBER_INPUT}' not found")
            return UpdateFailed(f"Input text entity '{FLIGHT_NUMBER_INPUT}' not found") # Or raise UpdateFailed
        
        flight_number = flight_entity.state
        
        if not flight_number or flight_number in ["unknown", "unavailable"]:
            _LOGGER.debug("Flight number is empty or unavailable")
            return UpdateFailed("Flight number is empty or unavailable")
        
        if not flight_number:
            raise UpdateFailed("Flight number input is empty.")

        url = f"https://aeroapi.flightaware.com/aeroapi/flights/{flight_number}"
        headers = {"x-apikey": self._api_key}

        try:
            response = await self.hass.async_add_executor_job(
                lambda: requests.get(url, headers=headers)
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as err:
            raise UpdateFailed(f"Error fetching data from FlightAware API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Got exception: {err}") from err

        predicted_arrival = None
        arrival_airport = None
        departing_airport = None
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=60)
        if data.get('flights'):
            for flight in data.get('flights'):
                if not 'estimated_in' in flight.keys():
                    continue
                dt = datetime.fromisoformat(flight['estimated_in'])
                if dt < cutoff:
                    continue
                if predicted_arrival == None or dt < predicted_arrival:
                    predicted_arrival = dt
                    if flight.get('destination') and flight.get('destination').get('code_iata'):
                        arrival_airport = flight['destination']['code_iata']
                    if flight.get('origin') and flight.get('origin').get('code_iata'):
                        arrival_airport = flight['origin']['code_iata']

            self.flight_data = {
                "predicted_arrival": predicted_arrival,
                "departing_airport": departing_airport,
                "arrival_airport": arrival_airport
            }
            return self.flight_data
        else:
            raise UpdateFailed("Predicted arrival time not found in response.")
        

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

    async_add_entities([
        # flight_input,
        FlightAwareArrivalAirportSensor(coordinator),
        FlightAwareDepartingAirportSensor(coordinator),
        FlightAwarePredictedArrivalSensor(coordinator)
    ], True)

# --- Sensor Entity ---
class FlightAwarePredictedArrivalSensor(CoordinatorEntity, SensorEntity):
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
        if self.coordinator.flight_data is None:
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
        self.async_on_remove(async_track_state_change_event(self.coordinator.hass, [FLIGHT_NUMBER_INPUT], self._async_on_change))
    
    @callback
    def _async_on_change(self, event: Event[EventStateChangedData]) -> None:
        self.async_schedule_update_ha_state(True)
        
    async def async_update(self):
        """Update the entity's data from the coordinator."""
        await self.coordinator.async_request_refresh()

# --- Sensor Entity ---
class FlightAwareArrivalAirportSensor(CoordinatorEntity, SensorEntity):
    """Representation of a FlightAware Arrival Time sensor."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_name = "Flight Arrival Airport"
        self._attr_unique_id = f"flightaware_arrival_airport_{coordinator.config_entry.entry_id}"
        self._attr_icon = "mdi:airplane-landing"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # 1. Check if coordinator data exists at all
        if self.coordinator.flight_data is None:
            return "unavailable"
    
        # 2. Safely get the value
        return self.coordinator.flight_data.get("arrival_airport")
    
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
        self.async_on_remove(async_track_state_change_event(self.coordinator.hass, [FLIGHT_NUMBER_INPUT], self._async_on_change))
    
    @callback
    def _async_on_change(self, event: Event[EventStateChangedData]) -> None:
        self.async_schedule_update_ha_state(True)
        
    async def async_update(self):
        """Update the entity's data from the coordinator."""
        await self.coordinator.async_request_refresh()


# --- Sensor Entity ---
class FlightAwareDepartingAirportSensor(CoordinatorEntity, SensorEntity):
    """Representation of a FlightAware Depature Airport sensor."""

    def __init__(self, coordinator):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._attr_name = "Flight Departing Airport"
        self._attr_unique_id = f"flightaware_departing_airport_{coordinator.config_entry.entry_id}"
        self._attr_icon = "mdi:airplane-takeoff"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        # 1. Check if coordinator data exists at all
        if self.coordinator.flight_data is None:
            return "unavailable"
    
        # 2. Safely get the value
        return self.coordinator.flight_data.get("departing_airport")
    
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
        self.async_on_remove(async_track_state_change_event(self.coordinator.hass, [FLIGHT_NUMBER_INPUT], self._async_on_change))
    
    @callback
    def _async_on_change(self, event: Event[EventStateChangedData]) -> None:
        self.async_schedule_update_ha_state(True)
        
    async def async_update(self):
        """Update the entity's data from the coordinator."""
        await self.coordinator.async_request_refresh()
