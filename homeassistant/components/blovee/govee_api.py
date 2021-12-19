import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Generator

import aiohttp
from aiohttp.client_reqrep import ClientResponse

from .dtos import BloveeDevice

GOVEE_API_URL = "https://developer-api.govee.com/v1/devices/"
HEADER_API_KEY = "Govee-API-Key"


class GoveeAPI:
    def __init__(self, api_key: str) -> None:
        self._session = aiohttp.ClientSession(headers={HEADER_API_KEY: api_key})

    async def __aexit__(self, *err):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
        self._session = None

    async def get_devices(self) -> ClientResponse:
        return await self._session.get(url=GOVEE_API_URL)

    async def get_device_state(self, device: BloveeDevice) -> ClientResponse:
        return await self._session.get(
            url=GOVEE_API_URL + "state",
            params={"device": device.mac, "model": device.model},
        )

    async def toggle_power(self, device: BloveeDevice, turn_on: bool) -> ClientResponse:
        return await self._session.put(
            url=GOVEE_API_URL + "control/",
            json={
                "device": device.mac,
                "model": device.model,
                "cmd": {"name": "turn", "value": "on" if turn_on else "off"},
            },
        )
