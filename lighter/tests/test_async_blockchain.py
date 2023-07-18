import pytest
import asyncio

pytest_plugins = ("pytest_asyncio",)

from lighter.lighter_client import Client
from lighter.modules.blockchain import OrderSide

fake_orderbook_data = {
    "address": "0xd2a4684b4Eaf79AbcF352C3C6b46090c1f83819D",
    "blockchain_id": 420,
    "id": 0,
    "pow_price_tick": 100000,
    "pow_size_tick": 1000000000000000,
    "symbol": "WETH_USDC",
    "token0_address": "0x479eE06EDDF5e251AADb016fB5413dc032a25b6e",
    "token0_symbol": "WETH",
    "token1_address": "0xfe53c0Ed29422d7bc897a4bfDC16377DEa93717D",
    "token1_symbol": "USDC",
}


@pytest.fixture
def mocked_client(mocker) -> Client:
    mocker.patch("web3.main.Web3.HTTPProvider")
    mocker.patch("web3.main.Web3")
    mocker.patch(
        "lighter.modules.api.Api.get_orderbook_meta",
        return_value=[],
    )

    mocker.patch(
        "lighter.modules.api.Api.get_blockchains",
        return_value=[
            {
                "chain_id": "420",
                "router_address": "xxx",
                "factory_address": "xxx",
            }
        ],
    )

    mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain._get_orderbook",
        return_value=fake_orderbook_data,
    )

    mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain._get_token_pow_decimal",
        side_effect=lambda x: {"WETH": 10**18, "USDC": 10**6}[x],
    )

    client = Client(private_key="xxx", api_auth="xxx", web3_provider_url="xxx")
    client.blockchain_id = 420
    return client


@pytest.mark.asyncio
async def test_prepare_tokens(mocker, mocked_client: Client):
    mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain._get_orderbooks",
        return_value=[fake_orderbook_data],
    )

    token_contract_mock = mocker.MagicMock()

    def fn():
        class cls:
            async def call(self):
                return 1

        return cls()

    decimals_mock = fn
    token_contract_mock.functions.decimals = decimals_mock

    mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain._get_token_contract",
        return_value=token_contract_mock,
    )

    expected_tokens = {
        fake_orderbook_data["token0_symbol"]: {
            "symbol": fake_orderbook_data["token0_symbol"],
            "decimal": 1,
            "address": fake_orderbook_data["token0_address"],
            "pow_decimal": 10,
        },
        fake_orderbook_data["token1_symbol"]: {
            "symbol": fake_orderbook_data["token1_symbol"],
            "decimal": 1,
            "address": fake_orderbook_data["token1_address"],
            "pow_decimal": 10,
        },
    }

    result = await mocked_client.async_blockchain.prepare_tokens()

    assert result == expected_tokens


@pytest.mark.asyncio
async def test_create_limit_order_batch(mocker, mocked_client: Client):
    given_human_readable_amounts = ["0.001", "0.002", "0.003"]
    given_human_readable_prices = ["1000", "1000.2", "1000.3"]
    given_sides = [OrderSide.BUY, OrderSide.SELL, OrderSide.BUY]
    given_orderbook_symbol = fake_orderbook_data["symbol"]

    class cls:
        @property
        def address(self):
            return "0x123"

    mock_router_contract = mocker.AsyncMock(return_value=cls())

    mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain.router_contract",
        new_callable=mock_router_contract,
    )

    mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain._get_hint_ids",
        return_value=[1, 2, 3],
    )

    mocked_send = mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain._send_eth_transaction"
    )

    expected_data = "0x010003000000000000000100000000000027100000000001000000000000000200000000000027120100000002000000000000000300000000000027130000000003"
    expected_options = dict(
        options=dict(
            to="0x123",
            data=expected_data,
        )
    )

    await mocked_client.async_blockchain.create_limit_order_batch(
        given_orderbook_symbol,
        given_human_readable_amounts,
        given_human_readable_prices,
        given_sides,
    )

    assert mocked_send.call_args[1] == expected_options


@pytest.mark.asyncio
async def test_update_limit_order_batch(mocker, mocked_client: Client):
    given_order_ids = [3505, 3506, 3507]
    given_human_readable_amounts = ["0.001", "0.002", "0.003"]
    given_human_readable_prices = ["1000", "1000.2", "1000.3"]
    given_sides = [OrderSide.BUY, OrderSide.SELL, OrderSide.BUY]
    given_orderbook_symbol = fake_orderbook_data["symbol"]

    class cls:
        @property
        def address(self):
            return "0x123"

    mock_router_contract = mocker.AsyncMock(return_value=cls())

    mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain.router_contract",
        new_callable=mock_router_contract,
    )

    mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain._get_hint_ids",
        return_value=[1, 2, 3],
    )

    mocked_send = mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain._send_eth_transaction"
    )

    expected_data = "0x02000300000db1000000000000000100000000000027100000000100000db2000000000000000200000000000027120000000200000db30000000000000003000000000000271300000003"
    expected_options = dict(
        options=dict(
            to="0x123",
            data=expected_data,
        )
    )

    await mocked_client.async_blockchain.update_limit_order_batch(
        given_orderbook_symbol,
        given_order_ids,
        given_human_readable_amounts,
        given_human_readable_prices,
        given_sides,
    )

    assert mocked_send.call_args[1] == expected_options


@pytest.mark.asyncio
async def test_cancel_limit_order_batch(mocker, mocked_client: Client):
    given_order_ids = [3505, 3506, 3507]
    given_orderbook_symbol = fake_orderbook_data["symbol"]

    class cls:
        @property
        def address(self):
            return "0x123"

    mock_router_contract = mocker.AsyncMock(return_value=cls())

    mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain.router_contract",
        new_callable=mock_router_contract,
    )

    mocked_send = mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain._send_eth_transaction"
    )
    expected_data = "0x03000300000db100000db200000db3"
    expected_options = dict(
        options=dict(
            to="0x123",
            data=expected_data,
        )
    )

    await mocked_client.async_blockchain.cancel_limit_order_batch(
        given_orderbook_symbol, given_order_ids
    )

    assert mocked_send.call_args[1] == expected_options


@pytest.mark.asyncio
async def test_create_market_order(mocker, mocked_client: Client):
    given_human_readable_amount = "0.001"
    given_human_readable_price = "1000"
    given_side = OrderSide.BUY
    given_orderbook_symbol = fake_orderbook_data["symbol"]

    class cls:
        @property
        def address(self):
            return "0x123"

    mock_router_contract = mocker.AsyncMock(return_value=cls())

    mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain.router_contract",
        new_callable=mock_router_contract,
    )

    mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain._get_hint_ids",
        return_value=[1, 2, 3],
    )

    mocked_send = mocker.patch(
        "lighter.modules.blockchain.AsyncBlockchain._send_eth_transaction"
    )

    expected_data = "0x04000000000000000001000000000000271000"
    expected_options = dict(
        options=dict(
            to="0x123",
            data=expected_data,
        )
    )

    await mocked_client.async_blockchain.create_market_order(
        given_orderbook_symbol,
        given_human_readable_amount,
        given_human_readable_price,
        given_side,
    )

    assert mocked_send.call_args[1] == expected_options
