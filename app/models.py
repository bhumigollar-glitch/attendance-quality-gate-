import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship
from app.database import Base


class UploadRecord(Base):
    """Stores metadata, status, metrics, and outcomes of uploaded attendance spreadsheets."""
    __tablename__ = "upload_records"

    id = Column(String(36), primary_key=True, index=True)  # UUID string
    original_filename = Column(String(255), nullable=False)
    file_extension = Column(String(10), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    raw_file_path = Column(String(512), nullable=False)
    cleaned_file_path = Column(String(512), nullable=True)

    status = Column(String(32), nullable=False, default="PENDING", index=True)
    # ACCEPTED, QUARANTINED, FAILED
    decision = Column(String(32), nullable=True, index=True)

    rule_version = Column(String(32), nullable=False, default="v1.0.0")

    total_rows = Column(Integer, default=0)
    valid_rows = Column(Integer, default=0)
    invalid_rows = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)

    processing_time_ms = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
        nullable=False,
    )

    # Relationships
    issues = relationship(
        "ValidationIssueRecord",
        back_populates="upload",
        cascade="all, delete-orphan",
        order_by="ValidationIssueRecord.row_number.asc().nullsfirst()",
    )


class ValidationIssueRecord(Base):
    """Stores individual validation findings and row-level data quality errors."""
    __tablename__ = "validation_issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    upload_id = Column(String(36), ForeignKey("upload_records.id", ondelete="CASCADE"), nullable=False, index=True)

    row_number = Column(Integer, nullable=True, index=True)  # 1-indexed sheet row, null for schema-level errors
    column_name = Column(String(64), nullable=True)
    invalid_value = Column(String(512), nullable=True)

    rule_id = Column(String(64), nullable=False, index=True)
    rule_description = Column(String(255), nullable=False)
    severity = Column(String(16), nullable=False)  # BLOCKING, WARNING, INFO
    message = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    upload = relationship("UploadRecord", back_populates="issues")
