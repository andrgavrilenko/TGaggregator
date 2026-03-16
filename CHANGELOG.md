# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-03-16

### Added

- Initial MVP scaffold for TGaggregator.
- Telegram ingestion CLI (`login`, `sync-channels`, `bootstrap`, `ingest-*`).
- Retry/backoff and FloodWait handling.
- FastAPI endpoints (`/health`, `/status`, `/channels`, `/feed`).
- Streamlit feed UI.
- SQLAlchemy models and repository layer.
- Alembic migrations (`0001_init`).
- Base tests for API and repository.
- Project documentation package (roadmap, status, architecture, runbook, API reference).