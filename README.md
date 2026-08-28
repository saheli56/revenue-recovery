# AI Revenue Recovery Engine (Track 03)

An autonomous, closed-loop revenue recovery pipeline built for high-throughput payment failures, checkout drop-offs, and subscription renewal declines.

---

## 1. Problem Statement & Architecture

Modern payment gateways encounter transaction failures across diverse root causes (e.g., technical timeouts, expired cards, low balances, authentication friction, or ambiguous customer support tickets). Manual dunning and blind retry loops cause merchant revenue leakage, customer fatigue, and fraud risks.

The AI Revenue Recovery Engine resolves this with a deterministic 5-stage closed-loop pipeline backed by safety guardrails and append-only audit logging:

```
[ Ingested Transaction / Cart Event ]
                 │
                 ▼
     ┌───────────────────────┐
     │   1. Detector Stage   │  --> Filters out Fraud, Duplicates, and Chargebacks
     └───────────┬───────────┘
                 │ (Qualified Genuine Cases)
                 ▼
     ┌───────────────────────┐
     │   2. Diagnoser Stage  │  --> Deterministic rule mapping + Groq / Gemini Flash LLM fallback
     └───────────┬───────────┘
                 │ (Root Cause & Confidence Score)
                 ▼
     ┌───────────────────────┐
     │  3. Strategist Stage  │  --> Policy Registry selection + Safety Guardrail check
     └───────────┬───────────┘
                 │ (Bounded Action Plan)
                 ▼
     ┌───────────────────────┐
     │   4. Executor Stage   │  --> Razorpay API calls & Simulated Dunning Channels
     └───────────┬───────────┘
                 │ (External Transaction Receipts)
                 ▼
     ┌───────────────────────┐
     │ 5. Outcome & Auditor  │  --> Closed-loop ledger update & Unbroken trace verification
     └───────────────────────┘
```

---

## 2. Pipeline Stages

### Stage 1: Detector
- **Responsibility**: Ingests payment events, cart drop-offs, and subscription failures.
- **Safety**: Automatically evaluates fraud flags, duplicate references, and existing refund requests.
- **Action**: Disqualifies high-risk cases into `stopped_by_policy` / `excluded` before any customer communication or charge attempt occurs.

### Stage 2: Diagnoser
- **Hybrid Architecture**:
  1. *Tier 1 (Deterministic)*: Instantly maps known gateway error codes (`card_expired`, `insufficient_funds`, `issuer_timeout`, `authentication_failed`, `cart_abandoned`) with 1.0 confidence.
  2. *Tier 2 (Groq & Gemini Flash Cascading Fallback)*: When errors are ambiguous or accompanied by Hinglish customer support notes (e.g., *"bhai paise cut gaye par order confirm nahi hua"*), high-throughput inference classifies the root cause into a strictly bounded taxonomy with zero cold start.

### Stage 3: Strategist & Policy Engine
- **Responsibility**: Matches diagnosed root cause against the 12 registered policy rules.
- **Deterministic Action Bounds**: Maps each root cause to permitted intervention strategies (`retry_with_alternative_rail`, `send_payment_link`, `schedule_cooldown_retry`, `escalate_human_ops`).
- **Safety Invariants**:
  - Customer velocity limit: Maximum 3 interventions per 24-hour window per customer.
  - Cooldown period: 48-hour delay enforced for soft declines.
  - Emergency Kill Switch: Instant circuit breaker halting all interventions globally.

### Stage 4: Executor
- **Responsibility**: Dispatches bounded actions via appropriate channels:
  - Razorpay REST API: Orders, Payment Links, Subscriptions.
  - Communication Services: WhatsApp, Email, SMS, Support Desk Escalation.
- **Idempotency**: Generates tracking identifiers (`order_...`, `plink_...`) with independent guardrail verification prior to dispatch.

### Stage 5: Outcome Tracker & Auditor
- **Responsibility**: Reconciles payment capture statuses (`recovered`, `stopped_by_policy`, `failed`, `escalated`).
- **Accounting Metrics**: Calculates gross recovered value, channel infrastructure costs, and net yield.
- **Audit Verification**: Validates 100% unbroken lifecycle traces across the database ledger.

---

## 3. Financial Performance & Metrics (150 Case Batch)

- **Total Ingested Portfolio**: INR 762,357.70 (150 Cases)
- **Gross Recovered Amount**: INR 313,965.04 (40.0% Recovery Rate)
- **Intervention Infrastructure Cost**: INR 545.80 (Nominal carrier & API fees)
- **Net Recovered Value**: INR 313,419.24
- **Cost-Aware Accounting ROI**: 575.2x Net Return per INR 1 spent
- **Guardrail Safety Precision**: 100.0% (Zero false actions on disqualified/fraud cases)
- **Average Resolution Latency**: 4.82 seconds

---

## 4. Tech Stack

- **Backend**: Python 3.11+, FastAPI 0.115, SQLAlchemy 2.0 (Async), Alembic, aiosqlite / asyncpg, Groq & Google Gemini SDKs, Pydantic v2, Pytest.
- **Frontend**: React 19, TypeScript, Vite 8, Tailwind CSS v4, Lucide React, Shadcn-style neutral design system.
- **Infrastructure**: Docker, Docker Compose, Nginx, PostgreSQL.

---

## 5. Quickstart & Local Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- (Optional) Docker & Docker Compose

### Option A: Running with Docker Compose (One Command)
```bash
docker compose up --build
```
- Dashboard UI: `http://localhost:3000`
- API Documentation (Swagger): `http://localhost:8000/docs`

---

### Option B: Running Locally

#### 1. Backend Setup
```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python scripts/init_db.py
python pipeline/run_tracker.py
uvicorn main:app --reload --port 8000
```

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 6. Running Tests & Evaluations

### Run All 23 Automated Integration & Unit Tests
```bash
cd backend
pytest tests/ -v
```

### Run Batch Pipeline Orchestration
```bash
cd backend
python orchestrator/run_batch.py --concurrency 5
```

### Run Evaluation Metrics Engine
```bash
cd backend
python evaluation/run_eval.py
```
Outputs complete metrics breakdown to console and exports structured JSON report to `data/evaluation_report.json`.

---

## 7. API Endpoints Reference

### Case Management
- `POST /api/v1/cases/ingest`: Ingest transaction with optional instant single-case auto-processing.
- `POST /api/v1/cases/batch-run`: Trigger concurrent batch run with bounded worker tasks.
- `GET /api/v1/cases`: Paginated listing with filtering by status, problem type, and search query.
- `GET /api/v1/cases/{case_id}`: Fetch single case details.
- `GET /api/v1/cases/{case_id}/trace`: Fetch complete 5-stage lifecycle decision and audit log trail.

### Performance & Analytics
- `GET /api/v1/analytics/summary`: Aggregate recovery and ROI figures.
- `GET /api/v1/analytics/breakdown`: Detailed breakdown by problem type, root causes, and channel expenses.

### Safety & Guardrails
- `GET /api/v1/policies`: Inspect all 12 policy rules and permitted action bounds.
- `GET /api/v1/guardrails/status`: Check emergency kill switch and velocity limit status.
- `POST /api/v1/guardrails/kill-switch`: Toggle emergency kill switch on/off.
