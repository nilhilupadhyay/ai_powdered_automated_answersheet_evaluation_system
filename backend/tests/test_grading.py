from fastapi.testclient import TestClient

from app.main import app


def _create_sheet_session(client: TestClient, exam_id: str, sheet_session_id: str) -> None:
    client.post(
        "/api/v1/sheets/generate",
        json={
            "exam_id": exam_id,
            "sheet_session_id": sheet_session_id,
            "total_questions": 5,
            "include_roll_number_box": True,
        },
    )


def _create_verified_submission(client: TestClient, sheet_session_id: str) -> int:
    upload = client.post(
        "/api/v1/capture/upload",
        params={"sheet_session_id": sheet_session_id},
        files={"file": ("answer.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    submission_id = upload.json()["submission_id"]
    client.post(f"/api/v1/capture/{submission_id}/process")
    client.post(
        f"/api/v1/capture/{submission_id}/manual-review/verify",
        json={"reviewer_id": "teacher-001", "corrected_roll_number": "R001"},
    )
    return submission_id


def _create_verified_submission_for_roll(client: TestClient, sheet_session_id: str, roll_number: str) -> int:
    upload = client.post(
        "/api/v1/capture/upload",
        params={"sheet_session_id": sheet_session_id},
        files={"file": ("answer.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    submission_id = upload.json()["submission_id"]
    client.post(f"/api/v1/capture/{submission_id}/process")
    client.post(
        f"/api/v1/capture/{submission_id}/manual-review/verify",
        json={"reviewer_id": "teacher-001", "corrected_roll_number": roll_number},
    )
    return submission_id


def _create_verified_submission_for_roll(client: TestClient, sheet_session_id: str, roll_number: str) -> int:
    upload = client.post(
        "/api/v1/capture/upload",
        params={"sheet_session_id": sheet_session_id},
        files={"file": ("answer.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    submission_id = upload.json()["submission_id"]
    client.post(f"/api/v1/capture/{submission_id}/process")
    client.post(
        f"/api/v1/capture/{submission_id}/manual-review/verify",
        json={"reviewer_id": "teacher-001", "corrected_roll_number": roll_number},
    )
    return submission_id


def test_exact_grading_for_verified_submission() -> None:
    client = TestClient(app)
    submission_id = _create_verified_submission(client, "session-grade-001")

    response = client.post(
        f"/api/v1/grading/{submission_id}/exact",
        json={
            "liberality": "moderate",
            "questions": [
                {
                    "question_no": 1,
                    "model_answer": "Photosynthesis converts light energy into chemical energy.",
                    "student_answer": "Photosynthesis converts light energy into chemical energy.",
                    "max_marks": 5,
                }
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grading_mode"] == "exact"
    assert data["total_awarded"] == 5.0
    assert data["total_max"] == 5.0
    assert data["grades"][0]["llm_fallback_used"] is False
    assert data["grades"][0]["prompt_version"] is None


def test_llm_grading_requires_verified_submission() -> None:
    client = TestClient(app)
    upload = client.post(
        "/api/v1/capture/upload",
        params={"sheet_session_id": "session-grade-002"},
        files={"file": ("answer.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    submission_id = upload.json()["submission_id"]

    response = client.post(
        f"/api/v1/grading/{submission_id}/llm",
        json={
            "liberality": "liberal",
            "questions": [
                {
                    "question_no": 1,
                    "model_answer": "Newton's second law is F = ma.",
                    "student_answer": "Second law says F=ma.",
                    "max_marks": 4,
                }
            ],
        },
    )
    assert response.status_code == 400


def test_llm_grading_returns_audit_metadata() -> None:
    client = TestClient(app)
    submission_id = _create_verified_submission(client, "session-grade-003")

    response = client.post(
        f"/api/v1/grading/{submission_id}/llm",
        json={
            "liberality": "moderate",
            "questions": [
                {
                    "question_no": 1,
                    "model_answer": "Water boils at 100 C at sea level.",
                    "student_answer": "At sea level, water boils at 100C.",
                    "max_marks": 3,
                }
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grading_mode"] == "llm"
    assert data["grades"][0]["prompt_version"] == "v1"
    assert data["grades"][0]["llm_provider"] == "gemini"
    assert data["grades"][0]["llm_fallback_used"] is True


def test_get_submission_grades_returns_persisted_history() -> None:
    client = TestClient(app)
    submission_id = _create_verified_submission(client, "session-grade-004")

    client.post(
        f"/api/v1/grading/{submission_id}/exact",
        json={
            "liberality": "moderate",
            "questions": [
                {
                    "question_no": 1,
                    "model_answer": "Earth revolves around the Sun.",
                    "student_answer": "Earth revolves around the Sun.",
                    "max_marks": 2,
                },
                {
                    "question_no": 2,
                    "model_answer": "Plants release oxygen.",
                    "student_answer": "Plants release oxygen.",
                    "max_marks": 3,
                },
            ],
        },
    )

    history_response = client.get(f"/api/v1/grading/{submission_id}")
    assert history_response.status_code == 200
    data = history_response.json()
    assert data["submission_id"] == submission_id
    assert data["grading_mode"] == "exact"
    assert data["total_awarded"] == 5.0
    assert data["total_max"] == 5.0
    assert len(data["grades"]) == 2


def test_get_submission_grades_not_found_when_ungraded() -> None:
    client = TestClient(app)
    submission_id = _create_verified_submission(client, "session-grade-005")
    response = client.get(f"/api/v1/grading/{submission_id}")
    assert response.status_code == 404


def test_student_report_by_roll_and_exam_returns_latest_graded_submission() -> None:
    client = TestClient(app)
    exam_id = "exam-physics-001"
    _create_sheet_session(client, exam_id, "session-grade-006")
    _create_sheet_session(client, exam_id, "session-grade-007")

    first_submission = _create_verified_submission(client, "session-grade-006")
    second_submission = _create_verified_submission(client, "session-grade-007")

    client.post(
        f"/api/v1/grading/{first_submission}/exact",
        json={
            "liberality": "moderate",
            "questions": [
                {"question_no": 1, "model_answer": "A", "student_answer": "A", "max_marks": 2},
            ],
        },
    )
    client.post(
        f"/api/v1/grading/{second_submission}/exact",
        json={
            "liberality": "moderate",
            "questions": [
                {"question_no": 1, "model_answer": "A", "student_answer": "A", "max_marks": 3},
            ],
        },
    )

    report = client.get("/api/v1/grading/report/student", params={"exam_id": exam_id, "roll_number": "R001"})
    assert report.status_code == 200
    data = report.json()
    assert data["exam_id"] == exam_id
    assert data["roll_number"] == "R001"
    assert data["submission_id"] == second_submission
    assert data["total_awarded"] == 3.0
    assert data["total_max"] == 3.0


def test_student_report_not_found_for_unknown_roll() -> None:
    client = TestClient(app)
    report = client.get(
        "/api/v1/grading/report/student",
        params={"exam_id": "exam-physics-001", "roll_number": "UNKNOWN"},
    )
    assert report.status_code == 404


def test_exam_class_report_returns_leaderboard_and_question_averages() -> None:
    client = TestClient(app)
    exam_id = "exam-math-analytics-001"
    _create_sheet_session(client, exam_id, "session-grade-101")
    _create_sheet_session(client, exam_id, "session-grade-102")
    _create_sheet_session(client, exam_id, "session-grade-103")

    sub_a = _create_verified_submission_for_roll(client, "session-grade-101", "R001")
    sub_b = _create_verified_submission_for_roll(client, "session-grade-102", "R002")
    sub_c = _create_verified_submission_for_roll(client, "session-grade-103", "R003")

    client.post(
        f"/api/v1/grading/{sub_a}/exact",
        json={
            "liberality": "moderate",
            "questions": [
                {"question_no": 1, "model_answer": "A", "student_answer": "A", "max_marks": 5},
                {"question_no": 2, "model_answer": "B", "student_answer": "B", "max_marks": 5},
            ],
        },
    )
    client.post(
        f"/api/v1/grading/{sub_b}/exact",
        json={
            "liberality": "moderate",
            "questions": [
                {"question_no": 1, "model_answer": "A", "student_answer": "A", "max_marks": 5},
                {"question_no": 2, "model_answer": "B", "student_answer": "X", "max_marks": 5},
            ],
        },
    )
    client.post(
        f"/api/v1/grading/{sub_c}/exact",
        json={
            "liberality": "moderate",
            "questions": [
                {"question_no": 1, "model_answer": "A", "student_answer": "X", "max_marks": 5},
                {"question_no": 2, "model_answer": "B", "student_answer": "X", "max_marks": 5},
            ],
        },
    )

    report = client.get("/api/v1/grading/report/exam", params={"exam_id": exam_id})
    assert report.status_code == 200
    data = report.json()
    assert data["exam_id"] == exam_id
    assert data["student_count"] == 3
    assert data["leaderboard"][0]["roll_number"] == "R001"
    assert data["leaderboard"][0]["rank"] == 1
    assert len(data["question_averages"]) == 2
    assert data["question_averages"][0]["question_no"] == 1


def test_exam_class_report_not_found_for_empty_exam() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/grading/report/exam", params={"exam_id": "exam-none"})
    assert response.status_code == 404


def test_exam_class_report_returns_leaderboard_and_question_averages() -> None:
    client = TestClient(app)
    exam_id = "exam-math-analytics-001"
    _create_sheet_session(client, exam_id, "session-grade-101")
    _create_sheet_session(client, exam_id, "session-grade-102")
    _create_sheet_session(client, exam_id, "session-grade-103")

    sub_a = _create_verified_submission_for_roll(client, "session-grade-101", "R001")
    sub_b = _create_verified_submission_for_roll(client, "session-grade-102", "R002")
    sub_c = _create_verified_submission_for_roll(client, "session-grade-103", "R003")

    client.post(
        f"/api/v1/grading/{sub_a}/exact",
        json={
            "liberality": "moderate",
            "questions": [
                {"question_no": 1, "model_answer": "A", "student_answer": "A", "max_marks": 5},
                {"question_no": 2, "model_answer": "B", "student_answer": "B", "max_marks": 5},
            ],
        },
    )
    client.post(
        f"/api/v1/grading/{sub_b}/exact",
        json={
            "liberality": "moderate",
            "questions": [
                {"question_no": 1, "model_answer": "A", "student_answer": "A", "max_marks": 5},
                {"question_no": 2, "model_answer": "B", "student_answer": "X", "max_marks": 5},
            ],
        },
    )
    client.post(
        f"/api/v1/grading/{sub_c}/exact",
        json={
            "liberality": "moderate",
            "questions": [
                {"question_no": 1, "model_answer": "A", "student_answer": "X", "max_marks": 5},
                {"question_no": 2, "model_answer": "B", "student_answer": "X", "max_marks": 5},
            ],
        },
    )

    report = client.get("/api/v1/grading/report/exam", params={"exam_id": exam_id})
    assert report.status_code == 200
    data = report.json()
    assert data["exam_id"] == exam_id
    assert data["student_count"] == 3
    assert data["leaderboard"][0]["roll_number"] == "R001"
    assert data["leaderboard"][0]["rank"] == 1
    assert len(data["question_averages"]) == 2
    assert data["question_averages"][0]["question_no"] == 1


def test_exam_class_report_not_found_for_empty_exam() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/grading/report/exam", params={"exam_id": "exam-none"})
    assert response.status_code == 404
