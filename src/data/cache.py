import hashlib
import os
import pickle
import time
from pathlib import Path

from config.settings import settings


def get_cache():
    """Return the appropriate cache backend: S3Cache on Lambda, local Cache otherwise."""
    if os.environ.get("AWS_LAMBDA") and settings.cache_bucket:
        from src.data.s3_cache import S3Cache
        return S3Cache(bucket=settings.cache_bucket, region=settings.aws_region)
    return Cache()


class Cache:
    def __init__(self) -> None:
        self._dir = Path(settings.cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._ttl = settings.cache_ttl_minutes * 60

    def _path(self, key: str) -> Path:
        hashed = hashlib.md5(key.encode()).hexdigest()
        return self._dir / f"{hashed}.pkl"

    def get(self, key: str):
        path = self._path(key)
        if not path.exists():
            return None
        try:
            with open(path, "rb") as f:
                ts, data = pickle.load(f)
            if time.time() - ts > self._ttl:
                path.unlink(missing_ok=True)
                return None
            return data
        except Exception:
            path.unlink(missing_ok=True)
            return None

    def set(self, key: str, data) -> None:
        path = self._path(key)
        with open(path, "wb") as f:
            pickle.dump((time.time(), data), f)

    def clear(self) -> None:
        for path in self._dir.glob("*.pkl"):
            path.unlink(missing_ok=True)
