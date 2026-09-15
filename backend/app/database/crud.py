"""Plain CRUD helpers used by the API routers."""
import json
from typing import Optional, List

from sqlalchemy.orm import Session

from app.database import models


# --- Users ---

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, email: str, password_hash: str) -> models.User:
    user = models.User(email=email, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# --- Documents ---

def create_document(
    db: Session, user_id: str, filename: str, stored_path: str, document_type: str
) -> models.Document:
    doc = models.Document(
        user_id=user_id,
        filename=filename,
        stored_path=stored_path,
        document_type=document_type,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_document(db: Session, document_id: str, user_id: str) -> Optional[models.Document]:
    return (
        db.query(models.Document)
        .filter(models.Document.id == document_id, models.Document.user_id == user_id)
        .first()
    )


# --- Reviews ---

def create_review(
    db: Session,
    user_id: str,
    contract_id: str,
    reference_id: str,
    status: str,
    result: dict,
) -> models.Review:
    review = models.Review(
        user_id=user_id,
        contract_id=contract_id,
        reference_id=reference_id,
        status=status,
        result_json=json.dumps(result),
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def list_reviews(db: Session, user_id: str) -> List[models.Review]:
    return (
        db.query(models.Review)
        .filter(models.Review.user_id == user_id)
        .order_by(models.Review.created_at.desc())
        .all()
    )


def get_review(db: Session, review_id: str, user_id: str) -> Optional[models.Review]:
    return (
        db.query(models.Review)
        .filter(models.Review.id == review_id, models.Review.user_id == user_id)
        .first()
    )
