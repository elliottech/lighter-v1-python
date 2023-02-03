from typing import Optional, List

from lighter.constants import DEFAULT_API_TIMEOUT
from lighter.constants import HOST
from lighter.helpers.request_helpers import generate_query_path
from lighter.helpers.requests import request, Response


class Api(object):
    def __init__(
        self,
        host: str,
        blockchain_id: int,
        api_auth: str,
        api_timeout: Optional[int],
    ):
        self.host = host
        self.blockchain_id = blockchain_id
        self.api_auth = api_auth

        self.api_timeout = (
            min(api_timeout, DEFAULT_API_TIMEOUT)
            if api_timeout
            else DEFAULT_API_TIMEOUT
        )

    # ============ Request Helpers ============
    def _get(
        self,
        request_path: str,
        params: dict = {},
        to_public_api: Optional[bool] = True,
    ) -> Response:
        host = self.host + "/api/v1" if to_public_api else self.host

        return request(
            generate_query_path(host + request_path, params),
            "get",
            headers={"Auth": self.api_auth},
            api_timeout=self.api_timeout,
        )

    # ============ Requests ============
    def get_blockchains(self) -> Response:
        uri = "/blockchains"
        return self._get(uri)

    def get_orderbook_meta(self) -> Response:
        uri = "/orderbookmetas"
        return self._get(uri, {"blockchain_id": self.blockchain_id})

    def get_orderbook(self, orderbook_symbol: str) -> Response:
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
    ) -> Response:
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
    ) -> Response:
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
    ) -> Response:
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
    ) -> Response:
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

    def _get_gas_price(self) -> Response:
        uri = "/gas_price"
        return self._get(
            uri,
            {
                "blockchain_id": self.blockchain_id,
            },
            False,
        )
