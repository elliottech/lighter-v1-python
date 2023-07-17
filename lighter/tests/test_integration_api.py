import pytest
import os

from lighter.lighter_client import Client
from lighter.constants import ORDERBOOK_WETH_USDC

TEST_OWNER_ADDRESS = "0xE425f4Dfe8b2446b686b2C5a7c17679b7170996e"


@pytest.fixture
def client() -> Client:
    API_KEY = os.environ.get("API_KEY")
    WEB3_URL = os.environ.get("WEB3_URL")
    return Client(api_auth=API_KEY, web3_provider_url=WEB3_URL)


def test_get_blockchains(client: Client):
    blockchains = client.api.get_blockchains()

    assert type(blockchains) == list
    assert len(blockchains) > 0


def test_get_orderbook_meta(client: Client):
    orderbook_meta = client.api.get_orderbook_meta()

    assert type(orderbook_meta) == list
    assert len(orderbook_meta) > 0


def test_get_orderbook(client: Client):
    orderbook = client.api.get_orderbook(ORDERBOOK_WETH_USDC)

    assert type(orderbook) == dict
    assert "symbol" in orderbook
    assert "asks" in orderbook
    assert "bids" in orderbook


def test_get_candles(client: Client):
    candles = client.api.get_candles(ORDERBOOK_WETH_USDC, 1687097397, 1687183683, "4h")

    assert type(candles) == dict
    assert "candlesticks" in candles
    assert type(candles["candlesticks"]) == list


def test_get_orders(client: Client):
    orders = client.api.get_orders(
        TEST_OWNER_ADDRESS,
        orderbook_symbol=ORDERBOOK_WETH_USDC,
        limit=1,
    )

    assert type(orders) == list
    assert len(orders) == 1


def test_get_trades(client: Client):
    trades = client.api.get_trades(
        owner=TEST_OWNER_ADDRESS,
        orderbook_symbol=ORDERBOOK_WETH_USDC,
        limit=1,
    )

    assert type(trades) == list


def test_get_gas_price(client: Client):
    gas_price = client.api.get_gas_price()

    assert "gas_price" in gas_price
    assert type(gas_price["gas_price"]) == int

def test_get_hint_ids(client: Client):
    hint_ids = client.api.get_hint_ids(
        orderbook_symbol=ORDERBOOK_WETH_USDC,
        prices=["1700", "1800"],
        sides=["buy", "sell"],
    )

    assert "hint_ids" in hint_ids
    assert len(hint_ids["hint_ids"]) == 2