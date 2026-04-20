# Ecobee Node Server — Configuration

## Required Custom Parameters

Set these in the **Custom Parameters** section of the node server:

| Key | Description |
|-----|-------------|
| `api_key` | Your Ecobee API key from the ecobee developer portal |

## First-Time Authorization (PIN Flow)

1. Set your `api_key` and **restart** the node server.
2. In the PG3x UI, check the **Notices** section — you will see a 4-character PIN displayed.
3. Log into [ecobee.com](https://www.ecobee.com) → **My Apps** → **Add Application**.
4. Enter the PIN shown in Notices.
5. **Restart the node server** — it will exchange the PIN for tokens automatically.

After initial authorization, tokens are stored and refreshed automatically. You should not need to re-authorize unless you revoke access in the ecobee portal.

## Poll Settings (recommended)

| Poll | Interval |
|------|----------|
| Short Poll | 120 seconds (thermostat data refresh) |
| Long Poll  | 3600 seconds (token refresh) |

## Nodes Created

- **Ecobee Controller** — top-level node, shows online status
- **Ecobee Thermostat** (one per registered thermostat) — temp, humidity, setpoints, mode, occupancy
- **Ecobee Sensor** (one per remote sensor) — temp, humidity, occupancy

## Commands Available on Thermostat Node

| Command | Description |
|---------|-------------|
| Set HVAC Mode | Heat / Cool / Auto / Off / Aux Heat Only |
| Set Heat Setpoint | Sets heat hold temperature (°F) |
| Set Cool Setpoint | Sets cool hold temperature (°F) |
| Resume Schedule | Cancels any holds and returns to normal schedule |
