import io
from fastapi.testclient import TestClient
from app.config import settings


def test_empty_file_upload(client: TestClient):
    """Uploading an empty 0-byte file must be rejected with 400 Bad Request."""
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/uploads",
        files={"file": ("empty.csv", empty_file, "text/csv")},
        data={"rule_version": "v1.0.0"},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_unsupported_file_extension(client: TestClient):
    """Uploading unsupported format (e.g. .txt, .pdf, .json) returns 400 Bad Request."""
    txt_file = io.BytesIO(b"some content")
    response = client.post(
        "/uploads",
        files={"file": ("report.txt", txt_file, "text/plain")},
        data={"rule_version": "v1.0.0"},
    )
    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_invalid_rule_version_specified(client: TestClient):
    """Specifying an unknown rule version returns 400 Bad Request."""
    csv_file = io.BytesIO(b"student_id,student_name,attendance_date,attendance_status\nSTU1,Alice,2024-10-01,Present\n")
    response = client.post(
        "/uploads",
        files={"file": ("test.csv", csv_file, "text/csv")},
        data={"rule_version": "v9.9.9"},
    )
    assert response.status_code == 400
    assert "unknown rule version" in response.json()["detail"].lower()


def test_oversized_file_rejected(client: TestClient, monkeypatch):
    """Files exceeding MAX_FILE_SIZE_BYTES must be rejected with 413 Payload Too Large."""
    # Temporarily set max size to 100 bytes for test
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_BYTES", 100)

    large_content = b"student_id,student_name,attendance_date,attendance_status\n" + b"STU001,Alice,2024-10-01,Present\n" * 10
    large_file = io.BytesIO(large_content)

    response = client.post(
        "/uploads",
        files={"file": ("large.csv", large_file, "text/csv")},
        data={"rule_version": "v1.0.0"},
    )
    assert response.status_code == 413
    assert "exceeds maximum allowed size" in response.json()["detail"].lower()


def test_non_existent_upload_queries(client: TestClient):
    """Queries for non-existent upload IDs return 404."""
    res_status = client.get("/uploads/00000000-0000-0000-0000-000000000000")
    assert res_status.status_code == 404

    res_report = client.get("/uploads/00000000-0000-0000-0000-000000000000/report")
    assert res_report.status_code == 404

    res_download = client.get("/uploads/00000000-0000-0000-0000-000000000000/download")
    assert res_download.status_code == 404
