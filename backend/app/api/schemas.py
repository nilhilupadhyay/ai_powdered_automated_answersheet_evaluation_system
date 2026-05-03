from pydantic import BaseModel, Field


class GenerateSheetRequest(BaseModel):
    exam_id: str = Field(..., min_length=1, description="Exam identifier")
    sheet_session_id: str = Field(..., min_length=1, description="Unique sheet session ID")
    total_questions: int = Field(..., ge=1, le=100)
    include_roll_number_box: bool = True


class GenerateSheetResponse(BaseModel):
    filename: str
    qr_payload: str
    pdf_base64: str


class CaptureUploadResponse(BaseModel):
    submission_id: int
    file_path: str
    status: str


class ProcessSubmissionResponse(BaseModel):
    submission_id: int
    qr_payload: str | None
    extracted_roll_number: str | None
    ocr_confidence: float | None
    status: str


class VerifySubmissionRequest(BaseModel):
    reviewer_id: str = Field(..., min_length=1, max_length=100)
    corrected_roll_number: str | None = Field(default=None, min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=1000)


class VerifySubmissionResponse(BaseModel):
    submission_id: int
    status: str
    extracted_roll_number: str | None
    reviewed_by: str
    reviewed_at: str


class GradeQuestion(BaseModel):
    question_no: int = Field(..., ge=1)
    question_text: str | None = None
    model_answer: str = Field(..., min_length=1)
    student_answer: str = Field(..., min_length=1)
    max_marks: float = Field(..., gt=0)


class GradeSubmissionRequest(BaseModel):
    liberality: str = Field(default="moderate", pattern="^(strict|moderate|liberal)$")
    questions: list[GradeQuestion] = Field(..., min_length=1)


class GradeItemResponse(BaseModel):
    question_no: int
    awarded_marks: float
    max_marks: float
    grading_mode: str
    feedback: str | None
    llm_provider: str | None = None
    llm_model: str | None = None
    prompt_version: str | None = None
    llm_response_id: str | None = None
    llm_fallback_used: bool = False


class GradeSubmissionResponse(BaseModel):
    submission_id: int
    grading_mode: str
    total_awarded: float
    total_max: float
    grades: list[GradeItemResponse]


class StudentReportResponse(BaseModel):
    exam_id: str
    roll_number: str
    submission_id: int
    grading_mode: str
    total_awarded: float
    total_max: float
    grades: list[GradeItemResponse]


class ClassLeaderboardItem(BaseModel):
    rank: int
    roll_number: str
    submission_id: int
    total_awarded: float
    total_max: float
    percentage: float


class ClassQuestionAverageItem(BaseModel):
    question_no: int
    average_awarded: float
    average_max: float
    average_percentage: float


class ClassReportResponse(BaseModel):
    exam_id: str
    student_count: int
    leaderboard: list[ClassLeaderboardItem]
    question_averages: list[ClassQuestionAverageItem]
