from __future__ import annotations

import json
import logging
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Any

from aibenchmark.app.automation.manager import AutomationManager
from aibenchmark.app.automation.models import NotificationRecord, RegressionRecord, SyncRecord

logger = logging.getLogger(__name__)


class NotificationProvider:
    def send(self, subject: str, body: str, payload: dict[str, Any]) -> bool:
        raise NotImplementedError


class ConsoleNotificationProvider(NotificationProvider):
    def send(self, subject: str, body: str, payload: dict[str, Any]) -> bool:
        logger.info("[NOTIFICATION] %s: %s", subject, body)
        return True


class WebhookNotificationProvider(NotificationProvider):
    def __init__(self, url: str) -> None:
        self.url = url

    def send(self, subject: str, body: str, payload: dict[str, Any]) -> bool:
        try:
            import urllib.request
            data = json.dumps({"subject": subject, "body": body, "payload": payload}).encode()
            req = urllib.request.Request(self.url, data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception as exc:
            logger.error("Webhook notification failed: %s", exc)
            return False


class SlackNotificationProvider(NotificationProvider):
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def send(self, subject: str, body: str, payload: dict[str, Any]) -> bool:
        try:
            import urllib.request
            data = json.dumps({"text": f"{subject}: {body}"}).encode()
            req = urllib.request.Request(self.webhook_url, data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception as exc:
            logger.error("Slack notification failed: %s", exc)
            return False


class DiscordNotificationProvider(NotificationProvider):
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url

    def send(self, subject: str, body: str, payload: dict[str, Any]) -> bool:
        try:
            import urllib.request
            data = json.dumps({"content": f"**{subject}**\n{body}"}).encode()
            req = urllib.request.Request(self.webhook_url, data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception as exc:
            logger.error("Discord notification failed: %s", exc)
            return False


class EmailNotificationProvider(NotificationProvider):
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str, to_addr: str) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.to_addr = to_addr

    def send(self, subject: str, body: str, payload: dict[str, Any]) -> bool:
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = self.username
            msg["To"] = self.to_addr
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                server.login(self.username, self.password)
                server.sendmail(self.username, [self.to_addr], msg.as_string())
            return True
        except Exception as exc:
            logger.error("Email notification failed: %s", exc)
            return False


class NotificationService:
    def __init__(self, manager: AutomationManager | None = None) -> None:
        self.manager = manager or AutomationManager()
        self.providers: dict[str, NotificationProvider] = {}

    def register(self, name: str, provider: NotificationProvider) -> None:
        self.providers[name] = provider

    def send(self, channel: str, subject: str, body: str, execution_id: int | None = None, payload: dict[str, Any] | None = None) -> None:
        provider = self.providers.get(channel)
        if provider is None:
            logger.warning("Notification channel '%s' not configured", channel)
            return
        ok = provider.send(subject, body, payload or {})
        self.manager.record_notification(
            NotificationRecord(
                execution_id=execution_id,
                channel=channel,
                status="sent" if ok else "failed",
                payload=json.dumps(payload) if payload else None,
            )
        )

