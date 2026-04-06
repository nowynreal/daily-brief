# Tennessee Economic Monitoring Architecture Plan

## Goals

- Preserve current daily brief generation and static deployment workflow.
- Expand from a fixed FRED snapshot script into a modular indicator platform.
- Keep costs low, legal risk lower, and operations simple.
- Prepare for future multi-state expansion without rewriting the core pipeline.

## Core principles

- Source priority: official/public datasets first, structured APIs second, controlled scraping only when necessary.
- Static-first outputs for GitHub Pages.
- Scheduled batch execution, no always-on server.
- Deterministic scoring by default for transparency.
- Clear separation of data stages.

## Data lifecycle

1. Registry layer

- Indicator metadata is defined in `daily_brief/config/indicator_registry_tn.json`.
- Registry controls activation, categories, source metadata, and scoring thresholds.

2. Collection layer

- Source connectors fetch raw observations by `collection_method`.
- Current implementation supports `fred_api`.

3. Normalization layer

- Raw source rows convert into consistent observation objects.
- Latest/previous/change snapshots are computed uniformly.

4. Signal layer

- Indicator-level signals are evaluated using registry transform rules.
- Category summaries and overall environment are computed from indicator signals.

5. Storage layer

- Raw data: `output/raw/YYYY-MM-DD/raw_observations.jsonl`
- Normalized export: `output/normalized/indicators_YYYY-MM-DD.json`
- Historical store: `output/indicator_store.sqlite3`

6. Rendering layer

- Legacy brief markdown and HTML remain first-class outputs.
- Expanded indicator dashboard sections are rendered into daily HTML pages.
- Archive page remains in `docs/index.html`.

## Module map

- `daily_brief/platform/models.py`: indicator, observation, snapshot models.
- `daily_brief/platform/registry.py`: registry loading and active filtering.
- `daily_brief/platform/connectors/`: source connectors (`fred_connector.py`).
- `daily_brief/platform/normalization.py`: data normalization and raw packaging.
- `daily_brief/platform/scoring.py`: indicator and category scoring.
- `daily_brief/platform/storage.py`: SQLite and raw/normalized file storage.
- `daily_brief/platform/pipeline.py`: orchestration for expanded indicators.

## Frequency support

The registry accepts `daily`, `weekly`, and `monthly` indicator frequencies.

## Multi-state extension path

- Duplicate registry with state-specific geography and source params.
- Reuse same pipeline and connectors.
- Keep per-state normalized exports and dashboard pages in static output directories.

## Operations and hosting

- Existing GitHub Actions workflow continues to execute `python python_code.py`.
- New artifacts are generated in output directories and can be committed with existing flow.
- No heavy backend, queue, or cloud database required at this stage.
