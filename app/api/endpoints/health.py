import datetime
import tempfile
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.schemas import HealthCheckResponse

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse, tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Verify application health, database connectivity, and file storage writability.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    storage_writable = False
    try:
        test_file = settings.RAW_STORAGE_DIR / ".health_probe"
        test_file.write_text("ok")
        if test_file.exists():
            test_file.unlink()
            storage_writable = True
    except Exception:
        storage_writable = False

    status = "healthy" if (db_status == "connected" and storage_writable) else "degraded"

    return HealthCheckResponse(
        status=status,
        database=db_status,
        app_version=settings.APP_VERSION,
        storage_writable=storage_writable,
        timestamp=datetime.datetime.utcnow(),
    )
