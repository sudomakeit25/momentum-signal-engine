"""Multi-criteria stock screener — combines filters + momentum scoring."""

from datetime import datetime

import pandas as pd

from config.settings import settings
from src.data import client
from src.data.models import ScanResult, SetupType
from src.scanner.filters import apply_filters
from src.scanner.momentum import (
    compute_momentum_score,
    detect_breakout,
    is_ema_aligned,
    is_near_52w_high,
    is_volume_surging,
)
from src.signals.indicators import relative_strength_vs_spy, volume_sma


def scan_universe(
    symbols: list[str],
    top_n: int | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_volume: int | None = None,
) -> list[ScanResult]:
    """Scan a list of symbols and return ranked momentum results.

    Args:
        symbols: List of ticker symbols to scan.
        top_n: Return top N results (default from settings).
        min_price: Minimum price filter.
        max_price: Maximum price filter.
        min_volume: Minimum average volume filter.

    Returns:
        List of ScanResult sorted by momentum score descending.
    """
    top_n = top_n or settings.scan_top_n
    min_price = min_price or settings.scan_min_price
    max_price = max_price or settings.scan_max_price
    min_volume = min_volume or settings.scan_min_volume

    # Fetch SPY for relative strength comparison
    spy_df = client.get_bars("SPY", days=200)

    # Fetch all symbol bars in one batch
    bars_map = client.get_multi_bars(symbols, days=200)

    results: list[ScanResult] = []

    for symbol, df in bars_map.items():
        if df.empty or len(df) < 50:
            continue

        if not apply_filters(df, min_price, max_price, min_volume):
            continue

        score = compute_momentum_score(df, spy_df)
        if score < 20:
            continue

        # Gather metadata
        last_close = df["close"].iloc[-1]
        prev_close = df["close"].iloc[-2] if len(df) > 1 else last_close
        change_pct = ((last_close - prev_close) / prev_close) * 100
        last_volume = int(df["volume"].iloc[-1])
        avg_vol = int(volume_sma(df["volume"], 20).iloc[-1])

        # Relative strength
        rs_val = 0.0
        if len(df) >= 63 and len(spy_df) >= 63:
            rs = relative_strength_vs_spy(df["close"], spy_df["close"], 63)
            rs_val = float(rs.iloc[-1]) if pd.notna(rs.iloc[-1]) else 0.0

        # Identify setup types present
        setups: list[SetupType] = []
        if is_ema_aligned(df):
            setups.append(SetupType.EMA_CROSSOVER)
        if detect_breakout(df):
            setups.append(SetupType.BREAKOUT)
        if is_near_52w_high(df, 0.05):
            setups.append(SetupType.FLAT_BASE)
        if is_volume_surging(df):
            setups.append(SetupType.GAP_UP)

        results.append(
            ScanResult(
                symbol=symbol,
                price=last_close,
                change_pct=round(change_pct, 2),
                volume=last_volume,
                avg_volume=avg_vol,
                relative_strength=round(rs_val, 3),
                score=round(score, 1),
                signals=[],  # Populated later by signal generator
                setup_types=setups,
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_n]


def get_default_universe() -> list[str]:
    """Get a default scan universe of liquid US equities.

    Returns a curated list of well-known liquid stocks for scanning.
    In production, this would dynamically fetch from Alpaca's asset list.
    """
    return [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD",
        "NFLX", "CRM", "ADBE", "ORCL", "AVGO", "QCOM", "INTC", "MU",
        "SHOP", "SQ", "PYPL", "COIN", "MARA", "RIOT", "SOFI", "PLTR",
        "SNOW", "DDOG", "NET", "CRWD", "ZS", "PANW", "ABNB", "UBER",
        "DASH", "RBLX", "U", "TTD", "ENPH", "SEDG", "FSLR", "CEG",
        "LLY", "UNH", "JNJ", "PFE", "ABBV", "MRK", "BMY", "AMGN",
        "XOM", "CVX", "COP", "SLB", "OXY", "DVN", "MPC", "PSX",
        "JPM", "BAC", "GS", "MS", "WFC", "C", "SCHW", "BLK",
        "CAT", "DE", "HON", "GE", "RTX", "LMT", "BA", "NOC",
        "SPY", "QQQ", "IWM", "DIA",
    ]
