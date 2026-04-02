from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List


def send_ready_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    email_from: str,
    email_to: List[str],
    email_cc: List[str],
    review_url: str,
    brief_date: str,
    reply_to: str,
) -> None:
    subject = f"Your Daily Brief is Ready - {brief_date}"
    plain = (
        "Your Daily Brief is ready.\n\n"
        + f"Review: {review_url}\n"
    )
    html = f"""
<html>
<body style=\"font-family: Segoe UI, sans-serif; color: #111827;\">
  <p>Your Daily Brief is ready.</p>
  <p>
    <a href=\"{review_url}\" style=\"background:#0f766e;color:#ffffff;padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:600;\">Review</a>
  </p>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = ", ".join(email_to)
    if email_cc:
        msg["Cc"] = ", ".join(email_cc)
    msg["Reply-To"] = reply_to
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        recipients = email_to + email_cc
        server.sendmail(email_from, recipients, msg.as_string())
