from homeassistant.const import Platform

DOMAIN = "hacs_flight_aware_intergration"

PLATFORMS = [
    "sensor",
    "input_text"
]

DEFAULT_SCAN_INTERVAL = 300 # 5 minutes in seconds
