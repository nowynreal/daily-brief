# Migration Notes: Legacy MVP -> Expanded Indicator Platform

## What stayed the same

- Entry point remains `python_code.py`.
- Main run path remains `scripts/generate_brief.py`.
- Existing FRED snapshot collection still runs.
- Existing deterministic warning flag logic still runs.
- Existing output contracts stay in place:
  - `output/brief_YYYY-MM-DD.json`
  - `output/brief_YYYY-MM-DD.md`
  - `docs/briefs/YYYY-MM-DD.html`
  - `docs/index.html`
- Optional email notification flow stays unchanged.
- GitHub Actions schedule and commit workflow stay unchanged.

## What was added

- Registry-driven indicator definitions:
  - `daily_brief/config/indicator_registry_tn.json`
- New modular platform package:
  - `daily_brief/platform/*`
- Storage separation:
  - raw source records (`output/raw/...`)
  - normalized static export (`output/normalized/...`)
  - SQLite historical store (`output/indicator_store.sqlite3`)
- Daily brief HTML now includes expanded dashboard sections and methodology notes when platform data is available.

## Runtime integration details

- `scripts/generate_brief.py` now runs the platform pipeline after legacy snapshots are collected.
- If the platform pipeline fails, legacy brief generation still continues.
- Platform summary is appended into markdown and embedded into HTML payloads.

## Output schema evolution

- `output/brief_YYYY-MM-DD.json` now includes a new optional `platform` object.
- Legacy fields (`snapshots`, `flags`, `signal_score`, etc.) are preserved.

## Environment changes

New optional settings in `.env`:

- `INDICATOR_REGISTRY_PATH`
- `INDICATOR_DB_PATH`

Defaults are configured for local and GitHub Actions runs.

## Next migration steps

1. Add additional connectors beyond `fred_api`.
2. Add category-level and indicator-level detail pages to static docs output.
3. Add trend chart data endpoints for richer front-end visualizations.
4. Introduce state registry variants (e.g., Tennessee + neighboring states).
