from typing import Optional, List
import aiohttp
import asyncio
import requests

from lighter.constants import DEFAULT_API_TIMEOUT
from lighter.constants import HOST
from lighter.errors import LighterApiError
from lighter.helpers.request_helpers import generate_query_path


class BaseApi(object):
    def __init__(
        self,
        host: str,
        blockchain_id: int,
        api_auth: str,
        api_timeout: Optional[int],
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        self.host = host
        self.blockchain_id = blockchain_id
        self.api_auth = api_auth

        self.api_timeout = (
            min(api_timeout, DEFAULT_API_TIMEOUT)
            if api_timeout
            else DEFAULT_API_TIMEOUT
        )
        self.loop = loop


class AsyncApi(BaseApi):
    def __init__(
        self, host: str, blockchain_id: int, api_auth: str, api_timeout: Optional[int]
    ):
        super().__init__(host, blockchain_id, api_auth, api_timeout)
        self.session = self._init_session()

    def _init_session(self) -> aiohttp.ClientSession:
        session = aiohttp.ClientSession(
            loop=self.loop,
            headers={
                "Accept": "application/json",
                "User-Agent": "lighter/python",
                "Auth": self.api_auth,
            },
        )
        return session

    async def close_connection(self):
        if self.session:
            assert self.session
            await self.session.close()

    # ============ Request Helpers ============
    async def _get(
        self,
        request_path: str,
        params: dict = {},
        to_public_api: Optional[bool] = True,
    ) -> dict:
        host = self.host + "/api/v1" if to_public_api else self.host
        url = generate_query_path(host + request_path, params)

        async with getattr(self.session, "get")(
            url, timeout=self.api_timeout
        ) as response:
            if not str(response.status).startswith("2"):
                raise LighterApiError(response)

            try:
                return await response.json()
            except:
                await self.close_connection()
                raise LighterApiError(f"Invalid response: {await response.text}")

    async def get_blockchains(self) -> dict:
        uri = "/blockchains"
        return await self._get(uri)

    async def get_orderbook_meta(self) -> dict:
        uri = "/orderbookmetas"
        return await self._get(uri, {"blockchain_id": self.blockchain_id})

    async def get_orderbook(self, orderbook_symbol: str) -> dict:
        uri = "/orderbook"
        return await self._get(
            uri,
            {"blockchain_id": self.blockchain_id, "orderbook_symbol": orderbook_symbol},
        )

    async def get_candles(
        self,
        orderbook_symbol: str,
        resolution: int,
        timestamp_start: int,
        timestamp_end: int,
    ) -> dict:
        uri = "/candles"
        return await self._get(
            uri,
            {
                "blockchain_id": self.blockchain_id,
                "orderbook_symbol": orderbook_symbol,
                "resolution_min": resolution,
                "start_timestamp": timestamp_start,
                "end_timestamp": timestamp_end,
            },
        )

    async def get_orders(
        self,
        owner: str,
        orderbook_symbol: Optional[str] = None,
        status: Optional[str] = None,
        type: Optional[str] = None,
        limit: Optional[int] = None,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
    ) -> dict:
        uri = "/orders"
        return await self._get(
            uri,
            {
                "blockchain_id": self.blockchain_id,
                "orderbook_symbol": orderbook_symbol,
                "owner": owner,
                "status": status,
                "type": type,
                "limit": limit,
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
            },
        )

    async def get_trades(
        self,
        owner: str,
        orderbook_symbol: Optional[str] = None,
        limit: Optional[int] = None,
        starting_before: Optional[int] = None,
    ) -> dict:
        uri = "/trades"
        return await self._get(
            uri,
            {
                "blockchain_id": self.blockchain_id,
                "orderbook_symbol": orderbook_symbol,
                "owner": owner,
                "limit": limit,
                "before": starting_before,
            },
        )

    async def _get_hint_ids(
        self, orderbook_symbol: str, prices: List[str], sides: List[str]
    ) -> dict:
        uri = "/hint_id"
        return await self._get(
            uri,
            {
                "blockchain_id": self.blockchain_id,
                "orderbook_symbol": orderbook_symbol,
                "prices": ",".join(prices),
                "sides": ",".join(sides),
            },
            False,
        )

    async def _get_gas_price(self) -> dict:
        uri = "/gas_price"
        return await self._get(
            uri,
            {
                "blockchain_id": self.blockchain_id,
            },
            False,
        )

    async def get_volume(self, timestamp: int) -> dict:
        uri = "/volume"
        return await self._get(
            uri, {"blockchain_id": self.blockchain_id, "timestamp": timestamp}, False
        )


class Api(BaseApi):
    def __init__(
        self,
        host: str,
        blockchain_id: int,
        api_auth: str,
        api_timeout: Optional[int],
    ):
        super().__init__(host, blockchain_id, api_auth, api_timeout)
        self.session = self._init_session()

    def _init_session(self) -> requests.Session:
        session = requests.session()
        session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "lighter/python",
                "Auth": self.api_auth,
            }
        )
        return session

    # ============ Request Helpers ============
    def _get(
        self,
        request_path: str,
        params: dict = {},
        to_public_api: Optional[bool] = True,
    ) -> dict:
        host = self.host + "/api/v1" if to_public_api else self.host
        url = generate_query_path(host + request_path, params)
        response = getattr(self.session, "get")(
            url,
        )

        if not str(response.status_code).startswith("2"):
            raise LighterApiError(response)

        try:
            return response.json()
        except:
            raise LighterApiError(f"Invalid response: {response.text}")

    # ============ Requests ============
    def get_blockchains(self) -> dict:
        uri = "/blockchains"
        return self._get(uri)

    def get_orderbook_meta(self) -> dict:
        uri = "/orderbookmetas"
        return self._get(uri, {"blockchain_id": self.blockchain_id})

    def get_orderbook(self, orderbook_symbol: str) -> dict:
        uri = "/orderbook"
        return self._get(
            uri,
            {"blockchain_id": self.blockchain_id, "orderbook_symbol": orderbook_symbol},
        )

    def get_candles(
        self,
        orderbook_symbol: str,
        resolution: int,
        timestamp_start: int,
        timestamp_end: int,
    ) -> dict:
        uri = "/candles"
        return self._get(
            uri,
            {
                "blockchain_id": self.blockchain_id,
                "orderbook_symbol": orderbook_symbol,
                "resolution_min": resolution,
                "start_timestamp": timestamp_start,
                "end_timestamp": timestamp_end,
            },
        )

    def get_orders(
        self,
        owner: str,
        orderbook_symbol: Optional[str] = None,
        status: Optional[str] = None,
        type: Optional[str] = None,
        limit: Optional[int] = None,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
    ) -> dict:
        uri = "/orders"
        return self._get(
            uri,
            {
                "blockchain_id": self.blockchain_id,
                "orderbook_symbol": orderbook_symbol,
                "owner": owner,
                "status": status,
                "type": type,
                "limit": limit,
                "start_timestamp": start_timestamp,
                "end_timestamp": end_timestamp,
            },
        )

    def get_trades(
        self,
        owner: str,
        orderbook_symbol: Optional[str] = None,
        limit: Optional[int] = None,
        starting_before: Optional[int] = None,
    ) -> dict:
        uri = "/trades"
        return self._get(
            uri,
            {
                "blockchain_id": self.blockchain_id,
                "orderbook_symbol": orderbook_symbol,
                "owner": owner,
                "limit": limit,
                "before": starting_before,
            },
        )

    def _get_hint_ids(
        self, orderbook_symbol: str, prices: List[str], sides: List[str]
    ) -> dict:
        uri = "/hint_id"
        return self._get(
            uri,
            {
                "blockchain_id": self.blockchain_id,
                "orderbook_symbol": orderbook_symbol,
                "prices": ",".join(prices),
                "sides": ",".join(sides),
            },
            False,
        )

    def _get_gas_price(self) -> dict:
        uri = "/gas_price"
        return self._get(
            uri,
            {
                "blockchain_id": self.blockchain_id,
            },
            False,
        )

    def get_volume(self, timestamp: int) -> dict:
        uri = "/volume"
        return self._get(
            uri, {"blockchain_id": self.blockchain_id, "timestamp": timestamp}, False
        )
