from datetime import datetime
from typing import Dict, Any, Optional

class DeviceStateManager:
    def __init__(self):
        self._devices: Dict[str, Dict[str, Any]] = {
            "pc": {
                "name": "Laptop Windows",
                "online": False,
                "last_seen": None,
                "battery": None,
                "active_window": None,
                "volume": None,
                "ip": None
            },
            "android": {
                "name": "Teléfono Android",
                "online": False,
                "last_seen": None,
                "battery": None,
                "is_charging": None,
                "volume": None,
                "flashlight": False,
                "contacts_count": 0,
                "ip": None
            },
            "alexa": {
                "name": "Amazon Echo / Alexa",
                "online": True,
                "last_seen": None
            }
        }

    def update_device_status(self, device_type: str, online: bool, extra_data: Optional[Dict[str, Any]] = None):
        if device_type in self._devices:
            self._devices[device_type]["online"] = online
            self._devices[device_type]["last_seen"] = datetime.now().isoformat()
            if extra_data:
                self._devices[device_type].update(extra_data)

    def get_device_info(self, device_type: str) -> Optional[Dict[str, Any]]:
        return self._devices.get(device_type)

    def get_all_devices(self) -> Dict[str, Dict[str, Any]]:
        return self._devices

device_state_manager = DeviceStateManager()
