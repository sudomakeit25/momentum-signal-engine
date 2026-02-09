"""Notification dispatcher: webhook (Discord/Telegram/Slack) + SMS (Twilio)."""

import logging
import json
import threading
from dataclasses import dataclass
from pathlib import Path

import requests as http_requests

logger = logging.getLogger("mse.notifications")

# Persistent config file path (survives restarts on disk-based deploys)
_CONFIG_PATH = Path(".notification_config.json")
_config_lock = threading.Lock()


@dataclass
class NotificationConfig:
    """Notification preferences — saved to disk."""
    webhook_url: str = ""
    webhook_platform: str = "discord"  # discord | telegram | slack
    sms_to: str = ""  # recipient phone e.g. "+15559876543"
    auto_alerts_enabled: bool = False
    min_confidence: float = 0.6  # only alert on signals >= this confidence

    def to_dict(self) -> dict:
        return {
            "webhook_url": self.webhook_url,
            "webhook_platform": self.webhook_platform,
            "sms_to": self.sms_to,
            "auto_alerts_enabled": self.auto_alerts_enabled,
            "min_confidence": self.min_confidence,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NotificationConfig":
        return cls(
            webhook_url=d.get("webhook_url", ""),
            webhook_platform=d.get("webhook_platform", "discord"),
            sms_to=d.get("sms_to", ""),
            auto_alerts_enabled=d.get("auto_alerts_enabled", False),
            min_confidence=d.get("min_confidence", 0.6),
        )


def load_config() -> NotificationConfig:
    """Load config from disk, or return defaults."""
    with _config_lock:
        if _CONFIG_PATH.exists():
            try:
                data = json.loads(_CONFIG_PATH.read_text())
                return NotificationConfig.from_dict(data)
            except Exception:
                pass
        return NotificationConfig()


def save_config(config: NotificationConfig) -> None:
    """Persist config to disk."""
    with _config_lock:
        _CONFIG_PATH.write_text(json.dumps(config.to_dict(), indent=2))


def send_webhook(url: str, platform: str, signals: list) -> bool:
    """Send signals to a webhook (Discord, Telegram, or Slack). Returns True on success."""
    if not url or not signals:
        return False

    try:
        if platform == "discord":
            fields = []
            for s in signals:
                emoji = "\U0001f7e2" if s.action.value == "BUY" else "\U0001f534"
                fields.append({
                    "name": f"{emoji} {s.symbol} — {s.action.value}",
                    "value": f"Entry: ${s.entry:.2f} | Conf: {s.confidence*100:.0f}% | R:R {s.rr_ratio:.1f}\n{s.reason[:100]}",
                    "inline": False,
                })
            payload = {"embeds": [{"title": "\U0001f514 MSE Signal Alert", "color": 3447003, "fields": fields}]}
            resp = http_requests.post(url, json=payload, timeout=10)
        elif platform == "telegram":
            lines = ["*\U0001f514 MSE Signal Alert*\n"]
            for s in signals:
                emoji = "\U0001f7e2" if s.action.value == "BUY" else "\U0001f534"
                lines.append(f"{emoji} *{s.symbol}* {s.action.value} @ ${s.entry:.2f} ({s.confidence*100:.0f}%)")
                lines.append(f"   R:R {s.rr_ratio:.1f} | {s.reason[:80]}")
            payload = {"text": "\n".join(lines), "parse_mode": "Markdown"}
            resp = http_requests.post(url, json=payload, timeout=10)
        else:
            # Slack or generic
            lines = ["\U0001f514 *MSE Signal Alert*\n"]
            for s in signals:
                emoji = ":green_circle:" if s.action.value == "BUY" else ":red_circle:"
                lines.append(f"{emoji} *{s.symbol}* {s.action.value} @ ${s.entry:.2f} ({s.confidence*100:.0f}%)")
            payload = {"text": "\n".join(lines)}
            resp = http_requests.post(url, json=payload, timeout=10)

        ok = 200 <= resp.status_code < 300
        if ok:
            logger.info("Webhook sent to %s: %d signals", platform, len(signals))
        else:
            logger.warning("Webhook failed (%s): HTTP %d", platform, resp.status_code)
        return ok
    except Exception as e:
        logger.warning("Webhook error (%s): %s", platform, e)
        return False


def send_sms(to_phone: str, signals: list) -> bool:
    """Send SMS alert via Twilio. Returns True on success."""
    if not to_phone or not signals:
        return False

    from config.settings import settings
    if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_from_number:
        logger.warning("SMS skipped: Twilio credentials not configured")
        return False

    try:
        from twilio.rest import Client
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

        lines = ["MSE Signal Alert\n"]
        for s in signals:
            arrow = "+" if s.action.value == "BUY" else "-"
            lines.append(f"{arrow} {s.symbol} {s.action.value} ${s.entry:.2f} ({s.confidence*100:.0f}%) R:R {s.rr_ratio:.1f}")

        body = "\n".join(lines)
        # Twilio SMS max is 1600 chars for long SMS, truncate if needed
        if len(body) > 1500:
            body = body[:1497] + "..."

        message = client.messages.create(
            body=body,
            from_=settings.twilio_from_number,
            to=to_phone,
        )

        logger.info("SMS sent to %s: SID %s", to_phone, message.sid)
        return True
    except Exception as e:
        logger.warning("SMS error: %s", e)
        return False


def dispatch_alerts(signals: list) -> dict:
    """Send alerts through all enabled channels. Returns status per channel."""
    config = load_config()
    results = {"webhook": False, "sms": False}

    if not config.auto_alerts_enabled:
        return results

    # Filter by minimum confidence
    filtered = [s for s in signals if s.confidence >= config.min_confidence]
    if not filtered:
        return results

    if config.webhook_url:
        results["webhook"] = send_webhook(config.webhook_url, config.webhook_platform, filtered)

    if config.sms_to:
        results["sms"] = send_sms(config.sms_to, filtered)

    return results
