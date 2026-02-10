# Momentum Signal Engine — Design Document

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Backend](#3-backend)
4. [Frontend](#4-frontend)
5. [Data Flow](#5-data-flow)
6. [AWS Deployment](#6-aws-deployment)
7. [Notification System](#7-notification-system)
8. [Configuration & Secrets](#8-configuration--secrets)
9. [Cost Estimate](#9-cost-estimate)

---

## 1. Overview

The Momentum Signal Engine (MSE) is a stock trading analysis platform that scans the market for high-probability momentum setups, generates buy/sell signals with risk-managed entries, and delivers real-time alerts via webhook (Discord/Telegram/Slack) and SMS (Twilio/Email Gateway/AWS SNS).

**Key capabilities:**

- Momentum scanning across 160+ liquid US equities and ETFs
- Technical signal generation (5 buy strategies, 4 sell strategies)
- Interactive charting with support/resistance, trendlines, and chart pattern detection
- Walk-forward backtesting engine
- Position sizing and portfolio risk analysis
- Paper trading via Alpaca Markets API
- Multi-channel alert dispatch with new-signal deduplication
- Serverless deployment on AWS (Lambda + S3/CloudFront)

**Tech stack:**

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Pandas, TA-Lib (`ta`) |
| Frontend | Next.js 14 (App Router), React, TanStack Query, TailwindCSS |
| Charting | TradingView Lightweight Charts v5.1 |
| Broker | Alpaca Markets API (paper trading) |
| Infrastructure | AWS Lambda, API Gateway, S3, CloudFront, DynamoDB, EventBridge |
| IaC | AWS SAM (Serverless Application Model) |
| CI/CD | GitHub Actions |

---

## 2. Architecture

### 2.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         CloudFront CDN                           │
│  ┌─────────────────────────────┬────────────────────────────┐    │
│  │   /*  (default)             │   /api/*                   │    │
│  │   ↓                         │   ↓                        │    │
│  │   S3 Bucket                 │   API Gateway (HTTP)       │    │
│  │   (static Next.js export)   │   ↓                        │    │
│  │                             │   Lambda: mse-api           │    │
│  │                             │   (FastAPI + Mangum)        │    │
│  └─────────────────────────────┴────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  EventBridge Rule (every 2 min)                                  │
│  ↓                                                               │
│  Lambda: mse-refresh                                             │
│  (scan market → generate signals → dispatch alerts)              │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  Persistence                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │  DynamoDB     │  │  S3 (cache)  │  │  SSM Parameter Store  │  │
│  │  (config)     │  │  (bars,      │  │  (secrets)            │  │
│  │              │  │   scan,       │  │                       │  │
│  │              │  │   state)      │  │                       │  │
│  └──────────────┘  └──────────────┘  └───────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Local Development Architecture

```
Browser (http://localhost:3000)
  ↓
Next.js dev server (npm run dev)
  ↓ API calls to http://localhost:8000
FastAPI (uvicorn)
  ├── Background refresh thread (every 120s)
  ├── File-based cache (.cache/*.pkl)
  └── File-based config (.notification_config.json)
```

The application runs identically in both modes. The `AWS_LAMBDA` environment variable gates all AWS-specific behavior — when unset, the app uses local file storage, a background thread for scanning, and standard uvicorn serving.

---

## 3. Backend

### 3.1 Module Map

```
src/
├── main.py                  # FastAPI app, lifespan, background refresh
├── lambda_handler.py        # API Lambda entrypoint (Mangum ASGI adapter)
├── refresh_handler.py       # Scheduled Lambda (market scan + alert dispatch)
├── api/
│   └── routes.py            # 30+ REST endpoints
├── data/
│   ├── models.py            # Pydantic data models (Signal, ScanResult, ChartBar, etc.)
│   ├── client.py            # Alpaca Markets data client (bars, quotes, assets)
│   ├── cache.py             # Cache factory + local file-based Cache
│   ├── s3_cache.py          # S3-backed 2-tier cache (Lambda /tmp + S3)
│   └── storage.py           # Notification config persistence (DynamoDB or file)
├── scanner/
│   ├── screener.py          # Universe definition, multi-criteria scan, scoring
│   ├── momentum.py          # Momentum score computation (0–100)
│   └── filters.py           # Price, volume, and sector filters
├── signals/
│   ├── generator.py         # Buy/sell signal generation with confidence scoring
│   ├── indicators.py        # Technical indicators (EMA, RSI, MACD, ATR, VWAP, etc.)
│   ├── patterns.py          # Setup pattern detection
│   ├── support_resistance.py # Support/resistance level detection
│   ├── trendlines.py        # Trendline analysis
│   ├── chart_patterns.py    # Chart pattern recognition
│   └── price_projection.py  # Forward price zone projection
├── backtest/
│   └── engine.py            # Walk-forward backtesting engine
├── risk/
│   ├── position_sizer.py    # Risk-based position sizing
│   └── rr_calculator.py     # Risk/reward ratio grading
├── notifications/
│   └── dispatcher.py        # Webhook + SMS alert dispatch
└── cli/
    └── commands.py          # CLI interface (Typer + Rich)
```

### 3.2 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/scan` | Momentum scanner (top N, with price/volume filters) |
| `GET` | `/scan/{symbol}` | Single-stock momentum analysis |
| `GET` | `/signals` | Buy/sell signals across the full universe |
| `GET` | `/signals/{symbol}` | Signals for a specific stock |
| `GET` | `/chart/{symbol}` | OHLCV + 14 indicators + technical analysis |
| `GET` | `/sectors` | Sector rotation (avg change %, RS, top stock per sector) |
| `GET` | `/breadth` | Market breadth (bullish/bearish counts, EMA21 above %) |
| `GET` | `/correlation` | Correlation matrix for a custom symbol list |
| `GET` | `/backtest` | Walk-forward backtest with equity curve and trade log |
| `GET` | `/risk/position-size` | Position sizing calculator |
| `GET` | `/risk-report` | Portfolio exposure and unrealized P&L |
| `GET` | `/portfolio` | Open positions from Alpaca paper account |
| `POST` | `/trade` | Place a paper market order via Alpaca |
| `POST` | `/webhook/test` | Send a test message to a webhook |
| `POST` | `/webhook/notify` | Send top signals to a webhook on demand |
| `GET` | `/notifications/carriers` | List supported SMS carrier gateways |
| `GET` | `/notifications/config` | Get notification configuration |
| `POST` | `/notifications/config` | Save notification configuration |
| `POST` | `/notifications/test-sms` | Send a test SMS |

### 3.3 Signal Generation

The signal engine runs on 200 days of daily OHLCV bars per symbol. All signals include an entry price, stop-loss, target, risk/reward ratio, and a confidence score (0.0–1.0).

**Buy signals (5 strategies):**

| Strategy | Trigger | Confidence |
|----------|---------|-----------|
| Breakout | Close > 20-day resistance on volume surge (>2x avg) | 0.75 |
| RSI Pullback | RSI 40–50 in bullish EMA stack (price > EMA9 > EMA21 > EMA50) | 0.70 |
| EMA Crossover | EMA9 crosses above EMA21 | 0.65 |
| VWAP Reclaim | Price reclaims VWAP from below | 0.60 |
| Uptrend Momentum | EMAs bullish-stacked, RSI 55–80 | 0.50 |

**Sell signals (4 strategies):**

| Strategy | Trigger |
|----------|---------|
| ATR Trailing Stop | Price below 2x ATR from 20-day high |
| EMA Death Cross | EMA9 crosses below EMA21 |
| RSI Divergence | Price makes new high but RSI doesn't |
| Volume Climax | 3x average volume on a down candle |

**Risk management for each signal:**
- Entry: Current close
- Stop-loss: Entry minus 2x ATR
- Target: Entry plus 4x ATR (default 2:1 R:R)
- Weekly trend confirmation boosts or penalizes confidence by ~0.1

### 3.4 Momentum Scanner

The scanner scores each symbol on a 0–100 composite:

| Criteria | Points | Calculation |
|----------|--------|-------------|
| Relative Strength vs SPY | 0–20 | 3-month price ratio percentile |
| Volume Surge | 0–20 | Current volume / 20-day SMA volume |
| Near 52-Week High | 0–20 | Within 5–15% of 52-week max close |
| EMA Alignment | 0–20 | Price > EMA9 > EMA21 > EMA50 |
| Breakout Detection | 0–20 | Close above 20-day consolidation on volume |

The default universe contains 160+ symbols across 16 sectors (mega-cap tech, semis, software, fintech, cloud/cyber, consumer, energy, healthcare, financials, industrials, telecom, utilities, materials, crypto, ETFs).

### 3.5 Backtesting Engine

Walk-forward simulation starting from bar 50 (indicator warmup):

1. On each bar, generate signals using the full signal engine
2. Take the highest-confidence BUY when no position is open
3. Exit on: stop-loss hit, target hit, or ATR trailing stop triggered
4. Track equity curve, max drawdown, and a per-trade log
5. Returns: total return, win rate, avg R:R, max drawdown, Sharpe-like metrics

### 3.6 Caching Strategy

| Data | Local | Lambda |
|------|-------|--------|
| Bar data (OHLCV) | `.cache/*.pkl` (15 min TTL) | Lambda `/tmp` + S3 (15 min TTL) |
| Scan results | In-memory dict (120s TTL) | S3 `cache/` prefix (120s TTL) |
| Notification config | `.notification_config.json` | DynamoDB table |
| Seen signal keys | In-memory set | S3 `state/seen_signal_keys.pkl` |

The S3 cache uses a 2-tier strategy: Lambda `/tmp` provides fast local access (warm start), and S3 provides durability across cold starts.

---

## 4. Frontend

### 4.1 Technology

- **Framework:** Next.js 14 (App Router), exported as a fully static SPA (`output: "export"`)
- **State management:** TanStack Query (React Query) for all server data
- **Charting:** TradingView Lightweight Charts v5.1 (candlestick, line, histogram series)
- **Styling:** TailwindCSS with a dark zinc/slate theme
- **UI library:** shadcn/ui (Button, Card, Input, Switch, Table, Skeleton, etc.)
- **Icons:** Lucide React

### 4.2 Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Home | Client-side redirect to `/scanner` |
| `/scanner` | Scanner | Momentum scanner table with 5 filter presets, auto-refresh |
| `/chart/[symbol]` | Chart | Full candlestick chart with EMA overlays, RSI, volume, S/R, trendlines, patterns, projections |
| `/signals-history` | Signals History | Historical signal log |
| `/alerts` | Alerts | Price alert manager (localStorage-backed) |
| `/watchlist` | Watchlist | Custom symbol watchlist (localStorage-backed) |
| `/backtest` | Backtest | Strategy backtester with interactive equity curve (Recharts) |
| `/portfolio` | Portfolio | Alpaca paper account positions, equity, unrealized P&L |
| `/risk-report` | Risk Report | Portfolio exposure breakdown, position-level risk |
| `/position-sizer` | Position Sizer | Calculator: account size, risk %, entry, stop → shares to buy |
| `/sectors` | Sectors | Sector rotation table (avg change %, RS, count, top stock) |
| `/heatmap` | Heatmap | Visual sector/symbol performance heatmap |
| `/correlation` | Correlation | Interactive correlation matrix for custom symbols |
| `/performance` | Performance | Portfolio performance metrics |
| `/notifications` | Notifications | Configure webhooks, SMS, auto-alerts, min confidence |
| `/earnings` | Earnings | Earnings calendar |
| `/guide` | Guide | User guide and documentation |

### 4.3 Key Components

**Chart system:**
- `CandlestickChart` — Core chart component using Lightweight Charts. Renders OHLCV candles, EMA overlays, VWAP, RS vs SPY, support/resistance zones, trendlines with projections, chart patterns with targets, price projection zones, and BUY/SELL signal markers. Includes crosshair-move tooltip for pattern hover.
- `RSIPanel` — RSI subplot with 30/70 reference lines
- `VolumePanel` — Volume histogram with 20-day SMA overlay
- `ChartToolbar` — Toggle controls for indicators and analysis layers
- `StockInfoHeader` — Symbol name, current price, change %, momentum score, active signals
- `TechnicalAnalysisPanel` — Expandable panel for support/resistance levels, trendlines, detected patterns, and price projections

**Scanner:**
- `ScannerTable` — Sortable, filterable results table
- `ScannerToolbar` — Preset filters (Large Caps, High Volume, Penny Movers, Near Highs, ETFs), manual refresh, auto-refresh toggle
- `BreadthWidget` — Market breadth gauge (bullish/bearish/neutral %)
- `ScoreBadge` — Color-coded 0–100 momentum score
- `SetupTypeBadge` — Setup type display (breakout, flag, pullback, etc.)

### 4.4 Custom Hooks

| Hook | Source | Refresh |
|------|--------|---------|
| `useScan(params)` | `GET /scan` | 30s auto-refetch |
| `useScanSymbol(symbol)` | `GET /scan/{symbol}` | On mount |
| `useChartData(symbol, days)` | `GET /chart/{symbol}` | On param change |
| `useBacktest(params)` | `GET /backtest` | On trigger |
| `useBreadth()` | `GET /breadth` | 60s auto-refetch |
| `useWatchlist()` | localStorage | — |
| `usePriceAlerts()` | localStorage | — |
| `usePositionSize()` | `GET /risk/position-size` | On input change |

### 4.5 API Client

```typescript
// frontend/src/lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function apiFetch<T>(path: string, params?): Promise<T> {
  const fullPath = API_BASE ? `${API_BASE}${path}` : `/api${path}`;
  // ...
}
```

- When `NEXT_PUBLIC_API_URL` is set (local dev, Render): calls that URL directly (e.g., `http://localhost:8000/scan`)
- When empty (CloudFront deploy): uses relative `/api/scan`, which CloudFront routes to API Gateway

### 4.6 Static Export

The frontend is exported as a fully static SPA via `next build` with `output: "export"`. This produces an `out/` directory with:
- 173 pre-rendered HTML pages (17 routes + 153 chart symbol pages)
- JS/CSS bundles with content-hashed filenames
- CloudFront's custom error response (403/404 → `/index.html`) handles SPA client-side routing for unlisted symbols

---

## 5. Data Flow

### 5.1 Request Flow (User Views Scanner)

```
Browser → CloudFront → S3 (scanner/index.html)
  ↓ (React mounts, TanStack Query fires)
Browser → CloudFront → API Gateway → Lambda (mse-api)
  ↓
FastAPI /api/scan endpoint
  ↓
Check in-memory/S3 cache (120s TTL)
  → Cache hit: return cached results
  → Cache miss:
      ├── Alpaca API: get_multi_bars() for 160+ symbols (200 days)
      ├── For each symbol: compute momentum score (RS, volume, EMA, breakout)
      ├── Filter by price/volume, sort by score, take top N
      ├── Parallel enrichment: generate_signals() + detect_patterns()
      └── Cache results, return JSON
```

### 5.2 Alert Dispatch Flow (Background Refresh)

```
EventBridge (every 2 min) → Lambda (mse-refresh)
  ↓
1. Load seen_signal_keys from S3
2. Fetch bars: Alpaca API → S3 cache
3. Run scan: filter + score + rank
4. Enrich: signals + patterns (8 threads)
5. Collect all signals, compute keys (symbol:action:entry)
6. Compare with seen set → identify NEW signals
7. If new signals exist:
   ├── Filter by min_confidence (from config)
   ├── Send webhook (Discord/Telegram/Slack)
   └── Send SMS (Twilio / Email Gateway / AWS SNS)
8. Save current keys to S3
```

### 5.3 Signal Deduplication

Each signal has a key: `{symbol}:{action}:{entry_price:.2f}` (e.g., `AAPL:BUY:189.50`).

- **First invocation:** All signals treated as new, dispatched, keys saved to S3.
- **Subsequent invocations:** Only signals with keys NOT in the saved set are dispatched. The full current key set replaces the old one each cycle.
- This means alerts fire when a new signal appears or when an existing signal's entry price changes significantly.

---

## 6. AWS Deployment

### 6.1 Infrastructure (SAM Template)

The entire stack is defined in `infra/template.yaml` using AWS SAM:

| Resource | Type | Purpose |
|----------|------|---------|
| `ConfigTable` | DynamoDB | Notification config persistence (PAY_PER_REQUEST) |
| `CacheBucket` | S3 | Market data cache + seen-signal state (1-day expiry) |
| `FrontendBucket` | S3 | Static frontend files (HTML, JS, CSS) |
| `ApiFunction` | Lambda (container) | FastAPI API handler (1024 MB, 120s timeout) |
| `RefreshFunction` | Lambda (container) | Scheduled market scan (2048 MB, 300s timeout, concurrency=1) |
| `HttpApi` | API Gateway (HTTP) | Routes `/api/*` to ApiFunction |
| `CDN` | CloudFront | Serves frontend (S3) and API (Gateway) from single domain |
| `OAC` | CloudFront OAC | Secure S3 access (no public bucket) |

**Why container images:** The Python dependency stack (pandas, numpy, ta-lib, alpaca-py, boto3, fastapi) exceeds Lambda's 250 MB zip limit. Container images support up to 10 GB.

**Single Dockerfile, two functions:** Both Lambda functions share the same Docker image. The `CMD` is overridden per function in the SAM template:
- `ApiFunction`: `src.lambda_handler.handler`
- `RefreshFunction`: `src.refresh_handler.handler`

### 6.2 CloudFront Configuration

CloudFront serves as a unified entry point with two origins:

```
CloudFront Distribution
├── Default behavior: /* → S3 (frontend)
│   ├── Cache policy: CachingOptimized (24h TTL, gzip)
│   └── Error pages: 403/404 → /index.html (SPA fallback)
│
└── Path pattern: /api/* → API Gateway (backend)
    ├── Cache policy: CachingDisabled (real-time)
    ├── Origin request: AllViewerExceptHostHeader
    └── Allowed methods: GET, HEAD, OPTIONS, PUT, PATCH, POST, DELETE
```

This means:
- `https://d1234.cloudfront.net/scanner` → S3 → `scanner/index.html`
- `https://d1234.cloudfront.net/api/scan` → API Gateway → Lambda
- No CORS issues (same domain for frontend and API)

### 6.3 Secrets Management

Secrets are stored in AWS SSM Parameter Store (free tier) and injected into Lambda environment variables via CloudFormation parameter references:

| Parameter | SSM Path |
|-----------|----------|
| Alpaca API Key | `/mse/ALPACA_API_KEY` |
| Alpaca Secret Key | `/mse/ALPACA_SECRET_KEY` |
| SMTP Email | `/mse/SMTP_EMAIL` |
| SMTP Password | `/mse/SMTP_PASSWORD` |

SSM Parameter Store is free for standard parameters. Secrets Manager ($0.40/secret/month) is not needed.

### 6.4 Deployment Pipeline (GitHub Actions)

```
Push to main
  ↓
Job 1: deploy-backend
  ├── Configure AWS credentials (OIDC role assumption)
  ├── sam build (Docker image)
  ├── sam deploy (CloudFormation changeset)
  └── Output: frontend bucket name, CloudFront distribution ID
  ↓
Job 2: deploy-frontend (depends on Job 1)
  ├── npm ci && npm run build (static export)
  ├── aws s3 sync out/ → frontend bucket
  │   ├── *.html: Cache-Control: no-cache (always fresh)
  │   └── *.js/*.css: Cache-Control: immutable, max-age=31536000
  └── aws cloudfront create-invalidation --paths "/*"
```

### 6.5 Deployment Commands (Manual)

```bash
# 1. Store secrets in SSM
aws ssm put-parameter --name /mse/ALPACA_API_KEY --value "PK..." --type SecureString
aws ssm put-parameter --name /mse/ALPACA_SECRET_KEY --value "SK..." --type SecureString
aws ssm put-parameter --name /mse/SMTP_EMAIL --value "you@gmail.com" --type SecureString
aws ssm put-parameter --name /mse/SMTP_PASSWORD --value "xxxx xxxx" --type SecureString

# 2. Deploy backend
cd infra && sam build && sam deploy

# 3. Deploy frontend
cd frontend && npm run build
aws s3 sync out/ s3://mse-frontend-prod-123456789012/ --delete

# 4. Invalidate CloudFront
aws cloudfront create-invalidation --distribution-id E1234 --paths "/*"
```

---

## 7. Notification System

### 7.1 Channels

| Channel | Method | Cost | Config Required |
|---------|--------|------|-----------------|
| Discord | Webhook POST (embed) | Free | Webhook URL |
| Telegram | Bot API POST (markdown) | Free | Bot token + chat ID |
| Slack | Webhook POST (text) | Free | Webhook URL |
| Email-to-SMS | SMTP → carrier gateway | Free | Gmail app password + carrier |
| Twilio SMS | REST API | ~$0.0079/msg | Account SID, auth token, from number |
| AWS SNS SMS | AWS SDK | ~$0.00645/msg | AWS credentials (auto on Lambda) |

### 7.2 SMS Carrier Gateways (Free)

Email-to-SMS sends an email to `{phone}@{gateway}` which the carrier delivers as a text message:

| Carrier | Gateway |
|---------|---------|
| AT&T | txt.att.net |
| T-Mobile | tmomail.net |
| Verizon | vtext.com |
| Sprint | messaging.sprintpcs.com |
| Boost Mobile | sms.myboostmobile.com |
| Cricket | sms.cricketwireless.net |
| Metro by T-Mobile | mymetropcs.com |
| US Cellular | email.uscc.net |
| Virgin Mobile | vmobl.com |
| Google Fi | msg.fi.google.com |
| Mint Mobile | tmomail.net |
| Visible | vtext.com |
| Xfinity Mobile | vtext.com |

**Limitations:** 160-character message cap, carrier rate-limiting on rapid sends. The system formats a single compact message per dispatch cycle with top signals that fit.

### 7.3 SMS Consent

TCPA-compliant opt-in is required before SMS sending:
- User must check a consent checkbox in the UI
- Consent timestamp is recorded (ISO 8601)
- Backend blocks SMS dispatch if `sms_consent` is false
- Consent status persists in DynamoDB (Lambda) or local config file

### 7.4 Notification Config (Persisted)

```json
{
  "webhook_url": "https://discord.com/api/webhooks/...",
  "webhook_platform": "discord",
  "sms_to": "+15559876543",
  "sms_method": "email_gateway",
  "sms_carrier": "tmobile",
  "sms_consent": true,
  "sms_consent_timestamp": "2025-01-15T10:30:00+00:00",
  "auto_alerts_enabled": true,
  "min_confidence": 0.6
}
```

---

## 8. Configuration & Secrets

### 8.1 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ALPACA_API_KEY` | Alpaca Markets API key | Yes |
| `ALPACA_SECRET_KEY` | Alpaca Markets secret key | Yes |
| `ALPACA_BASE_URL` | Alpaca base URL (paper/live) | No (default: paper) |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | No |
| `SMTP_EMAIL` | Gmail address for email-to-SMS | For email SMS |
| `SMTP_PASSWORD` | Gmail app password | For email SMS |
| `TWILIO_ACCOUNT_SID` | Twilio account SID | For Twilio SMS |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | For Twilio SMS |
| `TWILIO_FROM_NUMBER` | Twilio phone number | For Twilio SMS |
| `AWS_LAMBDA` | Set to `1` on Lambda (auto by SAM template) | Auto |
| `AWS_REGION` | AWS region | No (default: us-east-1) |
| `CACHE_BUCKET` | S3 bucket for cache | Lambda only |
| `CONFIG_TABLE` | DynamoDB table name | Lambda only |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend | Local dev only |

### 8.2 Local Development

```bash
# Backend
cp .env.example .env  # Fill in Alpaca keys
pip install -r requirements.txt
uvicorn src.main:app --reload

# Frontend
cd frontend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm install && npm run dev
```

---

## 9. Cost Estimate

### AWS Monthly Cost (Typical Usage)

| Service | Usage | Est. Cost |
|---------|-------|-----------|
| Lambda (API) | ~50K requests/mo, 128ms avg | ~$0.50 |
| Lambda (Refresh) | 720 invocations/mo (every 2 min), 10s avg | ~$0.30 |
| API Gateway | ~50K requests/mo | ~$0.05 |
| DynamoDB | <1K reads/writes per month | Free tier |
| S3 (cache) | ~100 MB storage, ~50K requests | ~$0.10 |
| S3 (frontend) | ~50 MB static files | ~$0.01 |
| CloudFront | ~5 GB transfer/mo | ~$0.50 |
| EventBridge | 720 invocations/mo | Free |
| SSM Parameter Store | 4 standard parameters | Free |
| **Total** | | **~$1–6/mo** |

Most services fall within AWS Free Tier for the first 12 months. After free tier: ~$2–6/month depending on traffic.
