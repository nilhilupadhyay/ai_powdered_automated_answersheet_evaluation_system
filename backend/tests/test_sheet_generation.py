from fastapi.testclient import TestClient

from app.main import app


def test_sheet_generation_returns_payload() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/sheets/generate",
        json={
            "exam_id": "math-midterm-01",
            "sheet_session_id": "session-abc-001",
            "total_questions": 5,
            "include_roll_number_box": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "session-abc-001.pdf"
    assert "sheet_session:session-abc-001|exam:math-midterm-01" == data["qr_payload"]
    assert len(data["pdf_base64"]) > 100
