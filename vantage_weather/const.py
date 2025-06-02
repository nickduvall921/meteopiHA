"""Constants for the Vantage Weather integration."""

from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    UnitOfSpeed,
    UnitOfPressure,
    UnitOfPrecipitationDepth,
    DEGREE,
    UnitOfVolumetricFlux,
    UnitOfIrradiance, # Added for Solar Radiation
)
# SensorDeviceClass and SensorStateClass are typically imported in sensor.py
# where they are instantiated. Here, we'll store their string representations
# as per common practice in const.py for defining sensor types.

DOMAIN = "vantage_weather"
DEFAULT_NAME = "Vantage Weather" # Default name for the integration instance
DEFAULT_SCAN_INTERVAL = 60 # Default polling interval in seconds
CONF_HOST = "host" # Key for host in config entry
CONF_NAME = "name" # Key for user-defined name in config entry

# SENSOR_TYPES:
# "json_key_from_rtd": (
#     "Name Suffix for Entity",
#     "json_key_from_rtd", # This is the key used to fetch data from coordinator.data.rtd
#     HA_unit_constant_or_fixed_string, # e.g., UnitOfTemperature.FAHRENHEIT, PERCENTAGE, DEGREE, None
#     "device_class_string",            # e.g., "temperature", "humidity", None. Will be converted to Enum in sensor.py.
#     "state_class_string",             # e.g., "measurement", "total_increasing", None. Will be converted to Enum in sensor.py.
#     "icon_override"                   # e.g., "mdi:thermometer", None
# )

SENSOR_TYPES = {
    # Temperature & Humidity (Base unit: Fahrenheit for Temps, % for Humidity)
    "tempin": ("Inside Temperature", "tempin", UnitOfTemperature.FAHRENHEIT, "temperature", "measurement", "mdi:home-thermometer"),
    "tempout": ("Outside Temperature", "tempout", UnitOfTemperature.FAHRENHEIT, "temperature", "measurement", None),
    "heat": ("Heat Index", "heat", UnitOfTemperature.FAHRENHEIT, "temperature", "measurement", None),
    "chill": ("Wind Chill", "chill", UnitOfTemperature.FAHRENHEIT, "temperature", "measurement", None),
    "humin": ("Inside Humidity", "humin", PERCENTAGE, "humidity", "measurement", "mdi:water-percent"),
    "humout": ("Outside Humidity", "humout", PERCENTAGE, "humidity", "measurement", None), # Assuming humidity is always %
    "cdew": ("Dew Point", "cdew", UnitOfTemperature.FAHRENHEIT, "temperature", "measurement", None),

    # Wind (Base unit: mph for Speed, Degrees for Direction)
    "windspd": ("Current Wind Speed", "windspd", UnitOfSpeed.MILES_PER_HOUR, "wind_speed", "measurement", "mdi:weather-windy"),
    "winddir": ("Current Wind Direction", "winddir", DEGREE, None, "measurement", "mdi:compass-outline"), # Wind direction is unitless in HA, but has °
    "windavg2": ("2 Min Avg Wind Speed", "windavg2", UnitOfSpeed.MILES_PER_HOUR, "wind_speed", "measurement", "mdi:weather-windy"),
    "windavg10": ("10 Min Avg Wind Speed", "windavg10", UnitOfSpeed.MILES_PER_HOUR, "wind_speed", "measurement", "mdi:weather-windy"),
    "gust": ("10 Min Wind Gust", "gust", UnitOfSpeed.MILES_PER_HOUR, "wind_speed", "measurement", "mdi:weather-windy-variant"),
    "gustdir": ("Wind Gust Direction", "gustdir", DEGREE, None, "measurement", "mdi:compass-outline"),

    # Barometer (Base unit: inHg)
    "bar": ("Barometer", "bar", UnitOfPressure.INHG, "pressure", "measurement", "mdi:gauge"),

    # Rain (Base unit: Inches for accumulation)
    # Rain Rate unit is None here; it will be derived in sensor.py (e.g., to in/hr)
    "rainr": ("Rain Rate", "rainr", None, "precipitation_intensity", "measurement", "mdi:weather-pouring"),
    "raind": ("Rain Daily", "raind", UnitOfPrecipitationDepth.INCHES, "precipitation", "total_increasing", "mdi:weather-rainy"),
    "storm": ("Rain Storm", "storm", UnitOfPrecipitationDepth.INCHES, "precipitation", "total_increasing", "mdi:weather-lightning-rainy"),
    "rainmon": ("Rain Month", "rainmon", UnitOfPrecipitationDepth.INCHES, "precipitation", "total_increasing", "mdi:calendar-month"),
    "rainyear": ("Rain Year", "rainyear", UnitOfPrecipitationDepth.INCHES, "precipitation", "total_increasing", "mdi:calendar-star"),
    "rain1h": ("Rain 1 Hour", "rain1h", UnitOfPrecipitationDepth.INCHES, "precipitation", "total", "mdi:clock-time-one-outline"), # Total over the last hour
    "rain24": ("Rain 24 Hour", "rain24", UnitOfPrecipitationDepth.INCHES, "precipitation", "total", "mdi:clock-time-twelve-outline"), # Total over the last 24 hours

    # Solar & UV (Base units: W/m² for Solar, unitless Index for UV)
    "solar": ("Solar Radiation", "solar", UnitOfIrradiance.WATTS_PER_SQUARE_METER, "irradiance", "measurement", "mdi:solar-power"),
    "uv": ("UV Index", "uv", None, None, "measurement", "mdi:sun-wireless-outline"), # UV Index is unitless
}

# Keys for special sensors not defined in the SENSOR_TYPES loop
SENSOR_KEY_LAST_UPDATE = "last_update" # For the "Last Update" timestamp sensor
SENSOR_KEY_BARO_TREND = "baro_trend"  # For the barometer trend (textual value, no unit)

# Keys from the 'info' part of the JSON (still useful for device info display in HA)
DEVICE_FIRMWARE_VER_KEY = "ver"       # Firmware version
DEVICE_MODEL_KEY = "stnmod"           # Station model code
DEVICE_STATION_NAME_KEY = "stnname"   # Station name from device config
DEVICE_WIFI_LOGGER_ID_KEY = "wid"     # WiFi Logger ID

# Keys for device's configured display units (from 'info' part of JSON).
# These are mainly for the coordinator to log or for potential future UI features,
# as the sensor entities will now rely on the fixed base units defined above.
DEVICE_UNIT_TEMP = "unitT"        # e.g., 'C' or 'F' (device display unit)
DEVICE_UNIT_WIND = "unitW"        # e.g., 'km/h', 'mph', 'm/s' (device display unit)
DEVICE_UNIT_PRESSURE = "unitB"    # e.g., 'in' (implies inHg), 'hPa', 'mb' (device display unit)
DEVICE_UNIT_RAIN = "unitR"        # e.g., 'in', 'mm' (device display unit)
