from datetime import datetime, timedelta

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus

from config.settings import settings
from src.data.cache import Cache

_cache = Cache()


def _get_data_client() -> StockHistoricalDataClient:
    return StockHistoricalDataClient(
        settings.alpaca_api_key,
        settings.alpaca_secret_key,
    )


def _get_trading_client() -> TradingClient:
    return TradingClient(
        settings.alpaca_api_key,
        settings.alpaca_secret_key,
        paper=("paper" in settings.alpaca_base_url),
    )


def get_bars(
    symbol: str,
    timeframe: TimeFrame = TimeFrame.Day,
    days: int = 200,
) -> pd.DataFrame:
    """Fetch historical bars for a symbol, returns a DataFrame."""
    cache_key = f"bars_{symbol}_{timeframe}_{days}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    client = _get_data_client()
    start = datetime.now() - timedelta(days=days)
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=start,
    )
    barset = client.get_stock_bars(request)
    bars = barset.df
    if isinstance(bars.index, pd.MultiIndex):
        bars = bars.droplevel("symbol")
    bars.index = pd.to_datetime(bars.index)
    bars = bars.sort_index()

    _cache.set(cache_key, bars)
    return bars


def get_multi_bars(
    symbols: list[str],
    timeframe: TimeFrame = TimeFrame.Day,
    days: int = 200,
) -> dict[str, pd.DataFrame]:
    """Fetch bars for multiple symbols at once."""
    cache_key = f"multi_bars_{'_'.join(sorted(symbols))}_{timeframe}_{days}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    client = _get_data_client()
    start = datetime.now() - timedelta(days=days)
    request = StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=timeframe,
        start=start,
    )
    barset = client.get_stock_bars(request)
    df = barset.df

    result: dict[str, pd.DataFrame] = {}
    if isinstance(df.index, pd.MultiIndex) and "symbol" in df.index.names:
        for sym in df.index.get_level_values("symbol").unique():
            sym_df = df.xs(sym, level="symbol").sort_index()
            sym_df.index = pd.to_datetime(sym_df.index)
            result[sym] = sym_df
    else:
        # Single symbol fallback
        df.index = pd.to_datetime(df.index)
        result[symbols[0]] = df.sort_index()

    _cache.set(cache_key, result)
    return result


def get_latest_quote(symbol: str) -> dict:
    """Get the latest quote for a symbol."""
    client = _get_data_client()
    request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
    quotes = client.get_stock_latest_quote(request)
    quote = quotes[symbol]
    return {
        "symbol": symbol,
        "bid": float(quote.bid_price),
        "ask": float(quote.ask_price),
        "bid_size": int(quote.bid_size),
        "ask_size": int(quote.ask_size),
    }


def get_tradeable_assets() -> list[dict]:
    """Get list of active, tradeable US equities."""
    cache_key = "tradeable_assets"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    client = _get_trading_client()
    request = GetAssetsRequest(
        asset_class=AssetClass.US_EQUITY,
        status=AssetStatus.ACTIVE,
    )
    assets = client.get_all_assets(request)
    result = [
        {"symbol": a.symbol, "name": a.name, "exchange": a.exchange}
        for a in assets
        if a.tradable and a.fractionable is not None
    ]
    _cache.set(cache_key, result)
    return result


def get_account() -> dict:
    """Get account info."""
    client = _get_trading_client()
    account = client.get_account()
    return {
        "equity": float(account.equity),
        "buying_power": float(account.buying_power),
        "cash": float(account.cash),
    }
