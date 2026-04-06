# Daily Brief Tennessee Monitor

This repository contains a practical low-cost system for generating daily economic briefings and publishing them as static pages.

The original MVP path remains intact and now runs alongside an expanded Tennessee-first indicator platform designed for future multi-state growth.

## Product flow

1. A scheduled job runs every morning.
2. Legacy snapshots are collected from FRED for the existing brief format.
3. Expanded indicator pipeline runs from the structured registry (currently FRED-backed connectors).
4. A deterministic rule-based summary is generated (default), with optional LLM narrative mode.
5. Output files are written:
   - `output/brief_YYYY-MM-DD.json`
   - `output/brief_YYYY-MM-DD.md`
   - `docs/briefs/YYYY-MM-DD.html`
   - `docs/index.html`
   - `output/raw/YYYY-MM-DD/raw_observations.jsonl`
   - `output/normalized/indicators_YYYY-MM-DD.json`
   - `output/indicator_store.sqlite3`
6. Optional email notification is sent.
7. Generated static files are committed by GitHub Actions and served via GitHub Pages.

## Why this architecture

- Very low recurring cost (GitHub Actions + static hosting + free public data sources).
- No always-on backend server.
- Clear separation of raw, normalized, and rendered artifacts.
- Structured indicator registry for incremental expansion.
- Operationally simple and transparent for users.

## Expanded architecture layers

- Source connectors / collectors
- Normalization layer
- Indicator registry and category definitions
- Scoring / signal layer
- Storage layer (JSONL + SQLite + static JSON exports)
- Rendering layer (brief + dashboard-like indicator sections)
- Methodology/source notes for transparency

Current active source methods:

- `fred_api`

Planned methods (not enabled by default):

- structured partner APIs
- controlled scraping connectors, only where necessary and policy-safe

## Quick start

1. Copy `.env.example` to `.env` and fill values.
2. Run:

```bash
python python_code.py
```

3. Open generated archive page:

- `docs/index.html`

## Environment variables

See `.env.example`.

Minimum required:

- `FRED_API_KEY`

Recommended additions:

- `INDICATOR_REGISTRY_PATH` (default: `daily_brief/config/indicator_registry_tn.json`)
- `INDICATOR_DB_PATH` (default: `output/indicator_store.sqlite3`)

Optional:

- `SEND_EMAIL=true` and SMTP settings for notifications.
- `USE_LLM=true` + `OPENAI_API_KEY` for AI-assisted narrative mode.

## Planning artifacts

- `docs/architecture-plan.md`
- `docs/tennessee-indicator-roadmap.md`
- `docs/migration-notes.md`

## Scheduling

- Local cron / Task Scheduler: run `python python_code.py` at 08:00.
- GitHub Actions: use `.github/workflows/daily-brief.yml`.

## Security notes

- Never commit `.env`.
- Use GitHub Secrets for CI.
- Keep SMTP and API credentials out of source code.
