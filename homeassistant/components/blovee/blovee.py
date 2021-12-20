import logging
from math import floor
from typing import Coroutine, Dict, List, Optional, Tuple

from aiohttp.client_reqrep import ClientResponse
from events import Events
import requests
from requests.api import head

from .dtos import BloveeDevice
from .govee_api import GoveeAPI

_LOGGER = logging.getLogger(__name__)


class Blovee:
    def __init__(self, api_key: str) -> None:
        self.events = Events()
        self._api = GoveeAPI(api_key=api_key)
        self._api_key = api_key
        self.devices: Dict[str, BloveeDevice] = {}

    async def get_devices(
        self,
    ) -> Tuple[List[BloveeDevice], Optional[str]]:
        response = await self._api.get_devices()
        error = None
        if response.status == 200:
            json = await response.json()
            for device in json["data"]["devices"]:
                device_id = device["device"]
                if device_id in self.devices.keys():
                    # Device has already been added.
                    continue

                # Create and add device to list
                self.devices[device_id] = BloveeDevice(
                    name=device["deviceName"],
                    model=device["model"],
                    mac=device_id,
                    is_on=False,
                    err="",
                    brightness=100,
                )
                self.events.new_device(self.devices[device_id])
        else:
            error = await response.text()

        return list(self.devices.values()), error

    async def get_device_state(self, device: BloveeDevice) -> BloveeDevice:
        response = await self._api.get_device_state(device)
        if response.status == 200:
            json: Dict = await response.json()
            for prop in json["data"]["properties"]:
                if "powerState" in prop:
                    device.is_on = prop["powerState"] == "on"
                if "brightness" in prop:
                    device.brightness = prop["brightness"]
        else:
            device.err = response.text

        return device

    async def get_states(self) -> List[BloveeDevice]:
        _LOGGER.debug("get_states invoked")
        for device in self.devices:
            self.devices[device] = await self.get_device_state(self.devices[device])

        return list(self.devices.values())

    async def toggle_power(self, device: BloveeDevice, turn_on: bool) -> BloveeDevice:
        response = await self._api.toggle_power(device, turn_on)
        if response.status == 200:
            _LOGGER.debug("%s turned %s", device.name, "on" if turn_on else "off")
            device.is_on = turn_on == True
        else:
            device.err = await response.text()
            _LOGGER.error(
                "Error turning %s %s: %s",
                "on" if turn_on else "off",
                device.name,
                response.text,
            )

        return device

    async def set_brightness(
        self, device: BloveeDevice, brightness: int
    ) -> BloveeDevice:
        brightness = max(1, floor(brightness * 100 / 255))
        response = await self._api.set_brightness(device, brightness)
        if response.status == 200:
            _LOGGER.debug("Set brightness for %s to %d", device.name, brightness)
            device.brightness = brightness
        else:
            device.err = await response.text()
            _LOGGER.error(
                "Failed to set brightness for %s to %d", device.name, brightness
            )
        return device
