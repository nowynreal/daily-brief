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


def append_history(history_file: Path, output_paths: Dict[str, Path], signal_env: str, score: int, alert_count: int = 0) -> None:
    history_file.parent.mkdir(parents=True, exist_ok=True)
    now_utc = datetime.now(timezone.utc)
    record = {
        "generated_at": now_utc.isoformat(),
        "date": now_utc.date().isoformat(),
        "signal_environment": signal_env,
        "signal_score": score,
        "alert_count": alert_count,
        "html": str(output_paths["html"]).replace("\\", "/"),
        "json": str(output_paths["json"]).replace("\\", "/"),
    }
    with history_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def render_index(site_dir: Path, history_file: Path) -> Path:
    briefs_dir = site_dir / "briefs"
    briefs_dir.mkdir(parents=True, exist_ok=True)

    cards = []
    latest_timestamp = None
    if history_file.exists():
        lines = [line.strip() for line in history_file.read_text(encoding="utf-8").splitlines() if line.strip()]
        for line in reversed(lines[-60:]):
            item = json.loads(line)
            if not latest_timestamp:
                latest_timestamp = item.get("generated_at", "")
            href = f"briefs/{item['date']}.html"
            display_date = _pretty_iso_date(item["date"])
            signal_env = item["signal_environment"]
            score = item["signal_score"]
            alert_count = item.get("alert_count", 0)
            
            badge_class = "stable"
            if score >= 5:
                badge_class = "elevated"
            elif score >= 2:
                badge_class = "moderate"
            
            alert_word = "alert" if alert_count == 1 else "alerts"
                        
            cards.append(f"""        <div class="brief-card">
          <div class="brief-meta">
            <div class="brief-date">{display_date}</div>
            <div class="brief-signal-group">
              <span class="signal-badge {badge_class}">{signal_env}</span>
              <div class="brief-alerts">
                <span class="alert-count">{alert_count}</span>
                <span><strong>{alert_count} {alert_word}</strong> triggered</span>
              </div>
            </div>
          </div>
          <div class="brief-actions">
            <a href="{href}" class="brief-btn">Review Full Brief</a>
          </div>
        </div>"""
            )

    cards_html = "\n".join(cards) if cards else '<div style="color: var(--muted); text-align: center; padding: 1rem;">No brief generated yet.</div>'
    timestamp_attr = f'data-last-generated="{latest_timestamp}"' if latest_timestamp else 'data-last-generated=""'
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
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
      margin-bottom: 1.5rem;
    }}
    .site-nav {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
    }}
    .site-brand {{
      font-size: 14px;
      font-weight: 700;
      color: #0f172a;
      letter-spacing: 0.02em;
      text-transform: uppercase;
    }}
    .nav-links {{
      list-style: none;
      display: flex;
      align-items: center;
      gap: 0.65rem;
      margin: 0;
      padding: 0;
      flex-wrap: wrap;
    }}
    .nav-link {{
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.42rem 0.7rem;
      border-radius: 999px;
      border: 1px solid #dbe3ee;
      background: #f8fafc;
      color: var(--accent);
      font-size: 13px;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.18s ease;
    }}
    .nav-link:hover {{
      transform: translateY(-1px);
      background: #eef5ff;
      border-color: #bfdbfe;
      color: #082a46;
    }}
    .live-status {{
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      padding: 0.42rem 0.68rem;
      border-radius: 999px;
      border: 1px solid #cbd5e1;
      background: #f8fafc;
      color: #334155;
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
    }}
    .live-status .dot {{
      width: 8px;
      height: 8px;
      border-radius: 999px;
      flex-shrink: 0;
      background: #64748b;
      box-shadow: 0 0 0 0 rgba(100, 116, 139, 0.35);
      transition: background 0.2s ease, box-shadow 0.2s ease;
    }}
    .live-status.live {{
      border-color: #86efac;
      background: #ecfdf3;
      color: #166534;
    }}
    .live-status.live .dot {{
      background: #22c55e;
      box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.16);
      animation: pulse-live 2.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }}
    .live-status.stale {{
      border-color: #fcd34d;
      background: #fffbeb;
      color: #92400e;
    }}
    .live-status.stale .dot {{
      background: #f59e0b;
      box-shadow: 0 0 0 5px rgba(245, 158, 11, 0.14);
    }}
    .live-status.offline {{
      border-color: #fecaca;
      background: #fef2f2;
      color: #991b1b;
    }}
    .live-status.offline .dot {{
      background: #ef4444;
      box-shadow: 0 0 0 5px rgba(239, 68, 68, 0.14);
    }}
    @keyframes pulse-live {{
      0%, 100% {{
        box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.16);
        opacity: 1;
      }}
      50% {{
        box-shadow: 0 0 0 8px rgba(34, 197, 94, 0.08);
        opacity: 0.9;
      }}
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 1.2rem;
    }}
    .signal-legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.55rem;
      margin-bottom: 1rem;
    }}
    .legend-pill {{
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      padding: 0.38rem 0.65rem;
      border-radius: 999px;
      font-size: 12px;
      color: #334155;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
    }}
    .legend-dot {{
      width: 8px;
      height: 8px;
      border-radius: 999px;
      flex-shrink: 0;
    }}
    .legend-dot.stable {{ background: #10b981; }}
    .legend-dot.moderate {{ background: #f59e0b; }}
    .legend-dot.elevated {{ background: #ef4444; }}
    .brief-cards {{
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }}
    .brief-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 11px;
      padding: 1.4rem;
      transition: all 0.28s cubic-bezier(0.4, 0, 0.2, 1);
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 1.2rem;
      align-items: start;
    }}
    .brief-card:hover {{
      border-color: var(--accent);
      box-shadow: 0 12px 28px rgba(11, 58, 94, 0.12);
      transform: translateY(-2px);
    }}
    .brief-meta {{
      display: flex;
      flex-direction: column;
      gap: 0.8rem;
    }}
    .brief-date {{
      font-size: 15px;
      font-weight: 600;
      color: var(--ink);
      line-height: 1.4;
    }}
    .brief-signal-group {{
      display: flex;
      align-items: center;
      gap: 0.8rem;
      flex-wrap: wrap;
    }}
    .signal-badge {{
      display: inline-block;
      padding: 0.5rem 0.9rem;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      white-space: nowrap;
    }}
    .signal-badge.stable {{
      background: #d1fae5;
      color: #047857;
      border: 1px solid #a7f3d0;
    }}
    .signal-badge.moderate {{
      background: #fed7aa;
      color: #92400e;
      border: 1px solid #fdba74;
    }}
    .signal-badge.elevated {{
      background: #fecaca;
      color: #991b1b;
      border: 1px solid #fca5a5;
    }}
    .brief-alerts {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-size: 13px;
      color: var(--muted);
      background: #f8fafc;
      padding: 0.5rem 0.8rem;
      border-radius: 7px;
      border: 1px solid #e2e8f0;
    }}
    .alert-count {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: #e2e8f0;
      font-size: 12px;
      font-weight: 700;
      color: #334155;
      flex-shrink: 0;
    }}
    .brief-alerts strong {{
      font-weight: 700;
      color: var(--ink);
    }}
    .brief-context {{
      margin: 0;
      font-size: 13px;
      color: #64748b;
      line-height: 1.45;
    }}
    .brief-actions {{
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
      align-items: flex-end;
    }}
    .brief-btn {{
      display: inline-block;
      padding: 0.75rem 1.4rem;
      font-size: 14px;
      font-weight: 700;
      color: #ffffff;
      background: linear-gradient(135deg, var(--accent), #1d4f75);
      border: none;
      border-radius: 9px;
      text-decoration: none;
      cursor: pointer;
      transition: all 0.24s ease;
      box-shadow: 0 4px 12px rgba(11, 58, 94, 0.18);
      white-space: nowrap;
    }}
    .brief-btn:hover {{
      background: linear-gradient(135deg, #082a46, #15384a);
      box-shadow: 0 8px 20px rgba(11, 58, 94, 0.28);
      transform: translateY(-2px);
    }}
    .brief-btn:active {{
      transform: translateY(0);
      box-shadow: 0 2px 6px rgba(11, 58, 94, 0.15);
    }}
    .footer {{
      margin-top: 1.2rem;
      padding-top: 1rem;
      border-top: 1px solid #dbe3ee;
    }}
    .footer-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.8rem;
      flex-wrap: wrap;
    }}
    .footer-brand {{
      font-size: 0.9rem;
      color: #334155;
    }}
    .footer-list {{
      margin: 0;
      padding: 0;
      list-style: none;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
    }}
    .footer-list a {{
      color: #0b3a5e;
      text-decoration: none;
      font-size: 0.84rem;
      font-weight: 600;
      border-bottom: 1px solid transparent;
      transition: color 0.18s ease, border-color 0.18s ease;
    }}
    .footer-list a:hover {{
      color: #082a46;
      border-bottom-color: #0b3a5e;
    }}
    .footer-note {{
      margin: 0.5rem 0 0;
      color: #64748b;
      font-size: 0.78rem;
      line-height: 1.45;
    }}
    @media (max-width: 768px) {{
      .brief-card {{
        grid-template-columns: 1fr;
        gap: 1rem;
      }}
      .brief-actions {{
        align-items: flex-start;
      }}
      .brief-btn {{
        width: 100%;
        text-align: center;
      }}
    }}
    @media (max-width: 640px) {{
      main {{
        padding: 0.85rem 0.65rem 1.5rem;
      }}
      .panel {{
        padding: 1rem;
      }}
      .brief-card {{
        padding: 1.1rem;
      }}
      .site-nav {{
        flex-direction: column;
        align-items: flex-start;
      }}
      .footer-top {{
        flex-direction: column;
        align-items: flex-start;
      }}
      .brief-alerts {{
        font-size: 12px;
        padding: 0.4rem 0.7rem;
      }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      .live-status.live .dot {{
        animation: none;
        box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.16);
        opacity: 1;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <nav class="site-nav" aria-label="Primary navigation">
        <div class="site-brand">BERC Daily Briefer</div>
        <ul class="nav-links">
          <li>
            <span id="liveStatus" class="live-status" {timestamp_attr} aria-live="polite">
              <span class="dot" aria-hidden="true"></span>
              Checking status...
            </span>
          </li>
          <li><a class="nav-link" href="https://www.mtsu.edu/berc/" target="_blank" rel="noopener noreferrer">Visit BERC Website &#8599;</a></li>
        </ul>
      </nav>
    </section>

    <div class="panel">
      <div class="signal-legend" aria-label="Signal legend">
        <span class="legend-pill"><span class="legend-dot stable" aria-hidden="true"></span>Low risk: no critical alerts</span>
        <span class="legend-pill"><span class="legend-dot moderate" aria-hidden="true"></span>Watch: some indicators rising</span>
        <span class="legend-pill"><span class="legend-dot elevated" aria-hidden="true"></span>High watch: multiple alerts active</span>
      </div>
      <div class="brief-cards">
        {cards_html}
      </div>
    </div>

    <footer class="footer">
      <div class="footer-top">
        <div class="footer-brand"><strong>BERC Daily Briefer</strong></div>
        <nav aria-label="Footer links">
          <ul class="footer-list">
            <li><a href="https://www.mtsu.edu/" target="_blank" rel="noopener noreferrer">MTSU</a></li>
            <li><a href="https://www.mtsu.edu/berc/" target="_blank" rel="noopener noreferrer">BERC</a></li>
            <li><a href="https://urp.mtsu.edu/" target="_blank" rel="noopener noreferrer">COE-URP</a></li>
            <li><a href="https://www.mtsu.edu/give/" target="_blank" rel="noopener noreferrer">Donate BERC</a></li>
            <li><a href="https://www.instagram.com/mtsublueraiders/" target="_blank" rel="noopener noreferrer">Instagram</a></li>
            <li><a href="https://www.linkedin.com/school/middle-tennessee-state-university/" target="_blank" rel="noopener noreferrer">LinkedIn</a></li>
          </ul>
        </nav>
      </div>
      <p class="footer-note">External links open in a new tab. Daily Brief status and archive entries are updated from the latest generated report.</p>
    </footer>
  </main>
  <script>
    (function () {{
      var statusEl = document.getElementById('liveStatus');
      if (!statusEl) {{
        return;
      }}

      var lastGeneratedRaw = statusEl.getAttribute('data-last-generated');
      var lastGenerated = lastGeneratedRaw ? new Date(lastGeneratedRaw) : null;
      if (!lastGenerated || Number.isNaN(lastGenerated.getTime())) {{
        statusEl.classList.add('offline');
        statusEl.textContent = 'Status unavailable';
        return;
      }}

      function formatAge(minutes) {{
        if (minutes < 1) {{
          return 'just now';
        }}
        if (minutes < 60) {{
          return Math.floor(minutes) + 'm ago';
        }}
        var hours = Math.floor(minutes / 60);
        if (hours < 48) {{
          return hours + 'h ago';
        }}
        var days = Math.floor(hours / 24);
        return days + 'd ago';
      }}

      function renderStatus() {{
        var minutes = (Date.now() - lastGenerated.getTime()) / 60000;
        var level = 'offline';
        var label = 'Offline';

        if (minutes <= 1500) {{
          level = 'live';
          label = 'Active';
        }} else if (minutes <= 4320) {{
          level = 'stale';
          label = 'Delayed';
        }}

        statusEl.classList.remove('live', 'stale', 'offline');
        statusEl.classList.add(level);
        statusEl.innerHTML = '<span class="dot" aria-hidden="true"></span>' + label + ' - updated ' + formatAge(minutes);
      }}

      renderStatus();
      window.setInterval(renderStatus, 60000);
    }})();
  </script>
</body>
</html>"""

    index_path = site_dir / "index.html"
    index_path.write_text(html_doc, encoding="utf-8")
    return index_path
