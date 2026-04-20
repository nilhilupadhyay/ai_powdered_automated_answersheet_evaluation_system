from fastapi import APIRouter
from sqlalchemy.orm import Session
from fastapi import Depends

from app.api.schemas import GenerateSheetRequest, GenerateSheetResponse
from app.db.session import get_db
from app.models.entities import SheetSession
from app.services.sheet_generator import render_sheet_pdf_base64


router = APIRouter()


@router.post("/generate", response_model=GenerateSheetResponse)
def generate_sheet(payload: GenerateSheetRequest, db: Session = Depends(get_db)) -> GenerateSheetResponse:
    qr_payload, pdf_base64 = render_sheet_pdf_base64(
        exam_id=payload.exam_id,
        sheet_session_id=payload.sheet_session_id,
        total_questions=payload.total_questions,
        include_roll_number_box=payload.include_roll_number_box,
    )
    existing = db.query(SheetSession).filter(SheetSession.sheet_session_id == payload.sheet_session_id).first()
    if existing is None:
        db.add(
            SheetSession(
                exam_id=payload.exam_id,
                sheet_session_id=payload.sheet_session_id,
                total_questions=payload.total_questions,
            )
        )
        db.commit()
    return GenerateSheetResponse(
        filename=f"{payload.sheet_session_id}.pdf",
        qr_payload=qr_payload,
        pdf_base64=pdf_base64,
    )
