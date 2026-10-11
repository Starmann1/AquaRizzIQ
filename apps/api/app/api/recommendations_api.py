import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.db.models import Recommendation, Assessment, Ward

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("")
def list_recommendations(assessment_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Return active municipal action recommendations from PostgreSQL."""
    query = db.query(Recommendation)
    if assessment_id:
        try:
            aid = uuid.UUID(assessment_id)
            query = query.filter(Recommendation.assessment_id == aid)
        except ValueError:
            return []

    records = query.order_by(Recommendation.created_at.desc()).limit(50).all()

    results = []
    for r in records:
        a = db.query(Assessment).filter(Assessment.id == r.assessment_id).first()
        results.append({
            "id": str(r.id),
            "assessment_id": str(r.assessment_id),
            "ward_id": a.ward_id if a else None,
            "type": r.recommendation_type,
            "priority": r.priority,
            "description": r.description,
            "actions": r.actions,
            "created_at": r.created_at.isoformat(),
        })

    return results
