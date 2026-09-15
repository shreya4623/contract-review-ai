import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database import crud, models
from app.api.security import get_current_user
from app.schemas.review import ReviewCreateRequest, ReviewResponse, ReviewListItem, ReviewReport
from app.agents.workflow import run_review_workflow

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: ReviewCreateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    contract_doc = crud.get_document(db, payload.contract_document_id, current_user.id)
    reference_doc = crud.get_document(db, payload.reference_document_id, current_user.id)

    if not contract_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract document not found.")
    if not reference_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference document not found.")

    try:
        final_state = run_review_workflow(contract_doc.stored_path, reference_doc.stored_path)
    except Exception as exc:  # noqa: BLE001 - last-resort safety net around the whole workflow
        logger.exception("Workflow crashed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Review workflow failed unexpectedly: {exc}",
        ) from exc

    if final_state.get("error"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=final_state["error"])

    report: ReviewReport = final_state["report"]

    review = crud.create_review(
        db,
        user_id=current_user.id,
        contract_id=contract_doc.id,
        reference_id=reference_doc.id,
        status=report.status.value,
        result=report.model_dump(mode="json"),
    )

    return ReviewResponse(
        id=review.id,
        status=review.status,
        result=report,
        created_at=review.created_at.isoformat(),
    )


@router.get("", response_model=list[ReviewListItem])
def get_reviews(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    reviews = crud.list_reviews(db, current_user.id)
    return [
        ReviewListItem(id=r.id, status=r.status, created_at=r.created_at.isoformat()) for r in reviews
    ]


@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(
    review_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    review = crud.get_review(db, review_id, current_user.id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")

    result_dict = json.loads(review.result_json)
    return ReviewResponse(
        id=review.id,
        status=review.status,
        result=ReviewReport.model_validate(result_dict),
        created_at=review.created_at.isoformat(),
    )
