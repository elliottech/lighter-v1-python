from lighter.lighter_client import Client
import os
from lighter.constants import ORDER_STATUS_OPEN, ORDER_TYPE_LIMIT, ORDERBOOK_WETH_USDC

private_key = os.environ.get("TEST_SOURCE_PRIVATE_KEY") or "xxx"
api_auth = os.environ.get("TEST_API_AUTH") or "xxx"

# You don't need to provide private key if you only want to use the api module.

client = Client(
    private_key=private_key, api_auth=api_auth, web3_provider_url="ALCHEMY_URL"
)

# Let's get available blockchains and their details from the api module.
blockchains = client.api.get_blockchains()

# example output:
# {
#     "blockchains": [
#         {
#             "id": 42161,
#             "name": "Arbitrum Mainnet",
#             "is_test": false,
#             "router_address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
#             "factory_address": "1CjPR7Z5ZSyWk6WtXvSFgkptmpoi4UM9BC"
#         },
#         {
#             "id": 421613,
#             "name": "Arbitrum Goerli",
#             "is_test": true,
#             "router_address": "0x2910543af39aba0cd09dbb2d50200b3e800a63d2",
#             "factory_address": "0x2a65Aca4D5fC5B5C859090a6c34d164135398226"
#         }
#     ]
# }

# Let's get available order books on the blockchain that provided web3 url and their details from the api module.
orderbook_meta_data = client.api.get_orderbook_meta()

# example output:
# {
#   "orderbookmetas": [
#     {
#       "address": "0xd2a4684b4Eaf79AbcF352C3C6b46090c1f83819D",
#       "blockchain_id": 420,
#       "day_change": 1197,
#       "day_high": 1902,
#       "day_low": 1186,
#       "day_volume0": 741712000000000000000,
#       "day_volume1": 921556231800,
#       "id": 0,
#       "price_tick": 100000,
#       "size_tick": 1000000000000000,
#       "symbol": "WETH_USDC",
#       "token0_address": "0x479eE06EDDF5e251AADb016fB5413dc032a25b6e",
#       "token0_symbol": "WETH",
#       "token1_address": "0xfe53c0Ed29422d7bc897a4bfDC16377DEa93717D",
#       "token1_symbol": "USDC"
#     },
#     {
#       "address": "0x1D44DF4647fad24501a9f1C2e54348383A2FD3AD",
#       "blockchain_id": 420,
#       "day_change": 0,
#       "day_high": 0,
#       "day_low": 0,
#       "day_volume0": 0,
#       "day_volume1": 0,
#       "id": 1,
#       "price_tick": 1000000,
#       "size_tick": 10000,
#       "symbol": "WBTC_USDC",
#       "token0_address": "0xA6dCE7f87Ec274A5dD99b06655ef6eF27A1D9281",
#       "token0_symbol": "WBTC",
#       "token1_address": "0xfe53c0Ed29422d7bc897a4bfDC16377DEa93717D",
#       "token1_symbol": "USDC"
#     }
#   ]
# }

# Let's get orders on WETH_USDC order book.
client.api.get_orderbook(orderbook_symbol=ORDERBOOK_WETH_USDC)

# example output:
# {
#     "asks": [
#         {
#             "price": 10.0,
#             "size": 100.0
#         },
#         {
#             "price": 11.0,
#             "size": 50.0
#         }
#     ],
#     "bids": [
#         {
#             "price": 9.0,
#             "size": 75.0
#         },
#         {
#             "price": 8.0,
#             "size": 25.0
#         }
#     ]
# }

# Let's get specific orders from WETH_USDC order book.
orders = client.api.get_orders(
    orderbook_symbol=ORDERBOOK_WETH_USDC,
    owner="YOUR_WALLET_ADDRESS",
    status=ORDER_STATUS_OPEN,
    type=ORDER_TYPE_LIMIT,
)

# example output:
# {
#     "orders": [
#         {
#             "order_id": 33413,
#             "price": 10.0,
#             "size": 100.0,
#             "timestamp": 1609276939,
#             "type": "ask",
#             "status": "open",
#         },
#         {
#             "order_id": 33424,
#             "price": 9.5,
#             "size": 75.0,
#             "timestamp": 1609276940,
#             "type": "bid",
#             "status": "closed",
#         },
#     ]
# }


# Let's get your trades from the WETH_USDC order book.
my_trades = client.api.get_trades(
    orderbook_symbol=ORDERBOOK_WETH_USDC, owner="YOUR_WALLET_ADDRESS"
)
# example output:
# {
#     "trades": [
#         {
#             "side": "ask",
#             "price": 10.0,
#             "amount": 100.0,
#             "timestamp": 1609276939,
#             "maker_address": "0xabc123",
#             "taker_address": "0xdef456",
#         },
#         {
#             "side": "bid,
#             "price": 9.5,
#             "amount": 50.0,
#             "timestamp": 1609276940,
#             "maker_address": "0xghi789",
#             "taker_address": "0xjkl012",
#         },
#     ]
# }

# Let's get candle stick data from the WETH_USDC order book.
candles = client.api.get_candles(
    orderbook_symbol=ORDERBOOK_WETH_USDC,
    resolution=5,
    timestamp_start=1609276939,
    timestamp_end=1609276940,
)

# example output:
# {
#     "candles": [
#         {
#             "timestamp": 1609276939,
#             "open": 10.0,
#             "high": 11.0,
#             "low": 9.0,
#             "close": 9.5,
#             "volume0": 100.0,
#             "volume1": 50.0
#         },
#         {
#             "timestamp": 1609276940,
#             "open": 9.5,
#             "high": 10.0,
#             "low": 8.5,
#             "close": 9.0,
#             "volume0": 75.0,
#             "volume1": 25.0
#         }
#     ]
# }
