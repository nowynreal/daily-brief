from __future__ import annotations

import html
import json
import re
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

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


def _format_dashboard_value(value, units: str) -> str:
    if value is None:
        return "NA"
    if units == "percent":
        return f"{value:.2f}%"
    if units == "count":
        return f"{value:,.0f}"
    if units == "thousands":
        return f"{value:,.1f}k"
    if units == "usd_per_gallon":
        return f"${value:.2f}/gal"
    if units == "million_usd":
        return f"${value:,.0f}M"
    return f"{value:,.2f}"


def _sparkline_svg(values: List[float]) -> str:
    if len(values) < 2:
        return '<svg viewBox="0 0 120 34" aria-hidden="true"></svg>'

    width = 120
    height = 34
    min_value = min(values)
    max_value = max(values)
    spread = (max_value - min_value) or 1.0

    points = []
    for index, value in enumerate(values):
        x = (index / max(1, len(values) - 1)) * width
        y = height - (((value - min_value) / spread) * (height - 4)) - 2
        points.append(f"{x:.1f},{y:.1f}")

    polyline = " ".join(points)
    return (
        '<svg viewBox="0 0 120 34" aria-hidden="true">'
        + '<polyline fill="none" stroke="#0b3a5e" stroke-width="2" points="'
        + polyline
        + '" />'
        + "</svg>"
    )


def _render_platform_dashboard(platform_payload: Optional[dict]) -> str:
    if not platform_payload:
        return ""

    environment = html.escape(str(platform_payload.get("signal_environment", "Unknown")))

    category_cards = []
    for category in platform_payload.get("categories", []):
        category_name = html.escape(str(category.get("category", "Unknown")))
        index_name = html.escape(str(category.get("index_name", f"{category_name} Index")))
        status = html.escape(str(category.get("status", "Stable")))
        status_class = status.lower()
        composite_score = category.get("composite_score")
        score_text = "Index: n/a" if composite_score is None else f"Index: {float(composite_score):+.2f}"

        category_cards.append(
            f"""
            <article class="category-card">
              <div class="summary-kicker">{index_name}</div>
              <div class="summary-value">{category_name}</div>
              <div class="summary-sub">{score_text}</div>
              <span class="status-pill {status_class}">{status}</span>
            </article>
            """
        )

    category_sections = []
    for category in platform_payload.get("categories", []):
        category_name = html.escape(str(category.get("category", "Uncategorized")))
        category_signal = html.escape(str(category.get("status", "Stable")))
        category_signal_class = category_signal.lower()
        counts_block = category.get("counts", {})

        indicator_cards = []
        for indicator in category.get("indicators", []):
            title = html.escape(str(indicator.get("title", indicator.get("indicator_id", "Indicator"))))
            latest = _format_dashboard_value(indicator.get("latest_value"), str(indicator.get("units", "")))
            abs_change = indicator.get("abs_change")
            pct_change = indicator.get("pct_change")

            if pct_change is not None:
                change_text = f"{float(pct_change):+.2f}%"
            elif abs_change is not None:
                change_text = _format_dashboard_value(abs_change, str(indicator.get("units", "")))
            else:
                change_text = "No change data"

            raw_arrow = str(indicator.get("change_arrow", "->"))
            arrow = "&#8594;"
            change_class = "flat"
            if raw_arrow == "^":
                arrow = "&#8593;"
                change_class = "up"
            elif raw_arrow == "v":
                arrow = "&#8595;"
                change_class = "down"

            change_label = html.escape(str(indicator.get("change_label", "flat")).capitalize())
            direction = html.escape(str(indicator.get("signal_direction", "unknown")))
            strength = html.escape(str(indicator.get("signal_strength", "stable")))
            source_name = html.escape(str(indicator.get("source_name", "Unknown source")))
            source_url = html.escape(str(indicator.get("source_url", "")))
            interpretation = html.escape(str(indicator.get("interpretation", "")))

            trend_values = [float(v) for v in indicator.get("trend_values", []) if v is not None]
            sparkline = _sparkline_svg(trend_values)
            source_link = (
                f'<a href="{source_url}" target="_blank" rel="noopener noreferrer">{source_name}</a>'
                if source_url
                else source_name
            )

            indicator_cards.append(
                f"""
              <article class="indicator-card strength-{strength}">
                <div class="indicator-top">
                  <h4>{title}</h4>
                  <span class="direction-tag">{direction}</span>
                </div>
                <div class="indicator-values">
                  <div class="latest">Latest: <strong>{latest}</strong></div>
                  <div class="change">Period change: {change_text}</div>
                  <div class="change-chip {change_class}"><span class="arrow" aria-hidden="true">{arrow}</span>{change_label}</div>
                </div>
                <div class="trend-sparkline">{sparkline}</div>
                <p class="indicator-note">{interpretation}</p>
                <p class="indicator-source">Source: {source_link}</p>
              </article>
              """
            )

        category_sections.append(
            f"""
          <section class="category-section">
            <div class="category-head">
              <h3>{category_name}</h3>
              <span class="category-signal {category_signal_class}">{category_signal}</span>
            </div>
            <p class="category-stats">
              {counts_block.get('improving', 0)} improving | {counts_block.get('worsening', 0)} worsening | {counts_block.get('stable', 0)} stable | {counts_block.get('unknown', 0)} unknown
            </p>
            <div class="indicator-grid">
              {''.join(indicator_cards)}
            </div>
          </section>
          """
        )

    methodology_items = []
    for note in platform_payload.get("methodology_notes", []):
        methodology_items.append(f"<li>{html.escape(str(note))}</li>")

    methodology_html = ""
    if methodology_items:
        methodology_html = (
            '<section class="methodology"><h3>Methodology and Source Notes</h3><ul>'
            + "".join(methodology_items)
            + "</ul></section>"
        )

    return f"""
    <section class="platform-dashboard">
      <h2>Expanded Tennessee Indicator Monitor</h2>
      <p class="platform-intro">{environment}. This dashboard highlights what changed, why it matters, and how reliable each signal is.</p>
      <section class="category-overview" aria-label="Category status cards">{''.join(category_cards)}</section>
      {''.join(category_sections)}
      {methodology_html}
    </section>
    """


def markdown_to_basic_html(markdown_text: str, title: str, platform_payload: Optional[dict] = None) -> str:
    body_html = _markdown_body_to_html(markdown_text)
    dashboard_html = _render_platform_dashboard(platform_payload)
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
    .platform-dashboard {{
      margin-bottom: 1rem;
      border: 1px solid var(--line);
      background: #fdfefe;
      border-radius: 14px;
      padding: 1rem;
      animation: rise .52s ease-out;
    }}
    .platform-dashboard h2 {{
      margin: 0;
      font-family: 'Fraunces', serif;
      font-size: 1.2rem;
    }}
    .platform-intro {{ color: var(--muted); margin: 0.45rem 0 0.8rem; }}
    .category-overview {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 0.7rem;
      margin-bottom: 0.9rem;
    }}
    .category-card {{
      border: 1px solid #dbe7f3;
      background: #f8fbff;
      border-radius: 11px;
      padding: 0.7rem;
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
    }}
    .summary-kicker {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; color: #64748b; }}
    .summary-value {{ font-weight: 700; margin-top: 0.2rem; }}
    .summary-sub {{ font-size: 0.86rem; color: #475569; margin-top: 0.12rem; }}
    .status-pill {{
      display: inline-block;
      width: fit-content;
      margin-top: 0.35rem;
      font-size: 0.74rem;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      border-radius: 999px;
      border: 1px solid #cbd5e1;
      background: #f8fafc;
      padding: 0.18rem 0.55rem;
      font-weight: 700;
      color: #334155;
    }}
    .status-pill.improving {{ border-color: #86efac; background: #ecfdf3; color: #166534; }}
    .status-pill.weakening {{ border-color: #fca5a5; background: #fef2f2; color: #991b1b; }}
    .status-pill.stable {{ border-color: #cbd5e1; background: #f8fafc; color: #334155; }}
    .category-section {{
      border-top: 1px solid #e2e8f0;
      padding-top: 0.9rem;
      margin-top: 0.8rem;
    }}
    .category-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 0.7rem;
      flex-wrap: wrap;
    }}
    .category-head h3 {{ margin: 0; font-size: 1rem; }}
    .category-signal {{
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      border-radius: 999px;
      border: 1px solid #cbd5e1;
      background: #f8fafc;
      padding: 0.2rem 0.55rem;
      color: #334155;
      font-weight: 600;
    }}
    .category-signal.improving {{ border-color: #86efac; background: #ecfdf3; color: #166534; }}
    .category-signal.weakening {{ border-color: #fca5a5; background: #fef2f2; color: #991b1b; }}
    .category-signal.stable {{ border-color: #cbd5e1; background: #f8fafc; color: #334155; }}
    .category-stats {{ margin: 0.35rem 0 0.7rem; color: #64748b; font-size: 0.88rem; }}
    .indicator-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 0.65rem;
    }}
    .indicator-card {{
      border: 1px solid #dbe7f3;
      border-radius: 10px;
      background: #ffffff;
      padding: 0.65rem;
    }}
    .indicator-card.strength-watch {{ border-color: #fdba74; background: #fffbeb; }}
    .indicator-card.strength-elevated {{ border-color: #fca5a5; background: #fef2f2; }}
    .indicator-top {{ display: flex; justify-content: space-between; gap: 0.5rem; align-items: start; }}
    .indicator-top h4 {{ margin: 0; font-size: 0.93rem; line-height: 1.35; }}
    .direction-tag {{ font-size: 0.74rem; color: #475569; text-transform: uppercase; letter-spacing: 0.03em; }}
    .indicator-values {{ margin-top: 0.35rem; font-size: 0.86rem; color: #334155; }}
    .latest strong {{ color: #0f172a; }}
    .change-chip {{
      margin-top: 0.25rem;
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
      border-radius: 999px;
      border: 1px solid #cbd5e1;
      background: #f8fafc;
      font-size: 0.76rem;
      font-weight: 700;
      color: #334155;
      padding: 0.12rem 0.45rem;
      width: fit-content;
    }}
    .change-chip.up {{ border-color: #86efac; background: #ecfdf3; color: #166534; }}
    .change-chip.down {{ border-color: #fca5a5; background: #fef2f2; color: #991b1b; }}
    .change-chip.flat {{ border-color: #cbd5e1; background: #f8fafc; color: #334155; }}
    .change-chip .arrow {{ font-size: 0.86rem; line-height: 1; }}
    .trend-sparkline svg {{ width: 100%; height: 34px; display: block; margin-top: 0.2rem; }}
    .indicator-note {{ margin: 0.3rem 0; font-size: 0.82rem; color: #475569; line-height: 1.4; }}
    .indicator-source {{ margin: 0; font-size: 0.8rem; color: #64748b; }}
    .indicator-source a {{ color: #0b3a5e; text-decoration: none; border-bottom: 1px solid transparent; }}
    .indicator-source a:hover {{ border-bottom-color: #0b3a5e; }}
    .methodology {{
      border-top: 1px solid #e2e8f0;
      margin-top: 0.9rem;
      padding-top: 0.8rem;
    }}
    .methodology h3 {{ margin: 0 0 0.45rem; font-size: 0.98rem; }}
    .methodology ul {{ margin: 0; padding-left: 1rem; }}
    .methodology li {{ margin: 0.25rem 0; font-size: 0.86rem; color: #334155; line-height: 1.45; }}
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
      .category-overview {{ grid-template-columns: 1fr; }}
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
    {dashboard_html}
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
    platform_payload: Optional[dict] = None,
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
        "platform": platform_payload,
    }

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(brief_markdown, encoding="utf-8")
    html_path.write_text(
        markdown_to_basic_html(brief_markdown, f"Daily Brief {today}", platform_payload=platform_payload),
        encoding="utf-8",
    )

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
