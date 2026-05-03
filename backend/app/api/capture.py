from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.schemas import (
    CaptureUploadResponse,
    ProcessSubmissionResponse,
    VerifySubmissionRequest,
    VerifySubmissionResponse,
)
from app.core.config import settings
from app.models.entities import Submission, SubmissionReview, SubmissionStatus
from app.services.capture_pipeline import align_document, decode_qr_payload, ensure_uploads_dir, extract_roll_number
from app.db.session import get_db


router = APIRouter()


@router.post("/upload", response_model=CaptureUploadResponse)
async def upload_sheet(
    sheet_session_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> CaptureUploadResponse:
    upload_dir = ensure_uploads_dir()
    file_path = upload_dir / f"{sheet_session_id}_{file.filename}"

    contents = await file.read()
    file_path.write_bytes(contents)

    submission = Submission(sheet_session_id=sheet_session_id, image_path=str(file_path))
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return CaptureUploadResponse(
        submission_id=submission.id,
        file_path=str(file_path),
        status=submission.status.value,
    )


@router.post("/{submission_id}/process", response_model=ProcessSubmissionResponse)
def process_submission(submission_id: int, db: Session = Depends(get_db)) -> ProcessSubmissionResponse:
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if not Path(submission.image_path).exists():
        submission.status = SubmissionStatus.failed
        db.commit()
        raise HTTPException(status_code=400, detail="Uploaded image file missing")

    align_document(submission.image_path)

    qr_payload = decode_qr_payload(submission.image_path)
    roll_number, confidence = extract_roll_number(submission.image_path)

    submission.qr_payload = qr_payload
    submission.extracted_roll_number = roll_number
    submission.ocr_confidence = confidence
    if not qr_payload or not roll_number or confidence < settings.ocr_confidence_threshold:
        submission.status = SubmissionStatus.needs_manual_review
    else:
        submission.status = SubmissionStatus.verified

    db.add(submission)
    db.commit()
    db.refresh(submission)

    return ProcessSubmissionResponse(
        submission_id=submission.id,
        qr_payload=submission.qr_payload,
        extracted_roll_number=submission.extracted_roll_number,
        ocr_confidence=submission.ocr_confidence,
        status=submission.status.value,
    )


@router.get("/manual-review", response_model=list[ProcessSubmissionResponse])
def list_manual_review_queue(db: Session = Depends(get_db)) -> list[ProcessSubmissionResponse]:
    items = (
        db.query(Submission)
        .filter(Submission.status == SubmissionStatus.needs_manual_review)
        .order_by(Submission.created_at.desc())
        .all()
    )
    return [
        ProcessSubmissionResponse(
            submission_id=item.id,
            qr_payload=item.qr_payload,
            extracted_roll_number=item.extracted_roll_number,
            ocr_confidence=item.ocr_confidence,
            status=item.status.value,
        )
        for item in items
    ]


@router.post("/{submission_id}/manual-review/verify", response_model=VerifySubmissionResponse)
def verify_submission_manually(
    submission_id: int,
    payload: VerifySubmissionRequest,
    db: Session = Depends(get_db),
) -> VerifySubmissionResponse:
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    if submission.status != SubmissionStatus.needs_manual_review:
        raise HTTPException(status_code=400, detail="Submission is not in manual review queue")

    if payload.corrected_roll_number:
        submission.extracted_roll_number = payload.corrected_roll_number

    submission.status = SubmissionStatus.verified
    review = SubmissionReview(
        submission_id=submission.id,
        reviewer_id=payload.reviewer_id,
        corrected_roll_number=payload.corrected_roll_number,
        notes=payload.notes,
    )
    db.add(submission)
    db.add(review)
    db.commit()
    db.refresh(submission)
    db.refresh(review)

    return VerifySubmissionResponse(
        submission_id=submission.id,
        status=submission.status.value,
        extracted_roll_number=submission.extracted_roll_number,
        reviewed_by=review.reviewer_id,
        reviewed_at=review.created_at.isoformat(),
    )
