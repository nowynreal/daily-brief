from __future__ import annotations

import base64
import smtplib
from datetime import datetime
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr
from typing import List


def _format_brief_date(brief_date: str) -> str:
    try:
        value = datetime.strptime(brief_date, "%Y-%m-%d")
        return f"{value.strftime('%B')} {value.day}, {value.year}"
    except ValueError:
        return brief_date


def _load_logo_data_uri() -> str:
  logo_path = Path(__file__).resolve().parents[2] / "assets" / "berc_logo.png"
  logo_bytes = logo_path.read_bytes()
  encoded = base64.b64encode(logo_bytes).decode("ascii")
  return f"data:image/png;base64,{encoded}"


def send_ready_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    email_from_name: str,
    email_from: str,
    email_to: List[str],
    email_cc: List[str],
    review_url: str,
    brief_date: str,
    reply_to: str,
) -> None:
    pretty_date = _format_brief_date(brief_date)
    subject = f"Your Daily Brief is Ready | {pretty_date}"
    plain = (
        "BERC Daily Briefer by Semih Yucekan.\n"
        + f"Date: {pretty_date}\n\n"
        + f"Review: {review_url}\n"
    )
    from_addr = parseaddr(email_from)[1] or email_from
    display_name = email_from_name or "Semih Yucekan"
    logo_data_uri = _load_logo_data_uri()
    html = f"""
<html>
  <body style="margin:0;padding:0;background:#edf2f7;font-family:Segoe UI, Inter, Helvetica, Arial, sans-serif;color:#0f172a;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;background:#edf2f7;margin:0;padding:24px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;background:#ffffff;border-radius:14px;overflow:hidden;border:1px solid #dbe3ee;box-shadow:0 10px 30px rgba(15,23,42,0.10);">
            <tr>
              <td style="background:#0b3a5e;padding:0;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;background:#0b3a5e;">
                  <tr>
                    <td style="padding:18px 22px;">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;">
                        <tr>
                          <td valign="middle" style="width:52px;padding-right:14px;">
                            <table role="presentation" width="44" height="44" cellpadding="0" cellspacing="0" border="0" style="width:44px;height:44px;">
                              <tr>
                                <td align="center" valign="middle" style="width:44px;height:44px;border-radius:22px;background:#ffffff;overflow:hidden;">
                                  <img src="{logo_data_uri}" alt="BERC" width="44" height="44" style="display:block;width:44px;height:44px;border-radius:22px;object-fit:cover;" />
                                </td>
                              </tr>
                            </table>
                          </td>
                          <td valign="middle" style="padding-left:0;">
                            <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#cfe3ee;font-weight:700;">Business and Economic Research Center</div>
                            <div style="font-size:18px;line-height:1.25;color:#ffffff;font-weight:700;margin-top:4px;">BERC Daily Briefer</div>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:24px 24px 10px 24px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;">
                  <tr>
                    <td style="padding-bottom:16px;">
                      <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#64748b;font-weight:700;">Daily edition</div>
                      <div style="font-size:24px;line-height:1.25;font-weight:800;color:#0f172a;margin-top:6px;">Your brief is ready to review</div>
                      <div style="font-size:15px;line-height:1.6;color:#475569;margin-top:10px;">A concise update is available for <strong style="color:#0f172a;">{pretty_date}</strong>. Click below to open the archive and review the latest brief.</div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding:8px 24px 24px 24px;">
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto;">
                  <tr>
                    <td align="center" bgcolor="#0f766e" style="border-radius:10px;box-shadow:0 8px 18px rgba(15,118,110,0.22);">
                      <a href="{review_url}" style="display:inline-block;padding:14px 28px;font-size:16px;line-height:1.2;font-weight:700;color:#ffffff;text-decoration:none;border-radius:10px;">Review</a>
                    </td>
                  </tr>
                </table>
                <div style="font-size:12px;line-height:1.6;color:#64748b;margin-top:12px;">If the button does not work, copy and paste this link into your browser:<br /><span style="word-break:break-all;color:#0b3a5e;">{review_url}</span></div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 24px 22px 24px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;border-top:1px solid #e2e8f0;">
                  <tr>
                    <td
                      style="
                        padding-top: 16px;
                        font-size: 12px;
                        line-height: 1.7;
                        color: #64748b;
                      "
                    >
                      <a
                        href="https://berc.mtsu.edu"
                        style="color: #64748b; text-decoration: underline"
                        >Business and Economic Research Center</a
                      ><br />
                      Contact: {reply_to} or berc@mtsu.edu
                    </td>
                    <td align="right" valign="top" style="padding-top:16px;font-size:12px;line-height:1.7;color:#64748b;">
                      Developed by Semih Yucekan<br />
                      <a href="https://semihyucekan.com" style="color:#64748b;text-decoration:underline;">semihyucekan.com</a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((display_name, from_addr))
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
        server.sendmail(from_addr, recipients, msg.as_string())