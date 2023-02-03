from lighter.lighter_client import Client
import os
from lighter.modules.blockchain import OrderSide
from lighter.constants import ORDERBOOK_WETH_USDC


private_key = os.environ.get("TEST_SOURCE_PRIVATE_KEY") or "xxx"
api_auth = os.environ.get("TEST_API_AUTH") or "xxx"


client = Client(
    private_key=private_key, api_auth=api_auth, web3_provider_url="ALCHEMY_URL"
)


x = client.blockchain  # initialize the blockchain module before using it


# Let's create a batch of limit orders

sizes = ["0.001", "0.001", "0.001"]
prices = ["1050", "1200", "1000"]
sides = [OrderSide.BUY, OrderSide.SELL, OrderSide.BUY]


tx_hash = client.blockchain.create_limit_order_batch("WETH_USDC", sizes, prices, sides)

# if you want to wait for the transaction to be mined and get order id and other details,
# you can use the following method.
# alternatively you can wait the data from websocket
result = client.blockchain.get_create_order_transaction_result(tx_hash, "WETH_USDC")

# example result:
# [
#     {
#         "orderbook": WETH_USDC,
#         "order_id": 123,
#         "size": "0.001",
#         "filled_size": "0.0",
#         "price": "1050",
#         "status": OrderStatus.PARTIALLY_FILLED,
#         "type": OrderType.LIMIT,
#         "side": OrderSide.BUY,
#         "fills": [..], # list of fills
#     } ...
# ]


# Let's update the orders
order_ids = [1234, 12345, 123456]
new_sizes = ["0.001", "0.001", "0.001"]
new_prices = ["1250", "1300", "1200"]
old_sides = [OrderSide.BUY, OrderSide.SELL, OrderSide.BUY]  # side cannot be updated

tx_hash = client.blockchain.update_limit_order_batch(
    ORDERBOOK_WETH_USDC, order_ids, new_sizes, new_prices, sides
)

# if you want to wait for the transaction to be mined and get order id and other details,
result = client.blockchain.get_update_limit_order_transaction_result(
    tx_hash, ORDERBOOK_WETH_USDC
)

# output is similar to create_limit_order_batch


# Let's cancel the orders
tx_hash = client.blockchain.cancel_limit_order_batch(ORDERBOOK_WETH_USDC, order_ids)

# if you want to wait for the transaction to be mined and get order id and other details
result = client.blockchain.get_limit_order_canceled_transaction_result(
    tx_hash, ORDERBOOK_WETH_USDC
)
# output is similar to create_limit_order_batch
