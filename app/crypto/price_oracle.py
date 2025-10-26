from typing import Dict, Optional
from datetime import datetime

try:  # pragma: no cover - dependency availability varies in tests
    import ccxt  # type: ignore
except ImportError:  # pragma: no cover - fallback when ccxt is unavailable
    ccxt = None  # type: ignore


class PriceOracle:
    """Gets crypto prices from exchanges"""

    def __init__(self) -> None:
        # Initialize exchange connection (Binance as default)
        if ccxt is not None:
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
            })
        else:
            self.exchange = None

    def get_price(self, symbol: str, vs_currency: str = 'USDT') -> Optional[float]:
        """
        Get current price for a crypto
        symbol: BTC, ETH, TON, etc.
        vs_currency: USDT, USD, etc.
        """
        try:
            if self.exchange is None:
                return None
            ticker = f"{symbol}/{vs_currency}"
            price_data = self.exchange.fetch_ticker(ticker)
            return price_data['last']
        except Exception as e:  # pragma: no cover - network errors
            print(f"Error fetching price for {symbol}: {e}")
            return None

    def get_multiple_prices(self, symbols: list, vs_currency: str = 'USDT') -> Dict[str, float]:
        """Get prices for multiple cryptos"""
        prices: Dict[str, float] = {}
        for symbol in symbols:
            price = self.get_price(symbol, vs_currency)
            if price is not None:
                prices[symbol] = price
        return prices

    def calculate_portfolio_value(self, holdings: Dict[str, float]) -> float:
        """
        Calculate total portfolio value in USD
        holdings: {'BTC': 0.5, 'ETH': 2.0, 'TON': 1000}
        """
        total_usd = 0.0

        for crypto, amount in holdings.items():
            price = self.get_price(crypto.upper(), 'USDT')
            if price is not None:
                total_usd += price * amount

        return total_usd
