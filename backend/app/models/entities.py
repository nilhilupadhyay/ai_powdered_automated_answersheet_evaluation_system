from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SubmissionStatus(str, Enum):
    uploaded = "uploaded"
    parsed = "parsed"
    verified = "verified"
    needs_manual_review = "needs_manual_review"
    failed = "failed"


class SheetSession(Base):
    __tablename__ = "sheet_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_id: Mapped[str] = mapped_column(String(100), index=True)
    sheet_session_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    total_questions: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sheet_session_id: Mapped[str] = mapped_column(String(100), index=True)
    image_path: Mapped[str] = mapped_column(Text)
    qr_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_roll_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[SubmissionStatus] = mapped_column(
        SqlEnum(SubmissionStatus), default=SubmissionStatus.uploaded, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class SubmissionReview(Base):
    __tablename__ = "submission_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), index=True)
    reviewer_id: Mapped[str] = mapped_column(String(100), index=True)
    corrected_roll_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class GradingMode(str, Enum):
    exact = "exact"
    llm = "llm"


class Liberality(str, Enum):
    strict = "strict"
    moderate = "moderate"
    liberal = "liberal"


class Grade(Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), index=True)
    question_no: Mapped[int] = mapped_column(Integer, index=True)
    max_marks: Mapped[float] = mapped_column(Float, nullable=False)
    awarded_marks: Mapped[float] = mapped_column(Float, nullable=False)
    grading_mode: Mapped[GradingMode] = mapped_column(SqlEnum(GradingMode), nullable=False)
    liberality: Mapped[Liberality] = mapped_column(SqlEnum(Liberality), nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_answer: Mapped[str] = mapped_column(Text)
    student_answer: Mapped[str] = mapped_column(Text)
    llm_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_response_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    llm_fallback_used: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
