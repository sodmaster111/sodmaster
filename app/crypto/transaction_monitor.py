from typing import Optional, Dict
from datetime import datetime
from web3 import Web3

class TransactionMonitor:
    """Monitors blockchain transactions"""
    
    def __init__(self, eth_rpc_url: str = 'https://eth.llamarpc.com'):
        self.w3 = Web3(Web3.HTTPProvider(eth_rpc_url))
    
    def verify_eth_transaction(self, tx_hash: str) -> Optional[Dict]:
        """
        Verify Ethereum transaction
        Returns transaction details if confirmed
        """
        try:
            tx = self.w3.eth.get_transaction(tx_hash)
            tx_receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            
            return {
                'hash': tx_hash,
                'from': tx['from'],
                'to': tx['to'],
                'value_eth': float(self.w3.from_wei(tx['value'], 'ether')),
                'confirmed': tx_receipt['status'] == 1,
                'block_number': tx_receipt['blockNumber'],
            }
        except Exception as e:
            print(f"Error verifying transaction {tx_hash}: {e}")
            return None
    
    def wait_for_confirmations(self, tx_hash: str, confirmations: int = 6) -> bool:
        """Wait for N confirmations on transaction"""
        try:
            tx_receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            current_block = self.w3.eth.block_number
            tx_block = tx_receipt['blockNumber']
            
            return (current_block - tx_block) >= confirmations
        except Exception as e:
            print(f"Error checking confirmations: {e}")
            return False
