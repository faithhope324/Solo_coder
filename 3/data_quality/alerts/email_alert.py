import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Any, Dict, List, Optional
from datetime import datetime

from .base import BaseAlert
from ..core.config import CheckResult, CheckStatus, AlertLevel


class EmailAlert(BaseAlert):
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.smtp_host = self.config.get("smtp_host", "")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.smtp_user = self.config.get("smtp_user", "")
        self.smtp_password = self.config.get("smtp_password", "")
        self.sender = self.config.get("sender", "")
        self.receivers = self.config.get("receivers", [])
        self.use_tls = self.config.get("use_tls", True)
        self.include_details = self.config.get("include_details", True)

    def send(self, result: CheckResult, alert_level: AlertLevel = AlertLevel.MEDIUM) -> bool:
        if not self._should_alert(result):
            return True

        if not self._is_configured():
            return False

        try:
            subject = f"[Data Quality Alert] {result.check_name} - {result.status.value}"
            body = self._build_email_body([result], alert_level)
            return self._send_email(subject, body)
        except Exception:
            return False

    def send_batch(self, results: List[CheckResult], alert_level: AlertLevel = AlertLevel.MEDIUM) -> bool:
        alert_results = [r for r in results if self._should_alert(r)]

        if not alert_results:
            return True

        if not self._is_configured():
            return False

        try:
            subject = f"[Data Quality Alert] {len(alert_results)} issues found"
            body = self._build_email_body(alert_results, alert_level)
            return self._send_email(subject, body)
        except Exception:
            return False

    def _is_configured(self) -> bool:
        return all([
            self.smtp_host,
            self.smtp_user,
            self.receivers,
        ])

    def _build_email_body(self, results: List[CheckResult], alert_level: AlertLevel) -> str:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html_parts = [
            "<html><body style='font-family: Arial, sans-serif;'>",
            f"<h2 style='color: #dc3545;'>Data Quality Alert - {alert_level.value}</h2>",
            f"<p><strong>Time:</strong> {timestamp}</p>",
            f"<p><strong>Total Issues:</strong> {len(results)}</p>",
            "<hr style='border: 1px solid #dee2e6;'>",
        ]

        for i, result in enumerate(results, 1):
            status_color = self._get_status_html_color(result.status)
            html_parts.extend([
                f"<h3 style='color: {status_color};'>Alert {i}: {result.check_name}</h3>",
                f"<p><strong>Type:</strong> {result.check_type}</p>",
                f"<p><strong>Status:</strong> <span style='color: {status_color};'>{result.status.value}</span></p>",
                f"<p><strong>Message:</strong> {result.message}</p>",
                f"<p><strong>Actual Value:</strong> {result.actual_value}</p>",
                f"<p><strong>Expected Value:</strong> {result.expected_value}</p>",
            ])

            if self.include_details and result.details:
                html_parts.append("<p><strong>Details:</strong></p>")
                html_parts.append("<ul>")
                for key, value in result.details.items():
                    html_parts.append(f"<li><strong>{key}:</strong> {value}</li>")
                html_parts.append("</ul>")

            if result.errors:
                html_parts.append("<p><strong>Errors:</strong></p>")
                html_parts.append("<ul>")
                for error in result.errors:
                    html_parts.append(f"<li>{error}</li>")
                html_parts.append("</ul>")

            html_parts.append("<hr style='border: 1px solid #e9ecef;'>")

        html_parts.extend([
            "<p style='color: #6c757d; font-size: 12px;'>",
            "This is an automated data quality alert. Please do not reply directly to this email.",
            "</p>",
            "</body></html>",
        ])

        return "".join(html_parts)

    def _send_email(self, subject: str, html_body: str) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = formataddr(("Data Quality Platform", self.sender or self.smtp_user))
            msg["To"] = ", ".join(self.receivers)
            msg["Subject"] = subject

            part = MIMEText(html_body, "html")
            msg.attach(part)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                if self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            return True
        except Exception:
            return False

    def _get_status_html_color(self, status: CheckStatus) -> str:
        color_map = {
            CheckStatus.PASS: "#28a745",
            CheckStatus.WARNING: "#ffc107",
            CheckStatus.FAIL: "#dc3545",
            CheckStatus.ERROR: "#6f42c1",
        }
        return color_map.get(status, "#6c757d")
