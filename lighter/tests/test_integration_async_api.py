import asyncio
import pytest
import os

from lighter.lighter_client import Client
from lighter.constants import ORDERBOOK_WETH_USDC

TEST_OWNER_ADDRESS = "0xE425f4Dfe8b2446b686b2C5a7c17679b7170996e"


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

    assert type(blockchains) == list
    assert len(blockchains) > 0


@pytest.mark.asyncio
async def test_get_orderbook_meta(client: Client):
    orderbook_meta = await client.async_api.get_orderbook_meta()

    assert type(orderbook_meta) == list
    assert len(orderbook_meta) > 0


@pytest.mark.asyncio
async def test_get_orderbook(client: Client):
    orderbook = await client.async_api.get_orderbook(ORDERBOOK_WETH_USDC)

    assert type(orderbook) == dict
    assert "symbol" in orderbook
    assert "asks" in orderbook
    assert "bids" in orderbook


@pytest.mark.asyncio
async def test_get_candles(client: Client):
    candles = await client.async_api.get_candles(
        ORDERBOOK_WETH_USDC, 1687097397, 1687183683, "4h"
    )

    assert type(candles) == dict
    assert "candlesticks" in candles
    assert type(candles["candlesticks"]) == list


@pytest.mark.asyncio
async def test_get_orders(client: Client):
    orders = await client.async_api.get_orders(
        TEST_OWNER_ADDRESS,
        orderbook_symbol=ORDERBOOK_WETH_USDC,
        limit=1,
    )

    assert type(orders) == list
    assert len(orders) == 1


@pytest.mark.asyncio
async def test_get_trades(client: Client):
    trades = await client.async_api.get_trades(
        owner=TEST_OWNER_ADDRESS,
        orderbook_symbol=ORDERBOOK_WETH_USDC,
        limit=1,
    )

    assert type(trades) == list


@pytest.mark.asyncio
async def test_get_gas_price(client: Client):
    gas_price = await client.async_api.get_gas_price()

    assert "gas_price" in gas_price
    assert type(gas_price["gas_price"]) == int
