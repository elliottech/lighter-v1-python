import asyncio
import websockets
import json
from pprint import pprint
from timeit import default_timer as timer


async def subscribe_to_orderbook(ws, auth):
    req = {
        "type": "subscribe",
        "channel": "orderbook/421613:WETH_USDC",
        "auth": auth,
        "topK": 10,
    }
    await ws.send(json.dumps(req))
    confirmation = json.loads(await ws.recv())
    print(">>> Sent orderbook subscription req")
    pprint(req)
    print("<<< Received orderbook subscription confirmation")
    pprint(confirmation)
    # {
    #     "channel": "421613:WETH_USDC",
    #     "orders": {
    #         "asks": [
    #             {"price": 1232.0, "size": 4.711},
    #             {"price": 1236.9, "size": 4.596},
    #             {"price": 1236.99, "size": 2.594},
    #             {"price": 1239.35, "size": 4.945},
    #         ],
    #         "bids": [
    #             {"price": 1217.56, "size": 3.286},
    #             {"price": 1216.34, "size": 2.007},
    #             {"price": 1212.78, "size": 2.133},
    #             {"price": 1206.55, "size": 1.465},
    #             {"price": 1001.0, "size": 0.003},
    #         ],
    #     },
    #     "type": "subscribed/orderbook",
    # }
    print("===\n\n")


async def subscribe_to_account(ws, auth):
    req = {
        "type": "subscribe",
        "channel": "account/421613:WETH_USDC",
        "auth": auth,
        "account": "XXXXX",
    }
    await ws.send(json.dumps(req))
    confirmation = json.loads(await ws.recv())
    print(">>> Sent account subscription req")
    pprint(req)
    print("<<< Received account subscription confirmation")
    pprint(confirmation)
    ### part of the trades and orders removed for the sake of brevity
    # {
    #     "account": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #     "balance": 1630711608558970000,
    #     "channel": "421613:WETH_USDC",
    #     "orders": [
    #         {
    #             "filled_amount": 0.0,
    #             "id": 620,
    #             "price": 1212.78,
    #             "side": "buy",
    #             "size": 2.1329,
    #             "status": "OPEN",
    #         },
    #         {
    #             "filled_amount": 0.0,
    #             "id": 644,
    #             "price": 1001.0,
    #             "side": "buy",
    #             "size": 0.001,
    #             "status": "OPEN",
    #         },
    #     ],
    #     "trades": [
    #         {
    #             "amount": 0.0001,
    #             "ask_id": 629,
    #             "bid_id": 707,
    #             "maker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #             "price": 1232.0,
    #             "side": "buy",
    #             "taker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #             "timestamp": 1673350061,
    #         },
    #         {
    #             "amount": 0.0001,
    #             "ask_id": 629,
    #             "bid_id": 706,
    #             "maker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #             "price": 1232.0,
    #             "side": "buy",
    #             "taker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #             "timestamp": 1673349019,
    #         },
    #     ],
    #     "type": "subscribed/account",
    # }
    print("===\n\n")


async def subscribe_to_trades(ws, auth, owner_filter):
    req = {
        "type": "subscribe",
        "channel": "trade/421613:WETH_USDC",
        "auth": auth,
    }
    # If owner is specified only the trades that owner is part of is sent, otherwise all trades are sent
    if owner_filter:
        req["owner"] = owner_filter

    await ws.send(json.dumps(req))
    confirmation = json.loads(await ws.recv())
    print(">>> Sent trades subscription req")
    pprint(req)
    print("<<< Received trades subscription confirmation")
    pprint(confirmation)
    # {
    #     "owner": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #     "trades": [
    #         {
    #             "amount": 0.0001,
    #             "ask_id": 629,
    #             "bid_id": 707,
    #             "maker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #             "price": 1232.0,
    #             "side": "buy",
    #             "taker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #             "timestamp": 1673350061,
    #         },
    #         {
    #             "amount": 0.0001,
    #             "ask_id": 629,
    #             "bid_id": 706,
    #             "maker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #             "price": 1232.0,
    #             "side": "buy",
    #             "taker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #             "timestamp": 1673349019,
    #         },
    #         {
    #             "amount": 0.0001,
    #             "ask_id": 629,
    #             "bid_id": 705,
    #             "maker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #             "price": 1232.0,
    #             "side": "buy",
    #             "taker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #             "timestamp": 1673348857,
    #         },
    #         {
    #             "amount": 0.0001,
    #             "ask_id": 629,
    #             "bid_id": 704,
    #             "maker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #             "price": 1232.0,
    #             "side": "buy",
    #             "taker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #             "timestamp": 1673348591,
    #         },
    #         {
    #             "amount": 0.0001,
    #             "ask_id": 629,
    #             "bid_id": 703,
    #             "maker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #             "price": 1232.0,
    #             "side": "buy",
    #             "taker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
    #             "timestamp": 1673348457,
    #         }
    #     ],
    #     "type": "subscribed/trade",
    # }
    print("===\n\n")


async def listen_for_updates(ws):
    import time

    async for msg in ws:
        print(time.time())
        pprint(json.loads(msg))

        ### Update message on orderbook
        # {
        #     "channel": "421613:WETH_USDC",
        #     "orders": {"asks": [], "bids": [{"price": 1232.0, "size": 0.0}]},
        #     "type": "update/orderbook",
        # }

        ### Update messsage on trades
        # {
        #     "channel": "421613:WETH_USDC",
        #     "owner": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
        #     "trades": [
        #         {
        #             "amount": 0.0001,
        #             "maker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
        #             "price": 1232.0,
        #             "side": "buy",
        #             "taker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
        #             "timestamp": 1673445801,
        #         }
        #     ],
        #     "type": "update/trade",
        # }

        ### Update messages on account

        # {
        #     "account": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
        #     "balance": 1627039335758970000,
        #     "channel": "421613:WETH_USDC",
        #     "orders": [
        #         {
        #             "filled_amount": 0.0,
        #             "id": "733",
        #             "price": 1232.0,
        #             "side": "buy",
        #             "size": 0.0001,
        #             "status": "OPEN",
        #         }
        #     ],
        #     "trades": [],
        #     "type": "update/account",
        # }

        # {
        #     "account": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
        #     "balance": 1627039335758970000,
        #     "channel": "421613:WETH_USDC",
        #     "orders": [
        #         {
        #             "filled_amount": 0.0197,
        #             "id": "629",
        #             "price": 1232.0,
        #             "side": "sell",
        #             "size": 4.7278,
        #             "status": "OPEN",
        #         },
        #         {
        #             "filled_amount": 0.0001,
        #             "id": "733",
        #             "price": 1232.0,
        #             "side": "buy",
        #             "size": 0.0001,
        #             "status": "FILLED",
        #         },
        #     ],
        #     "trades": [
        #         {
        #             "amount": 0.0001,
        #             "maker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
        #             "price": 1232.0,
        #             "side": "buy",
        #             "taker_address": "0xd057E08695d1843FC21F27bBd0Af5D4B06203F48",
        #             "timestamp": 1673445801,
        #         }
        #     ],
        #     "type": "update/account",
        # }
        print("======\n\n")


async def connect():
    auth = "XXXX"
    lighter_ws_url = "wss://mensa.elliot.ai/stream"
    async with websockets.connect(lighter_ws_url) as websocket:
        await subscribe_to_orderbook(websocket, auth)
        await subscribe_to_account(websocket, auth)
        await subscribe_to_trades(websocket, auth, "XXXX")
        await listen_for_updates(websocket)


asyncio.run(connect())
