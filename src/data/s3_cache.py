"""S3-backed cache for AWS Lambda. Two-tier: /tmp (fast) + S3 (durable)."""

import hashlib
import logging
import os
import pickle
import time
from pathlib import Path

logger = logging.getLogger("mse.cache")


class S3Cache:
    """Cache that stores in Lambda /tmp first, then persists to S3."""

    def __init__(self, bucket: str, region: str = "us-east-1") -> None:
        self._bucket = bucket
        self._region = region
        self._local_dir = Path("/tmp/mse-cache")
        self._local_dir.mkdir(parents=True, exist_ok=True)
        self._ttl = int(os.environ.get("CACHE_TTL_SECONDS", 900))  # 15 min
        self._s3 = None

    def _get_s3(self):
        if self._s3 is None:
            import boto3
            self._s3 = boto3.client("s3", region_name=self._region)
        return self._s3

    def _key(self, key: str) -> str:
        hashed = hashlib.md5(key.encode()).hexdigest()
        return f"cache/{hashed}.pkl"

    def _local_path(self, key: str) -> Path:
        hashed = hashlib.md5(key.encode()).hexdigest()
        return self._local_dir / f"{hashed}.pkl"

    def get(self, key: str):
        # Tier 1: check /tmp
        local = self._local_path(key)
        if local.exists():
            try:
                with open(local, "rb") as f:
                    ts, data = pickle.load(f)
                if time.time() - ts <= self._ttl:
                    return data
                local.unlink(missing_ok=True)
            except Exception:
                local.unlink(missing_ok=True)

        # Tier 2: check S3
        try:
            s3_key = self._key(key)
            resp = self._get_s3().get_object(Bucket=self._bucket, Key=s3_key)
            ts, data = pickle.loads(resp["Body"].read())
            if time.time() - ts <= self._ttl:
                # Warm /tmp for next call
                with open(local, "wb") as f:
                    pickle.dump((ts, data), f)
                return data
        except self._get_s3().exceptions.NoSuchKey:
            pass
        except Exception as e:
            logger.debug("S3 cache miss for %s: %s", key, e)

        return None

    def set(self, key: str, data) -> None:
        payload = (time.time(), data)

        # Write to /tmp
        local = self._local_path(key)
        with open(local, "wb") as f:
            pickle.dump(payload, f)

        # Write to S3
        try:
            s3_key = self._key(key)
            self._get_s3().put_object(
                Bucket=self._bucket,
                Key=s3_key,
                Body=pickle.dumps(payload),
            )
        except Exception as e:
            logger.warning("S3 cache write failed for %s: %s", key, e)

    def clear(self) -> None:
        # Clear /tmp
        for path in self._local_dir.glob("*.pkl"):
            path.unlink(missing_ok=True)
