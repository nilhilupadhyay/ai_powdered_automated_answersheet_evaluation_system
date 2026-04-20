from fastapi.testclient import TestClient

from app.main import app


def test_upload_and_process_submission() -> None:
    client = TestClient(app)

    upload_response = client.post(
        "/api/v1/capture/upload",
        params={"sheet_session_id": "session-cap-001"},
        files={"file": ("answer.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert upload_response.status_code == 200
    submission_id = upload_response.json()["submission_id"]

    process_response = client.post(f"/api/v1/capture/{submission_id}/process")
    assert process_response.status_code == 200
    data = process_response.json()
    assert data["submission_id"] == submission_id
    assert data["status"] == "needs_manual_review"


def test_manual_review_queue_returns_processed_item() -> None:
    client = TestClient(app)
    upload_response = client.post(
        "/api/v1/capture/upload",
        params={"sheet_session_id": "session-cap-002"},
        files={"file": ("answer.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    submission_id = upload_response.json()["submission_id"]
    client.post(f"/api/v1/capture/{submission_id}/process")

    queue_response = client.get("/api/v1/capture/manual-review")
    assert queue_response.status_code == 200
    queue_items = queue_response.json()
    assert any(item["submission_id"] == submission_id for item in queue_items)


def test_manual_verify_submission_marks_verified_with_audit_info() -> None:
    client = TestClient(app)
    upload_response = client.post(
        "/api/v1/capture/upload",
        params={"sheet_session_id": "session-cap-003"},
        files={"file": ("answer.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    submission_id = upload_response.json()["submission_id"]
    client.post(f"/api/v1/capture/{submission_id}/process")

    verify_response = client.post(
        f"/api/v1/capture/{submission_id}/manual-review/verify",
        json={
            "reviewer_id": "teacher-001",
            "corrected_roll_number": "R12345",
            "notes": "Confirmed from class register.",
        },
    )
    assert verify_response.status_code == 200
    data = verify_response.json()
    assert data["submission_id"] == submission_id
    assert data["status"] == "verified"
    assert data["extracted_roll_number"] == "R12345"
    assert data["reviewed_by"] == "teacher-001"
    assert data["reviewed_at"]


def test_manual_verify_fails_for_non_review_status() -> None:
    client = TestClient(app)
    upload_response = client.post(
        "/api/v1/capture/upload",
        params={"sheet_session_id": "session-cap-004"},
        files={"file": ("answer.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    submission_id = upload_response.json()["submission_id"]

    verify_response = client.post(
        f"/api/v1/capture/{submission_id}/manual-review/verify",
        json={"reviewer_id": "teacher-001"},
    )
    assert verify_response.status_code == 400
