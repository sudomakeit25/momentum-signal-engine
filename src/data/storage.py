"""Notification config storage: DynamoDB (AWS Lambda) or local JSON file."""

import json
import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger("mse.storage")

_IS_LAMBDA = bool(os.environ.get("AWS_LAMBDA"))

# Local file storage (same as before)
_CONFIG_PATH = Path(".notification_config.json")
_config_lock = threading.Lock()


def load_config_dict() -> dict:
    """Load notification config as a dict. Uses DynamoDB on Lambda, file locally."""
    if _IS_LAMBDA:
        return _load_dynamo()
    return _load_file()


def save_config_dict(data: dict) -> None:
    """Save notification config dict. Uses DynamoDB on Lambda, file locally."""
    if _IS_LAMBDA:
        _save_dynamo(data)
    else:
        _save_file(data)


# --- Local file backend ---

def _load_file() -> dict:
    with _config_lock:
        if _CONFIG_PATH.exists():
            try:
                return json.loads(_CONFIG_PATH.read_text())
            except Exception:
                pass
    return {}


def _save_file(data: dict) -> None:
    with _config_lock:
        _CONFIG_PATH.write_text(json.dumps(data, indent=2))


# --- DynamoDB backend ---

def _get_table():
    import boto3
    from config.settings import settings
    dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
    return dynamodb.Table(settings.config_table)


def _load_dynamo() -> dict:
    try:
        table = _get_table()
        resp = table.get_item(Key={"pk": "notification_config"})
        item = resp.get("Item", {})
        item.pop("pk", None)
        return item
    except Exception as e:
        logger.warning("DynamoDB load failed, falling back to empty: %s", e)
        return {}


def _save_dynamo(data: dict) -> None:
    try:
        table = _get_table()
        item = {**data, "pk": "notification_config"}
        table.put_item(Item=item)
    except Exception as e:
        logger.warning("DynamoDB save failed: %s", e)
