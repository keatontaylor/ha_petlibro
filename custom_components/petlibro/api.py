"Standalone PETLIBRO API"
from logging import getLogger
from hashlib import md5
from urllib.parse import urljoin
from typing import Any, Dict, List, TypeAlias

from aiohttp import ClientSession

from .exceptions import PetLibroAPIError, PetLibroInvalidAuth, PetLibroLoginExpired


JSON: TypeAlias = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None
_LOGGER = getLogger(__name__)


class PetLibroSession:
    """PetLibro AIOHTTP session"""
    def __init__(self, base_url: str, websession: ClientSession, token : str | None = None):
        self.base_url = base_url
        self.websession = websession
        self.token = token
        self.headers = {
            "source": "ANDROID",
            "language": "EN",
            "timezone": "Europe/Paris",
            "version": "1.3.45",
        }

    async def request(self, method: str, url: str, **kwargs: Any) -> JSON:
        """Make a request."""
        joined_url = urljoin(self.base_url, url)
        _LOGGER.debug("Making %s request to %s", method, joined_url)

        if "headers" not in kwargs:
            kwargs["headers"] = {}

        # Add default headers
        headers = self.headers.copy()
        headers.update(kwargs["headers"].copy())
        kwargs["headers"] = headers

        if self.token is not None:
            kwargs["headers"]["token"] = self.token

        # The API require an empty JSON
        if "json" not in kwargs:
            kwargs["json"] = {}

        async with self.websession.request(method, joined_url, **kwargs) as resp:
            if resp.status != 200:
                raise PetLibroAPIError(resp.content)

            data = await resp.json()

            _LOGGER.debug(
                "Received %s response from %s: %s", resp.status, joined_url, data
            )

            if not data:
                raise PetLibroAPIError("No JSON data")

            if data.get("code") == 1102:
                raise PetLibroInvalidAuth()

            if data.get("code") == 1009:
                raise PetLibroLoginExpired()

            # Catch all other non 0 code
            if data.get("code") != 0:
                raise PetLibroAPIError(f"Code: {data.get('code')}, Message: {data.get('msg')}")

            return data.get("data")

    async def post(self, path: str, **kwargs: Any) -> JSON:
        """Post on PetLibro API"""
        return await self.request("POST", path, **kwargs)


class PetLibroAPI:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    APPID = 1
    APPSN = "c35772530d1041699c87fe62348507a8"
    API_URLS = {
        "US": "https://api.us.petlibro.com"
    }

    def __init__(self, session: ClientSession, time_zone: str, region: str,
                 token: str | None = None) -> None:
        """Initialize."""
        self.session = PetLibroSession(self.API_URLS[region], session, token)
        self.region = region
        self.time_zone = time_zone

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Generate the password hash for the API

        :param password: The password
        :return: Hashed password
        """
        return md5(password.encode("UTF-8")).hexdigest()

    async def login(self, email: str, password: str):
        """
        Login to the API

        :param email: The account email
        :param password_hash: The account password hash
        :raises PetLibroAPIError: In case of API error
        """
        data = await self.session.post("/member/auth/login", json={
            "appId": self.APPID,
            "appSn": self.APPSN,
            "country": self.region,
            "email": email,
            "password": self.hash_password(password),
            "phoneBrand": "",
            "phoneSystemVersion": "",
            "timezone": self.time_zone,
            "thirdId": None,
            "type": None
        })

        if not isinstance(data, dict) or "token" not in data or not isinstance(data["token"], str):
            raise PetLibroAPIError("No token")

        self.session.token = data["token"]

    async def logout(self):
        """
        Logout of the API
        """
        await self.session.post("/member/auth/logout")
        self.session.token = None

    async def list_devices(self) -> List[dict]:
        """
        List all account devices

        :raises PetLibroAPIError: In case of API error
        :return: List of devices
        """
        return await self.session.post("/device/device/list")  # type: ignore

    async def device_base_info(self, serial: str) -> Dict[str, Any]:
        return await self.session.post("/device/device/baseInfo", json= {
                "id": serial
            })  # type: ignore

    async def device_realInfo(self, serial: str) -> Dict[str, Any]:
        return await self.session.post("/device/device/realInfo", json={
                "id": serial
            })  # type: ignore
