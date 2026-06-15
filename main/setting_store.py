import copy
import json
import os
import platform
import shutil
from contextlib import contextmanager
from datetime import datetime

from config.settings import DATA_DIR, SETTING_PATH

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    import msvcrt
except ImportError:
    msvcrt = None


SETTING_LOCK_PATH = f"{SETTING_PATH}.lock"
SETTING_BACKUP_PATH = f"{SETTING_PATH}.bak"

BASE_DEFAULT_CONFIG = {
    "relayboard_type": "8port",
    "relay_output_mode": "tcp",
    "tcp_relay": {
        "address": "192.168.5.138",
        "port": 502,
    },
    "sensor_ports": "com1",
    "test_mode": True,
    "irrigation_mix": False,
    "irrigation_mix_port": 0,
    "area_control": False,
    "area_infor": {
        "fan": 0,
        "open": 1,
        "close": 2,
        "address": "192.168.5.139",
        "port": 502,
    },
    "irrigation_channels": {
        "1": True,
        "2": False,
        "3": False,
        "4": False,
    },
    "led_channels": {
        "1": False,
        "2": False,
        "3": False,
        "4": False,
    },
    "irrigationpanel": {
        "control_mode": {
            "1": "timer",
            "2": "timer",
            "3": "timer",
            "4": "timer",
        },
        "relay_port_mapping": {
            "1": 0,
            "2": 1,
            "3": 2,
            "4": 3,
        },
        "irrigation_time": {
            "1": 100,
            "2": 100,
            "3": 100,
            "4": 100,
        },
    },
    "ledpanel": {
        "led_port_mapping": {
            "1": 4,
            "2": 5,
            "3": 6,
            "4": 7,
        },
        "led_time": {
            "1": {"on": "08:00", "off": "17:00"},
            "2": {"on": "08:00", "off": "17:00"},
            "3": {"on": "08:00", "off": "20:00"},
            "4": {"on": "08:00", "off": "17:00"},
        },
    },
    "time_control": {
        "1": ["10:00", "12:00", "14:00", "16:00"],
        "2": ["10:00", "12:00", "14:00", "16:00"],
        "3": ["10:00", "12:00", "14:00", "16:00"],
        "4": ["10:00", "12:00", "14:00", "16:00"],
    },
    "sensor_settings": {
        "1": {
            "target": 150,
            "start_time": "09:00",
            "end_time": "17:30",
            "refresh_sec": 150,
            "nf_value": 68,
            "dtm": 1.15,
            "data_table": "",
            "modules": "",
        },
        "2": {
            "target": 150,
            "start_time": "09:00",
            "end_time": "17:30",
            "refresh_sec": 300,
            "nf_value": 68,
            "dtm": 1.15,
            "data_table": "",
            "modules": "",
        },
        "3": {
            "target": 150,
            "start_time": "09:00",
            "end_time": "17:30",
            "refresh_sec": 300,
            "nf_value": 68,
            "dtm": 1.15,
            "data_table": "",
            "modules": "",
        },
        "4": {
            "target": 150,
            "start_time": "09:00",
            "end_time": "17:30",
            "refresh_sec": 300,
            "nf_value": 68,
            "dtm": 1.15,
            "data_table": "",
            "modules": "",
        },
    },
}


def _legacy_relay_output_mode():
    return "gpio" if platform.system() == "Linux" else "tcp"


def _default_config():
    config = copy.deepcopy(BASE_DEFAULT_CONFIG)
    config["relay_output_mode"] = _legacy_relay_output_mode()
    return config


def _deep_merge(default, override):
    result = copy.deepcopy(default)
    if not isinstance(override, dict):
        return result

    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _coerce_int(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def normalize_setting(config):
    if not isinstance(config, dict):
        raise ValueError("setting.json root must be an object")

    normalized = _deep_merge(_default_config(), config)

    if normalized.get("relayboard_type") not in {"4port", "8port"}:
        normalized["relayboard_type"] = "8port"

    if normalized.get("relay_output_mode") not in {"tcp", "gpio"}:
        normalized["relay_output_mode"] = _legacy_relay_output_mode()

    tcp_relay = normalized.get("tcp_relay")
    if not isinstance(tcp_relay, dict):
        tcp_relay = {}
    tcp_relay["address"] = str(tcp_relay.get("address") or "192.168.5.138")
    tcp_relay["port"] = _coerce_int(tcp_relay.get("port", 502), 502)
    normalized["tcp_relay"] = tcp_relay

    return normalized


@contextmanager
def _setting_file_lock():
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SETTING_LOCK_PATH, "a+") as lock_file:
        if fcntl:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        elif msvcrt:
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)

        try:
            yield
        finally:
            if fcntl:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            elif msvcrt:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)


def _write_setting_unlocked(config):
    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(SETTING_PATH):
        shutil.copy2(SETTING_PATH, SETTING_BACKUP_PATH)

    temp_path = f"{SETTING_PATH}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")

    os.replace(temp_path, SETTING_PATH)


def load_setting_data():
    with _setting_file_lock():
        if not os.path.exists(SETTING_PATH):
            setting = _default_config()
            _write_setting_unlocked(setting)
            return setting

        try:
            with open(SETTING_PATH, "r", encoding="utf-8") as f:
                loaded_setting = json.load(f)
            setting = normalize_setting(loaded_setting)
        except Exception as exc:
            invalid_path = f"{SETTING_PATH}.invalid_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                shutil.copy2(SETTING_PATH, invalid_path)
            except Exception:
                pass
            raise ValueError(f"설정 파일을 읽을 수 없습니다: {exc}") from exc

        if setting != loaded_setting:
            _write_setting_unlocked(setting)

        return setting


def save_setting_data(config):
    setting = normalize_setting(config)
    with _setting_file_lock():
        _write_setting_unlocked(setting)
    return setting


def apply_setting_update(current, new_data):
    for key, value in new_data.items():
        if key in ["irrigationpanel", "ledpanel", "sensor_settings", "time_control"]:
            current.setdefault(key, {})
            for subkey, subvalue in value.items():
                if isinstance(subvalue, dict):
                    current[key].setdefault(subkey, {}).update(subvalue)
                else:
                    current[key][subkey] = subvalue
        elif key.startswith("irrigation_channels_"):
            ch = key.split("_")[-1]
            current.setdefault("irrigation_channels", {})[ch] = value
        elif key.startswith("led_channels_"):
            ch = key.split("_")[-1]
            current.setdefault("led_channels", {})[ch] = value
        elif key.startswith("area_infor_"):
            field = key.replace("area_infor_", "")
            if field in ["fan", "open", "close", "port"]:
                value = _coerce_int(value, value)
            current.setdefault("area_infor", {})[field] = value
        elif key.startswith("tcp_relay_"):
            field = key.replace("tcp_relay_", "")
            if field == "port":
                value = _coerce_int(value, 502)
            current.setdefault("tcp_relay", {})[field] = value
        elif key == "irrigation_mix_port":
            current[key] = _coerce_int(value, value)
        else:
            current[key] = value

    return normalize_setting(current)
