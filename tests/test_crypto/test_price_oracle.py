import pytest
from app.crypto.price_oracle import PriceOracle


def test_price_oracle_init():
    oracle = PriceOracle()
    assert oracle is not None


def test_get_price():
    oracle = PriceOracle()
    btc_price = oracle.get_price('BTC', 'USDT')

    # BTC price should be reasonable
    if btc_price:
        assert btc_price > 10000  # BTC > $10k
        assert btc_price < 200000  # BTC < $200k


def test_get_multiple_prices():
    oracle = PriceOracle()
    prices = oracle.get_multiple_prices(['BTC', 'ETH'], 'USDT')
    assert isinstance(prices, dict)
