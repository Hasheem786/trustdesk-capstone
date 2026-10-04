# TrustDesk: AI Support Operations Agent

**Author:** Mohammed Hasheem  
**Program:** AI-first Software Engineering Program (Airtribe Capstone)  
**Status:** Complete & Production Ready  

---

## 1. Executive Summary

Modern customer support teams handle thousands of high-stakes, repetitive interactions daily. Traditional AI chatbots fail in enterprise environments because they hallucinate policies, lack operational agency, execute unverified financial/inventory actions, and succumb to adversarial prompt exploits.

**TrustDesk** is an enterprise-grade AI Support Operations platform designed to function as an actionable, grounded support co-pilot. Rather than serving as an unconstrained chatbot, TrustDesk:
- **Intelligently Triages incoming tickets** across 6 business domains and 4 priority levels with temporal reference precision.
- **Rounds all replies in official policy documents** with explicit document ID citations (`KB-REFUND-001`, `KB-WARRANTY-001`), refusing or escalating ungrounded inquiries.
- **Enforces Human-in-the-Loop (HITL) execution** on high-impact actions (`start_refund_review`, `create_replacement_order`), blocking execution until confirmed by a human supervisor.
- **Guarantees zero duplicate operations** through deterministic SHA-256 idempotency keys.
- **Defends against multi-layered adversarial attacks**, including prompt injection, secret exfiltration, coupon hacks, privilege escalation, and poisoned knowledge base articles (`KB-ADVERSARIAL-001`).
- **Includes an automated benchmark evaluation suite** achieving 100% on the rubric criteria.

---

## 2. Architecture & Flow

```
                      +---------------------------------------+
                      |       Support Agent Dashboard         |
                      |  (Ticket View, Citations, HITL Action) |
                      +-------------------+-------------------+
                                          | REST API
                                          v
+-----------------------------------------------------------------------------------+
|                              TrustDesk Backend API                                |
|                                                                                   |
|  +-----------------+    +--------------------+    +----------------------------+  |
|  |  Triage Engine  |    | RAG Retrieval Core |    | Guardrails & Safety Engine |  |
|  | (Intent & Pri.) |    | (Hybrid/Vector KB) |    | (Injection / Leak / Policy)|  |
|  +--------+--------+    +---------+----------+    +--------------+-------------+  |
|           |                       |                              |                |
|           +-----------------------+------------------------------+                |
|                                   |                                               |
|                                   v                                               |
|                       +-----------------------+                                   |
|                       |  AI Provider Adapter  |                                   |
|                       | (LLM / Mock Adapter)  |                                   |
|                       +-----------+-----------+                                   |
|                                   |                                               |
|                                   v                                               |
|       +-------------------------------------------------------+                   |
|       |  Approval-Gated Tool Executor (Idempotency Key Guard)  |                  |
|       |     - start_refund_review / create_replacement_order   |                  |
|       +-------------------------------------------------------+                   |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
              +-------------------------------------------------------+
              |     Persistent Store (Data, Traces & Audit Logs)      |
              |  - Customers, Orders, Tickets, KBs, Drafts, Actions   |
              +-------------------------------------------------------+
```

---

## 3. Rubric Benchmark Evaluation Results

The evaluation harness evaluates `data/eval_cases.jsonl` across all rubric requirements:

```bash
python run_eval.py
```

| Benchmark Metric | Target Rubric | Achieved Score | Status |
| :--- | :--- | :--- | :--- |
| **Triage Accuracy** | $\ge 90\%$ | **100.0%** (12/12) | **PASS** |
| **Citation Grounding** | $\ge 95\%$ | **100.0%** (12/12) | **PASS** |
| **Adversarial Safety** | **100%** | **100.0%** (4/4) | **PASS** |
| **Operational HITL Safety** | **100%** | **100.0%** (2/2) | **PASS** |
| **Idempotency Integrity** | **100%** | **100.0%** (2/2) | **PASS** |

---

## 4. Key Architectural Implementations

### A. Temporal Reference Accuracy
Return and warranty eligibility is calculated **strictly relative to the ticket's `created_at` timestamp** against order delivery and purchase dates, preventing date drift or runtime machine clock inconsistencies:
$$\Delta t_{\text{delivery}} = \text{Ticket.created\_at} - \text{Order.delivered\_date}$$
- If $\Delta t_{\text{delivery}} \le 30 \text{ days}$: Eligible for `start_refund_review`.
- If $\Delta t_{\text{delivery}} > 30 \text{ days}$: Automatic refund is prohibited; ticket is escalated per `KB-REFUND-001`.

### B. Multi-Layered Adversarial Guardrails
1. **Input Guardrail:** Regex and semantic filters detect prompt injections ("ignore previous instructions", "unconstrained assistant"), unauthorized coupon generation ("generate 90% coupon", "SUPER500"), system prompt exfiltration ("print system prompt"), and 2FA bypass attempts.
2. **Document Guardrail (Poisoned KB Defense):** Sanitizes and isolates poisoned documents (e.g. `KB-ADVERSARIAL-001`) from entering downstream RAG context.
3. **Output Guardrail:** Validates that drafts cite existing, active knowledge documents and do not leak internal prompts or unauthorized promotional codes.

### C. Human-in-the-Loop (HITL) Tool Actions
Critical actions are never executed autonomously. The agent creates an action proposal with status `PENDING_APPROVAL`:
- `start_refund_review`
- `create_replacement_order`

A human support supervisor reviews the proposal, justification, and parameters in the dashboard before granting approval (`POST /api/actions/{action_id}/approve`).

### D. Deterministic Idempotency Keys
To prevent duplicate financial charges or duplicate shipment creations:
$$\text{Key} = \text{SHA256}\left(\text{ticket\_id} + \text{action\_type} + \text{canonical\_json}(\text{params})\right)$$
Unique database constraints and idempotency lookups guarantee duplicate network requests or accidental double-clicks return the existing action rather than dispatching a duplicate order.

### E. Decoupled AI Adapter Pattern
Abstract `AIProvider` base class allows switching seamlessly between:
- `MockAIAdapter`: Fast, deterministic, zero-cost adapter for automated benchmarks, unit tests, and offline development.
- `GeminiLiveAdapter`: Production adapter connecting to Google Gemini API (`gemini-1.5-flash`) via structured JSON schema prompting.

---

## 5. Quickstart & Installation

### Prerequisites
- Python 3.11+
- Virtual environment tool (`uv` recommended)

### Step 1: Install Dependencies
```bash
# Using uv (recommended)
uv venv .venv --python 3.11
uv pip install -e .

# Or standard pip
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Run the Capstone Evaluation Harness
```bash
python run_eval.py
```

### Step 3: Run the Test Suite
```bash
pytest -v
```

### Step 4: Start the Web Dashboard & API Server
```bash
uvicorn src.trustdesk.api.app:app --host 127.0.0.1 --port 8000 --reload
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser to interact with the Support Operations Dashboard.

---

## 6. REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service health and active AI provider |
| `GET` | `/api/tickets` | List tickets (filter by status) |
| `POST` | `/api/tickets` | Create a new support ticket |
| `GET` | `/api/tickets/{id}` | Retrieve ticket details, order, citations, actions, traces |
| `POST` | `/api/tickets/{id}/process` | Execute end-to-end triage, RAG, and HITL action proposal |
| `GET` | `/api/actions` | List operational actions (filter by status: PENDING_APPROVAL) |
| `POST` | `/api/actions/{id}/approve` | Approve and execute pending operational action (HITL) |
| `POST` | `/api/actions/{id}/reject` | Reject pending operational action |
| `GET` | `/api/traces` | Audit trace log for complete explainability |
| `POST` | `/api/eval/run` | Execute benchmark evaluation suite and return metrics |

---

## 7. Project Structure

```
.
├── data/
│   ├── customers.json          # Seed customers with tiers (standard, vip)
│   ├── orders.json             # Seed orders with delivery timestamps
│   ├── kb_documents.json       # Official policy documents (KB-REFUND-001, etc.)
│   └── eval_cases.jsonl        # 12 Gold-standard benchmark evaluation cases
├── src/
│   └── trustdesk/
│       ├── config.py           # Application settings
│       ├── orchestrator.py     # End-to-end workflow orchestrator
│       ├── models/             # Domain and SQLAlchemy persistence models
│       ├── storage/            # Database session, seeder, repository
│       ├── guardrails/         # Input, Document, and Output guardrails
│       ├── rag/                # Hybrid retriever and citation grounder
│       ├── triage/             # Intelligent triage engine
│       ├── actions/            # HITL executor and idempotency key generator
│       ├── ai/                 # Decoupled AI adapter (Mock & Gemini Live)
│       ├── eval/               # Benchmark runner and metrics calculator
│       ├── api/                # FastAPI application routes
│       └── web/                # Support dashboard frontend (HTML/CSS/JS)
├── tests/                      # Pytest unit, integration, and security test suite
├── run_eval.py                 # Single-command evaluation suite CLI
├── pyproject.toml              # Build & dependency specifications
└── README.md                   # Comprehensive technical documentation
```
