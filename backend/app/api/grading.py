from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import (
    ClassLeaderboardItem,
    ClassQuestionAverageItem,
    ClassReportResponse,
    GradeItemResponse,
    GradeSubmissionRequest,
    GradeSubmissionResponse,
    StudentReportResponse,
)
from app.db.session import get_db
from app.models.entities import Grade, GradingMode, Liberality, SheetSession, Submission, SubmissionStatus
from app.services.grading import grade_exact_match, grade_with_llm


router = APIRouter()


def _validate_submission_for_grading(submission_id: int, db: Session) -> Submission:
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if submission.status != SubmissionStatus.verified:
        raise HTTPException(status_code=400, detail="Submission must be verified before grading")
    return submission


def _to_grade_item_response(grade: Grade) -> GradeItemResponse:
    return GradeItemResponse(
        question_no=grade.question_no,
        awarded_marks=grade.awarded_marks,
        max_marks=grade.max_marks,
        grading_mode=grade.grading_mode.value,
        feedback=grade.feedback,
        llm_provider=grade.llm_provider,
        llm_model=grade.llm_model,
        prompt_version=grade.prompt_version,
        llm_response_id=grade.llm_response_id,
        llm_fallback_used=grade.llm_fallback_used,
    )


@router.get("/{submission_id}", response_model=GradeSubmissionResponse)
def get_submission_grades(submission_id: int, db: Session = Depends(get_db)) -> GradeSubmissionResponse:
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    grades = db.query(Grade).filter(Grade.submission_id == submission_id).order_by(Grade.question_no.asc()).all()
    if not grades:
        raise HTTPException(status_code=404, detail="No grades found for submission")

    grade_items = [_to_grade_item_response(grade) for grade in grades]
    modes = {grade.grading_mode.value for grade in grades}
    grading_mode = modes.pop() if len(modes) == 1 else "mixed"
    total_awarded = round(sum(grade.awarded_marks for grade in grades), 2)
    total_max = round(sum(grade.max_marks for grade in grades), 2)

    return GradeSubmissionResponse(
        submission_id=submission_id,
        grading_mode=grading_mode,
        total_awarded=total_awarded,
        total_max=total_max,
        grades=grade_items,
    )


@router.get("/report/student", response_model=StudentReportResponse)
def get_student_report(exam_id: str, roll_number: str, db: Session = Depends(get_db)) -> StudentReportResponse:
    candidates = (
        db.query(Submission)
        .join(SheetSession, SheetSession.sheet_session_id == Submission.sheet_session_id)
        .filter(
            SheetSession.exam_id == exam_id,
            Submission.extracted_roll_number == roll_number,
            Submission.status == SubmissionStatus.verified,
        )
        .order_by(Submission.created_at.desc())
        .all()
    )
    if not candidates:
        raise HTTPException(status_code=404, detail="No verified submissions found for student in this exam")

    selected_submission = None
    selected_grades: list[Grade] = []
    for candidate in candidates:
        grades = (
            db.query(Grade)
            .filter(Grade.submission_id == candidate.id)
            .order_by(Grade.question_no.asc())
            .all()
        )
        if grades:
            selected_submission = candidate
            selected_grades = grades
            break

    if selected_submission is None:
        raise HTTPException(status_code=404, detail="No grades found for student in this exam")

    grade_items = [_to_grade_item_response(grade) for grade in selected_grades]
    modes = {grade.grading_mode.value for grade in selected_grades}
    grading_mode = modes.pop() if len(modes) == 1 else "mixed"
    total_awarded = round(sum(grade.awarded_marks for grade in selected_grades), 2)
    total_max = round(sum(grade.max_marks for grade in selected_grades), 2)

    return StudentReportResponse(
        exam_id=exam_id,
        roll_number=roll_number,
        submission_id=selected_submission.id,
        grading_mode=grading_mode,
        total_awarded=total_awarded,
        total_max=total_max,
        grades=grade_items,
    )


@router.get("/report/exam", response_model=ClassReportResponse)
def get_exam_class_report(exam_id: str, db: Session = Depends(get_db)) -> ClassReportResponse:
    submissions = (
        db.query(Submission)
        .join(SheetSession, SheetSession.sheet_session_id == Submission.sheet_session_id)
        .filter(SheetSession.exam_id == exam_id, Submission.status == SubmissionStatus.verified)
        .order_by(Submission.created_at.desc())
        .all()
    )
    if not submissions:
        raise HTTPException(status_code=404, detail="No verified submissions found for exam")

    latest_by_roll: dict[str, Submission] = {}
    for submission in submissions:
        if not submission.extracted_roll_number:
            continue
        if submission.extracted_roll_number not in latest_by_roll:
            latest_by_roll[submission.extracted_roll_number] = submission

    leaderboard_seed: list[tuple[str, Submission, list[Grade], float, float]] = []
    for roll, submission in latest_by_roll.items():
        grades = (
            db.query(Grade)
            .filter(Grade.submission_id == submission.id)
            .order_by(Grade.question_no.asc())
            .all()
        )
        if not grades:
            continue
        total_awarded = round(sum(grade.awarded_marks for grade in grades), 2)
        total_max = round(sum(grade.max_marks for grade in grades), 2)
        leaderboard_seed.append((roll, submission, grades, total_awarded, total_max))

    if not leaderboard_seed:
        raise HTTPException(status_code=404, detail="No grades found for verified submissions in exam")

    leaderboard_seed.sort(key=lambda row: (-row[3], row[0]))
    leaderboard: list[ClassLeaderboardItem] = []
    question_buckets: dict[int, list[tuple[float, float]]] = {}

    for idx, (roll, submission, grades, total_awarded, total_max) in enumerate(leaderboard_seed, start=1):
        percentage = round((total_awarded / total_max) * 100, 2) if total_max > 0 else 0.0
        leaderboard.append(
            ClassLeaderboardItem(
                rank=idx,
                roll_number=roll,
                submission_id=submission.id,
                total_awarded=total_awarded,
                total_max=total_max,
                percentage=percentage,
            )
        )
        for grade in grades:
            question_buckets.setdefault(grade.question_no, []).append((grade.awarded_marks, grade.max_marks))

    question_averages: list[ClassQuestionAverageItem] = []
    for question_no in sorted(question_buckets):
        values = question_buckets[question_no]
        avg_awarded = round(sum(v[0] for v in values) / len(values), 2)
        avg_max = round(sum(v[1] for v in values) / len(values), 2)
        avg_pct = round((avg_awarded / avg_max) * 100, 2) if avg_max > 0 else 0.0
        question_averages.append(
            ClassQuestionAverageItem(
                question_no=question_no,
                average_awarded=avg_awarded,
                average_max=avg_max,
                average_percentage=avg_pct,
            )
        )

    return ClassReportResponse(
        exam_id=exam_id,
        student_count=len(leaderboard),
        leaderboard=leaderboard,
        question_averages=question_averages,
    )


@router.post("/{submission_id}/exact", response_model=GradeSubmissionResponse)
def grade_submission_exact(
    submission_id: int,
    payload: GradeSubmissionRequest,
    db: Session = Depends(get_db),
) -> GradeSubmissionResponse:
    _validate_submission_for_grading(submission_id, db)
    liberality = Liberality(payload.liberality)

    results: list[GradeItemResponse] = []
    total_awarded = 0.0
    total_max = 0.0

    for item in payload.questions:
        grade_result = grade_exact_match(
            student_answer=item.student_answer,
            model_answer=item.model_answer,
            max_marks=item.max_marks,
        )
        grade = Grade(
            submission_id=submission_id,
            question_no=item.question_no,
            question_text=item.question_text,
            max_marks=item.max_marks,
            awarded_marks=grade_result.awarded_marks,
            grading_mode=GradingMode.exact,
            liberality=liberality,
            feedback=grade_result.feedback,
            model_answer=item.model_answer,
            student_answer=item.student_answer,
            llm_provider=grade_result.llm_provider,
            llm_model=grade_result.llm_model,
            prompt_version=grade_result.prompt_version,
            llm_response_id=grade_result.llm_response_id,
            llm_fallback_used=grade_result.llm_fallback_used,
        )
        db.add(grade)
        results.append(_to_grade_item_response(grade))
        total_awarded += grade_result.awarded_marks
        total_max += item.max_marks

    db.commit()

    return GradeSubmissionResponse(
        submission_id=submission_id,
        grading_mode=GradingMode.exact.value,
        total_awarded=round(total_awarded, 2),
        total_max=round(total_max, 2),
        grades=results,
    )


@router.post("/{submission_id}/llm", response_model=GradeSubmissionResponse)
def grade_submission_llm(
    submission_id: int,
    payload: GradeSubmissionRequest,
    db: Session = Depends(get_db),
) -> GradeSubmissionResponse:
    _validate_submission_for_grading(submission_id, db)
    liberality = Liberality(payload.liberality)

    results: list[GradeItemResponse] = []
    total_awarded = 0.0
    total_max = 0.0

    for item in payload.questions:
        grade_result = grade_with_llm(
            question_text=item.question_text,
            student_answer=item.student_answer,
            model_answer=item.model_answer,
            max_marks=item.max_marks,
            liberality=liberality,
        )
        grade = Grade(
            submission_id=submission_id,
            question_no=item.question_no,
            question_text=item.question_text,
            max_marks=item.max_marks,
            awarded_marks=grade_result.awarded_marks,
            grading_mode=GradingMode.llm,
            liberality=liberality,
            feedback=grade_result.feedback,
            model_answer=item.model_answer,
            student_answer=item.student_answer,
            llm_provider=grade_result.llm_provider,
            llm_model=grade_result.llm_model,
            prompt_version=grade_result.prompt_version,
            llm_response_id=grade_result.llm_response_id,
            llm_fallback_used=grade_result.llm_fallback_used,
        )
        db.add(grade)
        results.append(_to_grade_item_response(grade))
        total_awarded += grade_result.awarded_marks
        total_max += item.max_marks

    db.commit()

    return GradeSubmissionResponse(
        submission_id=submission_id,
        grading_mode=GradingMode.llm.value,
        total_awarded=round(total_awarded, 2),
        total_max=round(total_max, 2),
        grades=results,
    )
