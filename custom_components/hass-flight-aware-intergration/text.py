from homeassistant.components.text import TextEntity

# --- Platform Setup ---
async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the input_text platform."""
  
    async_add_entities([
        FlightAwarePredictedFlightInput()
    ], True)

class FlightAwarePredictedFlightInput(TextEntity):
    # Implement one of these methods.
    def __init__(self):
        """Initialize the sensor."""
        self._attr_name = "Flight Number To Track"
        self._attr_unique_id = f"flight_number_to_track"
        self._attr_icon = "mdi:airplane-takeoff"
        self._attr_native_value = ""

    async def async_set_value(self, value: str) -> None:
        """Set the text value."""
        self._attr_native_value = value
