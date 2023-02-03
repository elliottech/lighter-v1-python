# Lighter

Python client for Lighter (v1).

## Installation

```bash
pip install lighter-v1-python
```

## Getting Started

The `Client` object has two main modules;

- `Api`: allows interaction with the lighter api
- `Blockchain`: allows interaction with ligter contracts

`Client` can be created with private key or not depending on whether you are going to use the api or interract with the contracts. For more complete examples, see the [examples](./examples/) directory.

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
