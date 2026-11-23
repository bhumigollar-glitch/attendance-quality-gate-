import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    """GET /health returns healthy status, db connectivity, and version."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["storage_writable"] is True
    assert "timestamp" in data


def test_rules_endpoints(client: TestClient):
    """GET /rules and GET /rules/{version} return accurate rule specifications."""
    response = client.get("/rules")
    assert response.status_code == 200
    data = response.json()
    assert "v1.0.0" in data["available_versions"]
    assert "v1.1.0" in data["available_versions"]
    assert data["default_version"] == "v1.0.0"

    # Specific version
    res_v100 = client.get("/rules/v1.0.0")
    assert res_v100.status_code == 200
    assert res_v100.json()["version"] == "v1.0.0"

    # Not found version
    res_404 = client.get("/rules/v9.9.9")
    assert res_404.status_code == 404


def test_upload_valid_csv_accepted(client: TestClient, fixtures_dir: Path):
    """Upload valid CSV: verify 201 Created, ACCEPTED status, and download cleaned CSV."""
    file_path = fixtures_dir / "valid_clean.csv"
    with open(file_path, "rb") as f:
        response = client.post(
            "/uploads",
            files={"file": ("valid_clean.csv", f, "text/csv")},
            data={"rule_version": "v1.0.0"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "ACCEPTED"
    assert data["total_rows"] == 4
    assert data["valid_rows"] == 4
    assert data["invalid_rows"] == 0
    assert data["error_count"] == 0
    assert data["download_url"] is not None

    upload_id = data["upload_id"]

    # Verify download succeeds
    dl_response = client.get(f"/uploads/{upload_id}/download")
    assert dl_response.status_code == 200
    assert "text/csv" in dl_response.headers.get("content-type", "")
    content = dl_response.text
    assert "student_id,student_name,attendance_date,attendance_status,class_id" in content
    assert "STU001,Alice Johnson,2024-10-01,Present,CS101" in content


def test_upload_valid_xlsx_accepted(client: TestClient, fixtures_dir: Path):
    """Upload valid XLSX: verify ACCEPTED and download succeeds."""
    file_path = fixtures_dir / "valid_clean.xlsx"
    with open(file_path, "rb") as f:
        response = client.post(
            "/uploads",
            files={"file": ("valid_clean.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"rule_version": "v1.0.0"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "ACCEPTED"
    assert data["total_rows"] == 4

    upload_id = data["upload_id"]
    dl_response = client.get(f"/uploads/{upload_id}/download")
    assert dl_response.status_code == 200


def test_upload_whitespace_normalization(client: TestClient, fixtures_dir: Path):
    """Upload valid file with whitespace: verify whitespace is trimmed and casing normalized."""
    file_path = fixtures_dir / "valid_with_whitespace.csv"
    with open(file_path, "rb") as f:
        response = client.post(
            "/uploads",
            files={"file": ("valid_with_whitespace.csv", f, "text/csv")},
            data={"rule_version": "v1.0.0"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "ACCEPTED"

    upload_id = data["upload_id"]
    dl_response = client.get(f"/uploads/{upload_id}/download")
    assert dl_response.status_code == 200
    content = dl_response.text

    # Verify whitespace trimmed and dates formatted to YYYY-MM-DD
    assert "STU001,Alice Johnson,2024-10-01,Present,CS101" in content
    assert "STU002,Bob Smith,2024-10-01,Absent,CS101" in content


def test_quarantined_upload_blocks_download(client: TestClient, fixtures_dir: Path):
    """Quarantined uploads must be blocked with HTTP 403 Forbidden from downloading cleaned file."""
    file_path = fixtures_dir / "invalid_missing_columns.csv"
    with open(file_path, "rb") as f:
        response = client.post(
            "/uploads",
            files={"file": ("invalid_missing_columns.csv", f, "text/csv")},
            data={"rule_version": "v1.0.0"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["decision"] == "QUARANTINED"
    assert data["download_url"] is None
    upload_id = data["upload_id"]

    # Attempt download
    dl_response = client.get(f"/uploads/{upload_id}/download")
    assert dl_response.status_code == 403
    assert "quarantined" in dl_response.json()["detail"].lower()


def test_validation_report_details(client: TestClient, fixtures_dir: Path):
    """Verify validation report contains row numbers, column names, invalid values, and rule IDs."""
    file_path = fixtures_dir / "invalid_duplicate_records.csv"
    with open(file_path, "rb") as f:
        upload_res = client.post(
            "/uploads",
            files={"file": ("invalid_duplicate_records.csv", f, "text/csv")},
            data={"rule_version": "v1.0.0"},
        )

    upload_id = upload_res.json()["upload_id"]

    report_res = client.get(f"/uploads/{upload_id}/report")
    assert report_res.status_code == 200
    report = report_res.json()
    assert report["upload_id"] == upload_id
    assert report["decision"] == "QUARANTINED"
    assert "RULE-VAL-005" in report["failed_rule_ids"]

    # Row number check: duplicate is at row 4 in spreadsheet (header=1, row 2, row 3, row 4)
    dup_issue = next(i for i in report["issues"] if i["rule_id"] == "RULE-VAL-005")
    assert dup_issue["row_number"] == 4
    assert "duplicate" in dup_issue["message"].lower()


def test_rule_version_selection(client: TestClient, fixtures_dir: Path):
    """File valid_v1_1_extended is quarantined under v1.0.0 but accepted under v1.1.0."""
    file_path = fixtures_dir / "valid_v1_1_extended.csv"

    # Under v1.0.0
    with open(file_path, "rb") as f:
        res_v10 = client.post(
            "/uploads",
            files={"file": ("valid_v1_1_extended.csv", f, "text/csv")},
            data={"rule_version": "v1.0.0"},
        )
    assert res_v10.json()["decision"] == "QUARANTINED"

    # Under v1.1.0
    with open(file_path, "rb") as f:
        res_v11 = client.post(
            "/uploads",
            files={"file": ("valid_v1_1_extended.csv", f, "text/csv")},
            data={"rule_version": "v1.1.0"},
        )
    assert res_v11.json()["decision"] == "ACCEPTED"


def test_upload_metadata_persistence(client: TestClient, fixtures_dir: Path):
    """Verify GET /uploads/{id} and GET /uploads list endpoint."""
    file_path = fixtures_dir / "valid_clean.csv"
    with open(file_path, "rb") as f:
        upload_res = client.post(
            "/uploads",
            files={"file": ("valid_clean.csv", f, "text/csv")},
            data={"rule_version": "v1.0.0"},
        )
    upload_id = upload_res.json()["upload_id"]

    # Retrieve by ID
    get_res = client.get(f"/uploads/{upload_id}")
    assert get_res.status_code == 200
    summary = get_res.json()
    assert summary["upload_id"] == upload_id
    assert summary["original_filename"] == "valid_clean.csv"
    assert summary["decision"] == "ACCEPTED"

    # Retrieve list
    list_res = client.get("/uploads?limit=10")
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(item["upload_id"] == upload_id for item in items)


def test_all_manifest_fixtures(client: TestClient, fixtures_dir: Path):
    """
    Automated fixture test driving every fixture in fixtures_manifest.json
    to verify expected quarantine/accepted decision matches 100%.
    """
    manifest_path = fixtures_dir / "fixtures_manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    for item in manifest["fixtures"]:
        filename = item["file"]
        file_path = fixtures_dir / filename
        assert file_path.exists(), f"Fixture file {filename} does not exist"

        mime_type = "text/csv" if item["format"] == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        # Check v1.0.0
        with open(file_path, "rb") as f:
            res = client.post(
                "/uploads",
                files={"file": (filename, f, mime_type)},
                data={"rule_version": "v1.0.0"},
            )

        assert res.status_code == 201, f"Upload failed for {filename}: {res.text}"
        data = res.json()

        expected = item.get("expected_decision") or item.get("expected_decision_v1_0")
        assert data["decision"] == expected, (
            f"Fixture {filename} expected {expected} but got {data['decision']}"
        )

        if "expected_errors" in item:
            assert data["error_count"] == item["expected_errors"], (
                f"Fixture {filename} expected {item['expected_errors']} errors, got {data['error_count']}"
            )
