from typing import Dict, Optional
from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()


class WalletManager:
    """Manages multi-chain crypto wallets"""

    def __init__(self) -> None:
        # Ethereum
        self.eth_provider = os.getenv('ETH_RPC_URL', 'https://eth.llamarpc.com')
        self.w3 = Web3(Web3.HTTPProvider(self.eth_provider))

        # Wallet addresses (from env)
        self.wallets: Dict[str, str] = {
            'btc': os.getenv('BTC_WALLET_ADDRESS', 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh'),
            'eth': os.getenv('ETH_WALLET_ADDRESS', '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb'),
            'ton': os.getenv('TON_WALLET_ADDRESS', 'EQD-2j_j...'),
            'usdc': os.getenv('USDC_WALLET_ADDRESS', '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb'),
        }

    def get_wallet(self, crypto: str) -> Optional[str]:
        """Get wallet address for specific crypto"""
        return self.wallets.get(crypto.lower())

    def get_eth_balance(self, address: str) -> float:
        """Get Ethereum balance"""
        try:
            balance_wei = self.w3.eth.get_balance(address)
            return float(self.w3.from_wei(balance_wei, 'ether'))
        except Exception as e:  # pragma: no cover - network errors
            print(f"Error getting ETH balance: {e}")
            return 0.0

    def get_all_balances(self) -> Dict[str, float]:
        """Get balances for all wallets"""
        balances: Dict[str, float] = {}

        # ETH balance
        if self.wallets.get('eth'):
            balances['eth'] = self.get_eth_balance(self.wallets['eth'])

        # Note: BTC, TON, and USDC require additional API integrations
        balances['btc'] = 0.0  # Placeholder
        balances['ton'] = 0.0  # Placeholder
        balances['usdc'] = 0.0  # Placeholder

        return balances
