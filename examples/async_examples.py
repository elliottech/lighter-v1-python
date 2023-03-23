import time
from lighter.lighter_client import Client
import os
from lighter.modules.blockchain import OrderSide


private_key = os.environ.get("TEST_SOURCE_PRIVATE_KEY") or "xxx"
api_auth = os.environ.get("TEST_API_AUTH") or "xxx"

# You don't need to provide private key if you only want to use the api module.

client = Client(
    private_key=private_key, api_auth=api_auth, web3_provider_url="ALCHEMY_URL"
)


async def main():
    client.async_blockchain
    sizes = ["0.0001"]
    prices = ["100000"]
    sides = [OrderSide.SELL]
    print(await client.async_api.get_blockchains())
    print(await client.async_api.get_orderbook("WETH_USDC"))
    print(client.api.get_orderbook("WETH_USDC"))

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
    await client.async_api.close_connection()


if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
