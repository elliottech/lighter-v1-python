import pytest
import os

from lighter.lighter_client import Client


@pytest.fixture
def client() -> Client:
    API_KEY = os.environ.get("API_KEY")
    WEB3_URL = os.environ.get("WEB3_URL")
    return Client(api_auth=API_KEY, web3_provider_url=WEB3_URL)


def test_get_blockchains(client: Client):
    blockchains = client.api.get_blockchains()

    assert "blockchains" in blockchains
    assert len(blockchains["blockchains"]) > 0


def test_get_orderbook_meta(client: Client):
    orderbook_meta = client.api.get_orderbook_meta()

    assert "orderbookmetas" in orderbook_meta
    assert len(orderbook_meta["orderbookmetas"]) > 0


def test_get_orderbook(client: Client):
    orderbook = client.api.get_orderbook("WETH_USDC")

    assert "orderbooks" in orderbook
    assert len(orderbook["orderbooks"]) > 0


def test_get_candles(client: Client):
    candles = client.api.get_candles("WETH_USDC", 1, 1686569768, 1686570368)

    assert "candles" in candles
    assert len(candles["candles"]) > 0


def test_get_orders(client: Client):
    orders = client.api.get_orders(
        "0xE425f4Dfe8b2446b686b2C5a7c17679b7170996e", limit=1
    )

    assert "orders" in orders
    assert type(orders["orders"]) == dict

    assert "stats" in orders
    assert type(orders["stats"]) == dict


def test_get_trades(client: Client):
    trades = client.api.get_trades(
        "0xE425f4Dfe8b2446b686b2C5a7c17679b7170996e", limit=1
    )

    assert "trades" in trades
    assert type(trades["trades"]) == dict


def test_get_gas_price(client: Client):
    gas_price = client.api.get_gas_price()

    assert "gas_price" in gas_price
    assert type(gas_price["gas_price"]) == int


def test_get_volume(client: Client):
    volume = client.api.get_volume(1686570368)

    assert type(volume) == dict
    assert "dailyVolume" in volume
    assert "totalVolume" in volume
