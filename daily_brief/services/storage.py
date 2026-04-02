from __future__ import annotations

import html
import json
import re
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List

from daily_brief.analysis.rules import signal_environment, signal_score
from daily_brief.models import IndicatorSnapshot, WarningFlag


BRAND_TITLE = "BERC Daily Briefer"
BRAND_OWNER = "Semih Yucekan"
MTSU_WEBSITE = "https://www.mtsu.edu/"
COE_URP_BERC = "https://urp.mtsu.edu/"
BERC = "https://www.mtsu.edu/berc/"
DONATE_BERC = "https://www.mtsu.edu/give/"
BERC_INSTAGRAM = "https://www.instagram.com/mtsublueraiders/"
BERC_LINKEDIN = "https://www.linkedin.com/school/middle-tennessee-state-university/"


def _inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def _pretty_date(value: date) -> str:
  return f"{value.strftime('%B')} {value.day}, {value.year}"


def _pretty_iso_date(value: str) -> str:
  try:
    parsed = datetime.strptime(value, "%Y-%m-%d").date()
    return _pretty_date(parsed)
  except ValueError:
    return value


def _markdown_body_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    out: List[str] = []
    in_list = False

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            if in_list:
                out.append("</ul>")
                in_list = False
            continue

        if line.startswith("# "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h1>{_inline_markdown(line[2:])}</h1>")
            continue

        if line.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h2>{_inline_markdown(line[3:])}</h2>")
            continue

        if line.startswith("- "):
            if not in_list:
                out.append('<ul class="brief-list">')
                in_list = True
            out.append(f"<li>{_inline_markdown(line[2:])}</li>")
            continue

        if in_list:
            out.append("</ul>")
            in_list = False
        out.append(f"<p>{_inline_markdown(line)}</p>")

    if in_list:
        out.append("</ul>")

    return "\n".join(out)


def markdown_to_basic_html(markdown_text: str, title: str) -> str:
    body_html = _markdown_body_to_html(markdown_text)
    today = _pretty_date(date.today())
    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{html.escape(title)}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
    :root {{
      --bg: #f3f4f6;
      --surface: #ffffff;
      --surface-2: #f8fafc;
      --ink: #0f172a;
      --muted: #475569;
      --line: #e2e8f0;
      --accent: #0b3a5e;
      --accent-soft: #e2e8f0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: 'IBM Plex Sans', sans-serif;
      background:
        radial-gradient(1100px 560px at 100% -20%, #dde6f3 0%, transparent 62%),
        linear-gradient(180deg, #f8fafc, var(--bg));
      min-height: 100vh;
    }}
    .wrap {{ max-width: 980px; margin: 0 auto; padding: 1.2rem 1rem 2rem; }}
    .hero {{
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.92);
      border-radius: 14px;
      padding: 1rem 1.1rem;
      margin-bottom: 1rem;
      animation: rise .45s ease-out;
    }}
    .hero h1 {{
      margin: 0;
      font-family: 'Fraunces', serif;
      font-size: clamp(1.6rem, 2.5vw, 2.1rem);
      letter-spacing: 0.01em;
    }}
    .hero .accent {{
      font-family: 'IBM Plex Sans', sans-serif;
      font-style: normal;
      font-size: 0.65em;
      color: var(--muted);
      font-weight: 400;
      letter-spacing: 0;
    }}
    .hero p {{ margin: 0.45rem 0 0; color: var(--muted); }}
    .cta-row {{ margin-top: 0.8rem; display: flex; gap: 0.6rem; flex-wrap: wrap; }}
    .chip {{
      display: inline-block;
      border: 1px solid #cbd5e1;
      border-radius: 999px;
      padding: 0.35rem 0.75rem;
      font-size: 0.9rem;
      color: #1e293b;
      background: var(--accent-soft);
      text-decoration: none;
      font-weight: 500;
    }}
    .card {{
      border: 1px solid var(--line);
      background: var(--surface);
      border-radius: 14px;
      padding: 1.15rem;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
      animation: rise .55s ease-out;
    }}
    .card h1 {{ display: none; }}
    .card h2 {{
      margin: 1.15rem 0 0.6rem;
      font-size: 1.05rem;
      color: #0f172a;
      font-family: 'Fraunces', serif;
      letter-spacing: 0.01em;
    }}
    .card p {{ margin: 0.45rem 0; line-height: 1.6; }}
    .brief-list {{ margin: 0.35rem 0 0.8rem; padding-left: 1.1rem; }}
    .brief-list li {{ margin: 0.36rem 0; line-height: 1.55; }}
    .footer {{
      margin-top: 1rem;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: var(--surface-2);
      padding: 0.9rem;
    }}
    .footer-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.8rem;
      flex-wrap: wrap;
      margin-bottom: 0.55rem;
    }}
    .footer-brand {{ font-size: 0.95rem; color: #334155; }}
    .footer-list {{
      margin: 0;
      padding: 0;
      list-style: none;
      display: flex;
      gap: 0.9rem;
      flex-wrap: wrap;
    }}
    .footer-list li {{
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
    }}
    .footer-list a {{
      color: #0b3a5e;
      text-decoration: none;
      font-size: 0.86rem;
      font-weight: 500;
      border-bottom: 1px solid transparent;
      transition: color .18s ease, border-color .18s ease, transform .18s ease;
    }}
    .footer-list a:hover {{
      color: #082a46;
      border-bottom-color: #0b3a5e;
      transform: translateY(-1px);
    }}
    .footer-list a:focus-visible {{
      outline: 2px solid #93c5fd;
      outline-offset: 3px;
      border-radius: 2px;
    }}
    .link-icon {{
      color: #64748b;
      font-size: 0.74rem;
      line-height: 1;
    }}
    .footer-note {{ color: var(--muted); font-size: 0.82rem; line-height: 1.45; }}
    @keyframes rise {{
      from {{ opacity: 0; transform: translateY(8px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    @media (max-width: 640px) {{
      .wrap {{ padding: 0.9rem 0.75rem 1.4rem; }}
      .card {{ padding: 0.95rem; }}
      .footer {{ padding: 0.75rem; }}
      .footer-top {{ margin-bottom: 0.45rem; }}
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"hero\">
      <h1>{BRAND_TITLE}<span class=\"accent\"> by {BRAND_OWNER}</span></h1>
      

      <p>Edition: {today}.</p>
      <div class=\"cta-row\">
        <a class=\"chip\" href=\"../index.html\">Back to Archive</a>
      </div>
    </section>
    <div class=\"card\">
      {body_html}
    </div>
    <footer class="footer">
      <div class="footer-top">
        <div class="footer-brand"><strong>{BRAND_TITLE}</strong> | {BRAND_OWNER}</div>
        <nav aria-label="BERC links">
          <ul class="footer-list">
            <li><span class="link-icon" aria-hidden="true">&#8599;</span><a href="{MTSU_WEBSITE}" target="_blank" rel="noopener noreferrer">MTSU</a></li>
            <li><span class="link-icon" aria-hidden="true">&#8599;</span><a href="{BERC}" target="_blank" rel="noopener noreferrer">BERC</a></li>
            <li><span class="link-icon" aria-hidden="true">&#8599;</span><a href="{COE_URP_BERC}" target="_blank" rel="noopener noreferrer">COE-URP</a></li>
            <li><span class="link-icon" aria-hidden="true">&#8599;</span><a href="{DONATE_BERC}" target="_blank" rel="noopener noreferrer">Donate BERC</a></li>
            <li><span class="link-icon" aria-hidden="true">&#8599;</span><a href="{BERC_INSTAGRAM}" target="_blank" rel="noopener noreferrer">Instagram</a></li>
            <li><span class="link-icon" aria-hidden="true">&#8599;</span><a href="{BERC_LINKEDIN}" target="_blank" rel="noopener noreferrer">LinkedIn</a></li>
          </ul>
        </nav>
      </div>
    </footer>
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
            display_date = _pretty_iso_date(item["date"])
            rows.append(
                f"<tr><td>{display_date}</td><td>{item['signal_environment']}</td><td>{item['signal_score']}</td><td><a class='action' href='{href}'>Review / Incele</a></td></tr>"
            )

    table_body = "\n".join(rows) if rows else "<tr><td class='empty' colspan='4'>No brief generated yet.</td></tr>"
    html_doc = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>Daily Brief Archive</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
    :root {{
      --bg-1: #f8fafc;
      --bg-2: #f1f5f9;
      --ink: #1e293b;
      --muted: #475569;
      --panel: rgba(255, 255, 255, 0.94);
      --line: #dbe3ee;
      --accent: #0b3a5e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: 'IBM Plex Sans', sans-serif;
      background:
        radial-gradient(900px 450px at 100% -10%, #dde6f3 0%, transparent 62%),
        linear-gradient(170deg, var(--bg-1), var(--bg-2));
      min-height: 100vh;
    }}
    main {{ max-width: 980px; margin: 0 auto; padding: 1.2rem 1rem 2rem; }}
    .hero {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 1rem 1.1rem;
      margin-bottom: 1rem;
    }}
    .hero .accent {{
      font-family: 'IBM Plex Sans', sans-serif;
      font-style: normal;
      font-size: 0.65em;
      color: var(--muted);
      font-weight: 400;
      letter-spacing: 0;
    }}
    h1 {{ margin: 0; font-family: 'Fraunces', serif; font-size: clamp(1.5rem, 2.5vw, 2rem); }}
    .sub {{ color: var(--muted); margin: 0.45rem 0 0; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 0.45rem; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 0.72rem; border-bottom: 1px solid #e2e8f0; }}
    th {{ color: #0b3a5e; font-weight: 700; }}
    td {{ color: #0f172a; }}
    .action {{
      display: inline-block;
      text-decoration: none;
      font-weight: 700;
      color: #ffffff;
      background: linear-gradient(135deg, #0b3a5e, #1d4f75);
      border-radius: 10px;
      padding: 0.35rem 0.65rem;
    }}
    .empty {{ color: var(--muted); text-align: center; padding: 1rem; }}
    .footer {{
      margin-top: 0.95rem;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.94);
      padding: 0.85rem;
    }}
    .footer-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.7rem;
      flex-wrap: wrap;
      margin-bottom: 0.5rem;
    }}
    .footer-brand {{ font-size: 0.94rem; color: #334155; }}
    .footer-list {{
      margin: 0;
      padding: 0;
      list-style: none;
      display: flex;
      gap: 0.9rem;
      flex-wrap: wrap;
    }}
    .footer-list li {{
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
    }}
    .footer-list a {{
      color: #0b3a5e;
      text-decoration: none;
      font-size: 0.86rem;
      font-weight: 500;
      border-bottom: 1px solid transparent;
      transition: color .18s ease, border-color .18s ease, transform .18s ease;
    }}
    .footer-list a:hover {{
      color: #082a46;
      border-bottom-color: #0b3a5e;
      transform: translateY(-1px);
    }}
    .footer-list a:focus-visible {{
      outline: 2px solid #93c5fd;
      outline-offset: 3px;
      border-radius: 2px;
    }}
    .link-icon {{
      color: #64748b;
      font-size: 0.74rem;
      line-height: 1;
    }}
    .footer-note {{ color: var(--muted); font-size: 0.82rem; line-height: 1.45; }}
    @media (max-width: 640px) {{
      main {{ padding: 0.85rem 0.65rem 1.5rem; }}
      th, td {{ font-size: 0.92rem; padding: 0.6rem 0.5rem; }}
      .action {{ padding: 0.32rem 0.55rem; font-size: 0.85rem; }}
      .footer {{ padding: 0.72rem; }}
    }}
  </style>
</head>
<body>
  <main>
    <section class=\"hero\">
      <h1>{BRAND_TITLE}<span class=\"accent\"> by {BRAND_OWNER}</span></h1>
    </section>
    <div class=\"panel\">
      <table>
        <thead><tr><th>Date</th><th>Signal</th><th>Score</th><th>Action</th></tr></thead>
        <tbody>{table_body}</tbody>
      </table>
    </div>
    <footer class="footer">
      <div class="footer-top">
        <div class="footer-brand"><strong>{BRAND_TITLE}</strong> | {BRAND_OWNER}</div>
        <nav aria-label="BERC links">
          <ul class="footer-list">
            <li><span class="link-icon" aria-hidden="true">&#8599;</span><a href="{MTSU_WEBSITE}" target="_blank" rel="noopener noreferrer">MTSU</a></li>
            <li><span class="link-icon" aria-hidden="true">&#8599;</span><a href="{BERC}" target="_blank" rel="noopener noreferrer">BERC</a></li>
            <li><span class="link-icon" aria-hidden="true">&#8599;</span><a href="{COE_URP_BERC}" target="_blank" rel="noopener noreferrer">COE-URP</a></li>
            <li><span class="link-icon" aria-hidden="true">&#8599;</span><a href="{DONATE_BERC}" target="_blank" rel="noopener noreferrer">Donate BERC</a></li>
            <li><span class="link-icon" aria-hidden="true">&#8599;</span><a href="{BERC_INSTAGRAM}" target="_blank" rel="noopener noreferrer">Instagram</a></li>
            <li><span class="link-icon" aria-hidden="true">&#8599;</span><a href="{BERC_LINKEDIN}" target="_blank" rel="noopener noreferrer">LinkedIn</a></li>
          </ul>
        </nav>
      </div>
    </footer>
  </main>
</body>
</html>"""

    index_path = site_dir / "index.html"
    index_path.write_text(html_doc, encoding="utf-8")
    return index_path
