import pytest

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
        return_value={"orderbookmetas": []},
    )

    mocker.patch(
        "lighter.modules.api.Api.get_blockchains",
        return_value={
            "blockchains": [
                {
                    "chain_id": "420",
                    "router_address": "xxx",
                    "factory_address": "xxx",
                }
            ]
        },
    )

    mocker.patch(
        "lighter.modules.blockchain.Blockchain._get_orderbook",
        return_value=fake_orderbook_data,
    )

    mocker.patch(
        "lighter.modules.blockchain.Blockchain._get_token_pow_decimal",
        side_effect=lambda x: {"WETH": 10**18, "USDC": 10**6}[x],
    )

    client = Client(private_key="xxx", api_auth="xxx", web3_provider_url="xxx")
    client.blockchain_id = 420
    return client


def test_prepare_tokens(mocker, mocked_client: Client):
    mocker.patch(
        "lighter.modules.blockchain.Blockchain._get_orderbooks",
        return_value=[fake_orderbook_data],
    )

    token_contract_mock = mocker.MagicMock()
    token_contract_mock.functions.decimals.return_value.call.return_value = 1

    mocker.patch(
        "lighter.modules.blockchain.Blockchain._get_token_contract",
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

    result = mocked_client.blockchain.prepare_tokens()

    assert result == expected_tokens


def test_get_amount_base_with_correct_inputs(mocked_client: Client):
    given_amount = 10**18  # 1 ETH
    given_orderbook_symbol = fake_orderbook_data["symbol"]
    expected_amount_base = 1000

    assert (
        mocked_client.blockchain._get_amount_base(given_amount, given_orderbook_symbol)
        == expected_amount_base
    )


def test_get_amount_base_should_fail_with_wrong_size(mocked_client: Client):
    given_amount = 10**18 + 1

    with pytest.raises(ValueError):
        mocked_client.blockchain._get_amount_base(
            given_amount, fake_orderbook_data["symbol"]
        )


def test_get_price(mocked_client: Client):
    given_amount0 = 10**18
    given_amount1 = 10**9
    given_orderbook_symbol = fake_orderbook_data["symbol"]

    expected_result = "1000"

    assert (
        mocked_client.blockchain._get_price(
            given_amount0, given_amount1, given_orderbook_symbol
        )
        == expected_result
    )


def test_get_base_price(mocked_client: Client):
    given_price = "1000"
    given_token1 = fake_orderbook_data["token1_symbol"]
    given_orderbook_symbol = fake_orderbook_data["symbol"]

    expected_price_base = 10000

    assert (
        mocked_client.blockchain._get_price_base(
            given_price, given_token1, given_orderbook_symbol
        )
        == expected_price_base
    )


def test_get_base_price_should_raise_with_wrong_input(mocked_client: Client):
    given_price = "1000.22"
    given_token1 = fake_orderbook_data["token1_symbol"]
    given_orderbook_symbol = fake_orderbook_data["symbol"]

    with pytest.raises(ValueError):
        mocked_client.blockchain._get_price_base(
            given_price, given_token1, given_orderbook_symbol
        )


def test_get_amount1(mocked_client: Client):
    given_amount0 = 10**18
    given_price = "1000"
    given_token0 = fake_orderbook_data["token0_symbol"]
    given_token1 = fake_orderbook_data["token1_symbol"]

    expected_amount1 = 10**9

    assert (
        mocked_client.blockchain._get_amount1(
            given_amount0, given_price, given_token0, given_token1
        )
        == expected_amount1
    )


def test_get_amount1_should_raise_with_wrong_input(mocked_client: Client):
    given_amount0 = 10**18 + 1
    given_price = "1000"
    given_token0 = fake_orderbook_data["token0_symbol"]
    given_token1 = fake_orderbook_data["token1_symbol"]

    with pytest.raises(ValueError):
        mocked_client.blockchain._get_amount1(
            given_amount0, given_price, given_token0, given_token1
        )


def test_get_amount_from_human_readable(mocked_client: Client):
    given_human_readable_amount = "1"
    given_token_symbol = fake_orderbook_data["token0_symbol"]

    expected_amount = 10**18

    assert (
        mocked_client.blockchain._get_amount_from_human_readable(
            given_human_readable_amount, given_token_symbol
        )
        == expected_amount
    )


def test_get_human_readable_amount_from_amount(mocked_client: Client):
    given_amount = 10**18
    given_token_symbol = fake_orderbook_data["token0_symbol"]

    expected_human_readable_amount = "1"

    assert (
        mocked_client.blockchain._get_human_readable_amount_from_amount(
            given_amount, given_token_symbol
        )
        == expected_human_readable_amount
    )


def test_tick_check(mocked_client: Client):
    given_human_readable_amounts = ["1", "1.01", "0.001"]
    given_human_readable_prices = ["1000", "1000.1", "1000.3"]
    given_orderbook_symbol = fake_orderbook_data["symbol"]

    mocked_client.blockchain._tick_check(
        given_human_readable_amounts,
        given_human_readable_prices,
        given_orderbook_symbol,
    )


def test_tick_check_should_raise_with_wrong_size(mocked_client: Client):
    given_human_readable_amounts = ["1", "1.01", "0.0001"]
    given_human_readable_prices = ["1000", "1000.1", "1000.3"]
    given_orderbook_symbol = fake_orderbook_data["symbol"]

    with pytest.raises(ValueError):
        mocked_client.blockchain._tick_check(
            given_human_readable_amounts,
            given_human_readable_prices,
            given_orderbook_symbol,
        )


def test_tick_check_should_raise_with_wrong_price(mocked_client: Client):
    given_human_readable_amounts = ["1", "1.01", "0.001"]
    given_human_readable_prices = ["1000", "1000.1", "1000.21"]
    given_orderbook_symbol = fake_orderbook_data["symbol"]

    with pytest.raises(ValueError):
        mocked_client.blockchain._tick_check(
            given_human_readable_amounts,
            given_human_readable_prices,
            given_orderbook_symbol,
        )


def test_create_limit_order_batch(mocker, mocked_client: Client):
    given_human_readable_amounts = ["0.001", "0.002", "0.003"]
    given_human_readable_prices = ["1000", "1000.2", "1000.3"]
    given_sides = [OrderSide.BUY, OrderSide.SELL, OrderSide.BUY]
    given_orderbook_symbol = fake_orderbook_data["symbol"]

    mock_router_contract = mocker.MagicMock()
    mock_router_contract.address = "0x123"
    mocker.patch(
        "lighter.modules.blockchain.Blockchain.router_contract",
        new_callable=mocker.PropertyMock,
        return_value=mock_router_contract,
    )

    mocker.patch(
        "lighter.modules.blockchain.Blockchain._get_hint_ids", return_value=[1, 2, 3]
    )

    mocked_send = mocker.patch(
        "lighter.modules.blockchain.Blockchain._send_eth_transaction"
    )

    expected_data = "0x010003000000000000000100000000000027100000000001000000000000000200000000000027120100000002000000000000000300000000000027130000000003"
    expected_options = dict(
        options=dict(
            to="0x123",
            data=expected_data,
        )
    )

    mocked_client.blockchain.create_limit_order_batch(
        given_orderbook_symbol,
        given_human_readable_amounts,
        given_human_readable_prices,
        given_sides,
    )

    assert mocked_send.call_args[1] == expected_options


def test_update_limit_order_batch(mocker, mocked_client: Client):
    given_order_ids = [3505, 3506, 3507]
    given_human_readable_amounts = ["0.001", "0.002", "0.003"]
    given_human_readable_prices = ["1000", "1000.2", "1000.3"]
    given_sides = [OrderSide.BUY, OrderSide.SELL, OrderSide.BUY]
    given_orderbook_symbol = fake_orderbook_data["symbol"]

    mock_router_contract = mocker.MagicMock()
    mock_router_contract.address = "0x123"
    mocker.patch(
        "lighter.modules.blockchain.Blockchain.router_contract",
        new_callable=mocker.PropertyMock,
        return_value=mock_router_contract,
    )

    mocker.patch(
        "lighter.modules.blockchain.Blockchain._get_hint_ids", return_value=[1, 2, 3]
    )

    mocked_send = mocker.patch(
        "lighter.modules.blockchain.Blockchain._send_eth_transaction"
    )

    expected_data = "0x02000300000db1000000000000000100000000000027100000000100000db2000000000000000200000000000027120000000200000db30000000000000003000000000000271300000003"
    expected_options = dict(
        options=dict(
            to="0x123",
            data=expected_data,
        )
    )

    mocked_client.blockchain.update_limit_order_batch(
        given_orderbook_symbol,
        given_order_ids,
        given_human_readable_amounts,
        given_human_readable_prices,
        given_sides,
    )

    assert mocked_send.call_args[1] == expected_options


def test_cancel_limit_order_batch(mocker, mocked_client: Client):
    given_order_ids = [3505, 3506, 3507]
    given_orderbook_symbol = fake_orderbook_data["symbol"]

    mock_router_contract = mocker.MagicMock()
    mock_router_contract.address = "0x123"
    mocker.patch(
        "lighter.modules.blockchain.Blockchain.router_contract",
        new_callable=mocker.PropertyMock,
        return_value=mock_router_contract,
    )

    mocked_send = mocker.patch(
        "lighter.modules.blockchain.Blockchain._send_eth_transaction"
    )
    expected_data = "0x03000300000db100000db200000db3"
    expected_options = dict(
        options=dict(
            to="0x123",
            data=expected_data,
        )
    )

    mocked_client.blockchain.cancel_limit_order_batch(
        given_orderbook_symbol, given_order_ids
    )

    assert mocked_send.call_args[1] == expected_options


def test_create_market_order(mocker, mocked_client: Client):
    given_human_readable_amount = "0.001"
    given_human_readable_price = "1000"
    given_side = OrderSide.BUY
    given_orderbook_symbol = fake_orderbook_data["symbol"]

    mock_router_contract = mocker.MagicMock()
    mock_router_contract.address = "0x123"
    mocker.patch(
        "lighter.modules.blockchain.Blockchain.router_contract",
        new_callable=mocker.PropertyMock,
        return_value=mock_router_contract,
    )

    mocker.patch(
        "lighter.modules.blockchain.Blockchain._get_hint_ids", return_value=[1, 2, 3]
    )

    mocked_send = mocker.patch(
        "lighter.modules.blockchain.Blockchain._send_eth_transaction"
    )

    expected_data = "0x04000000000000000001000000000000271000"
    expected_options = dict(
        options=dict(
            to="0x123",
            data=expected_data,
        )
    )

    mocked_client.blockchain.create_market_order(
        given_orderbook_symbol,
        given_human_readable_amount,
        given_human_readable_price,
        given_side,
    )

    assert mocked_send.call_args[1] == expected_options
