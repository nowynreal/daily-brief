from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from daily_brief.models import IndicatorConfig


@dataclass
class Settings:
    region_name: str
    fred_api_key: str
    output_dir: Path
    site_dir: Path
    history_file: Path
    base_review_url: str
    send_email: bool
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    email_from_name: str
    email_from: str
    email_to: List[str]
    reply_to: str
    email_cc: List[str]
    use_llm: bool
    openai_api_key: str
    openai_model: str


DEFAULT_INDICATORS = [
    IndicatorConfig("US Unemployment Rate", "UNRATE", "percent", "monthly"),
    IndicatorConfig("US Initial Jobless Claims", "ICSA", "count", "weekly"),
    IndicatorConfig("Tennessee Unemployment Rate", "TNUR", "percent", "monthly"),
    IndicatorConfig("Tennessee Nonfarm Employment", "TNNA", "thousands", "monthly"),
    IndicatorConfig("US CPI", "CPIAUCSL", "index", "monthly"),
    IndicatorConfig("30Y Mortgage Rate", "MORTGAGE30US", "percent", "weekly"),
]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str) -> List[str]:
    raw = os.getenv(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_settings() -> Settings:
    output_dir = Path(os.getenv("OUTPUT_DIR", "output"))
    site_dir = Path(os.getenv("SITE_DIR", "docs"))
    history_file = output_dir / "history.jsonl"
    recipients = _env_list("EMAIL_TO")
    cc_recipients = _env_list("EMAIL_CC")

    smtp_user = os.getenv("SMTP_USER", "")
    return Settings(
        region_name=os.getenv("REGION_NAME", "Tennessee"),
        fred_api_key=os.getenv("FRED_API_KEY", ""),
        output_dir=output_dir,
        site_dir=site_dir,
        history_file=history_file,
        base_review_url=os.getenv("BASE_REVIEW_URL", ""),
        send_email=_env_bool("SEND_EMAIL", False),
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=smtp_user,
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        email_from_name=os.getenv("EMAIL_FROM_NAME", "Semih Yucekan"),
        email_from=os.getenv("EMAIL_FROM", smtp_user),
        email_to=recipients,
        reply_to=os.getenv("REPLY_TO", os.getenv("EMAIL_FROM", smtp_user)),
        email_cc=cc_recipients,
        use_llm=_env_bool("USE_LLM", False),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5.3-mini"),
    )


def validate_settings(settings: Settings) -> None:
    if not settings.fred_api_key:
        raise RuntimeError("FRED_API_KEY is required.")

    if settings.send_email:
        missing = []
        if not settings.smtp_host:
            missing.append("SMTP_HOST")
        if not settings.smtp_user:
            missing.append("SMTP_USER")
        if not settings.smtp_password:
            missing.append("SMTP_PASSWORD")
        if not settings.email_to:
            missing.append("EMAIL_TO")
        if missing:
            raise RuntimeError("Missing email settings: " + ", ".join(missing))

    if settings.use_llm and not settings.openai_api_key:
        raise RuntimeError("USE_LLM=true requires OPENAI_API_KEY.")

