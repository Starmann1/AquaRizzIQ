from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
def health_check():
    return {"status": "ok"}

@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database_backend": db.bind.dialect.name}
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database not ready")
