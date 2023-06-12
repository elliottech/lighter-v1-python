import asyncio
import pytest
import os

from lighter.lighter_client import Client


@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> Client:
    API_KEY = os.environ.get("API_KEY")
    WEB3_URL = os.environ.get("WEB3_URL")
    return Client(api_auth=API_KEY, web3_provider_url=WEB3_URL)


@pytest.mark.asyncio
async def test_get_blockchains(client: Client):
    blockchains = await client.async_api.get_blockchains()

    assert "blockchains" in blockchains
    assert len(blockchains["blockchains"]) > 0


@pytest.mark.asyncio
async def test_get_blockchains(client: Client):
    blockchains = await client.async_api.get_blockchains()

    assert "blockchains" in blockchains
    assert len(blockchains["blockchains"]) > 0


@pytest.mark.asyncio
async def test_get_orderbook_meta(client: Client):
    orderbook_meta = await client.async_api.get_orderbook_meta()

    assert "orderbookmetas" in orderbook_meta
    assert len(orderbook_meta["orderbookmetas"]) > 0


@pytest.mark.asyncio
async def test_get_orderbook(client: Client):
    orderbook = await client.async_api.get_orderbook("WETH_USDC")

    assert "orderbooks" in orderbook
    assert len(orderbook["orderbooks"]) > 0


@pytest.mark.asyncio
async def test_get_candles(client: Client):
    candles = await client.async_api.get_candles("WETH_USDC", 1, 1686569768, 1686570368)

    assert "candles" in candles
    assert len(candles["candles"]) > 0


@pytest.mark.asyncio
async def test_get_orders(client: Client):
    orders = await client.async_api.get_orders(
        "0xE425f4Dfe8b2446b686b2C5a7c17679b7170996e", limit=1
    )

    assert "orders" in orders
    assert type(orders["orders"]) == dict

    assert "stats" in orders
    assert type(orders["stats"]) == dict


@pytest.mark.asyncio
async def test_get_trades(client: Client):
    trades = await client.async_api.get_trades(
        "0xE425f4Dfe8b2446b686b2C5a7c17679b7170996e", limit=1
    )

    assert "trades" in trades
    assert type(trades["trades"]) == dict


@pytest.mark.asyncio
async def test_get_gas_price(client: Client):
    gas_price = await client.async_api.get_gas_price()

    assert "gas_price" in gas_price
    assert type(gas_price["gas_price"]) == int


@pytest.mark.asyncio
async def test_get_volume(client: Client):
    volume = await client.async_api.get_volume(1686570368)

    assert type(volume) == dict
    assert "dailyVolume" in volume
    assert "totalVolume" in volume
