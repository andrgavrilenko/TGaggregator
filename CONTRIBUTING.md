# Contributing

Thanks for contributing to TGaggregator.

## Workflow

1. Create a branch from `main`.
2. Keep changes scoped and atomic.
3. Add or update tests for behavior changes.
4. Run local checks before opening PR.

## Local checks

```bash
uv run pytest -q
```

## Commit conventions

Use clear, imperative messages.

Examples:
- `Add channel batch update endpoint`
- `Fix FloodWait retry state handling`
- `Update deploy runbook for systemd`

## Pull request checklist

- [ ] Problem statement is clear.
- [ ] Scope is limited and reviewable.
- [ ] Tests added/updated.
- [ ] Documentation updated.
- [ ] No secrets or runtime artifacts committed.

## Coding expectations

- Keep ingestion stable and idempotent.
- Preserve single-writer DB pattern.
- Avoid breaking API contracts without documentation.