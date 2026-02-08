"""Price projection: Fibonacci levels, pattern targets, trendline extensions."""

import numpy as np
import pandas as pd

from src.signals.support_resistance import find_pivot_highs, find_pivot_lows


def fibonacci_levels(df: pd.DataFrame) -> list[dict]:
    """Calculate Fibonacci retracement and extension levels from the most
    significant recent swing.

    Returns list of {price, confidence, reason, projection_type}.
    """
    if len(df) < 30:
        return []

    # Find the most significant recent swing
    pivots_high = find_pivot_highs(df, window=5)
    pivots_low = find_pivot_lows(df, window=5)

    if not pivots_high or not pivots_low:
        return []

    # Use the highest high and lowest low from recent pivots
    recent_high = max(pivots_high, key=lambda p: p["price"])
    recent_low = min(pivots_low, key=lambda p: p["price"])

    swing_range = recent_high["price"] - recent_low["price"]
    if swing_range <= 0:
        return []

    last_close = float(df["close"].iloc[-1])
    projections = []

    # Determine if we're in an upswing or downswing
    if recent_high["index"] > recent_low["index"]:
        # Upswing: retracements are support levels, extensions are bullish targets
        fib_ratios = [
            (0.236, "Fib 23.6% retracement"),
            (0.382, "Fib 38.2% retracement"),
            (0.500, "Fib 50.0% retracement"),
            (0.618, "Fib 61.8% retracement"),
        ]
        for ratio, label in fib_ratios:
            price = recent_high["price"] - swing_range * ratio
            if price < last_close:  # Only show levels below current price (support)
                projections.append({
                    "price": round(price, 2),
                    "confidence": 0.5 + (0.15 if ratio in (0.382, 0.618) else 0),
                    "reason": label,
                    "projection_type": "bearish",
                })

        # Fibonacci extensions (bullish targets)
        extensions = [
            (1.272, "Fib 127.2% extension"),
            (1.618, "Fib 161.8% extension"),
        ]
        for ratio, label in extensions:
            price = recent_low["price"] + swing_range * ratio
            if price > last_close:
                projections.append({
                    "price": round(price, 2),
                    "confidence": 0.45,
                    "reason": label,
                    "projection_type": "bullish",
                })
    else:
        # Downswing: retracements are resistance levels, extensions are bearish targets
        fib_ratios = [
            (0.236, "Fib 23.6% retracement"),
            (0.382, "Fib 38.2% retracement"),
            (0.500, "Fib 50.0% retracement"),
            (0.618, "Fib 61.8% retracement"),
        ]
        for ratio, label in fib_ratios:
            price = recent_low["price"] + swing_range * ratio
            if price > last_close:
                projections.append({
                    "price": round(price, 2),
                    "confidence": 0.5 + (0.15 if ratio in (0.382, 0.618) else 0),
                    "reason": label,
                    "projection_type": "bullish",
                })

        extensions = [
            (1.272, "Fib 127.2% extension"),
            (1.618, "Fib 161.8% extension"),
        ]
        for ratio, label in extensions:
            price = recent_high["price"] - swing_range * ratio
            if price < last_close and price > 0:
                projections.append({
                    "price": round(price, 2),
                    "confidence": 0.45,
                    "reason": label,
                    "projection_type": "bearish",
                })

    return projections


def project_price_zones(
    df: pd.DataFrame,
    patterns: list[dict],
    trendline_analysis: dict,
) -> list[dict]:
    """Combine all projection sources into a unified list of price targets.

    Returns list of {price, confidence, reason, projection_type}.
    """
    projections: list[dict] = []

    # 1. Pattern-based targets
    for pattern in patterns:
        if pattern.get("target_price"):
            last_close = float(df["close"].iloc[-1])
            is_bullish = pattern["target_price"] > last_close
            projections.append({
                "price": pattern["target_price"],
                "confidence": pattern["confidence"],
                "reason": f"{pattern['pattern_type'].replace('_', ' ').title()} target",
                "projection_type": "bullish" if is_bullish else "bearish",
            })

    # 2. Trendline projection endpoints
    for line in trendline_analysis.get("uptrends", []):
        if line.get("projection"):
            last_proj = line["projection"][-1]
            projections.append({
                "price": last_proj["price"],
                "confidence": min(0.3 + line["touches"] * 0.1, 0.7),
                "reason": f"Uptrend projection ({line['touches']} touches)",
                "projection_type": "bullish",
            })

    for line in trendline_analysis.get("downtrends", []):
        if line.get("projection"):
            last_proj = line["projection"][-1]
            if last_proj["price"] > 0:
                projections.append({
                    "price": last_proj["price"],
                    "confidence": min(0.3 + line["touches"] * 0.1, 0.7),
                    "reason": f"Downtrend projection ({line['touches']} touches)",
                    "projection_type": "bearish",
                })

    # 3. Fibonacci levels
    fib_projs = fibonacci_levels(df)
    projections.extend(fib_projs)

    # Deduplicate close targets (within 1%)
    projections = _deduplicate_projections(projections)

    # Sort by confidence
    projections.sort(key=lambda p: p["confidence"], reverse=True)

    # Limit to top 6
    return projections[:6]


def _deduplicate_projections(
    projections: list[dict], tolerance: float = 0.01
) -> list[dict]:
    """Remove projections at very similar price levels, keeping higher confidence."""
    if not projections:
        return []

    projections.sort(key=lambda p: p["confidence"], reverse=True)
    kept = []
    for proj in projections:
        is_dup = False
        for existing in kept:
            if existing["price"] > 0:
                diff = abs(proj["price"] - existing["price"]) / existing["price"]
                if diff < tolerance:
                    is_dup = True
                    break
        if not is_dup:
            kept.append(proj)
    return kept
