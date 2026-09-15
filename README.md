# Agentic AI Contract Review & Risk Identification System

A full-stack support tool that extracts contractual clauses from an uploaded
contract, compares them against a reference policy/template, flags
deviations and missing clauses, assigns a risk level, and validates every
finding against document evidence before producing a final report.

> **This is a contract-review support tool only. It does not provide
> professional legal advice.**

## Stack

| Layer      | Technology |
|------------|------------|
| Backend    | Python, FastAPI, LangGraph, OpenAI API, Pydantic, PostgreSQL, JWT |
| Retrieval  | Sentence-Transformers + FAISS |
| Frontend   | React, TypeScript, Tailwind CSS, Axios, React Router |
| Deployment | Backend → Render, Frontend → Vercel |

## How it works

```
START
  → Document Parsing Agent            (pypdf / python-docx, page-indexed)
  → Clause Extraction + Classification Agent   (LLM classifies, never rewrites text)
  → Policy Retrieval                  (Sentence-Transformers embeddings + FAISS)
  → Policy Comparison Agent           (LLM compares contract vs. reference clause)
  → Risk Detection Agent              (deterministic numeric rules + missing-clause detection)
  → Reviewer / Validation Agent       (verifies every evidence quote against source text)
  → Final Review Report
  → END
```

Every finding carries full traceability:

```
category, contract_requirement, reference_requirement, difference,
risk_level, contract_evidence, contract_page,
reference_evidence, reference_page, validated
```

## Repository layout

```
contract-review-ai/
├── backend/            FastAPI app, LangGraph agents, services, DB layer
├── frontend/            React + TypeScript client
├── sample_documents/     Sample contract + reference policy PDFs for testing
├── screenshots/          (add your own screenshots here)
└── README.md
```

See `backend/README.md` and `frontend/README.md` for detailed setup, local
run, test, and deployment instructions for each half of the stack.

## Quick start (local)

```bash
# 1. Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, JWT_SECRET_KEY, OPENAI_API_KEY
uvicorn app.main:app --reload --port 8000

# 2. Frontend (in a second terminal)
cd frontend
npm install
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Then open http://localhost:5173, create an account, and upload
`sample_documents/sample_contract.pdf` and
`sample_documents/sample_policy.pdf` to run the end-to-end test:

```
contract.pdf + reference_policy.pdf
  → parsing → clause extraction → classification
  → FAISS retrieval → policy comparison → risk detection
  → evidence validation → final report → React dashboard
```

The bundled sample contract deliberately deviates from the sample policy
(90-day vs. 30-day payment terms, a 15-day vs. 30-day termination notice
period, and missing Warranty / Indemnity / Insurance / Data Protection
clauses) so the demo produces a `HUMAN_REVIEW_REQUIRED` result with a mix of
HIGH and MEDIUM findings on first run.

## Quality & safety notes

- The LLM is never asked to invent evidence: it only classifies or compares
  text that was deterministically extracted from the source document, and
  the Reviewer/Validation Agent re-checks every quoted "evidence" string
  against the real source text before marking a finding `validated: true`.
- Numeric requirements (day counts) are compared deterministically in plain
  Python, not by LLM judgment.
- API keys are read from environment variables only and are never returned
  in any API response.
- Invalid file types, empty documents, and LLM/API failures all return
  clean 4xx/422 JSON errors instead of crashing the workflow.
