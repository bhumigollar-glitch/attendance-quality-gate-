import os
import time
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import UploadRecord, ValidationIssueRecord
from app.rules.registry import rule_registry
from app.schemas import (
    UploadResponse,
    UploadStatusSummary,
    ValidationReport,
    ValidationIssueSchema,
)
from app.services.file_service import FileService
from app.services.validator_service import ValidatorService
from app.services.cleaner_service import CleanerService

router = APIRouter()


@router.post(
    "/uploads",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Uploads"],
    summary="Upload an attendance spreadsheet and start validation",
)
async def upload_spreadsheet(
    file: UploadFile = File(..., description="CSV or XLSX attendance spreadsheet file"),
    rule_version: str = Form(settings.DEFAULT_RULE_VERSION, description="Rule set version to apply"),
    db: Session = Depends(get_db),
):
    """
    Upload an attendance spreadsheet.
    - Validates file format, extension, and content size.
    - Executes deterministic validation against the specified rule set version.
    - Classifies the file as ACCEPTED or QUARANTINED.
    - Automatically cleans and generates exportable output for accepted files.
    """
    start_time = time.time()
    upload_id = str(uuid.uuid4())

    # 1. Validate file extension and format
    original_filename, ext = FileService.validate_file_metadata(file)

    # 2. Check rule set version exists
    rule_set = rule_registry.get(rule_version)
    if not rule_set:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown rule version '{rule_version}'. Available versions: {', '.join(rule_registry.list_versions())}",
        )

    # 3. Stream and persist raw upload
    raw_path, file_size_bytes = await FileService.save_raw_file(file, upload_id, ext)

    # 4. Parse spreadsheet into DataFrame
    try:
        df = FileService.parse_file(raw_path, ext)
    except Exception as e:
        processing_ms = (time.time() - start_time) * 1000.0
        # Record failed upload in database
        failed_record = UploadRecord(
            id=upload_id,
            original_filename=original_filename,
            file_extension=ext,
            file_size_bytes=file_size_bytes,
            raw_file_path=str(raw_path),
            cleaned_file_path=None,
            status="FAILED",
            decision="QUARANTINED",
            rule_version=rule_version,
            total_rows=0,
            valid_rows=0,
            invalid_rows=0,
            error_count=1,
            warning_count=0,
            processing_time_ms=processing_ms,
            error_message=f"File parsing error: {str(e)}",
        )
        db.add(failed_record)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Unable to parse spreadsheet file: {str(e)}",
        )

    # 5. Validate DataFrame against versioned rules
    validation_res = ValidatorService.validate(df, rule_set)

    # 6. If ACCEPTED, generate cleaned file
    cleaned_file_path: Optional[str] = None
    if validation_res.decision == "ACCEPTED":
        cleaned_df = CleanerService.clean(df, rule_set)
        cleaned_saved_path = FileService.save_cleaned_file(cleaned_df, upload_id, ext)
        cleaned_file_path = str(cleaned_saved_path)

    processing_ms = (time.time() - start_time) * 1000.0

    # 7. Persist UploadRecord & ValidationIssues
    upload_record = UploadRecord(
        id=upload_id,
        original_filename=original_filename,
        file_extension=ext,
        file_size_bytes=file_size_bytes,
        raw_file_path=str(raw_path),
        cleaned_file_path=cleaned_file_path,
        status="COMPLETED",
        decision=validation_res.decision,
        rule_version=rule_set.version,
        total_rows=validation_res.total_rows,
        valid_rows=validation_res.valid_rows,
        invalid_rows=validation_res.invalid_rows,
        error_count=validation_res.error_count,
        warning_count=validation_res.warning_count,
        processing_time_ms=processing_ms,
    )
    db.add(upload_record)
    db.flush()

    for issue in validation_res.issues:
        sev = issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity)
        issue_record = ValidationIssueRecord(
            upload_id=upload_id,
            row_number=issue.row_number,
            column_name=issue.column_name,
            invalid_value=issue.invalid_value,
            rule_id=issue.rule_id,
            rule_description=issue.rule_description,
            severity=sev,
            message=issue.message,
        )
        db.add(issue_record)

    db.commit()
    db.refresh(upload_record)

    report_url = f"/uploads/{upload_id}/report"
    download_url = f"/uploads/{upload_id}/download" if upload_record.decision == "ACCEPTED" else None

    return UploadResponse(
        upload_id=upload_id,
        original_filename=original_filename,
        status=upload_record.status,
        decision=upload_record.decision,
        rule_version=upload_record.rule_version,
        total_rows=upload_record.total_rows,
        valid_rows=upload_record.valid_rows,
        invalid_rows=upload_record.invalid_rows,
        error_count=upload_record.error_count,
        warning_count=upload_record.warning_count,
        processing_time_ms=upload_record.processing_time_ms,
        report_url=report_url,
        download_url=download_url,
        created_at=upload_record.created_at,
    )


@router.get(
    "/uploads",
    response_model=List[UploadStatusSummary],
    tags=["Uploads"],
    summary="List upload history",
)
def list_uploads(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Retrieve historical list of spreadsheet uploads.
    """
    records = (
        db.query(UploadRecord)
        .order_by(UploadRecord.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        UploadStatusSummary(
            upload_id=rec.id,
            original_filename=rec.original_filename,
            file_extension=rec.file_extension,
            file_size_bytes=rec.file_size_bytes,
            status=rec.status,
            decision=rec.decision,
            rule_version=rec.rule_version,
            total_rows=rec.total_rows,
            valid_rows=rec.valid_rows,
            invalid_rows=rec.invalid_rows,
            error_count=rec.error_count,
            warning_count=rec.warning_count,
            processing_time_ms=rec.processing_time_ms,
            has_cleaned_file=rec.cleaned_file_path is not None,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
        )
        for rec in records
    ]


@router.get(
    "/uploads/{upload_id}",
    response_model=UploadStatusSummary,
    tags=["Uploads"],
    summary="Retrieve upload status and summary",
)
def get_upload_status(
    upload_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve metadata, processing status, row metrics, and acceptance decision for an upload.
    """
    record = db.query(UploadRecord).filter(UploadRecord.id == upload_id).first()
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Upload with ID '{upload_id}' not found.",
        )

    return UploadStatusSummary(
        upload_id=record.id,
        original_filename=record.original_filename,
        file_extension=record.file_extension,
        file_size_bytes=record.file_size_bytes,
        status=record.status,
        decision=record.decision,
        rule_version=record.rule_version,
        total_rows=record.total_rows,
        valid_rows=record.valid_rows,
        invalid_rows=record.invalid_rows,
        error_count=record.error_count,
        warning_count=record.warning_count,
        processing_time_ms=record.processing_time_ms,
        has_cleaned_file=record.cleaned_file_path is not None,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get(
    "/uploads/{upload_id}/report",
    response_model=ValidationReport,
    tags=["Uploads"],
    summary="Retrieve the validation report",
)
def get_validation_report(
    upload_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve comprehensive validation report containing row numbers, failure explanations,
    and failed rule sets.
    """
    record = db.query(UploadRecord).filter(UploadRecord.id == upload_id).first()
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Upload with ID '{upload_id}' not found.",
        )

    issues = [
        ValidationIssueSchema(
            id=iss.id,
            row_number=iss.row_number,
            column_name=iss.column_name,
            invalid_value=iss.invalid_value,
            rule_id=iss.rule_id,
            rule_description=iss.rule_description,
            severity=iss.severity,
            message=iss.message,
        )
        for iss in record.issues
    ]

    failed_rule_ids = sorted(list(set(iss.rule_id for iss in record.issues)))

    return ValidationReport(
        upload_id=record.id,
        original_filename=record.original_filename,
        status=record.status,
        decision=record.decision or "QUARANTINED",
        rule_version=record.rule_version,
        total_rows=record.total_rows,
        valid_rows=record.valid_rows,
        invalid_rows=record.invalid_rows,
        error_count=record.error_count,
        warning_count=record.warning_count,
        failed_rule_ids=failed_rule_ids,
        download_available=record.decision == "ACCEPTED" and record.cleaned_file_path is not None,
        processing_time_ms=record.processing_time_ms,
        created_at=record.created_at,
        issues=issues,
    )


@router.get(
    "/uploads/{upload_id}/download",
    tags=["Uploads"],
    summary="Download the cleaned file when allowed",
)
def download_cleaned_file(
    upload_id: str,
    db: Session = Depends(get_db),
):
    """
    Download the accepted, cleaned spreadsheet.
    Quarantined uploads are blocked from downloading and return HTTP 403 Forbidden.
    """
    record = db.query(UploadRecord).filter(UploadRecord.id == upload_id).first()
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Upload with ID '{upload_id}' not found.",
        )

    if record.decision == "QUARANTINED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Upload '{upload_id}' is quarantined due to blocking validation errors "
                f"({record.error_count} error(s)). Cleaned downloads are only permitted for accepted uploads."
            ),
        )

    if record.status == "FAILED" or not record.cleaned_file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No cleaned file available for upload '{upload_id}'.",
        )

    if not os.path.exists(record.cleaned_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The cleaned file could not be found on disk.",
        )

    base, ext = os.path.splitext(record.original_filename)
    download_filename = f"{base}_cleaned{ext}"

    media_type = "text/csv" if ext.lower() == ".csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return FileResponse(
        path=record.cleaned_file_path,
        filename=download_filename,
        media_type=media_type,
    )
