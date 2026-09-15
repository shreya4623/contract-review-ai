# Contract Review AI — Backend

FastAPI + LangGraph backend that extracts contract clauses, classifies them,
compares them against a reference policy, detects risks, and validates every
finding against document evidence before returning a final report.

## 1. Prerequisites

- Python 3.11 or 3.12
- PostgreSQL 14+ (local install, Docker, or a managed instance)
- An OpenAI API key

## 2. Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set at minimum:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/contract_review
JWT_SECRET_KEY=<generate a long random string>
OPENAI_API_KEY=sk-...
```

## 3. Database setup

Create the database (tables are created automatically on app startup):

```bash
# Using the local postgres CLI:
createdb contract_review

# Or with Docker:
docker run --name contract-review-pg -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=contract_review -p 5432:5432 -d postgres:16
```

No manual migrations are needed — `init_db()` runs `Base.metadata.create_all()`
on startup and creates the `users`, `documents`, and `reviews` tables.

## 4. Run locally

```bash
uvicorn app.main:app --reload --port 8000
```

- API docs (Swagger UI): http://localhost:8000/docs
- Health check: http://localhost:8000/health

## 5. Test commands

A quick manual smoke test without hitting OpenAI (auth + upload validation only):

```bash
python3 -m py_compile $(find app -name "*.py")   # syntax check
```

Full end-to-end test (requires `OPENAI_API_KEY` to be set and valid):

```bash
# 1. Register + login
curl -X POST localhost:8000/auth/register -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"password123"}'

# 2. Upload the contract and the reference policy (use the sample_documents/ files)
curl -X POST localhost:8000/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@../sample_documents/sample_contract.pdf" -F "document_type=contract"

curl -X POST localhost:8000/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@../sample_documents/sample_policy.pdf" -F "document_type=reference"

# 3. Run the review (use the returned document ids)
curl -X POST localhost:8000/reviews \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"contract_document_id":"<contract-id>","reference_document_id":"<reference-id>"}'
```

## 6. Architecture notes

- **Deterministic evidence**: the Document Parsing Agent and clause chunker
  never call an LLM — page numbers and clause text are extracted with `pypdf`
  / `python-docx` only. The LLM is only ever asked to *classify* or *compare*
  text it is given, never to invent it.
- **Reviewer/Validation Agent**: every finding's evidence quote is checked
  against the actual source clause text (fuzzy sentence matching) before
  `validated: true` is set. Unverifiable quotes are replaced with the full
  source clause and the finding is flagged for human review.
- **Deterministic risk scoring**: any finding where both the contract and
  reference requirement mention a number of days (payment terms, notice
  periods, etc.) has its risk level computed from the actual numeric gap,
  not from the LLM's judgment.
- **LangGraph workflow**: see `app/agents/workflow.py` for the full state
  graph (`parse -> extract_classify -> retrieve -> compare -> detect_risk ->
  reviewer_validate`). Each node catches its own exceptions and stores them
  in `state["error"]`, which the `/reviews` route surfaces as a 422 response.

## 7. Deploying to Render

1. Push this repo to GitHub.
2. In Render, create a **PostgreSQL** instance and copy its internal
   connection string.
3. Create a **Web Service** pointing at the `backend/` directory with:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables from `.env.example` (use the Render Postgres
   connection string for `DATABASE_URL`, and set `CORS_ORIGINS` to your
   Vercel frontend URL once deployed).
