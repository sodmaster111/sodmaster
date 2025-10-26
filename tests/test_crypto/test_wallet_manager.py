import pytest
from app.crypto.wallet_manager import WalletManager


def test_wallet_manager_init():
    wm = WalletManager()
    assert wm is not None
    assert 'btc' in wm.wallets
    assert 'eth' in wm.wallets
    assert 'ton' in wm.wallets


def test_get_wallet():
    wm = WalletManager()
    btc_wallet = wm.get_wallet('btc')
    assert btc_wallet is not None
    assert btc_wallet.startswith('bc1')


def test_get_all_balances():
    wm = WalletManager()
    balances = wm.get_all_balances()
    assert isinstance(balances, dict)
    assert 'eth' in balances
