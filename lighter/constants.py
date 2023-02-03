HOST = "https://mensa.elliot.ai"
TEST_HOST = "https://lighter-test.elliot.ai"

# ------------ Blockchain IDs -----------
BLOCKCHAIN_ARBITRUM_GOERLI_ID = 421613
BLOCKCHAIN_ARBITRUM_ID = 42161

# ------------ Assets -------------------
TOKEN_USDC = "USDC"
TOKEN_WBTC = "WBTC"
TOKEN_WETH = "WETH"
TOKEN_LINK = "LINK"
TOKEN_UNI = "UNI"

# ------------ Orderbooks -------------------
ORDERBOOK_WETH_USDC = "WETH_USDC"
ORDERBOOK_WBTC_USDC = "WBTC_USDC"
ORDERBOOK_WETH_WBTC = "WETH_WBTC"
ORDERBOOK_UNI_USDC = "UNI_USDC"
ORDERBOOK_LINK_USDC = "LINK_USDC"


# ------------ Order Statuses -------------------
ORDER_STATUS_OPEN = "partially_filled"
ORDER_STATUS_FILLED = "filled"
ORDER_STATUS_CANCELLED = "canceled"

# ------------ Order Types -------------------
ORDER_TYPE_LIMIT = "limit"
ORDER_TYPE_MARKET = "market"


# ------------ Ethereum Transactions ------------
DEFAULT_GAS_AMOUNT = 250000
DEFAULT_GAS_MULTIPLIER = 1.5
DEFAULT_GAS_PRICE = 4000000000
DEFAULT_GAS_PRICE_ADDITION = 300000
MAX_SOLIDITY_UINT = (
    115792089237316195423570985008687907853269984665640564039457584007913129639935
)
DEFAULT_API_TIMEOUT = 3000
