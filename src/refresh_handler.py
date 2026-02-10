"""AWS Lambda handler for scheduled market refresh (EventBridge → Lambda).

Runs one scan cycle: fetch bars, generate signals, dispatch alerts, cache results.
Persists _seen_signal_keys to S3 so new-signal detection works across invocations.
"""

import json
import logging
import os
import pickle

os.environ.setdefault("AWS_LAMBDA", "1")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("mse.refresh")


def _load_seen_keys(bucket: str, region: str) -> set:
    """Load previously seen signal keys from S3."""
    try:
        import boto3
        s3 = boto3.client("s3", region_name=region)
        resp = s3.get_object(Bucket=bucket, Key="state/seen_signal_keys.pkl")
        return pickle.loads(resp["Body"].read())
    except Exception:
        return set()


def _save_seen_keys(keys: set, bucket: str, region: str) -> None:
    """Persist seen signal keys to S3."""
    try:
        import boto3
        s3 = boto3.client("s3", region_name=region)
        s3.put_object(
            Bucket=bucket,
            Key="state/seen_signal_keys.pkl",
            Body=pickle.dumps(keys),
        )
    except Exception as e:
        logger.warning("Failed to save seen keys: %s", e)


def handler(event, context):
    """Single refresh cycle — triggered by EventBridge every 2 minutes."""
    from concurrent.futures import ThreadPoolExecutor

    from config.settings import settings
    from src.data import client
    from src.data.cache import get_cache
    from src.data.models import ScanResult
    from src.notifications.dispatcher import dispatch_alerts
    from src.scanner.screener import get_default_universe, scan_universe
    from src.signals.generator import generate_signals
    from src.signals.patterns import detect_patterns

    cache = get_cache()
    bucket = settings.cache_bucket
    region = settings.aws_region

    symbols = get_default_universe()

    try:
        # Fetch market data
        client.get_bars("SPY", days=200)
        bars_map = client.get_multi_bars(symbols, days=200)

        # Run scan
        results, bars_map = scan_universe(
            symbols, top_n=20, min_price=5.0, max_price=500.0,
            min_volume=500_000, return_bars=True,
        )

        # Enrich results with signals
        def _enrich(result: ScanResult) -> None:
            try:
                df = bars_map.get(result.symbol)
                if df is None or len(df) < 50:
                    return
                result.signals = generate_signals(df, result.symbol)
                result.setup_types.extend(detect_patterns(df))
                result.setup_types = list(set(result.setup_types))
            except Exception:
                pass

        with ThreadPoolExecutor(max_workers=8) as executor:
            executor.map(_enrich, results)

        # Cache scan results
        cache.set("scan_20_5.0_500.0_500000", results)

        # Collect all signals
        all_signals = []
        for r in results:
            all_signals.extend(r.signals)
        logger.info("Signal check: %d total signals from %d results", len(all_signals), len(results))

        # Load previously seen keys from S3
        seen_keys = _load_seen_keys(bucket, region)
        current_keys = {f"{s.symbol}:{s.action.value}:{s.entry:.2f}" for s in all_signals}

        if not seen_keys:
            # First invocation — treat all as new
            new_signals = all_signals
            logger.info("First invocation: treating all %d signals as new", len(new_signals))
        else:
            new_signals = [s for s in all_signals
                           if f"{s.symbol}:{s.action.value}:{s.entry:.2f}" not in seen_keys]

        # Dispatch alerts for new signals
        if new_signals:
            logger.info("Dispatching %d new signals...", len(new_signals))
            try:
                dispatch_results = dispatch_alerts(new_signals)
                logger.info("Dispatch result: webhook=%s, sms=%s",
                            dispatch_results["webhook"], dispatch_results["sms"])
            except Exception as e:
                logger.warning("Dispatch failed: %s", e)
        else:
            logger.info("No new signals to dispatch")

        # Persist seen keys for next invocation
        _save_seen_keys(current_keys, bucket, region)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "results": len(results),
                "signals": len(all_signals),
                "new_signals": len(new_signals),
            }),
        }

    except Exception as e:
        logger.error("Refresh failed: %s", e)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
