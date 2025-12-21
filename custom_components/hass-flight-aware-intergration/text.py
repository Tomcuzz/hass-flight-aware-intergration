from homeassistant.components.text import RestoreText

_LOGGER = logging.getLogger(__name__)

# --- Platform Setup ---
async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the input_text platform."""
  
    async_add_entities([
        FlightAwarePredictedFlightInput()
    ], True)

class FlightAwarePredictedFlightInput(RestoreText):
    # Implement one of these methods.
    def __init__(self):
        """Initialize the sensor."""
        self._attr_name = "Flight Number To Track"
        self._attr_unique_id = f"flight_number_to_track"
        self._attr_icon = "mdi:airplane-takeoff"
        self._attr_native_value = ""
    
    def set_value(self, value: str) -> None:
        """Set the text value."""
        self._attr_native_value = value

    async def async_set_value(self, value: str) -> None:
        """Set the text value."""
        self._attr_native_value = value
        
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last_text_data := await self.async_get_last_text_data()) is None:
            return
        _LOGGER.debug("Restored state: %s", last_text_data)
        self._attr_native_max = last_text_data.native_max
        self._attr_native_min = last_text_data.native_min
        self._attr_native_value = last_text_data.native_value
