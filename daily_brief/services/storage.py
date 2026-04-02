from __future__ import annotations

import html
import json
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List

from daily_brief.analysis.rules import signal_environment, signal_score
from daily_brief.models import IndicatorSnapshot, WarningFlag


def markdown_to_basic_html(markdown_text: str, title: str) -> str:
    escaped = html.escape(markdown_text)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: Georgia, serif; background: #f7f5f0; color: #1f2937; margin: 0; }}
    .wrap {{ max-width: 900px; margin: 0 auto; padding: 2rem 1rem; }}
    .card {{ background: #fff; border: 1px solid #d6d3d1; border-radius: 12px; padding: 1.2rem; box-shadow: 0 4px 14px rgba(0,0,0,0.05); }}
    pre {{ white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    a {{ color: #0f766e; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
      <pre>{escaped}</pre>
    </div>
  </div>
</body>
</html>"""


def save_brief(
    output_dir: Path,
    site_dir: Path,
    region_name: str,
    brief_markdown: str,
    snapshots: List[IndicatorSnapshot],
    flags: List[WarningFlag],
) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    (site_dir / "briefs").mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    json_path = output_dir / f"brief_{today}.json"
    md_path = output_dir / f"brief_{today}.md"
    html_path = site_dir / "briefs" / f"{today}.html"

    payload = {
        "id": timestamp,
        "date": today,
        "region": region_name,
        "signal_environment": signal_environment(flags),
        "signal_score": signal_score(flags),
        "brief_markdown": brief_markdown,
        "snapshots": [asdict(item) for item in snapshots],
        "flags": [asdict(item) for item in flags],
    }

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(brief_markdown, encoding="utf-8")
    html_path.write_text(markdown_to_basic_html(brief_markdown, f"Daily Brief {today}"), encoding="utf-8")

    return {
        "json": json_path,
        "markdown": md_path,
        "html": html_path,
    }


def append_history(history_file: Path, output_paths: Dict[str, Path], signal_env: str, score: int) -> None:
    history_file.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "date": date.today().isoformat(),
        "signal_environment": signal_env,
        "signal_score": score,
        "html": str(output_paths["html"]).replace("\\", "/"),
        "json": str(output_paths["json"]).replace("\\", "/"),
    }
    with history_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def render_index(site_dir: Path, history_file: Path) -> Path:
    briefs_dir = site_dir / "briefs"
    briefs_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    if history_file.exists():
        lines = [line.strip() for line in history_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        for line in reversed(lines[-60:]):
            item = json.loads(line)
            href = f"briefs/{item['date']}.html"
            rows.append(
                f"<tr><td>{item['date']}</td><td>{item['signal_environment']}</td><td>{item['signal_score']}</td><td><a href='{href}'>Review</a></td></tr>"
            )

    table_body = "\n".join(rows) if rows else "<tr><td colspan='4'>No brief generated yet.</td></tr>"
    html_doc = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Daily Brief Archive</title>
  <style>
    body {{ margin: 0; font-family: 'Segoe UI', Tahoma, sans-serif; background: linear-gradient(135deg, #e7eef6, #f8f5ec); color: #172554; }}
    main {{ max-width: 960px; margin: 0 auto; padding: 2rem 1rem; }}
    h1 {{ margin-bottom: 0.4rem; }}
    .panel {{ background: rgba(255,255,255,0.95); border: 1px solid #bfdbfe; border-radius: 14px; padding: 1rem; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 0.7rem; border-bottom: 1px solid #dbeafe; }}
    a {{ color: #0f766e; font-weight: 600; }}
  </style>
</head>
<body>
  <main>
    <h1>Daily Brief Archive</h1>
    <p>Generated automatically at 08:00 every day.</p>
    <div class=\"panel\">
      <table>
        <thead><tr><th>Date</th><th>Signal</th><th>Score</th><th>Action</th></tr></thead>
        <tbody>{table_body}</tbody>
      </table>
    </div>
  </main>
</body>
</html>"""

    index_path = site_dir / "index.html"
    index_path.write_text(html_doc, encoding="utf-8")
    return index_path
