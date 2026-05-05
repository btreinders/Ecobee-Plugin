# Ecobee Plugin for eisy / PG3x

A PG3x Node Server plugin that integrates Ecobee thermostats and remote sensors into the Universal Devices eisy / IoX platform.

## Features

- Supports multiple Ecobee thermostats and remote sensors
- Reads temperature, humidity, setpoints, HVAC mode, occupancy, and equipment status
- Outside weather data including temperature, humidity, wind speed, and weather symbol
- Full control of HVAC mode, heat/cool setpoints, and comfort profiles
- Hold type support (Next Transition or Indefinite)
- Resume Schedule command
- Auto-discovers all registered thermostats and their associated remote sensors
- Polls Ecobee API on a configurable schedule (default: 2 min / 60 min)

## Nodes

### Ecobee Controller
- Online status
- Query command

### Ecobee Thermostat
| Driver | Description |
|--------|-------------|
| ST | Current Temperature |
| CLITEMP | Temperature |
| CLIHUM | Humidity |
| CLIMD | HVAC Mode |
| CLISPH | Heat Setpoint |
| CLISPC | Cool Setpoint |
| GV0 | Occupancy |
| GV1 | Heat Running |
| GV2 | Cool Running |
| GV3 | Fan Running |
| GV4 | Aux Heat Running |
| GV5 | Comfort Profile |
| GV6 | Outside Temp |
| GV7 | Outside Humidity |
| GV8 | Wind Speed |
| GV9 | Weather Symbol |

### Ecobee Sensor
| Driver | Description |
|--------|-------------|
| ST | Temperature |
| CLITEMP | Temperature |
| CLIHUM | Humidity |
| GV0 | Occupancy |

## Weather Symbol Values

| Index | Condition |
|-------|-----------|
| 0 | No Data |
| 1 | Sunny |
| 2 | Few Clouds |
| 3 | Partly Cloudy |
| 4 | Mostly Cloudy |
| 5 | Overcast |
| 6 | Drizzle |
| 7 | Rain |
| 8 | Freezing Rain |
| 9 | Wintry Mix |
| 10 | Freezing Drizzle |
| 11 | Snow |
| 12 | Flurries |
| 13 | Blizzard |

## Commands

| Command | Description |
|---------|-------------|
| Set HVAC Mode | Set mode: Heat, Cool, Auto, Off, Aux Heat Only |
| Set Heat Setpoint | Set the heat setpoint (°F) |
| Set Cool Setpoint | Set the cool setpoint (°F) |
| Set Comfort Profile | Set profile (Home, Away, Sleep, Smart 1-8) with hold type |
| Resume Schedule | Resume the normal Ecobee schedule |

## Installation

### Prerequisites
- eisy running PG3x
- Ecobee developer API key (free at [developer.ecobee.com](https://developer.ecobee.com))
- Python 3 with `requests` library

### Steps

1. Clone or copy this plugin to your eisy:
   ```bash
   git clone https://github.com/btreinders/Ecobee-Plugin.git /home/admin/plugins/udi-ecobee-pg3
   ```

2. Run the install script:
   ```bash
   cd /home/admin/plugins/udi-ecobee-pg3 && bash install.sh
   ```

3. In the PG3x dashboard, add the plugin and enter your Ecobee API key in the configuration parameters.

4. On first run the plugin will display a PIN code. Go to the Ecobee web portal under **My Apps** and enter the PIN to authorize the plugin.

5. Restart the plugin after authorization. It will exchange the PIN for tokens and begin polling.

## Configuration

| Parameter | Description |
|-----------|-------------|
| api_key | Your Ecobee developer API key |

Tokens are stored locally at `/home/admin/plugins/udi-ecobee-pg3/tokens.json` and refreshed automatically.

## Poll Intervals

| Poll | Default | Description |
|------|---------|-------------|
| Short Poll | 120 sec | Updates thermostat and sensor data |
| Long Poll | 3600 sec | Full refresh |

## Tested On

- eisy running PG3x
- 3 Ecobee thermostats
- 11 remote sensors

## Author

BTR — April 2026  
[https://github.com/btreinders/Ecobee-Plugin](https://github.com/btreinders/Ecobee-Plugin)

## License

MIT

