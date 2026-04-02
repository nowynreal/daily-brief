# Daily Brief MVP

This repository contains a practical low-cost MVP for generating a daily economic brief, publishing it as a static page, and optionally sending a notification email.

## Product flow (MVP)

1. A scheduled job runs every morning.
2. The script collects selected indicators from FRED.
3. A deterministic rule-based summary is generated (default).
4. Output files are written:
   - `output/brief_YYYY-MM-DD.json`
   - `output/brief_YYYY-MM-DD.md`
   - `docs/briefs/YYYY-MM-DD.html`
   - `docs/index.html` (archive)
5. Optional email notification is sent with a Review button.
6. Files are committed by GitHub Actions and served with GitHub Pages.

## Why this architecture

- Very low recurring cost: can run on free GitHub tier + free FRED API.
- No always-on backend server.
- Static pages are simple and operationally cheap.
- Secrets are handled via environment variables and GitHub Secrets.

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

Optional:

- `SEND_EMAIL=true` and SMTP settings for notifications.
- `USE_LLM=true` + `OPENAI_API_KEY` if you need AI-assisted writing.

## Scheduling

- Local cron / Task Scheduler: run `python python_code.py` at 08:00.
- GitHub Actions: use `.github/workflows/daily-brief.yml`.

## Security notes

- Never commit `.env`.
- Use GitHub Secrets for CI.
- Keep SMTP and API credentials out of source code.
