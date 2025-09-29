# MCP Environment & Token Integration Overview

## Required Environment Variables
The MCP integration relies on the application's configuration defined in `backend/core/config.py`. The following settings must be populated through environment variables or the `.env` file:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Connection string for the primary database used by MCP services to persist data. |
| `OPENAI_API_KEY` | API key required for MCP-driven AI interactions (placeholder for future provider integration). |
| `SECRET_KEY` | Symmetric key used to sign MCP access and refresh tokens. Must be a secure random value in production. |
| `ALGORITHM` | JWT signing algorithm identifier shared by MCP token generators and verifiers. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifetime of MCP access tokens that authorize short-lived requests. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Lifetime of MCP refresh tokens used to mint new access tokens without re-authentication. |
| `EXPIRING_ITEMS_THRESHOLD_DAYS` | Threshold leveraged by MCP logic that surfaces soon-to-expire items. |
| `ADMIN_EMAILS` / `ADMIN_EMAIL_DOMAINS` | Whitelist configuration for privileged MCP administrators. |

> These values are read via the `Settings` object exported from `backend/core/config.py`, ensuring consistency across services.

## JWT Helper Coverage
`backend/security/tokens.py` exposes helpers for both token lifecycles required by MCP clients:

- `create_access_token(user_id, extra_claims=None)` generates short-lived access tokens using the configured `ACCESS_TOKEN_EXPIRE_MINUTES` setting.
- `create_refresh_token(user_id, extra_claims=None)` issues longer-lived refresh tokens governed by `REFRESH_TOKEN_EXPIRE_DAYS`.
- `decode_token(token)` centralizes signature validation and payload decoding for both token types.

Together these helpers implement the full access/refresh flow for MCP authentication while sharing the core `create_token` utility.

## Backlog: Additional MCP Settings
Add the following configuration knobs in a future update to complete MCP support:

- `MCP_MANIFEST_URL`: URL pointing to the MCP manifest describing available capabilities.
- `MCP_CLIENT_ID`: Identifier used when MCP clients negotiate authentication.
- `MCP_ALLOWED_ORIGINS`: Optional CORS override tailored for MCP host environments.

Track this work in `docs/backlog.md`.
