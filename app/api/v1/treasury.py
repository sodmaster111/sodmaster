from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import Any, Dict
from app.crypto import WalletManager, PriceOracle

router = APIRouter(prefix="/api/v1/treasury", tags=["treasury"])

wallet_manager = WalletManager()
price_oracle = PriceOracle()


@router.get("/balances")
async def get_balances() -> Dict[str, Any]:
    """Get all crypto balances"""
    try:
        balances = wallet_manager.get_all_balances()
        return {
            "status": "success",
            "data": balances,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prices")
async def get_prices() -> Dict[str, Any]:
    """Get current crypto prices"""
    try:
        cryptos = ['BTC', 'ETH', 'TON', 'USDC']
        prices = price_oracle.get_multiple_prices(cryptos, 'USDT')
        return {
            "status": "success",
            "data": prices,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio-value")
async def get_portfolio_value() -> Dict[str, Any]:
    """Calculate total portfolio value in USD"""
    try:
        balances = wallet_manager.get_all_balances()
        total_usd = price_oracle.calculate_portfolio_value(balances)

        return {
            "status": "success",
            "data": {
                "total_usd": round(total_usd, 2),
                "breakdown": balances,
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wallets")
async def get_wallet_addresses() -> Dict[str, Any]:
    """Get all wallet addresses for deposits"""
    return {
        "status": "success",
        "data": wallet_manager.wallets,
        "note": "Send crypto to these addresses"
    }
