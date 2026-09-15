import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database.database import init_db
from app.api import auth, documents, reviews

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(
    title="Agentic AI Contract Review & Risk Identification System",
    description=(
        "Support tool for extracting, classifying, and comparing contract clauses "
        "against a reference policy. This system does not provide professional legal advice."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(reviews.router)
