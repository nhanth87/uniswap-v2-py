import os
import json
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput


class UniswapV2Utils(object):

    ZERO_ADDRESS = Web3.toHex(0x0)

    @staticmethod
    def sort_tokens(token_a, token_b):
        assert token_a != token_b
        (token_0, token_1) = (token_a, token_b) if int(token_a, 16) < int(token_b, 16) else (token_b, token_a)
        assert token_0 != UniswapV2Utils.ZERO_ADDRESS
        return token_0, token_1

    @staticmethod
    def pair_for(factory, token_a, token_b):
        prefix = Web3.toHex(hexstr="ff")
        encoded_tokens = Web3.solidityKeccak(["address", "address"], UniswapV2Utils.sort_tokens(token_a, token_b))
        suffix = Web3.toHex(hexstr="96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f")
        raw = Web3.solidityKeccak(["bytes", "address", "bytes", "bytes"], [prefix, factory, encoded_tokens, suffix])
        return Web3.toChecksumAddress(Web3.toHex(raw)[-40:])

    @staticmethod
    def get_reserves(factory, token_a, token_b):
        pass  # TODO move to UniswapV2Client

    @staticmethod
    def calculate_quote(amount_a, reserve_a, reserve_b):
        assert amount_a > 0
        assert reserve_a > 0 and reserve_b > 0
        return amount_a * (reserve_b/reserve_a)

    @staticmethod
    def get_amount_out(amount_in, reserve_in, reserve_out):
        """
        Given an input asset amount, returns the maximum output amount of the
        other asset (accounting for fees) given reserves.

        :param amount_in: Amount of input asset.
        :param reserve_in: Reserve of input asset in the pair contract.
        :param reserve_out: Reserve of input asset in the pair contract.
        :return: Maximum amount of output asset.
        """
        assert amount_in > 0
        assert reserve_in > 0 and reserve_out > 0
        amount_in_with_fee = amount_in*997
        numerator = amount_in_with_fee*reserve_out
        denominator = reserve_in*1000 + amount_in_with_fee
        return numerator/denominator

    @staticmethod
    def get_amount_in(amount_out, reserve_in, reserve_out):
        """
        Returns the minimum input asset amount required to buy the given
        output asset amount (accounting for fees) given reserves.

        :param amount_out: Amount of output asset.
        :param reserve_in: Reserve of input asset in the pair contract.
        :param reserve_out: Reserve of input asset in the pair contract.
        :return: Required amount of input asset.
        """
        assert amount_out > 0
        assert reserve_in > 0 and reserve_out > 0
        numerator = reserve_in*reserve_out*1000
        denominator = reserve_out - amount_out*997
        return numerator/denominator + 1

    @staticmethod
    def get_amounts_out(amount_in, path):
        """
        Given an input asset amount and an array of token addresses, calculates
        all subsequent maximum output token amounts by calling get_reserves
        for each pair of token addresses in the path in turn, and using these to
        call get_amount_out.

        :param amount_in: Amount of input asset.
        :param path: Array of token addresses (pools of consecutive pair of addresses must exist).
        :return: Maximum amount of output asset.
        """
        pass  # TODO move to UniswapV2Client

    @staticmethod
    def get_amounts_in(amount_out, path):
        """
        Given an output asset amount and an array of token addresses,
        calculates all preceding minimum input token amounts by calling
        get_reserves for each pair of token addresses in the path in turn,
        and using these to call get_amount_in.

        :param amount_out: Amount of output asset.
        :param path: Array of token addresses (pools of consecutive pair of addresses must exist).
        :return: Required amount of input asset.
        """
        pass


class UniswapObject(object):

    def __init__(self, address, private_key, provider=None):
        self.address = Web3.toChecksumAddress(address)
        self.private_key = private_key

        self.provider = os.environ["PROVIDER"] if not provider else provider
        self.conn = Web3(Web3.HTTPProvider(self.provider, request_kwargs={"timeout": 60}))
        if not self.conn.isConnected():
            raise RuntimeError("Unable to connect to provider at " + self.provider)

    def _create_transaction_params(self, value=0, gas=1500000):
        return {
            "from": self.address,
            "value": value,
            'gasPrice': self.conn.toWei("15", "gwei"),
            "gas": gas,
            "nonce": self.conn.eth.getTransactionCount(self.address),
        }

    def _send_transaction(self, func, params):
        tx = func.buildTransaction(params)
        signed_tx = self.conn.eth.account.sign_transaction(tx, private_key=self.private_key)
        return self.conn.eth.sendRawTransaction(signed_tx.rawTransaction)


class UniswapV2Client(UniswapObject):

    FACTORY_ADDRESS = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
    ADDRESS = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
    ABI = json.load(open(os.path.dirname(os.path.abspath(__file__)) + "/assets/IUniswapV2Factory.json"))["abi"]

    ROUTER_ADDRESS = "0xf164fC0Ec4E93095b804a4795bBe1e041497b92a"
    ROUTER_ABI = json.load(open(os.path.dirname(os.path.abspath(__file__)) + "/assets/IUniswapV2Router01.json"))["abi"]

    MAX_APPROVAL_HEX = "0x" + "f" * 64
    MAX_APPROVAL_INT = int(MAX_APPROVAL_HEX, 16)
    ERC20_ABI = json.load(open(os.path.dirname(os.path.abspath(__file__)) + "/assets/IUniswapV2ERC20.json"))["abi"]

    PAIR_ABI = json.load(open(os.path.dirname(os.path.abspath(__file__)) + "/assets/IUniswapV2Pair.json"))["abi"]

    def __init__(self, address, private_key, provider=None):
        super().__init__(address, private_key, provider)
        self.contract = self.conn.eth.contract(
            address=Web3.toChecksumAddress(UniswapV2Client.ADDRESS), abi=UniswapV2Client.ABI)
        self.router = self.conn.eth.contract(
            address=Web3.toChecksumAddress(UniswapV2Client.ROUTER_ADDRESS), abi=UniswapV2Client.ROUTER_ABI)

    # Utilities
    # -----------------------------------------------------------
    def _is_approved(self, token, amount=MAX_APPROVAL_INT):
        erc20_contract = self.conn.eth.contract(
            address=Web3.toChecksumAddress(token), abi=UniswapPair.ABI)
        approved_amount = erc20_contract.functions.allowance(self.address, self.router.address).call()
        return approved_amount >= amount

    def is_approved(self, token, amount=MAX_APPROVAL_INT):
        return self._is_approved(token, amount)

    def approve(self, token, max_approval=MAX_APPROVAL_INT):
        if self._is_approved(token, max_approval):
            return

        print("Approving {} of {}".format(max_approval, token))
        erc20_contract = self.conn.eth.contract(
            address=Web3.toChecksumAddress(token), abi=UniswapV2Client.ERC20_ABI)

        func = erc20_contract.functions.approve(self.router.address, max_approval)
        params = self._create_transaction_params()
        tx = self._send_transaction(func, params)

        # wait for transaction receipt
        self.conn.eth.waitForTransactionReceipt(tx, timeout=6000)  # TODO raise exception on timeout

    # Factory Read-Only Functions
    # -----------------------------------------------------------
    def get_pair(self, token_a, token_b):
        """
        Gets the address of the pair for token_a and token_b,
        if it has been created, else 0x0.
        :return: Address of the pair.
        """
        addr_1 = self.conn.toChecksumAddress(token_a)
        addr_2 = self.conn.toChecksumAddress(token_b)
        return self.contract.functions.getPair(addr_1, addr_2).call()

    def get_pair_by_index(self, pair_index):
        """
        Gets the address of the nth pair (0-indexed) created through
        the factory, or 0x0 if not enough pairs have been created yet.

        :param pair_index: Index of the pair in the factory.
        :return: Address of the indexed pair.
        """
        try:
            return self.contract.functions.allPairs(pair_index).call()
        except BadFunctionCallOutput:
            return "0x0000000000000000000000000000000000000000"

    def get_num_pairs(self):
        """
        Gets the total number of pairs created through the factory so far.

        :return: Total number of pairs.
        """
        return self.contract.functions.allPairsLength().call()

    def get_fee(self):
        """
        :return: Protocol wide fee.
        """
        return self.contract.functions.feeTo().call()

    def get_fee_setter(self):
        """
        :return: Address allowed to change the fee.
        """
        return self.contract.functions.feeToSetter().call()

    # Factory State-Changing Functions
    # -----------------------------------------------------------
    def _create_pair(self, token_1, token_2):  # TODO remove deprecated
        """
        Creates a pair for tokenA and tokenB if one does not exist already.
        :return: the created address of the pair.
        """
        func = self.contract.functions.createPair(token_1, token_2)
        params = self._create_transaction_params()
        return self._send_transaction(func, params)

    # Router Read-Only Functions
    # -----------------------------------------------------------
    def get_factory(self, query_chain=False):
        """
        Returns the address for the factory contract.

        :param query_chain: Whether or not to query the on chain contract.
        :return: The factory address.
        """
        if query_chain:
            return self.router.functions.factory().call()
        return UniswapV2Client.FACTORY_ADDRESS

    def get_weth_address(self):
        """
        Returns the canonical WETH address on the Ethereum mainnet, or the
        Ropsten, Rinkeby, Gorli, or Kovan testnets.

        :return: The canonical WETH address
        """
        return self.router.functions.WETH().call()

    # Router State-Changing Functions
    # -----------------------------------------------------------
    def add_liquidity(self, token_a, token_b, amount_a, amount_b, min_a, min_b, to, deadline):
        """
        Add liquidity to a ERC20-ERC20 token pool.

        :param token_a: Address of a pool token.
        :param token_b: Address of a pool token.
        :param amount_a: Amount of token_a to add as liquidity.
        :param amount_b: Amount of token_b to add as liquidity.
        :param min_a: Bound to the extent to which the B/A price can go up before the transaction reverts.
        :param min_b: Bound tp the extent to which the A/B price can go up before the transaction reverts.
        :param to: Address of the recipient for the liquidity tokens.
        :param deadline: Unix timestamp after which the transaction will revert.
        :return:
            - amount_a - Amount of token_a sent to the pool.
            - amount_b - Amount of token_b sent to the pool.
            - liquidity - Amount of liquidity tokens minted.
        """
        self.approve(token_a, amount_a)
        self.approve(token_b, amount_b)
        func = self.router.functions.addLiquidity(token_a, token_b, amount_a, amount_b, min_a, min_b, to, deadline)
        params = self._create_transaction_params()
        return self._send_transaction(func, params)

    def add_liquidity_eth(self, token, amount_token, amount_eth, min_token, min_eth, to, deadline):
        """
        Add liquidity to an ERC20-WETH pool with ETH.

        :param token: Address of a pool token.
        :param amount_token: Amount of token to add as liquidity.
        :param amount_eth: Amount of ETH to add as liquidity.
        :param min_token: Bound to the extent to which the WETH/token price can go up before the transaction reverts
        :param min_eth: Bound to the extent to which the token/WETH price can go up before the transaction reverts.
        :param to: Address of the recipient for the liquidity tokens.
        :param deadline: Unix timestamp after which the transaction will revert.
        :return:
            - amount_token - Amount of token sent to the pool.
            - amount_eth - Amount of ETH converted to WETH and sent to the pool.
            - liquidity - Amount of liquidity tokens minted.
        """
        self.approve(token, amount_token)
        func = self.router.functions.addLiquidityETH(token, amount_token, min_token, min_eth, to, deadline)
        params = self._create_transaction_params(amount_eth)
        return self._send_transaction(func, params)

    def remove_liquidity(self, token_a, token_b, liquidity, min_a, min_b, to, deadline):
        """
        Remove liquidity from an ERC20-ERC20 pool.

        :param token_a: Address of a pool token.
        :param token_b: Address of a pool token.
        :param liquidity: Amount of liquidity tokens to remove.
        :param min_a: Minimum amount of token_a that must be received for the transaction not to revert.
        :param min_b: Minimum amount of token_b that must be received for the transaction not to revert.
        :param to: Address of the recipient for the underlying assets.
        :param deadline: Unix timestamp after which the transaction will revert.
        :return:
            - amount_a - Amount of token_a received.
            - amount_b - Amount of token_b received.
        """
        self.approve(self.get_pair(token_a, token_b), liquidity)
        func = self.router.functions.removeLiquidity(token_a, token_b, liquidity, min_a, min_b, to, deadline)
        params = self._create_transaction_params()
        return self._send_transaction(func, params)

    def remove_liquidity_eth(self, token, liquidity, min_token, min_eth, to, deadline):
        """
        Remove liquidity from an ERC20-WETH pool and receive ETH.

        :param token: Address of a pool token.
        :param liquidity: Amount of liquidity tokens to remove.
        :param min_token: Minimum amount of token that must be received for the transaction not to revert.
        :param min_eth: Minimum amount of ETH that must be received for the transaction not to revert.
        :param to: Address of the recipient for the underlying assets.
        :param deadline: Unix timestamp after which the transaction will revert.
        :return:
            - amount_token - Amount of token received.
            - amount_eth - Amount of ETH received.
        """
        self.approve(self.get_pair(token, "0xc778417e063141139fce010982780140aa0cd5ab"), liquidity)  # FIXME hardcoded WETH address
        func = self.router.functions.removeLiquidityETH(token, liquidity, min_token, min_eth, to, deadline)
        params = self._create_transaction_params()
        return self._send_transaction(func, params)

    def remove_liquidity_with_permit(
            self, token_a, token_b, liquidity, min_a, min_b, to, deadline, approve_max, v, r, s):
        """
        Remove liquidity from an ERC20-ERC20 pool without pre-approval, thanks to permit.

        :param token_a: Address of a pool token.
        :param token_b: Address of a pool token.
        :param liquidity: Amount of liquidity tokens to remove.
        :param min_a: Minimum amount of token_a that must be received for the transaction not to revert.
        :param min_b: Minimum amount of token_b that must be received for the transaction not to revert.
        :param to: Address of the recipient for the underlying assets.
        :param deadline: Unix timestamp after which the transaction will revert.
        :param approve_max: Whether or not the approval amount in the signature is for liquidity or uint(-1).
        :param v: Component v of the permit signature.
        :param r: Component r of the permit signature.
        :param s: Component s of the permit signature.
        :return:
            - amount_a - Amount of token_a received.
            - amount_b - Amount of token_b received.
        """
        func = self.router.functions.removeLiquidityWithPermit(
            token_a, token_b, liquidity, min_a, min_b, to, deadline, approve_max, v, r, s)
        params = self._create_transaction_params()
        return self._send_transaction(func, params)

    def remove_liquidity_eth_with_permit(
            self,  token, liquidity, min_token, min_eth, to, deadline, approve_max, v, r, s):
        """
        Remove liquidity from an ERC20-WETH pool and receive ETH without pre-approval, thanks to permit.

        :param token: Address of a pool token.
        :param liquidity: Amount of liquidity tokens to remove.
        :param min_token: Minimum amount of token that must be received for the transaction not to revert.
        :param min_eth: Minimum amount of ETH that must be received for the transaction not to revert.
        :param to: Address of the recipient for the underlying assets.
        :param deadline: Unix timestamp after which the transaction will revert.
        :param approve_max: Whether or not the approval amount in the signature is for liquidity or uint(-1).
        :param v: Component v of the permit signature.
        :param r: Component r of the permit signature.
        :param s: Component s of the permit signature.
        :return:
            - amount_token - Amount of token received.
            - amount_eth - Amount of ETH received.
        """
        func = self.router.functions.removeLiquidityETHWithPermit(
            token, liquidity, min_token, min_eth, to, deadline, approve_max, v, r, s)
        params = self._create_transaction_params()
        return self._send_transaction(func, params)

    def swap_exact_tokens_for_tokens(self, amount, min_out, path, to, deadline):
        """
        Swaps an exact amount of input tokens for as many output tokens as
        possible, along the route determined by the path. The first element of
        path is the input token, the last is the output token, and any intermediate
        elements represent intermediate pairs to trade through (if for example,
        a direct pair does not exist)

        :param amount: Amount of input tokens to send.
        :param min_out: Minimum amount of output tokens that must be received for the transaction not to revert.
        :param path: Array of token addresses (pools of consecutive pair of addresses must exist and have liquidity).
        :param to: Address of the recipient for the output tokens.
        :param deadline: Unix timestamp after which the transaction will revert.
        :return: Input token amount and all subsequent output token amounts.
        """
        self.approve(path[0], amount)
        func = self.router.functions.swapExactTokensForTokens(amount, min_out, path, to, deadline)
        params = self._create_transaction_params()
        return self._send_transaction(func, params)

    def swap_tokens_for_exact_tokens(self, amount_out, amount_in_max, path, to, deadline):
        """
        Receive an exact amount of output tokens for as few input tokens as
        possible, along the route determined by the path. The first element of
        path is the input token, the last is the output token, and any intermediate
        elements represent intermediate pairs to trade through (if for example,
        a direct pair does not exist).

        :param amount_out: Amount of tokens to receive.
        :param amount_in_max: Maximum amount of input tokens that can be required before the transaction reverts.
        :param path: Array of token addresses (pools of consecutive pair of addresses must exist and have liquidity).
        :param to: Address of the recipient for the output tokens.
        :param deadline: Unix timestamp after which the transaction will revert.
        :return: Input token amount and all subsequent output token amounts.
        """
        self.approve(path[0], amount_out)
        func = self.router.functions.swapTokensForExactTokens(amount_out, amount_in_max, path, to, deadline)
        params = self._create_transaction_params()
        return self._send_transaction(func, params)

    def swap_exact_eth_for_tokens(self, amount, min_out, path, to, deadline):
        """
        Swaps an exact amount of ETH for as many output tokens as possible,
        along the route determined by the path. The first element of path must
        be WETH, the last is the output token, and any intermediate elements
        represent intermediate pairs to trade through (if for example, a direct
        pair does not exist).

        :param amount: Amount of ETH to send.
        :param min_out: Minimum amount of output tokens that must be received for the transaction not to revert.
        :param path: Array of token addresses (pools of consecutive pair of addresses must exist and have liquidity).
        :param to: Address of the recipient for the output tokens.
        :param deadline: Unix timestamp after which the transaction will revert.
        :return: Input token amount and all subsequent output token amounts.
        """
        func = self.router.functions.swapExactETHForTokens(min_out, path, to, deadline)
        params = self._create_transaction_params(amount)
        return self._send_transaction(func, params)

    def swap_tokens_for_exact_eth(self, amount_out, amount_in_max, path, to, deadline):
        """
        Receive an exact amount of ETH for as few input tokens as possible,
        along the route determined by the path. The first element of path is the
        input token, the last must be WETH, and any intermediate elements
        represent intermediate pairs to trade through (if for example, a direct
        pair does not exist).

        :param amount_out: Amount of ETH to receive.
        :param amount_in_max: Maximum amount of input tokens that can be required before the transaction reverts.
        :param path: Array of token addresses (pools of consecutive pair of addresses must exist and have liquidity).
        :param to: Address of the recipient for the ETH.
        :param deadline: Unix timestamp after which the transaction will revert.
        :return: Input token amount and all subsequent output token amounts.
        """
        self.approve(path[0], amount_out)
        func = self.router.functions.swapTokensForExactETH(amount_out, amount_in_max, path, to, deadline)
        params = self._create_transaction_params()
        return self._send_transaction(func, params)

    def swap_exact_tokens_for_eth(self, amount, min_out, path, to, deadline):
        """
        Swaps an exact amount of tokens for as much ETH as possible, along
        the route determined by the path. The first element of path is the input
        token, the last must be WETH, and any intermediate elements represent
        intermediate pairs to trade through (if for example, a direct pair does
        not exist).

        :param amount: Amount of input tokens to send.
        :param min_out: Minimum amount of output tokens that must be received for the transaction not to revert.
        :param path: Array of token addresses (pools of consecutive pair of addresses must exist and have liquidity).
        :param to: Address of the recipient for the ETH.
        :param deadline: Unix timestamp after which the transaction will revert.
        :return: Input token amount and all subsequent output token amounts.
        """
        self.approve(path[0], amount)
        func = self.router.functions.swapExactTokensForETH(amount, min_out, path, to, deadline)
        params = self._create_transaction_params()
        return self._send_transaction(func, params)
        pass

    def swap_eth_for_exact_tokens(self, amount_out, amount_in_max, path, to, deadline):
        """
        Receive an exact amount of tokens for as little ETH as possible, along
        the route determined by the path. The first element of path must be
        WETH, the last is the output token and any intermediate elements
        represent intermediate pairs to trade through (if for example, a direct
        pair does not exist).

        :param amount_out: Amount of tokens to receive.
        :param amount_in_max: Maximum amount of ETH that can be required before the transaction reverts.
        :param path: Array of token addresses (pools of consecutive pair of addresses must exist and have liquidity).
        :param to: Address of the recipient for the output tokens.
        :param deadline: Unix timestamp after which the transaction will revert.
        :return: Input token amount and all subsequent output token amounts.
        """
        func = self.router.functions.swapETHForExactTokens(amount_out, path, to, deadline)
        params = self._create_transaction_params(amount_in_max)
        return self._send_transaction(func, params)

    # Pair Read-Only Functions
    # -----------------------------------------------------------

    def get_token_0(self, pair):
        """
        Gets the address of the pair token with the lower sort order.

        :param pair: Address of the pair.
        :return: Address of the pair token with the lower sort order
        """
        pair_contract = self.conn.eth.contract(
            address=Web3.toChecksumAddress(pair), abi=UniswapV2Client.PAIR_ABI)
        return pair_contract.functions.token0().call()

    def get_token_1(self, pair):
        """
        Gets the address of the pair token with the lower sort order.

        :param pair: Address of the pair.
        :return: Address of the pair token with the lower sort order.
        """
        pair_contract = self.conn.eth.contract(
            address=Web3.toChecksumAddress(pair), abi=UniswapV2Client.PAIR_ABI)
        return pair_contract.functions.token1().call()

    def get_reserves(self, pair):
        """
        Gets the reserves of token_0 and token_1 used to price trades
        and distribute liquidity as well as the timestamp of the last block
        during which an interaction occurred for the pair.

        :param pair: Address of the pair.
        :return:
            - reserve_0 - Amount of token_0 in the contract.
            - reserve_1 - Amount of token_1 in the contract.
            - liquidity - Unix timestamp of the block containing the last pair interaction.
        """
        pair_contract = self.conn.eth.contract(
            address=Web3.toChecksumAddress(pair), abi=UniswapV2Client.PAIR_ABI)
        return pair_contract.functions.getReserves().call()

    def get_price_0_cumulative_last(self, pair):
        """
        Gets the commutative price of the pair calculated relatively
        to token_0.

        :param pair: Address of the pair.
        :return: Commutative price relative to token_0.
        """
        pair_contract = self.conn.eth.contract(
            address=Web3.toChecksumAddress(pair), abi=UniswapV2Client.PAIR_ABI)
        return pair_contract.functions.price0CumulativeLast().call()

    def get_price_1_cumulative_last(self, pair):
        """
        Gets the commutative price of the pair calculated relatively
        to token_1.

        :param pair: Address of the pair.
        :return: Commutative price relative to token_1.
        """
        pair_contract = self.conn.eth.contract(
            address=Web3.toChecksumAddress(pair), abi=UniswapV2Client.PAIR_ABI)
        return pair_contract.functions.price1CumulativeLast().call()

    def get_k_last(self, pair):
        """
        Returns the product of the reserves as of the most recent
        liquidity event.

        :param pair: Address of the pair.
        :return: Product of the reserves.
        """
        pair_contract = self.conn.eth.contract(
            address=Web3.toChecksumAddress(pair), abi=UniswapV2Client.PAIR_ABI)
        return pair_contract.functions.kLast().call()


class UniswapPair(UniswapObject):

    ABI = json.load(open(os.path.dirname(os.path.abspath(__file__)) + "/assets/IUniswapV2Pair.json"))

    MAX_APPROVAL_HEX = "0x" + "f" * 64
    MAX_APPROVAL_INT = int(MAX_APPROVAL_HEX, 16)
    ERC20_ABI = json.load(open(os.path.dirname(os.path.abspath(__file__)) + "/assets/IUniswapV2ERC20.json"))["abi"]

    def __init__(self, pair_address, address, private_key, provider=None):
        super().__init__(address, private_key, provider)
        self.contract = self.conn.eth.contract(
            address=Web3.toChecksumAddress(pair_address), abi=UniswapPair.ABI)

        self.token_0 = None
        self.token_1 = None


def main():
    address = Web3.toChecksumAddress("0x09B487E73B4Ca5aEb7B108a9Ebd91d977Aa36648")
    private_key = "fe7f7b941ee8a53d7da1d16e8d4093de26046e2566880e37611265f7c3813f2b"
    provider = "https://ropsten.infura.io/v3/8ce5c9d6732945bd9e8baa57c6798e0b"
    uniswap = UniswapV2Client(address, private_key, provider)

    uniswap.approve(Web3.toChecksumAddress("0x98A608D3f29EebB496815901fcFe8eCcC32bE54a"))
    print(uniswap.is_approved("0x98A608D3f29EebB496815901fcFe8eCcC32bE54a", amount=2 * 10 ** 14))

    """num_pairs = uniswap.get_num_pairs()
    print("Number of pools: {}".format(num_pairs))

    pool_addr = uniswap.get_pair_by_index(42)
    pool = UniswapPair(pool_addr, address, private_key, provider)
    token_0 = pool.get_token_0()
    token_1 = pool.get_token_1()
    print(token_0)
    print(token_1)"""

    link_addr = "0x20fE562d797A42Dcb3399062AE9546cd06f63280"
    link_amount = 1*(10**19)  # 10.0 linkies
    eth_amount = 2*(10**17)   # 0.2  double digit shitcoin

    """
    uniswap.approve(link_addr)
    uniswap.add_liquidity_eth(
        token=link_addr, amount_token=link_amount, amount_eth=eth_amount, min_token=int(eth_amount/link_amount) + 1,
        min_eth=int(link_amount/eth_amount) + 1, to=address, deadline=int(time.time()) + 1000)
    """


    """pools = {}
    for i in range(num_pairs):
        print("Fetching pool {} of {}...".format(i, num_pairs - 1))
        pool_addr = uniswap.all_pair_by_index(i)
        pool = UniswapPair(pool_addr, address, private_key, provider)
        token_0 = pool.get_token_0()
        token_1 = pool.get_token_1()
        pools[str(i)] = {"pair": pool_addr, "token_0": token_0, "token_1": token_1}

    with open("pools.json", "w") as f:
        f.write(json.dumps(pools))"""


    """pool_0_addr = uniswap.all_pair_by_index(0)
    print("Pool 0: {}".format(pool_0_addr))

    pool_0 = UniswapPair(pool_0_addr, address, private_key, provider)
    token_0 = pool_0.get_token_0()  # MOO
    token_1 = pool_0.get_token_1()  # WETH

    reserves = pool_0.get_reserves()
    ratio_0_to_1 = reserves[1]/reserves[0]
    ratio_1_to_0 = reserves[0]/reserves[1]

    print("Token 0: {}".format(token_0))
    print("Token 1: {}".format(token_1))
    print("Reserves: {}".format(reserves))

    pool_0.approve(token_0)
    pool_0.approve(token_1)

    amount_to_send = 10**14  # WETH
    amount_to_recv = int(amount_to_send*ratio_1_to_0)
    print(amount_to_send)
    print(amount_to_recv)

    print("C Ratio > {}".format((10**18)*ratio_0_to_1))
    print("A Ratio > {}".format(UniswapLibrary.get_quote((10**18), reserves[0], reserves[1])))
    print("Swapping {} WETH for {} MOO".format(amount_to_send/(10**18), amount_to_recv/(10**18)))
    pool_0.swap(amount_to_recv, amount_to_send, address)"""


if __name__ == '__main__':
    factory = Web3.toChecksumAddress("0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f")
    link_token = Web3.toChecksumAddress("0x20fe562d797a42dcb3399062ae9546cd06f63280")
    weth_token = Web3.toChecksumAddress("0xc778417E063141139Fce010982780140Aa0cD5Ab")

    #pair = UniswapLibrary.pair_for(factory, link_token, weth_token)
    #print(pair == "0x98A608D3f29EebB496815901fcFe8eCcC32bE54a")
    #main()

    # Ropsten testnet
    #conn = web3.Web3(web3.Web3.HTTPProvider("HTTP://127.0.0.1:7545"))

    #address = web3.Web3.toChecksumAddress("0x09B487E73B4Ca5aEb7B108a9Ebd91d977Aa36648")
    #private_key = "fe7f7b941ee8a53d7da1d16e8d4093de26046e2566880e37611265f7c3813f2b"

    """factory = conn.eth.contract(abi=ABI, bytecode=BYTECODE)
    factory.constructor().transact()

    txn = factory.constructor().buildTransaction({
        'from': address,
        'nonce': conn.eth.getTransactionCount(address),
        'gas': 1,
        'gasPrice': conn.toWei('21', 'gwei')})
    signed_txn = conn.eth.account.signTransaction(txn, private_key=private_key)

    conn.eth.sendRawTransaction(signed_txn.rawTransaction)"""

    #factory = UniswapFactory(address, private_key, conn)
    #print(factory.all_pair_by_index(0))