from enum import Enum
import json
import decimal
import os
from typing import Any, Dict, List, Optional, TypedDict, Union
from hexbytes import (
    HexBytes,
)
from web3 import Web3
from web3.contract import Contract, ContractFunction
from web3.types import TxParams, TxReceipt, _Hash32, EventData
from eth_account.signers.local import LocalAccount
from eth_account.datastructures import SignedTransaction
from decimal import Decimal
from web3.logs import DISCARD

from lighter.constants import DEFAULT_GAS_AMOUNT
from lighter.constants import DEFAULT_GAS_MULTIPLIER
from lighter.constants import DEFAULT_GAS_PRICE
from lighter.constants import DEFAULT_GAS_PRICE_ADDITION
from lighter.constants import MAX_SOLIDITY_UINT
from lighter.errors import TransactionReverted
from collections.abc import Iterable

from lighter.modules.api import Api

ERC20_ABI = "abi/erc20.json"
ROUTER_ABI = "abi/router.json"
FACTORY_ABI = "abi/factory.json"
ORDERBOOK_ABI = "abi/orderbook.json"

Orderbook = TypedDict(
    "Orderbook",
    {
        "address": str,
        "id": int,
        "pow_price_tick": int,
        "pow_size_tick": int,
        "symbol": str,
        "token0_address": str,
        "token0_symbol": str,
        "token1_address": str,
        "token1_symbol": str,
    },
)


Token = TypedDict(
    "Token", {"symbol": str, "decimal": int, "address": str, "pow_decimal": int}
)


class OrderStatus(Enum):
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderSide(Enum):
    SELL = "SELL"
    BUY = "BUY"


OrderCreatedEvent = TypedDict(
    "OrderCreatedEvent",
    {
        "orderbook": str,
        "order_id": int,
        "size": str,
        "price": str,
        "type": OrderType,
        "side": OrderSide,
    },
)

OrderCanceledEvent = TypedDict(
    "OrderCanceledEvent",
    {
        "orderbook": str,
        "order_id": int,
        "size": str,
        "price": str,
        "type": OrderType,
        "status": OrderStatus,
        "side": OrderSide,
    },
)


TradeEvent = TypedDict(
    "TradeEvent", {"size": str, "price": str, "ask_id": str, "bid_id": str}
)

ProcessedTransactionReceipt = TypedDict(
    "ProcessedTransactionReceipt",
    {
        "limit_order_created_events": List[OrderCreatedEvent],
        "limit_order_canceled_event": List[OrderCanceledEvent],
        "market_order_created_events": List[OrderCreatedEvent],
        "trade_events": List[TradeEvent],
    },
)

# ====== Method return types
OrderCreated = TypedDict(
    "LimitOrderCreated",
    {
        "orderbook": str,
        "order_id": int,
        "size": str,
        "filled_size": str,
        "price": str,
        "status": OrderStatus,
        "type": OrderType,
        "side": OrderSide,
        "fills": List[TradeEvent],
    },
)


LimitOrderCanceled = TypedDict(
    "LimitOrderCanceled",
    {
        "orderbook": str,
        "order_id": int,
        "size": str,
        "price": str,
        "status": OrderStatus,
        "type": OrderType,
        "side": OrderSide,
    },
)

Order = TypedDict(
    "Order",
    {
        "id": int,
        "owner": str,
        "size": str,
        "price": str,
        "type": OrderType,
        "status": OrderStatus,
        "side": OrderSide,
    },
)

OrderbookOrders = TypedDict(
    "OrderbookOrders", {"asks": List[Order], "bids": List[Order]}
)


class Blockchain(object):
    def __init__(
        self,
        web3: Web3,
        blockchain_id: int,
        orderbooks: List[Orderbook],  # client gives this, by getting it from api
        private_key: str,
        api: Api,
        router_address: str,
        factory_address: str,
        send_options: Any,
    ):
        self.web3 = web3
        self.id = blockchain_id
        self.private_key = private_key
        self._api = api
        self.router_address = router_address
        self.factory_address = factory_address
        self.send_options = send_options

        self.cached_contracts = {}
        self._next_nonce_for_address: Dict[str, int] = {}
        self._account = None

        self._orderbooks = {orderbook["symbol"]: orderbook for orderbook in orderbooks}
        self._tokens = self.prepare_tokens()

    def prepare_tokens(self) -> Dict[str, Token]:
        result: Dict[str, Token] = {}
        for orderbook in self._get_orderbooks():
            if orderbook["token0_symbol"] not in result:
                token_contract = self._get_token_contract(
                    orderbook["token0_symbol"], orderbook["token0_address"]
                )
                decimal = token_contract.functions.decimals().call()
                result[orderbook["token0_symbol"]] = {
                    "symbol": orderbook["token0_symbol"],
                    "address": orderbook["token0_address"],
                    "decimal": decimal,
                    "pow_decimal": 10**decimal,
                }
            if orderbook["token1_symbol"] not in result:
                token_contract = self._get_token_contract(
                    orderbook["token1_symbol"], orderbook["token1_address"]
                )
                decimal = token_contract.functions.decimals().call()
                result[orderbook["token1_symbol"]] = {
                    "symbol": orderbook["token1_symbol"],
                    "address": orderbook["token1_address"],
                    "decimal": decimal,
                    "pow_decimal": 10**decimal,
                }

        return result

    @property
    def account(self) -> LocalAccount:
        if not self._account:
            self._account = self.web3.eth.account.from_key(self.private_key)
        return self._account

    @property
    def router_contract(self) -> Contract:
        contract_address = Web3.toChecksumAddress(self.router_address)
        return self._get_contract(contract_address, ROUTER_ABI)

    @property
    def factory_contract(self) -> Contract:
        contract_address = Web3.toChecksumAddress(self.factory_address)
        return self._get_contract(contract_address, FACTORY_ABI)

    def orderbook_contract(self, orderbook_symbol: str) -> Contract:
        orderbooks = self._get_orderbooks()
        orderbook = next(
            (item for item in orderbooks if item["symbol"] == orderbook_symbol), None
        )
        if orderbook is None:
            raise ValueError(
                "No orderbook {} contract on blockchain {}".format(
                    orderbook_symbol,
                    self.id,
                )
            )

        contract_address = orderbook["address"]
        contract_address = Web3.toChecksumAddress(contract_address)
        return self._get_contract(contract_address, ORDERBOOK_ABI)

    def _get_orderbooks(self) -> List[Orderbook]:
        return list(self._orderbooks.values())

    def _get_orderbook(self, symbol: str) -> Orderbook:
        orderbook = self._orderbooks.get(symbol)
        if not orderbook:
            raise ValueError(
                "Orderbook: {} is not supported in the exchange".format(symbol)
            )

        return orderbook

    def _get_tokens(self) -> List[Token]:
        return list(self._tokens.values())

    def _get_token(self, token: str) -> Token:
        tkn = self._tokens.get(token)
        if not tkn:
            raise ValueError("Token: {} is not supported in the exchange".format(token))

        return tkn

    def _get_token_pow_decimal(self, token: str) -> int:
        return self._get_token(token)["pow_decimal"]

    def _get_amount_base(self, amount: int, orderbook_symbol: str) -> int:
        orderbook = self._get_orderbook(orderbook_symbol)
        amount_base = Decimal(amount) / Decimal(orderbook["pow_size_tick"])
        if amount_base == 0 or amount_base % 1 != 0:
            raise ValueError("Invalid Value {}".format(amount))

        return int(amount_base)

    def _get_price(self, amount0: int, amount1: int, orderbook_symbol: str) -> str:
        orderbook = self._get_orderbook(orderbook_symbol)
        token0_pow_decimal = self._get_token_pow_decimal(orderbook["token0_symbol"])
        token1_pow_decimal = self._get_token_pow_decimal(orderbook["token1_symbol"])

        return str(
            Decimal(amount1 * token0_pow_decimal)
            / Decimal(amount0)
            / Decimal(token1_pow_decimal)
        )

    def _get_price_base(self, price: str, token1: str, orderbook_symbol: str) -> int:
        token1_pow_decimals = self._get_token_pow_decimal(token1)
        orderbook = self._get_orderbook(orderbook_symbol)

        pow_price_tick = orderbook["pow_price_tick"]
        price_base = (
            Decimal(price) * Decimal(token1_pow_decimals) / Decimal(pow_price_tick)
        )

        if price_base == 0 or price_base % 1 != 0:
            raise ValueError(
                "invalid price base value {} for orderbook {}".format(
                    str(price_base), orderbook_symbol
                )
            )

        return int(price_base)

    def _get_amount1(self, amount0: int, price: str, token0: str, token1: str) -> int:
        pow_token0_decimals = self._get_token_pow_decimal(token0)
        pow_token1_decimals = self._get_token_pow_decimal(token1)

        amount1 = (
            Decimal(price)
            * Decimal(amount0)
            * Decimal(pow_token1_decimals)
            / Decimal(pow_token0_decimals)
        )

        if amount1 == 0 or amount1 % 1 != 0:
            raise ValueError("Invalid value {}, price {}".format(str(amount1), price))

        return int(amount1)

    def _get_amount_from_human_readable(
        self, human_readable_amount: str, token_symbol: str
    ) -> int:
        amount = Decimal(human_readable_amount) * Decimal(
            self._get_token_pow_decimal(token_symbol)
        )

        if amount == 0 or amount % 1 != 0:
            raise ValueError("Invalid value {}".format(str(amount)))

        return int(amount)

    def _get_human_readable_amount_from_amount(
        self, amount: int, token_symbol: str
    ) -> str:
        return str(
            (Decimal(amount) / Decimal(self._get_token_pow_decimal(token_symbol)))
        )

    def _create_contract(
        self,
        address: str,
        file_path: str,
    ) -> Contract:
        lighter_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
        )

        address = Web3.toChecksumAddress(address)
        return self.web3.eth.contract(
            address=address,
            abi=json.load(open(os.path.join(lighter_folder, file_path), "r")),
        )

    def _get_contract(
        self,
        address: str,
        file_path: str,
    ) -> Contract:
        if address not in self.cached_contracts:
            self.cached_contracts[address] = self._create_contract(
                address,
                file_path,
            )
        return self.cached_contracts[address]

    def _get_token_contract(
        self, token: str, token_address: Optional[str] = None
    ) -> Contract:
        token_address = token_address or self._get_token(token)["address"]
        token_address = Web3.toChecksumAddress(token_address)
        return self._get_contract(token_address, ERC20_ABI)

    def _get_next_nonce(
        self,
        address: Optional[str],
    ) -> int:
        if not address:
            address = self.account.address
        if not address:
            raise ValueError("No address")
        if self._next_nonce_for_address.get(address) is None:
            self._next_nonce_for_address[address] = self.web3.eth.getTransactionCount(
                address
            )
        return self._next_nonce_for_address[address]

    def _sign_tx(
        self,
        method: Optional[ContractFunction],
        options: Optional[TxParams],
    ) -> SignedTransaction:
        if method is None:
            tx = options
        else:
            tx = method.buildTransaction(options)
        return self.web3.eth.account.sign_transaction(
            tx,
            self.private_key,
        )

    def _wait_for_tx(
        self,
        tx_hash: _Hash32,
    ) -> TxReceipt:
        """
        Wait for a tx to be mined and return the receipt. Raise on revert.

        :param tx_hash: required
        :type tx_hash: number

        :returns: transactionReceipt

        :raises: TransactionReverted
        """
        tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        if tx_receipt["status"] == 0:
            raise TransactionReverted(tx_receipt)

        return tx_receipt

    def _send_eth_transaction(
        self,
        method: Optional[ContractFunction] = None,
        options: Any = None,
    ) -> HexBytes:
        options = dict(self.send_options, **(options or {}))

        options["chainId"] = self.id

        if "from" not in options:
            options["from"] = self.account.address
        if options.get("from") is None:
            raise ValueError(
                "options['from'] is not set, and no default address is set",
            )
        auto_detect_nonce = "nonce" not in options
        if auto_detect_nonce:
            options["nonce"] = self._get_next_nonce(options["from"])
        if "gasPrice" not in options:
            try:
                g = self._get_gas_price()
                options["gasPrice"] = g + DEFAULT_GAS_PRICE_ADDITION
            except Exception:
                options["gasPrice"] = DEFAULT_GAS_PRICE
        if "value" not in options:
            options["value"] = 0
        gas_multiplier = options.pop("gasMultiplier", DEFAULT_GAS_MULTIPLIER)
        if "gas" not in options and method:
            try:
                options["gas"] = int(method.estimateGas(options) * gas_multiplier)
            except Exception:
                options["gas"] = DEFAULT_GAS_AMOUNT

        signed = self._sign_tx(method, options)
        try:
            tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)

        except ValueError as error:
            while auto_detect_nonce and (
                "nonce too low" in str(error)
                or "replacement transaction underpriced" in str(error)
            ):
                try:
                    options["nonce"] += 1
                    signed = self._sign_tx(method, options)
                    tx_hash = self.web3.eth.sendRawTransaction(
                        signed.rawTransaction,
                    )
                except ValueError as inner_error:
                    error = inner_error
                else:
                    break  # Break on success...
            else:
                raise error  # ...and raise error otherwise.

        # Update next nonce for the account.
        self._next_nonce_for_address[options["from"]] = options["nonce"] + 1

        return tx_hash

    def _process_transaction_events(
        self, tx_hash: HexBytes, orderbook_symbol: str
    ) -> ProcessedTransactionReceipt:
        orderbook_contract = self.orderbook_contract(orderbook_symbol)
        orderbook = self._get_orderbook(orderbook_symbol)

        receipt = self._wait_for_tx(tx_hash)

        limit_order_created_events: Iterable[
            EventData
        ] = orderbook_contract.events.LimitOrderCreated().processReceipt(
            receipt, errors=DISCARD
        )

        processed_limit_order_created_events = self._process_order_created_events(
            limit_order_created_events, orderbook
        )

        market_order_created_events: Iterable[
            EventData
        ] = orderbook_contract.events.MarketOrderCreated().processReceipt(
            receipt, errors=DISCARD
        )

        processed_market_order_created_events = self._process_order_created_events(
            market_order_created_events, orderbook
        )

        limit_order_canceled_events = (
            orderbook_contract.events.LimitOrderCanceled().processReceipt(
                receipt, errors=DISCARD
            )
        )

        processed_limit_order_cancelled_events = self._process_order_cancelled_event(
            limit_order_canceled_events, orderbook
        )

        trade_events: Iterable[
            EventData
        ] = orderbook_contract.events.Swap().processReceipt(receipt, errors=DISCARD)

        processed_trade_events = self._process_trade_events(trade_events, orderbook)

        return {
            "limit_order_created_events": processed_limit_order_created_events,
            "market_order_created_events": processed_market_order_created_events,
            "limit_order_canceled_event": processed_limit_order_cancelled_events,
            "trade_events": processed_trade_events,
        }

    def _process_order_created_events(
        self, events: Iterable[EventData], orderbook: Orderbook
    ) -> List[OrderCreatedEvent]:
        result: List[OrderCreatedEvent] = []

        for event in events:
            result.append(
                {
                    "orderbook": orderbook["symbol"],
                    "order_id": event["args"]["id"],
                    "size": self._get_human_readable_amount_from_amount(
                        event["args"]["amount0"], orderbook["token0_symbol"]
                    ),
                    "price": self._get_price(
                        event["args"]["amount0"],
                        event["args"]["amount1"],
                        orderbook["symbol"],
                    ),
                    "type": OrderType.LIMIT
                    if event["event"] == "LimitOrderCreated"
                    else OrderType.MARKET,
                    "side": OrderSide.SELL if event["args"]["isAsk"] else OrderSide.BUY,
                }
            )

        return result

    def _process_order_cancelled_event(
        self, events: Iterable[EventData], orderbook: Orderbook
    ) -> List[OrderCanceledEvent]:
        result: List[LimitOrderCanceled] = []

        for event in events:
            result.append(
                {
                    "orderbook": orderbook["symbol"],
                    "order_id": event["args"]["id"],
                    "size": self._get_human_readable_amount_from_amount(
                        event["args"]["amount0"], orderbook["token0_symbol"]
                    ),
                    "price": self._get_price(
                        event["args"]["amount0"],
                        event["args"]["amount1"],
                        orderbook["symbol"],
                    ),
                    "type": OrderType.LIMIT,
                    "side": OrderSide.SELL if event["args"]["isAsk"] else OrderSide.BUY,
                    "status": OrderStatus.CANCELED,
                }
            )

        return result

    def _process_trade_events(
        self, events: Iterable[EventData], orderbook: Orderbook
    ) -> List[TradeEvent]:
        result: List[TradeEvent] = []

        for event in events:
            result.append(
                {
                    "size": self._get_human_readable_amount_from_amount(
                        event["args"]["amount0"], orderbook["token0_symbol"]
                    ),
                    "price": self._get_price(
                        event["args"]["amount0"],
                        event["args"]["amount1"],
                        orderbook["symbol"],
                    ),
                    "ask_id": event["args"]["askId"],
                    "bid_id": event["args"]["bidId"],
                }
            )

        return result

    def get_create_order_transaction_result(
        self,
        tx_hash: HexBytes,
        orderbook_symbol: str,
        processed_events: Optional[ProcessedTransactionReceipt] = None,
    ) -> List[OrderCreated]:
        processed_events = (
            processed_events
            if processed_events
            else self._process_transaction_events(tx_hash, orderbook_symbol)
        )

        result: List[OrderCreated] = []

        order_created_events = (
            processed_events["limit_order_created_events"]
            + processed_events["market_order_created_events"]
        )
        trade_events = processed_events["trade_events"]

        for created_event in order_created_events:
            if created_event["side"] == OrderSide.SELL:
                fills = [
                    fill
                    for fill in trade_events
                    if fill["ask_id"] == created_event["order_id"]
                ]
            else:
                fills = [
                    fill
                    for fill in trade_events
                    if fill["bid_id"] == created_event["order_id"]
                ]

            fill_size = str(sum(Decimal(fill["size"]) for fill in fills))

            result.append(
                {
                    "orderbook": orderbook_symbol,
                    "order_id": created_event["order_id"],
                    "size": created_event["size"],
                    "filled_size": fill_size,
                    "price": created_event["price"],
                    "status": OrderStatus.FILLED
                    if fill_size == created_event["size"]
                    else OrderStatus.PARTIALLY_FILLED,
                    "type": created_event["type"],
                    "side": created_event["side"],
                    "fills": fills,
                }
            )

        return result

    def get_limit_order_canceled_transaction_result(
        self,
        tx_hash: HexBytes,
        orderbook_symbol: str,
        processed_events: Optional[ProcessedTransactionReceipt] = None,
    ) -> List[LimitOrderCanceled]:
        processed_events = (
            processed_events
            if processed_events
            else self._process_transaction_events(tx_hash, orderbook_symbol)
        )

        result: List[LimitOrderCanceled] = []

        limit_order_canceled_events = processed_events["limit_order_canceled_event"]

        for canceled_event in limit_order_canceled_events:
            result.append(
                {
                    "orderbook": orderbook_symbol,
                    "order_id": canceled_event["order_id"],
                    "size": canceled_event["size"],
                    "price": canceled_event["price"],
                    "status": OrderStatus.CANCELED,
                    "type": OrderType.LIMIT,
                    "side": canceled_event["side"],
                }
            )

        return result

    def get_update_limit_order_transaction_result(
        self, tx_hash: HexBytes, orderbook_symbol: str
    ) -> List[Union[OrderCreated, LimitOrderCanceled]]:
        result: List[Union[OrderCreated, LimitOrderCanceled]] = []
        events = self._process_transaction_events(tx_hash, orderbook_symbol)

        created_results = self.get_create_order_transaction_result(
            tx_hash, orderbook_symbol, events
        )
        result.extend(created_results)
        cancelled_results = self.get_limit_order_canceled_transaction_result(
            tx_hash, orderbook_symbol, events
        )
        result.extend(cancelled_results)

        return result

    # -----------------------------------------------------------
    # Transactions
    # -----------------------------------------------------------
    def _tick_check(
        self,
        human_readable_sizes: List[str],
        human_readable_prices: List[str],
        orderbook_symbol: str,
    ) -> None:
        orderbook = self._get_orderbook(orderbook_symbol)

        for i in range(len(human_readable_prices)):
            size = human_readable_sizes[i]
            price = human_readable_prices[i]

            if (
                Decimal(size) == 0
                or (
                    Decimal(size)
                    * Decimal(self._get_token_pow_decimal(orderbook["token0_symbol"]))
                )
                % Decimal(orderbook["pow_size_tick"])
                != 0
            ):
                raise ValueError(
                    "Invalid size {}, size should be multiple of size thick {}".format(
                        size, orderbook["pow_size_tick"]
                    )
                )

            if (
                Decimal(price) == 0
                or (
                    Decimal(price)
                    * Decimal(self._get_token_pow_decimal(orderbook["token1_symbol"]))
                )
                % Decimal(orderbook["pow_price_tick"])
                != 0
            ):
                raise ValueError(
                    "Invalid price {}, price should be multiple of price thick {}".format(
                        price, orderbook["pow_price_tick"]
                    )
                )

    def create_limit_order_batch(
        self,
        orderbook_symbol: str,
        human_readable_sizes: List[str],
        human_readable_prices: List[str],
        sides: List[OrderSide],
    ) -> HexBytes:
        self._tick_check(human_readable_sizes, human_readable_prices, orderbook_symbol)
        orderbook = self._get_orderbook(orderbook_symbol)

        sizes = [
            self._get_amount_from_human_readable(size, orderbook["token0_symbol"])
            for size in human_readable_sizes
        ]

        hint_ids = self._get_hint_ids(orderbook_symbol, human_readable_prices, sides)

        amount_bases = [
            self._get_amount_base(size, orderbook["symbol"]) for size in sizes
        ]

        price_bases = [
            self._get_price_base(price, orderbook["token1_symbol"], orderbook_symbol)
            for price in human_readable_prices
        ]

        orders_data = "".join(
            "{:016x}{:016x}{:02x}{:08x}".format(
                amount_base, price_base, side == OrderSide.SELL, hint_id
            )
            for amount_base, price_base, side, hint_id in zip(
                amount_bases, price_bases, sides, hint_ids
            )
        )

        data = "0x01{:02x}{:02x}{}".format(orderbook["id"], len(sizes), orders_data)

        options = dict(
            to=self.router_contract.address,
            data=data,
            gas=4000000,
        )

        return self._send_eth_transaction(options=options)

    def update_limit_order_batch(
        self,
        orderbook_symbol: str,
        order_ids: List[int],
        human_readable_sizes: List[str],
        human_readable_prices: List[str],
        old_sides: List[OrderSide],
    ) -> HexBytes:
        self._tick_check(human_readable_sizes, human_readable_prices, orderbook_symbol)

        orderbook = self._get_orderbook(orderbook_symbol)

        sizes = [
            self._get_amount_from_human_readable(size, orderbook["token0_symbol"])
            for size in human_readable_sizes
        ]

        hint_ids = self._get_hint_ids(
            orderbook_symbol, human_readable_prices, old_sides
        )

        amount_bases = [
            self._get_amount_base(size, orderbook["symbol"]) for size in sizes
        ]

        price_bases = [
            self._get_price_base(price, orderbook["token1_symbol"], orderbook_symbol)
            for price in human_readable_prices
        ]

        orders_data = "".join(
            "{:08x}{:016x}{:016x}{:08x}".format(
                order_id, amount_base, price_base, hint_id
            )
            for order_id, amount_base, price_base, hint_id in zip(
                order_ids, amount_bases, price_bases, hint_ids
            )
        )

        data = "0x02{:02x}{:02x}{}".format(orderbook["id"], len(sizes), orders_data)

        options = dict(
            to=self.router_contract.address,
            data=data,
            gas=4000000,
        )

        return self._send_eth_transaction(options=options)

    def cancel_limit_order_batch(
        self, orderbook_symbol: str, order_ids: List[int]
    ) -> HexBytes:
        orderbook = self._get_orderbook(orderbook_symbol)

        orders_data = "".join("{:08x}".format(order_id) for order_id in order_ids)

        data = "0x03{:02x}{:02x}{}".format(orderbook["id"], len(order_ids), orders_data)

        options = dict(
            to=self.router_contract.address,
            data=data,
            gas=4000000,
        )

        return self._send_eth_transaction(options=options)

    def create_market_order(
        self,
        orderbook_symbol: str,
        human_readable_size: str,
        human_readable_price: str,
        side: OrderSide,
    ) -> HexBytes:
        self._tick_check(
            [human_readable_size], [human_readable_price], orderbook_symbol
        )
        orderbook = self._get_orderbook(orderbook_symbol)

        size = self._get_amount_from_human_readable(
            human_readable_size, orderbook["token0_symbol"]
        )

        amount_base = self._get_amount_base(size, orderbook["symbol"])

        price_base = self._get_price_base(
            human_readable_price, orderbook["token1_symbol"], orderbook_symbol
        )

        orders_data = "{:016x}{:016x}{:02x}".format(
            amount_base, price_base, side == OrderSide.SELL
        )

        data = "0x04{:02x}{}".format(orderbook["id"], orders_data)

        options = dict(
            to=self.router_contract.address,
            data=data,
            gas=4000000,
        )

        return self._send_eth_transaction(options=options)

    def set_token_max_allowance(
        self,
        spender: str,
        token: str,
        send_options: Any = None,
    ) -> HexBytes:
        contract = self._get_token_contract(token)
        return self._send_eth_transaction(
            method=contract.functions.approve(
                spender,
                MAX_SOLIDITY_UINT,
            ),
            options=send_options,
        )

    # -----------------------------------------------------------
    # Getters
    # -----------------------------------------------------------
    def _get_hint_ids(
        self, orderbook_symbol: str, prices: List[str], sides: List[OrderSide]
    ) -> List[int]:
        orderbook = self._get_orderbook(orderbook_symbol)
        sides_str = [side.value.lower() for side in sides]
        return self._api._get_hint_ids(orderbook["symbol"], prices, sides_str).data[
            "hint_ids"
        ]

    def _get_gas_price(self) -> int:
        return self._api._get_gas_price().data["gas_price"]

    def get_eth_balance(
        self,
        owner: Optional[str] = None,
    ) -> Union[int, decimal.Decimal]:
        owner = owner or self.account.address
        if owner is None:
            raise ValueError(
                "owner was not provided, and no default address is set",
            )

        wei_balance = self.web3.eth.getBalance(owner)
        return Web3.fromWei(wei_balance, "ether")

    def get_token_balance(
        self,
        owner: Optional[str],
        token: str,
    ) -> int:
        owner = owner or self.account.address
        if owner is None:
            raise ValueError(
                "owner was not provided, and no default address is set",
            )

        contract = self._get_token_contract(token)
        return contract.functions.balanceOf(owner).call()

    def get_token_allowance(
        self, spender: str, token: str, owner: Optional[str] = None
    ) -> int:
        owner = owner or self.account.address
        if owner is None:
            raise ValueError(
                "owner was not provided, and no default address is set",
            )

        contract = self._get_token_contract(token)
        return contract.functions.allowance(owner, spender).call()
