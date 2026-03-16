# Security Policy

## Supported Version

Current active branch: `main`.

## Reporting a Vulnerability

Please do not open public issues for sensitive security problems.

Contact:
- GitHub account: `@andrgavrilenko`
- Preferred channel: private message/email associated with repository owner

Include:
- affected component
- reproduction steps
- impact assessment
- suggested mitigation (optional)

## Secret Handling

- `.env`, Telegram sessions, and database files must stay local.
- Rotate credentials if accidental exposure is suspected.
- Use least-privilege network exposure for API/UI in production.