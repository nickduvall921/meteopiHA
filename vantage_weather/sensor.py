"""Sensor platform for Vantage Weather."""
import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    UnitOfSpeed,
    UnitOfPressure,
    UnitOfPrecipitationDepth,
    DEGREE,
    UnitOfVolumetricFlux,
    UnitOfIrradiance,
)
from homeassistant.core import callback # Though not used in this version, good practice for HA
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    SENSOR_TYPES,
    SENSOR_KEY_LAST_UPDATE,
    SENSOR_KEY_BARO_TREND,
    DEVICE_FIRMWARE_VER_KEY,
    DEVICE_MODEL_KEY,
)
from .coordinator import VantageWeatherDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# REVISED_UNIT_MAPPING is now minimal, primarily for fixed string units
# that are not direct HA UnitOf... constants, if any are ever needed.
REVISED_UNIT_MAPPING = {
    # Example: if a sensor reported "custom_unit_str" that needed mapping.
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensor platform."""
    coordinator: VantageWeatherDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    _LOGGER.debug("Setting up sensor platform for Vantage Weather: %s", config_entry.title)

    entities = []
    # Log device's display units from coordinator for informational purposes
    if coordinator.last_update_success and coordinator.data and "info" in coordinator.data:
        _LOGGER.info(
            "Coordinator successfully fetched initial data. Device display units (for reference): "
            "Temp=%s, Wind=%s, Pressure=%s, Rain=%s. "
            "Note: HA integration will use fixed base units for sensor data.",
            coordinator.device_temperature_unit,
            coordinator.device_wind_speed_unit,
            coordinator.device_pressure_unit,
            coordinator.device_rain_unit,
        )
    elif coordinator.last_update_success and coordinator.data:
        _LOGGER.warning("Coordinator fetched data, but 'info' key (with device display units) is missing.")
    else:
        _LOGGER.error("Coordinator failed to fetch initial data. Sensor setup may encounter issues.")

    # Create standard sensors based on SENSOR_TYPES
    for sensor_json_key, (name_suffix, _, unit_constant_or_string, device_class_str, state_class_str, icon) in SENSOR_TYPES.items():
        _LOGGER.debug(
            "Creating sensor: key_from_rtd=%s, name_suffix=%s, unit_const/str=%s, device_class_str=%s, state_class_str=%s",
            sensor_json_key, name_suffix, unit_constant_or_string, device_class_str, state_class_str
        )
        entities.append(
            VantageWeatherStandardSensor(
                coordinator=coordinator,
                name_suffix=name_suffix,
                json_data_key=sensor_json_key, 
                sensor_base_key=sensor_json_key,
                unit_constant_or_string=unit_constant_or_string,
                device_class_str=device_class_str,
                state_class_str=state_class_str,
                icon_override=icon,
                config_entry_id=config_entry.entry_id
            )
        )

    # Create special sensors
    _LOGGER.debug("Creating Barometer Trend sensor")
    entities.append(VantageWeatherBaroTrendSensor(coordinator, config_entry.entry_id))
    _LOGGER.debug("Creating Last Update sensor")
    entities.append(VantageWeatherLastUpdateSensor(coordinator, config_entry.entry_id))

    async_add_entities(entities)
    _LOGGER.info("Finished adding %s sensor entities for %s", len(entities), config_entry.title)


class VantageWeatherBaseSensor(CoordinatorEntity[VantageWeatherDataUpdateCoordinator], SensorEntity):
    """Base class for Vantage Weather sensors."""
    _attr_has_entity_name = True

    def __init__(self, coordinator: VantageWeatherDataUpdateCoordinator, config_entry_id: str, name_suffix: str, sensor_base_key: str):
        super().__init__(coordinator)
        self._config_entry_id = config_entry_id
        self._sensor_base_key = sensor_base_key
        self._attr_name = name_suffix 
        self._attr_unique_id = f"{config_entry_id}_{self._sensor_base_key}"
        _LOGGER.debug("BaseSensor '%s' (unique_id: %s) initialized.", self._attr_name, self._attr_unique_id)

    @property
    def device_info(self):
        info_data = self.coordinator.data.get("info", {}) if self.coordinator.data else {}
        model_code_str = info_data.get(DEVICE_MODEL_KEY)
        model_name = "Unknown Model"
        if model_code_str is not None:
            try:
                model_code = int(model_code_str)
                models = {0: "Wizard III", 1: "Wizard II", 2: "Monitor", 3: "Perception", 4: "GroWeather",
                          5: "Energy Enviromonitor", 6: "Health Enviromonitor", 16: "Vantage Pro/Pro2", 17: "Vantage Vue"}
                model_name = models.get(model_code, f"Unknown Model Code ({model_code})")
            except ValueError:
                model_name = f"Invalid Model Code ({model_code_str})"
        return {
            "identifiers": {(DOMAIN, self._config_entry_id)}, 
            "name": self.coordinator.device_name, 
            "manufacturer": "Davis Instruments (Assumed for Vantage)",
            "model": model_name,
            "sw_version": info_data.get(DEVICE_FIRMWARE_VER_KEY),
            "configuration_url": f"http://{self.coordinator.host}",
        }

    @property
    def available(self) -> bool:
        is_avail = super().available and self.coordinator.data is not None and "rtd" in self.coordinator.data
        return is_avail


class VantageWeatherStandardSensor(VantageWeatherBaseSensor):
    """Representation of a standard Vantage Weather Sensor."""

    def __init__(self, coordinator: VantageWeatherDataUpdateCoordinator, name_suffix: str,
                 json_data_key: str, sensor_base_key: str, unit_constant_or_string: str | None,
                 device_class_str: str | None, state_class_str: str | None,
                 icon_override: str | None, config_entry_id: str):
        super().__init__(coordinator, config_entry_id, name_suffix, sensor_base_key)
        self._json_data_key = json_data_key
        # Use _attr_native_unit_of_measurement instead of _attr_unit_of_measurement
        self._attr_native_unit_of_measurement = None 
        self._attr_icon = icon_override

        if unit_constant_or_string is not None:
            if not isinstance(unit_constant_or_string, str):
                self._attr_native_unit_of_measurement = unit_constant_or_string
                _LOGGER.debug(
                    "Sensor '%s' (%s): Directly assigned unit '%s' to native_unit_of_measurement from SENSOR_TYPES HA constant.",
                    self._attr_name, self._sensor_base_key, self._attr_native_unit_of_measurement
                )
            else: 
                mapped_unit = REVISED_UNIT_MAPPING.get(unit_constant_or_string)
                if mapped_unit:
                    self._attr_native_unit_of_measurement = mapped_unit
                    _LOGGER.debug(
                        "Sensor '%s' (%s): Mapped string unit '%s' to HA unit '%s' for native_unit_of_measurement via REVISED_UNIT_MAPPING.",
                        self._attr_name, self._sensor_base_key, unit_constant_or_string, self._attr_native_unit_of_measurement
                    )
                else: 
                    self._attr_native_unit_of_measurement = unit_constant_or_string
                    _LOGGER.debug(
                        "Sensor '%s' (%s): Assigned unit '%s' to native_unit_of_measurement directly from SENSOR_TYPES string (e.g., %%, °).",
                        self._attr_name, self._sensor_base_key, self._attr_native_unit_of_measurement
                    )
        
        if device_class_str == SensorDeviceClass.PRECIPITATION_INTENSITY.value and unit_constant_or_string is None:
            self._attr_native_unit_of_measurement = UnitOfVolumetricFlux.INCHES_PER_HOUR
            _LOGGER.debug(
                "Sensor '%s' (%s) (Rain Rate): Derived unit as '%s' for native_unit_of_measurement based on Inches accumulation.",
                self._attr_name, self._sensor_base_key, self._attr_native_unit_of_measurement
            )

        if device_class_str:
            try:
                self._attr_device_class = SensorDeviceClass(device_class_str)
            except ValueError:
                _LOGGER.warning("Sensor '%s': Invalid device_class string '%s'. Setting to None.", self._attr_name, device_class_str)
                self._attr_device_class = None
        else:
            self._attr_device_class = None

        if state_class_str:
            try:
                self._attr_state_class = SensorStateClass(state_class_str)
            except ValueError:
                _LOGGER.warning("Sensor '%s': Invalid state_class string '%s'. Setting to None.", self._attr_name, state_class_str)
                self._attr_state_class = None
        else:
            self._attr_state_class = None

        _LOGGER.debug(
            "Sensor '%s' (%s) final setup: native_unit_of_measurement='%s', device_class='%s', state_class='%s', icon='%s'",
            self._attr_name, self._sensor_base_key, self._attr_native_unit_of_measurement, self._attr_device_class, self._attr_state_class, self._attr_icon
        )
        
        if self._attr_device_class and self._attr_native_unit_of_measurement is None:
            dc_requiring_unit = [
                SensorDeviceClass.TEMPERATURE, SensorDeviceClass.HUMIDITY, SensorDeviceClass.PRESSURE,
                SensorDeviceClass.WIND_SPEED, SensorDeviceClass.PRECIPITATION, SensorDeviceClass.PRECIPITATION_INTENSITY,
                SensorDeviceClass.IRRADIANCE
            ]
            if self._attr_device_class in dc_requiring_unit:
                _LOGGER.error(
                    "Sensor '%s' (%s) has device class '%s' but its native_unit_of_measurement is None. This WILL cause Home Assistant validation errors.",
                    self._attr_name, self._sensor_base_key, self._attr_device_class
                )

    @property
    def native_value(self):
        if not self.available:
            return None
        
        rtd_data = self.coordinator.data.get("rtd", {})
        if self._json_data_key not in rtd_data:
            _LOGGER.debug("Sensor '%s': JSON key '%s' not found in rtd data.", self._attr_name, self._json_data_key)
            return None

        value = rtd_data[self._json_data_key]

        if value is None: return None
        if isinstance(value, str) and (value.strip() == "---" or value.strip() == ""):
            _LOGGER.debug("Sensor '%s': Received '---' or empty string, treating as None.", self._attr_name)
            return None

        is_numeric_conversion_needed = (
            self._attr_device_class in [
                SensorDeviceClass.TEMPERATURE, SensorDeviceClass.HUMIDITY, SensorDeviceClass.PRESSURE,
                SensorDeviceClass.WIND_SPEED, SensorDeviceClass.PRECIPITATION, SensorDeviceClass.PRECIPITATION_INTENSITY,
                SensorDeviceClass.IRRADIANCE,
            ] or 
            (self._attr_native_unit_of_measurement == DEGREE and self._attr_device_class is None) or
            (self._sensor_base_key == "uv" and self._attr_native_unit_of_measurement is None)
        )

        if is_numeric_conversion_needed:
            try: return float(value)
            except (ValueError, TypeError):
                _LOGGER.warning("Sensor '%s': Could not convert value '%s' (type: %s) to float.", self._attr_name, value, type(value))
                return None
        
        return value


class VantageWeatherBaroTrendSensor(VantageWeatherBaseSensor):
    """Representation of the Barometer Trend Sensor."""
    def __init__(self, coordinator: VantageWeatherDataUpdateCoordinator, config_entry_id: str):
        super().__init__(coordinator, config_entry_id, "Barometer Trend", SENSOR_KEY_BARO_TREND)
        self._attr_icon = "mdi:chart-line" 

    @property
    def native_value(self):
        if not self.available: return None
        rtd_data = self.coordinator.data.get("rtd", {})
        if "bartr" not in rtd_data:
            _LOGGER.debug("BaroTrendSensor: 'bartr' key not found in rtd data.")
            return None
        
        trend_code_str = rtd_data["bartr"]
        try: trend_code = float(trend_code_str)
        except (ValueError, TypeError):
            _LOGGER.warning("BaroTrendSensor: 'bartr' value '%s' is not numeric.", trend_code_str)
            self._attr_icon = "mdi:help-circle-outline"; return "Unknown"

        if trend_code == -60: self._attr_icon = "mdi:trending-down"; return "Falling Rapidly"
        if trend_code == -20: self._attr_icon = "mdi:trending-down"; return "Falling Slowly"
        if trend_code == 0:   self._attr_icon = "mdi:trending-neutral"; return "Steady"
        if trend_code == 20:  self._attr_icon = "mdi:trending-up"; return "Rising Slowly"
        if trend_code == 60:  self._attr_icon = "mdi:trending-up"; return "Rising Rapidly"
        
        _LOGGER.info("BaroTrendSensor: Unknown trend_code '%s'.", trend_code)
        self._attr_icon = "mdi:help-circle-outline"; return "---"


class VantageWeatherLastUpdateSensor(VantageWeatherBaseSensor):
    """Representation of the Last Update Sensor."""
    def __init__(self, coordinator: VantageWeatherDataUpdateCoordinator, config_entry_id: str):
        super().__init__(coordinator, config_entry_id, "Last Update", SENSOR_KEY_LAST_UPDATE)
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:clock-check-outline"

    @property
    def native_value(self) -> datetime | None:
        if not self.available: return None
        rtd_data = self.coordinator.data.get("rtd", {})
        date_str, time_str = rtd_data.get("date"), rtd_data.get("time")
        if date_str and time_str:
            try:
                naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y/%m/%d %H:%M:%S")
                aware_dt = dt_util.as_local(naive_dt)
                return aware_dt
            except ValueError:
                _LOGGER.error("LastUpdateSensor: Could not parse date/time: date='%s', time='%s'.", date_str, time_str)
        else:
            _LOGGER.debug("LastUpdateSensor: Date ('%s') or time ('%s') not found.", date_str, time_str)
        return None
