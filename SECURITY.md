# Security Policy

## Supported versions

Only the latest release (and `main`) receive security fixes.

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Instead, use
GitHub's private vulnerability reporting ("Report a vulnerability" under the
repository's **Security** tab). You should receive an initial response within
a week.

Please include:

- A description of the issue and its impact
- Steps to reproduce (a minimal proof of concept helps)
- Any suggested fix, if you have one

## Deployment security model

The defaults target **local, single-user use**: the API is unauthenticated,
CORS only trusts the local Vite dev server, and rate limiting is off. Before
exposing the backend beyond localhost, set `API_KEY`, `CORS_ORIGINS`, and
`RATE_LIMIT_PER_MINUTE` — see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
A report that assumes those knobs are unset on a public host is a
configuration issue, not a vulnerability; anything that bypasses them when
set absolutely is one.
