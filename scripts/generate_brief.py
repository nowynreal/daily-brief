from __future__ import annotations

import traceback
from datetime import date

from daily_brief.analysis.rules import build_warning_flags, signal_environment, signal_score
from daily_brief.analysis.summarizer import maybe_build_llm_brief
from daily_brief.collectors.fred_collector import fetch_snapshots
from daily_brief.config.settings import DEFAULT_INDICATORS, load_settings, validate_settings
from daily_brief.services.emailer import send_ready_email
from daily_brief.services.storage import append_history, render_index, save_brief


def main() -> int:
    settings = load_settings()

    try:
        validate_settings(settings)
        snapshots = fetch_snapshots(DEFAULT_INDICATORS, settings.fred_api_key)
        flags = build_warning_flags(snapshots)

        brief_markdown = maybe_build_llm_brief(
            settings.use_llm,
            settings.openai_api_key,
            settings.openai_model,
            settings.region_name,
            snapshots,
            flags,
        )

        paths = save_brief(
            settings.output_dir,
            settings.site_dir,
            settings.region_name,
            brief_markdown,
            snapshots,
            flags,
        )

        append_history(
            settings.history_file,
            paths,
            signal_environment(flags),
            signal_score(flags),
        )
        index_path = render_index(settings.site_dir, settings.history_file)

        review_url = settings.base_review_url.strip() or f"briefs/{date.today().isoformat()}.html"
        if settings.send_email:
            send_ready_email(
                smtp_host=settings.smtp_host,
                smtp_port=settings.smtp_port,
                smtp_user=settings.smtp_user,
                smtp_password=settings.smtp_password,
                email_from=settings.email_from,
                email_to=settings.email_to,
                email_cc=settings.email_cc,
                reply_to=settings.reply_to,
                review_url=review_url,
                brief_date=date.today().isoformat(),
            )

        print("Daily brief generated.")
        print(f"- Markdown: {paths['markdown']}")
        print(f"- JSON: {paths['json']}")
        print(f"- HTML: {paths['html']}")
        print(f"- Index: {index_path}")
        if settings.send_email:
            print("- Notification email sent.")
        else:
            print("- Email disabled (SEND_EMAIL=false).")

        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
