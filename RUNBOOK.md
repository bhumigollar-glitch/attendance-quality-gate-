# Operational Runbook & Architecture Tradeoffs
## Attendance Spreadsheet Quality Gate (APP-059)

**Student Developers:** Dhruv Yadav, Sujal Maruti Gollar  
**Project Mentor:** Tanishka  
**Version:** v1.0.0  

---

### 1. System Architecture & Component Overview

```
                      +-----------------------------+
                      |   Client / Web Dashboard    |
                      +--------------+--------------+
                                     |
               HTTP Multipart POST   |   HTTP GET (Report/Download)
                                     v
                  +----------------------------------+
                  |        FastAPI Application       |
                  +-----------------+----------------+
                                    |
            +-----------------------+-----------------------+
            |                       |                       |
            v                       v                       v
     +--------------+      +-----------------+      +---------------+
     | FileService  |      | ValidatorService|      | CleanerService|
     +-------+------+      +--------+--------+      +-------+-------+
             |                      |                       |
    Saves raw & cleaned     Applies versioned        Conservative
    spreadsheets to disk     rules (v1.0.0, v1.1.0)  cleaning on ACCEPTED
             |                      |                       |
             v                      v                       v
    +-----------------+    +-----------------------------------------+
    |   Disk Storage  |    |     SQLite / PostgreSQL Database         |
    | (raw / cleaned) |    |  (UploadRecord, ValidationIssueRecord)  |
    +-----------------+    +-----------------------------------------+
```

---

### 2. Operational Procedures

#### Starting the Backend Service
```bash
# Activate virtual environment
source .venv/bin/activate

# Launch ASGI server with hot reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Health Checking & Monitoring
- **Endpoint:** `GET /health`
- **Expected Status:** `200 OK`
- **Monitored Subsystems:**
  - Database connectivity (SQL ping via `SELECT 1`)
  - Storage file permissions (write probe verification)

```bash
curl -s http://localhost:8000/health | jq .
```
Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "app_version": "1.0.0",
  "storage_writable": true,
  "timestamp": "2026-11-18T08:20:00.000000"
}
```

---

### 3. Quarantine Remediation Workflow

When a file is flagged as **QUARANTINED**:
1. The spreadsheet is blocked from the `/uploads/{id}/download` endpoint (`HTTP 403 Forbidden`).
2. An Operations Analyst or Education Administrator accesses `/uploads/{id}/report`.
3. The report identifies exact **spreadsheet row numbers**, **columns**, **invalid values**, and **Rule IDs**.
4. The administrator corrects the issues in the original spreadsheet.
5. The corrected file is re-uploaded. Once valid, it is classified as **ACCEPTED**, cleaned output is generated, and downstream reporting teams can ingest it.

---

### 4. Design Decisions & Tradeoffs

| Area | Decision | Tradeoff & Rationale |
|---|---|---|
| **Processing Paradigm** | Synchronous execution for initial releases | Attendance spreadsheets are typically < 50,000 rows. In-memory processing with pandas completes in < 50ms, eliminating operational overhead of Celery/Redis workers. Can easily be converted to async Celery tasks if bulk imports scale. |
| **Cleaning Policy** | Conservative deterministic transformations only | Never impute or invent missing student IDs or attendance dates. Whitespace trimming, Title Case status normalization, and ISO-8601 date formatting are safe and predictable. Ambiguous cases trigger quarantine for human review. |
| **Rule Versioning** | Immutable code-defined rule sets | Rules are defined in `app/rules/versions/` and registered with unique versions (`v1.0.0`, `v1.1.0`). Historical validations remain 100% reproducible; changing rules in v1.1.0 does not mutate past v1.0.0 results. |
| **Storage Architecture** | File system separation with DB metadata | Raw uploads and cleaned files are stored in isolated directories (`data/raw`, `data/cleaned`) using UUIDs to prevent directory traversal and name collisions. Database maintains audit links and metrics. |
| **Quarantine Enforcement** | Server-side hard barrier | Download endpoint rejects quarantined files with `403 Forbidden`. No unsafe or malformed data can reach reporting systems by accident. |

---

### 5. Troubleshooting Guide

| Symptom | Probable Cause | Remediation |
|---|---|---|
| `413 Payload Too Large` | File exceeds `MAX_FILE_SIZE_BYTES` (default 10 MB). | Compress or split the file, or adjust `MAX_FILE_SIZE_BYTES` in `.env`. |
| `400 Unsupported file extension` | File is not `.csv` or `.xlsx`. | Save the spreadsheet as CSV or modern XLSX format before uploading. |
| `403 Forbidden on Download` | File failed one or more blocking rules and is quarantined. | Inspect the validation report at `/uploads/{id}/report` and fix row-level errors. |
| Database connection error | Database file locked or corrupted. | Check write permissions on `attendance_gate.db` or restart the uvicorn process. |
