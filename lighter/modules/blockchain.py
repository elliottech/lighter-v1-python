from enum import Enum
import json
import decimal
import os
from typing import Any, Dict, List, Optional, TypedDict, Union
from hexbytes import (
    HexBytes,
)
from web3 import Web3, AsyncWeb3
from web3.contract.contract import Contract, ContractFunction
from web3.contract.async_contract import AsyncContract, AsyncContractFunction
from web3.types import TxParams, TxReceipt, _Hash32, EventData
from eth_account.signers.local import LocalAccount
from eth_account.datastructures import SignedTransaction
from decimal import Decimal
from web3.logs import DISCARD
import asyncio
import nest_asyncio

from lighter.constants import DEFAULT_GAS_AMOUNT
from lighter.constants import DEFAULT_MAX_PRIORITY_FEE_PER_GAS
from lighter.constants import DEFAULT_GAS_MULTIPLIER
from lighter.constants import DEFAULT_MAX_FEE_PER_GAS
from lighter.constants import MAX_SOLIDITY_UINT
from lighter.errors import TransactionReverted
from collections.abc import Iterable

from lighter.modules.api import Api, AsyncApi

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
    OPEN = "OPEN"
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
        "fee": str,
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

ContractResult = TypedDict(
    "ContractResult",
    {
        "events": Union[
            List[OrderCreated],
            List[LimitOrderCanceled],
            List[Union[OrderCreated, LimitOrderCanceled]],
        ],
        "tx_hash": str,
        "fee": str,
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


class BaseBlockchain(object):
    def __init__(
        self,
        blockchain_id: int,
        orderbooks: List[Orderbook],  # client gives this, by getting it from api
        private_key: str,
        router_address: str,
        factory_address: str,
        send_options: Any,
    ):
        self.id = blockchain_id
        self.private_key = private_key
        self.router_address = router_address
        self.factory_address = factory_address
        self.send_options = send_options

        self.cached_contracts = {}
        self._next_nonce_for_address: Dict[str, int] = {}
        self._account = None

        self._orderbooks = {orderbook["symbol"]: orderbook for orderbook in orderbooks}
        self._tokens: Dict[str, Token] = {}

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
                    "Invalid size {}, size should be multiple of size tick {}".format(
                        size,
                        str(
                            Decimal(orderbook["pow_size_tick"])
                            / Decimal(
                                self._get_token_pow_decimal(orderbook["token0_symbol"])
                            )
                        ),
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
                    "Invalid price {}, price should be multiple of price tick {}".format(
                        price,
                        str(
                            Decimal(orderbook["pow_price_tick"])
                            / Decimal(
                                self._get_token_pow_decimal(orderbook["token1_symbol"])
                            )
                        ),
                    )
                )


class AsyncBlockchain(BaseBlockchain):
    def __init__(
        self,
        web3: AsyncWeb3,
        blockchain_id: int,
        orderbooks: List[Orderbook],  # client gives this, by getting it from api
        private_key: str,
        api: AsyncApi,
        router_address: str,
        factory_address: str,
        send_options: Any,
    ):
        super().__init__(
            blockchain_id=blockchain_id,
            orderbooks=orderbooks,
            private_key=private_key,
            router_address=router_address,
            factory_address=factory_address,
            send_options=send_options,
        )

        self.web3 = web3
        self._api = api

        loop = asyncio.get_event_loop()
        nest_asyncio.apply()

        self._tokens = loop.run_until_complete(self.prepare_tokens())

    async def prepare_tokens(self) -> Dict[str, Token]:
        result: Dict[str, Token] = {}
        for orderbook in self._get_orderbooks():
            if orderbook["token0_symbol"] not in result:
                token_contract = await self._get_token_contract(
                    orderbook["token0_symbol"], orderbook["token0_address"]
                )
                decimal = await token_contract.functions.decimals().call()
                result[orderbook["token0_symbol"]] = {
                    "symbol": orderbook["token0_symbol"],
                    "address": orderbook["token0_address"],
                    "decimal": decimal,
                    "pow_decimal": 10**decimal,
                }
            if orderbook["token1_symbol"] not in result:
                token_contract = await self._get_token_contract(
                    orderbook["token1_symbol"], orderbook["token1_address"]
                )
                decimal = await token_contract.functions.decimals().call()
                result[orderbook["token1_symbol"]] = {
                    "symbol": orderbook["token1_symbol"],
                    "address": orderbook["token1_address"],
                    "decimal": decimal,
                    "pow_decimal": 10**decimal,
                }

        return result

    @property
    async def account(self) -> LocalAccount:
        if not self._account:
            self._account = self.web3.eth.account.from_key(self.private_key)
        return self._account

    @property
    async def router_contract(self) -> AsyncContract:
        contract_address = Web3.to_checksum_address(self.router_address)
        return await self._get_contract(contract_address, ROUTER_ABI)

    @property
    async def factory_contract(self) -> AsyncContract:
        contract_address = Web3.to_checksum_address(self.factory_address)
        return await self._get_contract(contract_address, FACTORY_ABI)

    async def orderbook_contract(self, orderbook_symbol: str) -> AsyncContract:
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
        contract_address = Web3.to_checksum_address(contract_address)
        return await self._get_contract(contract_address, ORDERBOOK_ABI)

    async def _create_contract(
        self,
        address: str,
        file_path: str,
    ) -> AsyncContract:
        lighter_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
        )

        address = Web3.to_checksum_address(address)
        return self.web3.eth.contract(
            address=address,
            abi=json.load(open(os.path.join(lighter_folder, file_path), "r")),
        )

    async def _get_contract(
        self,
        address: str,
        file_path: str,
    ) -> AsyncContract:
        if address not in self.cached_contracts:
            self.cached_contracts[address] = await self._create_contract(
                address,
                file_path,
            )
        return self.cached_contracts[address]

    async def _get_token_contract(
        self, token: str, token_address: Optional[str] = None
    ) -> AsyncContract:
        token_address = token_address or self._get_token(token)["address"]
        token_address = Web3.to_checksum_address(token_address)
        return await self._get_contract(token_address, ERC20_ABI)

    async def _get_next_nonce(
        self,
        address: Optional[str],
    ) -> int:
        if not address:
            address = (await self.account).address
        if not address:
            raise ValueError("No address")

        if self._next_nonce_for_address.get(address) is None:
            checksum_address = Web3.to_checksum_address(address)
            self._next_nonce_for_address[
                address
            ] = await self.web3.eth.get_transaction_count(checksum_address)
        return self._next_nonce_for_address[address]

    async def _sign_tx(
        self,
        method: Optional[AsyncContractFunction],
        options: Optional[TxParams],
    ) -> SignedTransaction:
        if method is None:
            tx = options
        else:
            tx = method.build_transaction(options)
        return self.web3.eth.account.sign_transaction(
            tx,
            self.private_key,
        )

    async def _wait_for_tx(
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
        tx_receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash)
        if tx_receipt["status"] == 0:
            raise TransactionReverted(tx_receipt)

        return tx_receipt

    async def _send_eth_transaction(
        self,
        method: Optional[AsyncContractFunction] = None,
        options: Any = None,
    ) -> HexBytes:
        options = dict(self.send_options, **(options or {}))

        options["chainId"] = self.id
        options["type"] = "0x2"

        if "from" not in options:
            options["from"] = (await self.account).address
        if options.get("from") is None:
            raise ValueError(
                "options['from'] is not set, and no default address is set",
            )
        auto_detect_nonce = "nonce" not in options
        if auto_detect_nonce:
            options["nonce"] = await self._get_next_nonce(options["from"])
        if "value" not in options:
            options["value"] = 0
        gas_multiplier = options.pop("gasMultiplier", DEFAULT_GAS_MULTIPLIER)
        options["maxFeePerGas"] = DEFAULT_MAX_FEE_PER_GAS
        options["maxPriorityFeePerGas"] = DEFAULT_MAX_PRIORITY_FEE_PER_GAS
        if "gas" not in options and method:
            try:
                options["gas"] = int(method.estimate_gas(options) * gas_multiplier)
            except Exception:
                options["gas"] = DEFAULT_GAS_AMOUNT

        signed = await self._sign_tx(method, options)
        try:
            tx_hash = await self.web3.eth.send_raw_transaction(signed.rawTransaction)
        except ValueError as error:
            retry_count = 0
            while retry_count < 3:
                if auto_detect_nonce and (
                    "nonce too low" in str(error)
                    or "replacement transaction underpriced" in str(error)
                ):
                    try:
                        retry_count += 1
                        options["nonce"] = await self.web3.eth.get_transaction_count(
                            options["from"]
                        )
                        signed = await self._sign_tx(method, options)
                        tx_hash = await self.web3.eth.send_raw_transaction(
                            signed.rawTransaction,
                        )
                    except ValueError as inner_error:
                        error = inner_error
                    else:
                        break
                elif "max fee per gas less than block base fee" in str(error):
                    try:
                        retry_count += 1
                        options["maxFeePerGas"] += options["maxFeePerGas"]
                        signed = await self._sign_tx(method, options)
                        tx_hash = await self.web3.eth.send_raw_transaction(
                            signed.rawTransaction,
                        )
                    except ValueError as inner_error:
                        error = inner_error
                    else:
                        break
                else:
                    raise error
            else:
                raise error

        # Update next nonce for the account.
        self._next_nonce_for_address[options["from"]] = options["nonce"] + 1

        return tx_hash

    async def _process_transaction_events(
        self, tx_hash: HexBytes, orderbook_symbol: str
    ) -> ProcessedTransactionReceipt:
        orderbook_contract = await self.orderbook_contract(orderbook_symbol)
        orderbook = self._get_orderbook(orderbook_symbol)

        receipt = await self._wait_for_tx(tx_hash)
        fee = str(
            Decimal(str(receipt["gasUsed"]))
            * Decimal(str(receipt["effectiveGasPrice"]))
            / 10**18
        )

        limit_order_created_events: Iterable[
            EventData
        ] = orderbook_contract.events.LimitOrderCreated().process_receipt(
            receipt, errors=DISCARD
        )

        processed_limit_order_created_events = self._process_order_created_events(
            limit_order_created_events, orderbook
        )

        market_order_created_events: Iterable[
            EventData
        ] = orderbook_contract.events.MarketOrderCreated().process_receipt(
            receipt, errors=DISCARD
        )

        processed_market_order_created_events = self._process_order_created_events(
            market_order_created_events, orderbook
        )

        limit_order_canceled_events = (
            orderbook_contract.events.LimitOrderCanceled().process_receipt(
                receipt, errors=DISCARD
            )
        )

        processed_limit_order_cancelled_events = self._process_order_cancelled_event(
            limit_order_canceled_events, orderbook
        )

        trade_events: Iterable[
            EventData
        ] = orderbook_contract.events.Swap().process_receipt(receipt, errors=DISCARD)

        processed_trade_events = self._process_trade_events(trade_events, orderbook)

        return {
            "limit_order_created_events": processed_limit_order_created_events,
            "market_order_created_events": processed_market_order_created_events,
            "limit_order_canceled_event": processed_limit_order_cancelled_events,
            "trade_events": processed_trade_events,
            "fee": fee,
        }

    async def get_create_order_transaction_result(
        self,
        tx_hash: HexBytes,
        orderbook_symbol: str,
        processed_events: Optional[ProcessedTransactionReceipt] = None,
    ) -> ContractResult:
        processed_events = (
            processed_events
            if processed_events
            else await self._process_transaction_events(tx_hash, orderbook_symbol)
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
                    else OrderStatus.OPEN,
                    "type": created_event["type"],
                    "side": created_event["side"],
                    "fills": fills,
                }
            )

        return {
            "events": result,
            "tx_hash": tx_hash.hex(),
            "fee": processed_events["fee"],
        }

    async def get_limit_order_canceled_transaction_result(
        self,
        tx_hash: HexBytes,
        orderbook_symbol: str,
        processed_events: Optional[ProcessedTransactionReceipt] = None,
    ) -> ContractResult:
        processed_events = (
            processed_events
            if processed_events
            else await self._process_transaction_events(tx_hash, orderbook_symbol)
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

        return {
            "events": result,
            "tx_hash": tx_hash.hex(),
            "fee": processed_events["fee"],
        }

    async def get_update_limit_order_transaction_result(
        self, tx_hash: HexBytes, orderbook_symbol: str
    ) -> ContractResult:
        result: List[Union[OrderCreated, LimitOrderCanceled]] = []
        events = await self._process_transaction_events(tx_hash, orderbook_symbol)

        created_results = await self.get_create_order_transaction_result(
            tx_hash, orderbook_symbol, events
        )
        result.extend(created_results["events"])
        cancelled_results = await self.get_limit_order_canceled_transaction_result(
            tx_hash, orderbook_symbol, events
        )
        result.extend(cancelled_results["events"])

        return {
            "events": result,
            "tx_hash": tx_hash.hex(),
            "fee": cancelled_results["fee"],
        }

    # -----------------------------------------------------------
    # Transactions
    # -----------------------------------------------------------
    async def create_limit_order_batch(
        self,
        orderbook_symbol: str,
        human_readable_sizes: List[str],
        human_readable_prices: List[str],
        sides: List[OrderSide],
        options: Dict[str, Any] = {},
    ) -> HexBytes:
        if not all(isinstance(x, str) for x in human_readable_sizes):
            raise ValueError("Invalid size, size should be string")
        if not all(isinstance(x, str) for x in human_readable_prices):
            raise ValueError("Invalid price, price should be string")

        self._tick_check(human_readable_sizes, human_readable_prices, orderbook_symbol)
        orderbook = self._get_orderbook(orderbook_symbol)

        sizes = [
            self._get_amount_from_human_readable(size, orderbook["token0_symbol"])
            for size in human_readable_sizes
        ]

        hint_ids = await self._get_hint_ids(
            orderbook_symbol, human_readable_prices, sides
        )

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
            to=(await self.router_contract).address, data=data, **(options or {})
        )

        return await self._send_eth_transaction(options=options)

    async def update_limit_order_batch(
        self,
        orderbook_symbol: str,
        order_ids: List[int],
        human_readable_sizes: List[str],
        human_readable_prices: List[str],
        old_sides: List[OrderSide],
        options: Dict[str, Any] = {},
    ) -> HexBytes:
        if not all(isinstance(x, str) for x in human_readable_sizes):
            raise ValueError("Invalid size, size should be string")
        if not all(isinstance(x, str) for x in human_readable_prices):
            raise ValueError("Invalid price, price should be string")

        self._tick_check(human_readable_sizes, human_readable_prices, orderbook_symbol)

        orderbook = self._get_orderbook(orderbook_symbol)

        sizes = [
            self._get_amount_from_human_readable(size, orderbook["token0_symbol"])
            for size in human_readable_sizes
        ]

        hint_ids = await self._get_hint_ids(
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
            to=(await self.router_contract).address, data=data, **(options or {})
        )

        return await self._send_eth_transaction(options=options)

    async def cancel_limit_order_batch(
        self, orderbook_symbol: str, order_ids: List[int], options: Dict[str, Any] = {}
    ) -> HexBytes:
        orderbook = self._get_orderbook(orderbook_symbol)

        orders_data = "".join("{:08x}".format(order_id) for order_id in order_ids)

        data = "0x03{:02x}{:02x}{}".format(orderbook["id"], len(order_ids), orders_data)

        options = dict(
            to=(await self.router_contract).address, data=data, **(options or {})
        )

        return await self._send_eth_transaction(options=options)

    async def create_market_order(
        self,
        orderbook_symbol: str,
        human_readable_size: str,
        human_readable_price: str,
        side: OrderSide,
        options: Dict[str, Any] = {},
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
            to=(await self.router_contract).address, data=data, **(options or {})
        )

        return await self._send_eth_transaction(options=options)

    async def set_token_max_allowance(
        self,
        spender: str,
        token: str,
        send_options: Any = None,
    ) -> HexBytes:
        contract = await self._get_token_contract(token)
        return await self._send_eth_transaction(
            method=contract.functions.approve(
                spender,
                MAX_SOLIDITY_UINT,
            ),
            options=send_options,
        )

    # -----------------------------------------------------------
    # Getters
    # -----------------------------------------------------------
    async def _get_hint_ids(
        self, orderbook_symbol: str, prices: List[str], sides: List[OrderSide]
    ) -> List[int]:
        orderbook = self._get_orderbook(orderbook_symbol)
        sides_str = [side.value.lower() for side in sides]
        return (await self._api.get_hint_ids(orderbook["symbol"], prices, sides_str))[
            "hint_ids"
        ]

    async def _get_gas_price(self) -> int:
        return (await self._api.get_gas_price())["gas_price"]

    async def get_eth_balance(
        self,
        owner: Optional[str] = None,
    ) -> Union[int, decimal.Decimal]:
        owner = owner or (await self.account).address
        if owner is None:
            raise ValueError(
                "owner was not provided, and no default address is set",
            )
        checksum_address = Web3.to_checksum_address(owner)
        wei_balance = await self.web3.eth.get_balance(checksum_address)
        return Web3.from_wei(wei_balance, "ether")

    async def get_token_balance(
        self,
        owner: Optional[str],
        token: str,
    ) -> int:
        owner = owner or (await self.account).address
        if owner is None:
            raise ValueError(
                "owner was not provided, and no default address is set",
            )

        contract = await self._get_token_contract(token)
        return await contract.functions.balanceOf(owner).call()

    async def get_token_allowance(
        self, spender: str, token: str, owner: Optional[str] = None
    ) -> int:
        owner = owner or (await self.account).address
        if owner is None:
            raise ValueError(
                "owner was not provided, and no default address is set",
            )

        contract = await self._get_token_contract(token)
        return await contract.functions.allowance(owner, spender).call()


class Blockchain(BaseBlockchain):
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
        super().__init__(
            blockchain_id=blockchain_id,
            orderbooks=orderbooks,
            private_key=private_key,
            router_address=router_address,
            factory_address=factory_address,
            send_options=send_options,
        )
        self.web3 = web3
        self._api = api
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
        contract_address = Web3.to_checksum_address(self.router_address)
        return self._get_contract(contract_address, ROUTER_ABI)

    @property
    def factory_contract(self) -> Contract:
        contract_address = Web3.to_checksum_address(self.factory_address)
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
        contract_address = Web3.to_checksum_address(contract_address)
        return self._get_contract(contract_address, ORDERBOOK_ABI)

    def _create_contract(
        self,
        address: str,
        file_path: str,
    ) -> Contract:
        lighter_folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
        )

        address = Web3.to_checksum_address(address)
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
        token_address = Web3.to_checksum_address(token_address)
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
            checksum_address = Web3.to_checksum_address(address)
            self._next_nonce_for_address[address] = self.web3.eth.get_transaction_count(
                checksum_address
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
            tx = method.build_transaction(options)
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
        options["type"] = "0x2"

        if "from" not in options:
            options["from"] = self.account.address
        if options.get("from") is None:
            raise ValueError(
                "options['from'] is not set, and no default address is set",
            )
        auto_detect_nonce = "nonce" not in options
        if auto_detect_nonce:
            options["nonce"] = self._get_next_nonce(options["from"])
        if "value" not in options:
            options["value"] = 0

        gas_multiplier = options.pop("gasMultiplier", DEFAULT_GAS_MULTIPLIER)
        if "maxFeePerGas" not in options:
            options["maxFeePerGas"] = DEFAULT_MAX_FEE_PER_GAS
        if "maxPriorityFeePerGas" not in options:
            options["maxPriorityFeePerGas"] = DEFAULT_MAX_PRIORITY_FEE_PER_GAS
        if "gas" not in options:
            if not method:
                options["gas"] = DEFAULT_GAS_AMOUNT
            else:
                try:
                    options["gas"] = int(method.estimate_gas(options) * gas_multiplier)
                except Exception:
                    options["gas"] = DEFAULT_GAS_AMOUNT

        signed = self._sign_tx(method, options)

        try:
            tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
        except ValueError as error:
            retry_count = 0
            while retry_count < 3:
                if auto_detect_nonce and (
                    "nonce too low" in str(error)
                    or "replacement transaction underpriced" in str(error)
                ):
                    try:
                        retry_count += 1
                        options["nonce"] = self.web3.eth.get_transaction_count(
                            options["from"]
                        )
                        signed = self._sign_tx(method, options)
                        tx_hash = self.web3.eth.send_raw_transaction(
                            signed.rawTransaction,
                        )
                    except ValueError as inner_error:
                        error = inner_error
                    else:
                        break
                elif "max fee per gas less than block base fee" in str(error):
                    try:
                        retry_count += 1
                        options["maxFeePerGas"] += options["maxFeePerGas"]
                        signed = self._sign_tx(method, options)
                        tx_hash = self.web3.eth.send_raw_transaction(
                            signed.rawTransaction,
                        )
                    except ValueError as inner_error:
                        error = inner_error
                    else:
                        break
                else:
                    raise error
            else:
                raise error

        # Update next nonce for the account.
        self._next_nonce_for_address[options["from"]] = options["nonce"] + 1

        return tx_hash

    def _process_transaction_events(
        self, tx_hash: HexBytes, orderbook_symbol: str
    ) -> ProcessedTransactionReceipt:
        orderbook_contract = self.orderbook_contract(orderbook_symbol)
        orderbook = self._get_orderbook(orderbook_symbol)

        receipt = self._wait_for_tx(tx_hash)
        fee = str(
            Decimal(str(receipt["gasUsed"]))
            * Decimal(str(receipt["effectiveGasPrice"]))
            / 10**18
        )

        limit_order_created_events: Iterable[
            EventData
        ] = orderbook_contract.events.LimitOrderCreated().process_receipt(
            receipt, errors=DISCARD
        )

        processed_limit_order_created_events = self._process_order_created_events(
            limit_order_created_events, orderbook
        )

        market_order_created_events: Iterable[
            EventData
        ] = orderbook_contract.events.MarketOrderCreated().process_receipt(
            receipt, errors=DISCARD
        )

        processed_market_order_created_events = self._process_order_created_events(
            market_order_created_events, orderbook
        )

        limit_order_canceled_events = (
            orderbook_contract.events.LimitOrderCanceled().process_receipt(
                receipt, errors=DISCARD
            )
        )

        processed_limit_order_cancelled_events = self._process_order_cancelled_event(
            limit_order_canceled_events, orderbook
        )

        trade_events: Iterable[
            EventData
        ] = orderbook_contract.events.Swap().process_receipt(receipt, errors=DISCARD)

        processed_trade_events = self._process_trade_events(trade_events, orderbook)

        return {
            "limit_order_created_events": processed_limit_order_created_events,
            "market_order_created_events": processed_market_order_created_events,
            "limit_order_canceled_event": processed_limit_order_cancelled_events,
            "trade_events": processed_trade_events,
            "fee": fee,
        }

    def get_create_order_transaction_result(
        self,
        tx_hash: HexBytes,
        orderbook_symbol: str,
        processed_events: Optional[ProcessedTransactionReceipt] = None,
    ) -> ContractResult:
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
                    else OrderStatus.OPEN,
                    "type": created_event["type"],
                    "side": created_event["side"],
                    "fills": fills,
                }
            )

        return {
            "events": result,
            "tx_hash": tx_hash.hex(),
            "fee": processed_events["fee"],
        }

    def get_limit_order_canceled_transaction_result(
        self,
        tx_hash: HexBytes,
        orderbook_symbol: str,
        processed_events: Optional[ProcessedTransactionReceipt] = None,
    ) -> ContractResult:
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

        return {
            "events": result,
            "tx_hash": tx_hash.hex(),
            "fee": processed_events["fee"],
        }

    def get_update_limit_order_transaction_result(
        self, tx_hash: HexBytes, orderbook_symbol: str
    ) -> ContractResult:
        result: List[Union[OrderCreated, LimitOrderCanceled]] = []
        events = self._process_transaction_events(tx_hash, orderbook_symbol)

        created_results = self.get_create_order_transaction_result(
            tx_hash, orderbook_symbol, events
        )
        result.extend(created_results["events"])
        cancelled_results = self.get_limit_order_canceled_transaction_result(
            tx_hash, orderbook_symbol, events
        )
        result.extend(cancelled_results["events"])

        return {
            "events": result,
            "tx_hash": tx_hash.hex(),
            "fee": cancelled_results["fee"],
        }

    # -----------------------------------------------------------
    # Transactions
    # -----------------------------------------------------------
    def create_limit_order_batch(
        self,
        orderbook_symbol: str,
        human_readable_sizes: List[str],
        human_readable_prices: List[str],
        sides: List[OrderSide],
        options: Dict[str, Any] = {},
    ) -> HexBytes:
        if not all(isinstance(x, str) for x in human_readable_sizes):
            raise ValueError("Invalid size, size should be string")
        if not all(isinstance(x, str) for x in human_readable_prices):
            raise ValueError("Invalid price, price should be string")

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

        options = dict(to=self.router_contract.address, data=data, **(options or {}))

        return self._send_eth_transaction(options=options)

    def update_limit_order_batch(
        self,
        orderbook_symbol: str,
        order_ids: List[int],
        human_readable_sizes: List[str],
        human_readable_prices: List[str],
        old_sides: List[OrderSide],
        options: Dict[str, Any] = {},
    ) -> HexBytes:
        if not all(isinstance(x, str) for x in human_readable_sizes):
            raise ValueError("Invalid size, size should be string")
        if not all(isinstance(x, str) for x in human_readable_prices):
            raise ValueError("Invalid price, price should be string")

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

        options = dict(to=self.router_contract.address, data=data, **(options or {}))

        return self._send_eth_transaction(options=options)

    def cancel_limit_order_batch(
        self, orderbook_symbol: str, order_ids: List[int], options: Dict[str, Any] = {}
    ) -> HexBytes:
        orderbook = self._get_orderbook(orderbook_symbol)

        orders_data = "".join("{:08x}".format(order_id) for order_id in order_ids)

        data = "0x03{:02x}{:02x}{}".format(orderbook["id"], len(order_ids), orders_data)

        options = dict(
            to=self.router_contract.address,
            data=data,
            **(options or {}),
        )

        return self._send_eth_transaction(options=options)

    def create_market_order(
        self,
        orderbook_symbol: str,
        human_readable_size: str,
        human_readable_price: str,
        side: OrderSide,
        options: Dict[str, Any] = {},
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

        options = dict(to=self.router_contract.address, data=data, **(options or {}))

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
        return self._api.get_hint_ids(orderbook["symbol"], prices, sides_str)[
            "hint_ids"
        ]

    def _get_gas_price(self) -> int:
        return self._api.get_gas_price()["gas_price"]

    def get_eth_balance(
        self,
        owner: Optional[str] = None,
    ) -> Union[int, decimal.Decimal]:
        owner = owner or self.account.address
        if owner is None:
            raise ValueError(
                "owner was not provided, and no default address is set",
            )

        checksummed_address = Web3.to_checksum_address(owner)
        wei_balance = self.web3.eth.get_balance(checksummed_address)
        return Web3.from_wei(wei_balance, "ether")

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
