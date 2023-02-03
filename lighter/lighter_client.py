from typing import List, Optional
from web3 import Web3

from lighter.constants import DEFAULT_API_TIMEOUT, HOST, TEST_HOST
from lighter.modules.blockchain import Blockchain, Orderbook
from lighter.modules.api import Api


class Client(object):
    def __init__(
        self,
        api_auth: str,
        web3_provider_url: str,
        private_key: Optional[str] = None,
        host: Optional[str] = None,
        send_options: Optional[dict] = {},
        api_timeout: Optional[int] = None,
    ):

        self.host = host or HOST

        if self.host.endswith("/"):
            self.host = self.host[:-1]

        self.private_key = private_key
        self.api_timeout = api_timeout or DEFAULT_API_TIMEOUT
        self.send_options = send_options or {}

        web3_provider = Web3.HTTPProvider(
            web3_provider_url, request_kwargs={"timeout": self.api_timeout}
        )
        self.web3 = Web3(web3_provider)
        self.blockchain_id = self.web3.eth.chain_id
        self.api_auth = api_auth

        self._api = Api(
            host=self.host,
            blockchain_id=self.blockchain_id,
            api_auth=self.api_auth,
            api_timeout=api_timeout,
        )
        self._blockchain = None

    @property
    def api(self):
        """
        Get the api module, used for interacting with endpoints.
        """
        return self._api

    @property
    def blockchain(self):
        """
        Get the blockchain module, used for interracting with contracts.
        """

        if not self._blockchain:
            if self.web3 and self.private_key:

                orderbooks: List[Orderbook] = self.api.get_orderbook_meta().data[
                    "orderbookmetas"
                ]

                chains = self.api.get_blockchains().data["blockchains"]

                chain = next(
                    (
                        item
                        for item in chains
                        if item["chain_id"] == str(self.blockchain_id)
                    ),
                    None,
                )

                if not chain:
                    raise Exception(
                        "Chain with chain_id {} not found".format(self.blockchain_id)
                    )

                self._blockchain = Blockchain(
                    web3=self.web3,
                    blockchain_id=self.blockchain_id,
                    orderbooks=orderbooks,
                    private_key=self.private_key,
                    api=self._api,
                    router_address=chain["router_address"],
                    factory_address=chain["factory_address"],
                    send_options=self.send_options,
                )
            else:
                raise Exception(
                    "Blockchain module is not supported since neither web3 "
                    + "nor web3_provider was provided OR since"
                    + "private_key was not provided",
                )

        return self._blockchain
