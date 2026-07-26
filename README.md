# AI-Powered AML Agent

An end-to-end Anti-Money Laundering (AML) detection system combining Hybrid ML, an agentic backend, and a ChatGPT-style investigation assistant.

---

## Project Overview

This system detects money laundering patterns in financial transactions using a **Hybrid ML Engine** (XGBoost + Isolation Forest) and exposes results through an **AI agent** powered by Groq LLaMA 3.3 70B.

The agent understands natural language queries, routes them to the correct analytical tool, and returns concise, grounded investigation reports.

---

## Architecture

```
User Query
    │
    ▼
Planner (intent classification + entity extraction)
    │
    ▼
Router (dynamic tool chaining + dependency resolution)
    │
    ├── analytics_tool        → group-by analysis (bank/currency/format)
    ├── investigation_tool    → customer / transaction / bank deep-dive
    ├── pattern_detection_tool→ structuring, rapid, cross-bank, anomaly
    ├── comparison_tool       → side-by-side entity comparison
    ├── knowledge_tool        → AML system knowledge base
    ├── customer_summary      → O(1) indexed customer lookup
    ├── transaction_summary   → single transaction with ML scores
    ├── top_suspicious_transactions → pre-ranked by hybrid score
    ├── run_eda               → cached dataset statistics
    ├── generate_risk         → hybrid ML scoring
    ├── generate_explanation  → feature-flag reasons
    └── rule_engine           → deterministic AML rules
         │
         ▼
    Hybrid ML Engine
    (XGBoost 85% + Isolation Forest 15%)
         │
         ▼
    Groq LLaMA 3.3 70B
    (summarises results only — never predicts)
         │
         ▼
    Natural Language Response
```

---

## Hybrid ML Engine

| Component | Type | Weight | Role |
|---|---|---|---|
| XGBoost | Supervised classifier | 85% | P(transaction = laundering) |
| Isolation Forest | Unsupervised anomaly detector | 15% | Statistical outlier flag |

**Risk Score Formula:**
```
Final Risk Score = 0.85 × XGBoost_probability + 0.15 × Isolation_Forest_flag
```

**Risk Levels:**
| Level | Score Range | Action |
|---|---|---|
| CRITICAL | ≥ 0.90 | Freeze account immediately |
| HIGH | 0.75 – 0.89 | Escalate to AML analyst |
| MEDIUM | 0.50 – 0.74 | Manual review required |
| LOW | < 0.50 | Continue monitoring |

---

## Dataset

**IBM HI-Small AML Dataset**
- 5,078,345 transactions
- 35 engineered features
- Fraud rate: ~0.10%

**Key Features:**
- Temporal: Hour, Day, Month, Weekday
- Amount: High_Value, Near_Threshold, Sender_Deviation
- Behaviour: Rapid_5m, Unique_Receivers, Sender_Tx_Count
- Bank: Cross_Bank, Currency_Change

**AML Patterns Detected:**
| Pattern | Description |
|---|---|
| Structuring / Smurfing | Transactions just below $10,000 to avoid reporting |
| Layering | Cross-bank, cross-currency transfers to obscure trail |
| Rapid Transactions | Multiple transactions within 5 minutes |
| Fan-Out Layering | One sender → many unique receivers rapidly |
| Large Value Transfer | Top 1% transactions by amount |
| Isolation Forest Anomaly | Statistically unusual transactions |

---

## Tech Stack

**Backend**
- FastAPI + Uvicorn
- XGBoost, scikit-learn (Isolation Forest)
- pandas, joblib
- Groq SDK (LLaMA 3.3 70B)
- python-dotenv

**Frontend**
- React 18 + TypeScript
- Vite
- Tailwind CSS
- Framer Motion
- Recharts
- React Router v6
- Axios

---

## Setup & Running

### Prerequisites
- Python 3.11+
- Node.js 18+
- A free Groq API key from https://console.groq.com

### 1. Clone and install Python dependencies

```bash
pip install fastapi uvicorn joblib pandas xgboost scikit-learn groq python-dotenv
```

### 2. Set your Groq API key

Edit `.env` in the project root:
```
GROQ_API_KEY=gsk_your_key_here
```

### 3. Start the backend

```bash
uvicorn backend.app:app --reload --port 8000
```

Wait for: `AML Agent ready.` and `Customer index ready.`

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Open the app

```
http://localhost:5173
```

---

## Pages

| Page | Description |
|---|---|
| Dashboard | Real-time risk overview, charts, top suspicious transactions |
| AI Agent | ChatGPT-style AML investigation assistant |
| Customer Lookup | Search by account ID — risk profile + LLM analysis |
| Transaction Explorer | Inspect any transaction — ML scores + explanations |
| Analytics | Dataset statistics — fraud rate, bank/currency/format distributions |

---

## AI Agent Example Queries

```
Analyze the dataset
Show top 20 suspicious transactions
Find structuring patterns
Find rapid transaction patterns
Investigate customer 436419
Investigate transaction 0
Which bank has the highest suspicious transactions?
Compare Bank 10 and Bank 70
Show me the highest-risk customer
How is the risk score calculated?
What is XGBoost?
What is Isolation Forest?
```

The agent supports **follow-up questions** using conversation context:
```
User: Investigate customer 436419
AI: (customer details)

User: Why was this customer flagged?
AI: (uses context — no need to repeat customer ID)
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | System health + model status |
| `/dashboard` | GET | Dashboard statistics |
| `/eda` | GET | Dataset EDA (cached at startup) |
| `/query` | POST | Natural language agent query |
| `/customer/{id}` | GET | Customer risk profile |
| `/transaction/{id}` | GET | Transaction details + ML scores |
| `/top_suspicious` | GET | Top N highest-risk transactions |
| `/rule_engine` | POST | Deterministic AML rule checks |

---

## Performance

| Operation | Time |
|---|---|
| EDA query | < 1 ms (startup cache) |
| Customer lookup | ~50 ms (indexed) |
| Risk scoring (customer) | ~25 ms |
| LLM report generation | ~1–3 seconds |
| Full query end-to-end | ~5–8 seconds |

---

## Project Structure

```
├── backend/
│   ├── app.py          # FastAPI routes
│   ├── planner.py      # Intent classification + dynamic planning
│   ├── router.py       # Tool execution + dependency resolution
│   ├── tools.py        # All analytical tools
│   ├── loader.py       # Model/data loading + startup caching
│   ├── llm.py          # Groq LLM integration
│   └── utils.py        # Helpers
├── frontend/
│   └── src/
│       ├── pages/      # Dashboard, Agent, Customer, Transaction, Analytics
│       └── components/ # UI components
├── models/             # Trained ML models (.pkl)
├── data/               # Dataset files (.csv)
└── .env                # API keys
```
