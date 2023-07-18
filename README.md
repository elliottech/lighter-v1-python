# Lighter

Python client for Lighter (v1). The sdk is tested against Python versions 3.9, 3.10 and 3.11.

## Installation

```bash
pip install lighter-v1-python
```

## Getting Started

The `Client` object has four main modules;

- `Api`: allows interaction with the lighter api
- `AsyncApi`: allows for async interaction with the lighter api
- `Blockchain`: allows interaction with lighter contracts
- `AsyncBlockchain`: allows async interaction with lighter contracts

`Client` can be created with private key or not depending on whether you are going to use the api or interact with the contracts. For more complete examples, see the [examples](./examples/) directory.

### API

Following parameters are required to use `Api` module:

- `api_auth`: You should get the key from our servers.
- `web3_provider_url`: You need a node to interact with the contract. We suggest alchemy which provides 300M free compute units monthly, You can register and get your keys [here](https://www.alchemy.com/)

```python
from lighter.lighter_client import Client
import os
from lighter.modules.blockchain import OrderSide
from lighter.constants import ORDERBOOK_WETH_USDC

api_auth = os.environ.get("API_AUTH")

# You don't need to provide private key if you only want to use the api module.

client = Client(api_auth=api_auth, web3_provider_url="ALCHEMY_URL")

# Let's get available blockchains and their details from the api module.
blockchains = client.api.get_blockchains().data
```

### Blockchain

Following parameters are required to use `Blockchain` module:

- `api_auth`: You should get the key from our servers.
- `private_key`: You need to provide your wallet private key to sign your transactions.
- `web3_provider_url`: You need a node to interact with the contract. We suggest alchemy which provides 300M free compute units monthly, You can register and get your keys [here](https://www.alchemy.com/)

Blockchain module enables you to do multiple operations in one transaction. The number of operations is limited to 4 million gas. So the limits are roughly;

- 25 order creations in one transaction
- 100 order cancellations in one transaction
- 25 order updates in one transaction

```python
from lighter.lighter_client import Client
import os
from lighter.modules.blockchain import OrderSide
from lighter.constants import ORDERBOOK_WETH_USDC


private_key = os.environ.get("SOURCE_PRIVATE_KEY")
api_auth = os.environ.get("API_AUTH")


client = Client(
    private_key=private_key, api_auth=api_auth, web3_provider_url="ALCHEMY_URL"
)


x = client.blockchain  # initialize the blockchain module before using it


# You need to give allowance for the trading tokens
client.blockchain.set_token_max_allowance(
    spender=client.blockchain.router_contract.address, token="WETH"
)

client.blockchain.set_token_max_allowance(
    spender=client.blockchain.router_contract.address, token="USDC"
)


# Let's create a batch of limit orders
sizes = ["0.001", "0.001", "0.001"]
prices = ["1050", "1200", "1000"]
sides = [OrderSide.BUY, OrderSide.SELL, OrderSide.BUY]


tx_hash = client.blockchain.create_limit_order_batch("WETH_USDC", sizes, prices, sides)

# if you want to wait for the transaction to be mined and get order id and other details,
# you can use the following method.
# alternatively you can wait the data from websocket
result = client.blockchain.get_create_order_transaction_result(tx_hash, "WETH_USDC")
```

### Async Examples

```python
from lighter.lighter_client import Client
import os
from lighter.modules.blockchain import OrderSide
from lighter.constants import ORDERBOOK_WETH_USDC


private_key = os.environ.get("SOURCE_PRIVATE_KEY")
api_auth = os.environ.get("API_AUTH")


client = Client(
    private_key=private_key, api_auth=api_auth, web3_provider_url="ALCHEMY_URL"
)


async def main():
    client.async_blockchain # to initialize the module
    sizes = ["0.0001"]
    prices = ["1000"]
    sides = [OrderSide.SELL]

    # Test async api
    print(await client.async_api.get_blockchains())
    print(await client.async_api.get_orderbook("WETH_USDC"))

    print(
        client.api.get_candles(
            orderbook_symbol="WETH_USDC",
            resolution=60,
            timestamp_start=int(time.time()) - 60 * 60 * 60 * 24,
            timestamp_end=int(time.time()),
        )
    )

    tx_hash = await client.async_blockchain.create_limit_order_batch(
        "WETH_USDC", sizes, prices, sides
    )
    # tx_hash = await client.async_blockchain.cancel_limit_order_batch(
    #     "WETH_USDC", [24989]
    # )
    # tx_hash = await client.async_blockchain.update_limit_order_batch(
    #     "WETH_USDC", [24991], ["0.0001"], ["100"], [OrderSide.BUY]
    # )
    # tx_hash = await client.async_blockchain.create_market_order(
    #     "WETH_USDC", "0.0001", "100", OrderSide.SELL
    # )

    result = await client.async_blockchain.get_create_order_transaction_result(
        tx_hash, "WETH_USDC"
    )
    # result = await client.async_blockchain.get_limit_order_canceled_transaction_result(
    #     tx_hash, "WETH_USDC"
    # )
    # result = await client.async_blockchain.get_update_limit_order_transaction_result(
    #     tx_hash, "WETH_USDC"
    # )
    print(result)

    # close the aiohtpp session
    await client.async_api.close_connection()


if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
```
