# FlowForge Ostium Service

Internal Python microservice for Ostium integration. This service is called by `flowforge-backend` over HMAC-signed requests and encapsulates all Ostium SDK interactions.

## Status

**Ready**. Fully modularized with support for 15+ Advanced SDK features (Limit/Stop orders, partial closes, metrics).

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 5002
```

## API Endpoints

### 🩺 Health & System
- `GET /health`: Basic health check.
- `GET /ready`: SDK and configuration readiness.

### 📈 Trading & Positions
- `POST /v1/positions/list`: List open trades.
- `POST /v1/positions/open`: Open Market/Limit/Stop trades.
- `POST /v1/positions/close`: Full or partial trade closure.
- `POST /v1/positions/update-sl`: Update stop-loss price.
- `POST /v1/positions/update-tp`: Update take-profit price.
- `POST /v1/positions/metrics`: Live PnL, fees, and liquidation price.

### 📝 Order Management
- `POST /v1/orders/list`: List pending Limit/Stop orders.
- `POST /v1/orders/cancel`: Cancel a pending order.
- `POST /v1/orders/update`: Modify price/SL/TP of a pending order.
- `POST /v1/orders/track`: Real-time lifecycle tracking of an order.

### 📊 Market Intelligence
- `POST /v1/markets/list`: List available pairs.
- `POST /v1/prices/get`: Fetch bid/mid/ask market prices.
- `POST /v1/markets/funding-rate`: Current funding fees.
- `POST /v1/markets/rollover-rate`: Current rollover fees.
- `POST /v1/markets/details`: Detailed configuration for a market pair.

### 👤 Account & Utilities
- `POST /v1/accounts/balance`: Current USDC/Native balances.
- `POST /v1/accounts/history`: Detailed historical trade data.
- `POST /v1/faucet/request`: Request testnet USDC (Testnet only).

## Auth

All `/v1/*` routes require HMAC-SHA256 authentication headers:

- `x-timestamp`: Epoch milliseconds.
- `x-signature`: HMAC-SHA256 signature.

Signature payload format: `{timestamp}:{HTTP_METHOD}:{path}:{raw_body}`
