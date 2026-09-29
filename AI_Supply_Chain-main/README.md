# AI-Powered Supply Chain Risk Intelligence Assistant

A production-grade, full-stack intelligence and decision-support platform designed to monitor, forecast, and mitigate supply chain disruptions using **Hybrid Supply Chain RAG (Structured Analytics + Semantic Vector Knowledge)**, **Pre-Retrieval Role-Based Access Control (RBAC)**, **Supplier Data Isolation**, **Deterministic Fallback Mechanisms**, and a **Real-Time 8-Dimension Evaluation & Observability Engine**.

---

## 1. System Architecture

```text
                     User Query / API Request
                                ↓
       JWT Authentication + Role & Scope Resolution
                 (ADMIN | SUPPLY_CHAIN_MANAGER | SUPPLIER)
                                ↓
               Semantic Query Planner & Classifier
                                ↓
          RBAC Pre-Retrieval Validation & Scope Filter
       (Supplier Isolation: Unauthorized evidence blocked BEFORE retrieval)
                                ↓
                   Hybrid Supply Chain Retrieval
         ┌──────────────────────┴──────────────────────┐
         ↓                                             ↓
  Structured Analytics                          Semantic RAG
 (SQL / Pandas / Transactions)        (Vector Documents: 2,000 Products,
                                              150 Suppliers)
         └──────────────────────┬──────────────────────┘
                                ↓
                  Authorized Evidence Assembly
                                ↓
                 LLM Synthesis / Explanation
                                ↓
           Deterministic Fallback & Policy Verification
                                ↓
            Persistent Audit Trail & Live Observability
```

---

## 2. Core Implementation Phases

### Phase 1 — Authentication, JWT & RBAC
- Stateless JWT bearer token authentication with cryptographically hashed passwords (`bcrypt`).
- Role-based access control protecting operational endpoints and internal resources.
- Roles supported: `ADMIN`, `SUPPLY_CHAIN_MANAGER`, and `SUPPLIER` (scoped to a specific `supplier_id`).

### Phase 2 — Transactional Workflow & Business Operations
- Complete supplier offer lifecycle: **Submit → Edit → Withdraw → Accept → Reject**.
- Transactional integrity with atomic rollbacks: accepting an offer automatically creates a corresponding Purchase Order and updates product inventory within a single atomic database transaction.

### Phase 3 — Role-Based React Frontend
- Dynamic role-aware navigation and route guards.
- Admin views: User Administration, System Evaluation, Global Audit, Platform Settings.
- Manager views: Supply chain operations, Product Catalog, Inventory, Purchase Orders, Risk Intelligence.
- Supplier views: Strictly isolated "My Dashboard", "My Products", "My Orders", "My Offers", and "My Performance".

### Phase 4 — Secure AI Query + Pre-Retrieval RBAC
- Query Planner and Query Classifier classify user intent, target domain, and entity IDs.
- **Pre-Retrieval RBAC**: Access authorization is verified *before* evidence retrieval.
- Unauthorized cross-supplier queries immediately return `status = "denied"` with **0 evidence count**, ensuring unauthorized data never reaches the LLM context window.

### Phase 5 — Hybrid Supply Chain RAG
- **Structured Retrieval**: Fast, deterministic analytics over operational databases (inventory days of cover, demand pressure, supplier late rates, 3PL delivery delays).
- **Semantic Retrieval**: Vector retrieval over 2,000 product knowledge documents and 150 supplier relationship profiles.
- **Hybrid Retrieval**: Combines structured analytical evidence with semantic profiles for comprehensive risk summaries.
- **Deterministic Fallback**: If vector embeddings or external LLM APIs are unavailable, the assistant falls back to safe, grounded deterministic analytics.

### Phase 6 — Evaluation & Observability
- Built-in evaluation framework measuring **8 Dimensions**:
  1. Planner Correctness
  2. Retrieval Mode Correctness (`structured`, `semantic`, `hybrid`)
  3. Evidence Grounding Score
  4. Answer Relevance Score
  5. RBAC Enforcement Correctness (Allowed vs. Denied)
  6. Fallback Correctness
  7. Execution Latency (Total, Planning, Retrieval, LLM)
  8. Audit Completeness
- Automated execution across a 12-benchmark query suite.
- Summary KPI dashboard with Recharts retrieval distribution charts and full audit trail inspection.
- Automatic zero-division handling and credential scrubbing (passwords, JWTs, and API keys are redacted).

### Phase 7 — Unified Risk Intelligence & User Experience
- Unified tab navigation across all 4 analytical risk dimensions: **Supplier Risk**, **Inventory Risk**, **Delivery Risk**, and **Route Risk**.
- Observable `retrieval_mode` badges (`STRUCTURED`, `SEMANTIC`, `HYBRID`) rendered directly in the conversational AI assistant.

---

## 3. Role Matrix & Security Scopes

| Role | Analytics & Dashboards | Offers & Orders | AI Query Scope | Evaluation & Audit |
|---|---|---|---|---|
| **ADMIN** | Full global access (All suppliers, products, routes, 3PLs) | Full access; approve/reject offers; edit orders | Global query access across all domains | View & trigger evaluations; inspect audit trail |
| **SUPPLY_CHAIN_MANAGER** | Full global access (All suppliers, products, routes, 3PLs) | Full access; approve/reject offers; manage orders | Global query access across all domains | View dashboard KPIs; no user administration |
| **SUPPLIER** | Scoped strictly to assigned `supplier_id` (e.g. `S0001`) | Manage own offers; view own purchase orders | Strictly scoped to own products, orders, and metrics | No access (isolated) |
  
---

## 4. API Endpoints Reference

### Authentication & Users
- `POST /api/auth/login` — Authenticate and receive JWT token.
- `GET /api/auth/me` — Retrieve current authenticated user profile.
- `GET /api/users` — List platform users (Admin only).
- `POST /api/users` — Create user account (Admin only).

### Transactional Operations
- `GET /api/offers` — List supplier offers (filtered by role and supplier scope).
- `POST /api/offers` — Create a new supplier offer.
- `PUT /api/offers/{id}` — Edit an offer.
- `POST /api/offers/{id}/accept` — Accept offer (triggers atomic order creation & inventory update).
- `POST /api/offers/{id}/reject` — Reject offer.
- `POST /api/offers/{id}/withdraw` — Withdraw offer (Supplier).
- `GET /api/orders` — List purchase orders.
- `GET /api/products` — Product catalog.
- `GET /api/inventory` — Warehouse inventory levels.

### Analytics & Forecasting
- `GET /api/analytics/dashboard` — Executive control tower KPIs.
- `GET /api/analytics/supplier-risk` — Supplier reliability scores & late rates.
- `GET /api/analytics/inventory-risk` — Stockout probability, days of cover, demand pressure.
- `GET /api/analytics/delivery-risk` — 3PL delivery delays and logistics performance.
- `GET /api/analytics/route-risk` — Transit corridor risk and route bottlenecks.
- `GET /api/analytics/anomalies/orders` — Statistical anomaly detection (IQR/Z-score).
- `GET /api/forecast/products` — Forecastable product inventory list.
- `GET /api/forecast/predict/{product_id}` — Demand projection and trend modeling.

### AI Assistant & Evaluation
- `POST /api/query` — Role-scoped Hybrid RAG query execution.
- `GET /api/evaluation/summary` — Aggregate Phase 6 evaluation KPIs.
- `GET /api/evaluation/results` — Granular evaluation benchmark records.
- `POST /api/evaluation/run` — Trigger live benchmark evaluation suite.
- `GET /api/audit/recent` — Recent system audit traces.

---

## 5. Local Setup & Quickstart

### Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Node.js 18+ and npm

### 1. Backend Setup
```powershell
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API and Swagger documentation will be available at:
`http://127.0.0.1:8000/docs`

### 2. Frontend Setup
```powershell
# Navigate to frontend directory
cd frontend

# Install npm dependencies
npm install

# Start development server
npm run dev
```
The React frontend application will be available at:
`http://localhost:5173`

### 3. Production Frontend Build
```powershell
cd frontend
npm run build
```

---

## 6. Demo User Credentials

| Username | Password | Role | Assigned Supplier | Access Description |
|---|---|---|---|---|
| `admin` | `admin123` | `ADMIN` | None | Full administrative and evaluation access |
| `manager` | `manager123` | `SUPPLY_CHAIN_MANAGER` | None | Supply chain operations and risk intelligence |
| `supplier_s001` | `supplier123` | `SUPPLIER` | `S0001` | Scoped strictly to supplier S0001 |

---

## 7. Automated Test Suite

The test suite runs with deterministic mocks and does **not** require external API keys.

To run the complete 66-test regression suite:
```powershell
cd backend
python -m pytest tests/test_rag.py tests/test_query_rbac.py tests/test_auth_rbac.py tests/test_phase2_transactional.py tests/test_api.py tests/test_evaluation.py -v
```

### Test Suite Breakdown
- `tests/test_rag.py` (12 tests): Hybrid RAG retrieval, vector search, supplier scoping, deterministic fallback.
- `tests/test_query_rbac.py` (12 tests): Pre-retrieval authorization, role scoping, zero evidence leakage on denial.
- `tests/test_auth_rbac.py` (2 tests): JWT authentication, token decoding, password verification.
- `tests/test_phase2_transactional.py` (9 tests): Offer lifecycle, atomic PO creation, rollback on failure.
- `tests/test_api.py` (13 tests): Operational REST endpoints, products, orders, inventory.
- `tests/test_evaluation.py` (18 tests): All 8 evaluation dimensions, 12 benchmark cases, summary KPIs, zero-division safety, credential scrubbing.

**Result: 66 passed, 0 failed (100% green).**
