from homeassistant.const import Platform

DOMAIN = "hacs_flight_aware_intergration"

PLATFORMS = [
    "text",
    "sensor"
]

DEFAULT_SCAN_INTERVAL = 300 # 5 minutes in seconds
