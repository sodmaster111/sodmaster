import ccxt
from typing import Dict, Optional
from datetime import datetime

class PriceOracle:
    """Gets crypto prices from exchanges"""
    
    def __init__(self):
        # Initialize exchange connection (Binance as default)
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
        })
    
    def get_price(self, symbol: str, vs_currency: str = 'USDT') -> Optional[float]:
        """
        Get current price for a crypto
        symbol: BTC, ETH, TON, etc.
        vs_currency: USDT, USD, etc.
        """
        try:
            ticker = f"{symbol}/{vs_currency}"
            price_data = self.exchange.fetch_ticker(ticker)
            return price_data['last']
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
            return None
    
    def get_multiple_prices(self, symbols: list, vs_currency: str = 'USDT') -> Dict[str, float]:
        """Get prices for multiple cryptos"""
        prices = {}
        for symbol in symbols:
            price = self.get_price(symbol, vs_currency)
            if price:
                prices[symbol] = price
        return prices
    
    def calculate_portfolio_value(self, holdings: Dict[str, float]) -> float:
        """
        Calculate total portfolio value in USD
        holdings: {'BTC': 0.5, 'ETH': 2.0, 'TON': 1000}
        """
        total_usd = 0.0
        
        for crypto, amount in holdings.items():
            price = self.get_price(crypto, 'USDT')
            if price:
                total_usd += price * amount
        
        return total_usd
