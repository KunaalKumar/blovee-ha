import logging
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
        pass

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
                    mac=device["device"],
                    is_on=False,
                    err="",
                )
                self.events.new_device(self.devices[device_id])
        else:
            error = response.text

        return list(self.devices.values()), error

    async def get_device_state(self, device: BloveeDevice) -> BloveeDevice:
        response = await self._api.get_device_state(device)
        if response.status == 200:
            json: Dict = await response.json()
            for prop in json["data"]["properties"]:
                if "powerState" in prop:
                    device.is_on = prop["powerState"] == "on"
        else:
            device.err = response.text

        return device

    async def get_states(self) -> List[BloveeDevice]:
        _LOGGER.debug("get_states invoked")
        for device in self.devices:
            self.devices[device] = await self.get_device_state(self.devices[device])

        return list(self.devices.values())

    async def toggle_power(self, device: BloveeDevice, turn_on: bool):
        response = await self._api.toggle_power(device, turn_on)
        if response.status == 200:
            _LOGGER.debug("%s turned on", device.name)
        else:
            device.err = await response.text()
            _LOGGER.error("Error turning on %s: %s", device.name, response.text)
