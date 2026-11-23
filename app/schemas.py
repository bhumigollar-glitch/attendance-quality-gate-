import datetime
from typing import List, Optional, Set
from pydantic import BaseModel, Field, ConfigDict


class ValidationIssueSchema(BaseModel):
    """Schema for individual validation finding."""
    id: Optional[int] = None
    row_number: Optional[int] = Field(None, description="Physical 1-indexed row in the spreadsheet")
    column_name: Optional[str] = Field(None, description="Affected column name(s)")
    invalid_value: Optional[str] = Field(None, description="The invalid cell value encountered")
    rule_id: str = Field(..., description="Stable rule identifier, e.g. RULE-VAL-001")
    rule_description: str = Field(..., description="Human-readable rule description")
    severity: str = Field(..., description="BLOCKING, WARNING, or INFO")
    message: str = Field(..., description="Detailed explanation of the validation failure")

    model_config = ConfigDict(from_attributes=True)


class UploadResponse(BaseModel):
    """Response returned immediately after file upload and validation processing."""
    upload_id: str
    original_filename: str
    status: str
    decision: str
    rule_version: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    error_count: int
    warning_count: int
    processing_time_ms: float
    report_url: str
    download_url: Optional[str] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class UploadStatusSummary(BaseModel):
    """Metadata, status, and metrics of an upload."""
    upload_id: str
    original_filename: str
    file_extension: str
    file_size_bytes: int
    status: str
    decision: Optional[str]
    rule_version: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    error_count: int
    warning_count: int
    processing_time_ms: float
    has_cleaned_file: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class ValidationReport(BaseModel):
    """Detailed validation report with row-level issues and failure reasons."""
    upload_id: str
    original_filename: str
    status: str
    decision: str
    rule_version: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    error_count: int
    warning_count: int
    failed_rule_ids: List[str]
    download_available: bool
    processing_time_ms: float
    created_at: datetime.datetime
    issues: List[ValidationIssueSchema]

    model_config = ConfigDict(from_attributes=True)


class RuleDefinitionSchema(BaseModel):
    """Details of a single validation rule."""
    rule_id: str
    name: str
    description: str
    severity: str
    category: str

    model_config = ConfigDict(from_attributes=True)


class RuleSetSchema(BaseModel):
    """Detailed specification of a versioned rule set."""
    version: str
    name: str
    description: str
    required_columns: List[str]
    optional_columns: List[str]
    permitted_statuses: List[str]
    rules: List[RuleDefinitionSchema]

    model_config = ConfigDict(from_attributes=True)


class RuleVersionsResponse(BaseModel):
    """List of all available rule versions."""
    available_versions: List[str]
    default_version: str
    rule_sets: List[RuleSetSchema]


class HealthCheckResponse(BaseModel):
    """System health check status."""
    status: str
    database: str
    app_version: str
    storage_writable: bool
    timestamp: datetime.datetime
