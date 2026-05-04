#!/usr/bin/env python3
"""
Ecobee Node Server for Universal Devices eisy / PG3x
Supports: temperature, humidity, setpoints, mode control, occupancy, remote sensors
Author: Custom build for eisy PG3x
"""

import udi_interface
import sys
import time
import json
import requests
import threading

LOGGER = udi_interface.LOGGER
Custom = udi_interface.Custom

# ---------------------------------------------------------------------------
# Ecobee API helpers
# ---------------------------------------------------------------------------


ECOBEE_API = "https://api.ecobee.com"
TOKEN_FILE = "/home/admin/plugins/udi-ecobee-pg3/tokens.json"

HVAC_MODE_MAP = {
    "heat":    0,
    "cool":    1,
    "auto":    2,
    "off":     3,
    "auxHeatOnly": 4,
}
MODE_IDX_TO_STR = {v: k for k, v in HVAC_MODE_MAP.items()}
CLIMATE_MAP = {
    "home":   0,
    "away":   1,
    "sleep":  2,
    "smart1": 3,
    "smart2": 4,
    "smart3": 5,
    "smart4": 6,
    "smart5": 7,
    "smart6": 8,
    "smart7": 9,
    "smart8": 10,
}
CLIMATE_IDX_TO_REF = {v: k for k, v in CLIMATE_MAP.items()}


def _headers(access_token):
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def get_thermostats(access_token):
    """Fetch all thermostats with runtime, settings, and remote sensors."""
    selection = {
        "selectionType": "registered",
        "selectionMatch": "",
        "includeRuntime": True,
        "includeSettings": True,
        "includeSensors": True,
        "includeEquipmentStatus": True,
        "includeProgram": True,
        "includeEvents": True,
    }
    params = {"json": json.dumps({"selection": selection})}
    resp = requests.get(
        f"{ECOBEE_API}/1/thermostat",
        headers=_headers(access_token),
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status", {}).get("code", 0) != 0:
        raise Exception(f"Ecobee API error: {data['status']}")
    return data.get("thermostatList", [])


def set_hvac_mode(access_token, identifier, mode_str):
    body = {
        "selection": {
            "selectionType": "thermostats",
            "selectionMatch": identifier,
        },
        "thermostat": {
            "settings": {"hvacMode": mode_str}
        },
    }
    resp = requests.post(
        f"{ECOBEE_API}/1/thermostat",
        headers=_headers(access_token),
        params={"format": "json"},
        data=json.dumps(body),
        timeout=15,
    )
    resp.raise_for_status()


def set_hold(access_token, identifier, heat_f, cool_f):
    """Set a temperature hold (values in Fahrenheit * 10 per Ecobee API)."""
    body = {
        "selection": {
            "selectionType": "thermostats",
            "selectionMatch": identifier,
        },
        "functions": [
            {
                "type": "setHold",
                "params": {
                    "holdType": "indefinite",
                    "heatHoldTemp": int(heat_f * 10),
                    "coolHoldTemp": int(cool_f * 10),
                },
            }
        ],
    }
    resp = requests.post(
        f"{ECOBEE_API}/1/thermostat",
        headers=_headers(access_token),
        params={"format": "json"},
        data=json.dumps(body),
        timeout=15,
    )
    resp.raise_for_status()


def resume_program(access_token, identifier):
    body = {
        "selection": {
            "selectionType": "thermostats",
            "selectionMatch": identifier,
        },
        "functions": [
            {"type": "resumeProgram", "params": {"resumeAll": True}}
        ],
    }
    resp = requests.post(
        f"{ECOBEE_API}/1/thermostat",
        headers=_headers(access_token),
        params={"format": "json"},
        data=json.dumps(body),
        timeout=15,
    )
    resp.raise_for_status()


def set_climate(access_token, identifier, climate_ref, hold_type="nextTransition"):
    body = {
        "selection": {
            "selectionType": "thermostats",
            "selectionMatch": identifier,
        },
        "functions": [
            {"type": "setHold", "params": {
                "holdType": hold_type,
                "holdClimateRef": climate_ref,
            }}
        ],
    }
    resp = requests.post(
        f"{ECOBEE_API}/1/thermostat",
        headers=_headers(access_token),
        params={"format": "json"},
        data=json.dumps(body),
        timeout=15,
    )
    resp.raise_for_status()


def refresh_tokens(api_key, refresh_token):
    resp = requests.post(
        f"{ECOBEE_API}/token",
        params={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": api_key,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()  # access_token, refresh_token, expires_in


def get_pin(api_key):
    resp = requests.get(
        f"{ECOBEE_API}/authorize",
        params={
            "response_type": "ecobeePin",
            "client_id": api_key,
            "scope": "smartWrite",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()  # ecobeePin, code, expires_in


def exchange_pin(api_key, auth_code):
    resp = requests.post(
        f"{ECOBEE_API}/token",
        params={
            "grant_type": "ecobeePin",
            "code": auth_code,
            "client_id": api_key,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Remote Sensor Node
# ---------------------------------------------------------------------------

class EcobeeSensorNode(udi_interface.Node):
    id = "ecobee_sensor"

    def __init__(self, polyglot, primary, address, name):
        super().__init__(polyglot, primary, address, name)
        self.poly = polyglot

    def update(self, temp_f, humidity, occupancy):
        """Push latest sensor data."""
        self.setDriver("ST",   round(temp_f, 1))
        self.setDriver("CLITEMP", round(temp_f, 1))
        self.setDriver("CLIHUM", int(humidity) if humidity is not None else 0)
        self.setDriver("GV0",  1 if occupancy else 0)

    commands = {}
    drivers = [
        {"driver": "ST",      "value": 0, "uom": 17},   # temp °F
        {"driver": "CLITEMP", "value": 0, "uom": 17},
        {"driver": "CLIHUM",  "value": 0, "uom": 22},   # %RH
        {"driver": "GV0",     "value": 0, "uom": 2},    # occupancy bool
    ]


# ---------------------------------------------------------------------------
# Thermostat Node
# ---------------------------------------------------------------------------

class EcobeeThermostatNode(udi_interface.Node):
    id = "ecobee_thermostat"

    def __init__(self, polyglot, primary, address, name, identifier, controller):
        super().__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.identifier = identifier
        self.controller = controller

    def update(self, tstat):
        rt = tstat.get("runtime", {})
        settings = tstat.get("settings", {})

        actual_temp  = rt.get("actualTemperature", 0) / 10.0
        actual_hum   = rt.get("actualHumidity", 0)
        heat_sp      = rt.get("desiredHeat", 0) / 10.0
        cool_sp      = rt.get("desiredCool", 0) / 10.0
        hvac_mode    = settings.get("hvacMode", "off")
        mode_idx     = HVAC_MODE_MAP.get(hvac_mode, 3)
        occupancy    = tstat.get("runtime", {}).get("connected", False)
        equip        = tstat.get("equipmentStatus", "")
        heat_on      = 1 if any(x in equip for x in ["heatPump", "heatPump2", "heatPump3", "auxHeat1", "auxHeat2", "auxHeat3"]) else 0
        cool_on      = 1 if any(x in equip for x in ["compCool1", "compCool2"]) else 0
        fan_on       = 1 if "fan" in equip else 0
        aux_on       = 1 if any(x in equip for x in ["auxHeat1", "auxHeat2", "auxHeat3"]) else 0
        self.setDriver("ST",      round(actual_temp, 1))
        self.setDriver("CLITEMP", round(actual_temp, 1))
        self.setDriver("CLIHUM",  int(actual_hum))
        self.setDriver("CLIMD",   mode_idx)
        self.setDriver("CLISPH",  round(heat_sp, 1))
        self.setDriver("CLISPC",  round(cool_sp, 1))
        # Check for active hold event first, fall back to scheduled climate
        events = tstat.get("events", [])
        active_hold = next((e for e in events if e.get("type") == "hold" and e.get("running")), None)
        if active_hold and active_hold.get("holdClimateRef"):
            climate_ref = active_hold["holdClimateRef"]
        else:
            climate_ref = tstat.get("program", {}).get("currentClimateRef", "home")
        climate_idx = CLIMATE_MAP.get(climate_ref, 0)
        self.setDriver("GV0",     1 if occupancy else 0)
        self.setDriver("GV5",     climate_idx)
        self.setDriver("GV1",     heat_on)
        self.setDriver("GV2",     cool_on)
        self.setDriver("GV3",     fan_on)
        self.setDriver("GV4",     aux_on)

    # --- Commands ---

    def set_mode(self, command):
        val = int(command.get("query", {}).get("mode.uom67", command.get("value", 3)))
        mode_str = MODE_IDX_TO_STR.get(val, "off")
        LOGGER.info(f"Setting HVAC mode to {mode_str} on {self.identifier}")
        token = self.controller.get_access_token()
        set_hvac_mode(token, self.identifier, mode_str)
        self.setDriver("CLIMD", val)

    def set_heat_sp(self, command):
        val = float(command.get("query", {}).get("heat.uom17", command.get("value", 70)))
        current_cool = self.getDriver("CLISPC")
        LOGGER.info(f"Setting heat setpoint to {val}°F on {self.identifier}")
        token = self.controller.get_access_token()
        set_hold(token, self.identifier, val, float(current_cool))
        self.setDriver("CLISPH", val)

    def set_cool_sp(self, command):
        val = float(command.get("query", {}).get("cool.uom17", command.get("value", 75)))
        current_heat = self.getDriver("CLISPH")
        LOGGER.info(f"Setting cool setpoint to {val}°F on {self.identifier}")
        token = self.controller.get_access_token()
        set_hold(token, self.identifier, float(current_heat), val)
        self.setDriver("CLISPC", val)

    def resume(self, command):
        LOGGER.info(f"Resuming program on {self.identifier}")
        token = self.controller.get_access_token()
        resume_program(token, self.identifier)

    def set_climate_cmd(self, command):
        query = command.get("query", {})
        val = int(query.get("climate.uom25", command.get("value", 0)))
        hold_idx = int(query.get("holdtype.uom25", 0))
        climate_ref = CLIMATE_IDX_TO_REF.get(val, "home")
        hold_type = "indefinite" if hold_idx == 1 else "nextTransition"
        LOGGER.info(f"Setting climate to {climate_ref} hold={hold_type} on {self.identifier}")
        token = self.controller.get_access_token()
        set_climate(token, self.identifier, climate_ref, hold_type)
        self.setDriver("GV5", val)

    commands = {
        "CLIMD":    set_mode,
        "CLISPH":   set_heat_sp,
        "CLISPC":   set_cool_sp,
        "RESUME":   resume,
        "SET_CLIMATE":  set_climate_cmd,
    }

    drivers = [
        {"driver": "ST",      "value": 0, "uom": 17},   # actual temp °F
        {"driver": "CLITEMP", "value": 0, "uom": 17},
        {"driver": "CLIHUM",  "value": 0, "uom": 22},
        {"driver": "CLIMD",   "value": 3, "uom": 67},   # mode index
        {"driver": "CLISPH",  "value": 0, "uom": 17},   # heat setpoint
        {"driver": "CLISPC",  "value": 0, "uom": 17},   # cool setpoint
        {"driver": "GV0",     "value": 0, "uom": 2},    # occupancy
        {"driver": "GV5",     "value": 0, "uom": 25},   # comfort profile
        {"driver": "GV0",     "value": 0, "uom": 2},    # occupancy
        {"driver": "GV1",     "value": 0, "uom": 2},    # heat running
        {"driver": "GV2",     "value": 0, "uom": 2},    # cool running
        {"driver": "GV3",     "value": 0, "uom": 2},    # fan running
        {"driver": "GV4",     "value": 0, "uom": 2},    # aux heat running
    ]


# ---------------------------------------------------------------------------
# Controller Node
# ---------------------------------------------------------------------------

class EcobeeController(udi_interface.Node):
    id = "ecobee_controller"

    def __init__(self, polyglot, primary, address, name):
        super().__init__(polyglot, primary, address, name)
        self.poly = polyglot
        self.Parameters = Custom(polyglot, "customParams")
        self.Notices = Custom(polyglot, "notices")

        self._access_token = None
        self._refresh_token = None
        self._api_key = None
        self._auth_code = None   # from PIN flow
        self._tstat_nodes = {}   # address -> EcobeeThermostatNode
        self._sensor_nodes = {}  # address -> EcobeeSensorNode
        self._discover_lock = threading.Lock()

        polyglot.subscribe(polyglot.START,           self.start, address)
        polyglot.subscribe(polyglot.CUSTOMPARAMS,    self.param_handler)
        polyglot.subscribe(polyglot.POLL,            self.poll)

        polyglot.ready()
        polyglot.addNode(self)

    # ------------------------------------------------------------------ #
    # Startup / params


    def param_handler(self, params):
        self.Parameters.load(params)
        self._api_key = self.Parameters.get("api_key", "")
        saved = self._load_token_file()
        self._access_token  = saved.get("access_token", "")
        self._refresh_token = saved.get("refresh_token", "")
        self._auth_code     = saved.get("auth_code", "")
        if self._api_key:
            self._authorize()

    def start(self):
        LOGGER.info("Ecobee node server starting...")
        self.setDriver("ST", 1)
        # Fallback: if param_handler hasn't fired yet, wait briefly then check
        time.sleep(2)
        if not self._tstat_nodes:
            if not self._api_key:
                self._api_key = "fw7n3tzopHoo5idUoi4G5hdzgaQ510o7"
            saved = self._load_token_file()
            if saved:
                if not self._access_token:
                    self._access_token  = saved.get("access_token", "")
                    self._refresh_token = saved.get("refresh_token", "")
                    self._auth_code     = saved.get("auth_code", "")
                if self._refresh_token:
                    self._authorize()

    def _authorize(self):
        """Handle the PIN-based OAuth2 flow."""
        if not self._api_key:
            self.Notices["cfg"] = "Please set your 'api_key' in Custom Parameters."
            LOGGER.error("No api_key configured.")
            return

        # If we already have tokens, try a refresh
        if self._refresh_token:
            try:
                self._do_refresh()
                LOGGER.info("Token refreshed successfully.")
                self._discover()
                return
            except Exception as e:
                LOGGER.warning(f"Token refresh failed: {e}. Re-authorizing via PIN.")

        # If we have an auth_code from a prior PIN, try to exchange it
        saved = self._load_token_file()
        if self._auth_code and not self._access_token and saved.get("ready") != False:
            try:
                tok = exchange_pin(self._api_key, self._auth_code)
                self._save_tokens(tok)
                LOGGER.info("PIN exchanged for tokens successfully.")
                self._discover()
                return
            except Exception as e:
                LOGGER.error(f"PIN exchange failed: {e}")
                LOGGER.error(f"auth_code was: {self._auth_code}")
                return

        # Fresh PIN request
        try:
            pin_data = get_pin(self._api_key)
            pin  = pin_data["ecobeePin"]
            code = pin_data["code"]
            self._auth_code = code
            self._save_token_file({"auth_code": code, "ready": False})
            self.Notices["pin"] = (
                f"Go to ecobee.com → My Apps → Add Application and enter PIN: {pin}  "
                f"Then restart this node server."
            )
            LOGGER.info(f"Ecobee PIN: {pin} — enter this in the ecobee portal, then restart.")
        except Exception as e:
            LOGGER.error(f"Failed to get PIN: {e}")

    def _do_refresh(self):
        tok = refresh_tokens(self._api_key, self._refresh_token)
        self._save_tokens(tok)

    def _save_tokens(self, tok):
        self._access_token  = tok["access_token"]
        self._refresh_token = tok["refresh_token"]
        self._save_token_file({
            "access_token":  self._access_token,
            "refresh_token": self._refresh_token,
            "ready": True
        })
        self.Notices.delete("pin")

    def _load_token_file(self):
        try:
            with open(TOKEN_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_token_file(self, data):
        try:
            with open(TOKEN_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            LOGGER.error(f"Failed to save token file: {e}")
    def get_access_token(self):
        """Return a valid access token, refreshing if needed."""
        if not self._access_token:
            raise Exception("No access token available.")
        return self._access_token

    # ------------------------------------------------------------------ #
    # Discovery

    def _discover(self):
        if not self._discover_lock.acquire(blocking=False):
            LOGGER.info("Discovery already in progress, skipping.")
            return
        try:
            LOGGER.info("Discovering Ecobee thermostats...")
            tstats = get_thermostats(self._access_token)

            # Pass 1: add all thermostat nodes first
            for tstat in tstats:
                identifier = tstat["identifier"]
                name       = tstat["name"]
                t_addr     = f"t_{identifier[:12].lower()}"
                if t_addr not in self._tstat_nodes:
                    node = EcobeeThermostatNode(
                        self.poly, self.address, t_addr,
                        f"Ecobee {name}", identifier, self
                    )
                    self.poly.addNode(node)
                    self._tstat_nodes[t_addr] = node
                    LOGGER.info(f"Added thermostat node: {name}")
                    time.sleep(1)

            # Wait for all thermostat nodes to register
            time.sleep(10)

            # Pass 2: update thermostats and add sensors
            for tstat in tstats:
                identifier = tstat["identifier"]
                t_addr     = f"t_{identifier[:12].lower()}"
                self._tstat_nodes[t_addr].update(tstat)

                for sensor in tstat.get("remoteSensors", []):
                    s_id   = sensor.get("id", "").replace(":", "").lower()[:8]
                    s_addr = f"s_{t_addr[-4:]}_{s_id}"
                    s_name = sensor.get("name", "Sensor")
                    temp_cap = next((c for c in sensor.get("capability", []) if c["type"] == "temperature"), None)
                    hum_cap  = next((c for c in sensor.get("capability", []) if c["type"] == "humidity"), None)
                    occ_cap  = next((c for c in sensor.get("capability", []) if c["type"] == "occupancy"), None)
                    temp_f   = (float(temp_cap["value"]) / 10.0) if temp_cap and temp_cap["value"] != "unknown" else 0
                    humidity = float(hum_cap["value"]) if hum_cap and hum_cap.get("value") not in (None, "unknown") else 0
                    occupied = (occ_cap["value"] == "true") if occ_cap else False
                    if s_addr not in self._sensor_nodes:
                        snode = EcobeeSensorNode(
                           self.poly, self.address, s_addr,
                           f"Sensor {s_name}"
                        )
                        self.poly.addNode(snode)
                        self._sensor_nodes[s_addr] = snode
                        LOGGER.info(f"Added sensor node: {s_name}")
                        time.sleep(1)
                    self._sensor_nodes[s_addr].update(temp_f, humidity, occupied)

            self.setDriver("ST", 1)
            LOGGER.info(f"Discovery complete. {len(self._tstat_nodes)} thermostats, {len(self._sensor_nodes)} sensors.")
        except Exception as e:
            LOGGER.error(f"Discovery failed: {e}")
            self.setDriver("ST", 0)
        finally:
            self._discover_lock.release()


    def poll(self, flag):
        if "longPoll" in flag:
            LOGGER.error("Long poll — refreshing tokens.")
            try:
                self._do_refresh()
            except Exception as e:
                LOGGER.error(f"Token refresh on long poll failed: {e}")
            return

        LOGGER.debug("Short poll — updating thermostat data.")
        try:
            tstats = get_thermostats(self._access_token)
        except Exception as e:
            LOGGER.error(f"Poll update failed: {e}")
            self.setDriver("ST", 0)
            return

        for tstat in tstats:
            identifier = tstat["identifier"]
            t_addr = f"t_{identifier[:12].lower()}"
            if t_addr in self._tstat_nodes:
                self._tstat_nodes[t_addr].update(tstat)

            for sensor in tstat.get("remoteSensors", []):
                s_id   = sensor.get("id", "").replace(":", "").lower()[:12]
                s_addr = f"s_{s_id}"
                if s_addr not in self._sensor_nodes:
                    continue
                temp_cap = next((c for c in sensor.get("capability", []) if c["type"] == "temperature"), None)
                hum_cap  = next((c for c in sensor.get("capability", []) if c["type"] == "humidity"), None)
                occ_cap  = next((c for c in sensor.get("capability", []) if c["type"] == "occupancy"), None)
                temp_f   = (float(temp_cap["value"]) / 10.0) if temp_cap and temp_cap["value"] != "unknown" else 0
                humidity = float(hum_cap["value"]) if hum_cap and hum_cap.get("value") not in (None, "unknown") else 0
                occupied = (occ_cap["value"] == "true") if occ_cap else False
                self._sensor_nodes[s_addr].update(temp_f, humidity, occupied)

        self.setDriver("ST", 1)

    # ------------------------------------------------------------------ #

    def query(self, command=None):
        self.poll("shortPoll")

    commands = {"QUERY": query}

    drivers = [
        {"driver": "ST", "value": 0, "uom": 2},  # online bool
    ]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        polyglot = udi_interface.Interface([EcobeeController, EcobeeThermostatNode, EcobeeSensorNode])
        polyglot.start()
        EcobeeController(polyglot, 'controller', 'controller', 'Ecobee Controller')
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
    except Exception as e:
        LOGGER.exception(f"Unhandled exception: {e}")
        sys.exit(1)
