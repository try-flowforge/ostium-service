# FlowForge Ostium Service

Internal Python microservice for Ostium integration. This service is called by `flowforge-backend` over HMAC-signed requests and encapsulates all Ostium SDK interactions.

## Status

Initial implementation in progress.

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 5002
```

## Endpoints

- `GET /health` (no auth)
- `GET /ready` (no auth)
- `POST /v1/markets/list` (HMAC)
- `POST /v1/prices/get` (HMAC)
- `POST /v1/accounts/balance` (HMAC)
- `POST /v1/positions/list` (HMAC)
- `POST /v1/positions/open` (HMAC)
- `POST /v1/positions/close` (HMAC)
- `POST /v1/positions/update-sl` (HMAC)
- `POST /v1/positions/update-tp` (HMAC)

## Auth

All `/v1/*` routes require:

- `x-timestamp`
- `x-signature`

Signature payload format:

`{timestamp}:{HTTP_METHOD}:{path}:{raw_body}`

Algorithm: `HMAC-SHA256` with shared `HMAC_SECRET`.
