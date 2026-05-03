export type GradeItem = {
  question_no: number;
  awarded_marks: number;
  max_marks: number;
  grading_mode: string;
  feedback?: string | null;
};

export type GradeQuestion = {
  question_no: number;
  question_text?: string;
  model_answer: string;
  student_answer: string;
  max_marks: number;
};

export type GradeSubmissionResponse = {
  submission_id: number;
  grading_mode: string;
  total_awarded: number;
  total_max: number;
  grades: GradeItem[];
};

export type StudentReport = {
  exam_id: string;
  roll_number: string;
  submission_id: number;
  grading_mode: string;
  total_awarded: number;
  total_max: number;
  grades: GradeItem[];
};

export type LeaderboardItem = {
  rank: number;
  roll_number: string;
  submission_id: number;
  total_awarded: number;
  total_max: number;
  percentage: number;
};

export type QuestionAverage = {
  question_no: number;
  average_awarded: number;
  average_max: number;
  average_percentage: number;
};

export type ClassReport = {
  exam_id: string;
  student_count: number;
  leaderboard: LeaderboardItem[];
  question_averages: QuestionAverage[];
};

export type ManualReviewItem = {
  submission_id: number;
  qr_payload: string | null;
  extracted_roll_number: string | null;
  ocr_confidence: number | null;
  status: string;
};

export type VerifySubmissionResponse = {
  submission_id: number;
  status: string;
  extracted_roll_number: string | null;
  reviewed_by: string;
  reviewed_at: string;
};

export type GenerateSheetResponse = {
  filename: string;
  qr_payload: string;
  pdf_base64: string;
};

export type CaptureUploadResponse = {
  submission_id: number;
  file_path: string;
  status: string;
};

export type ProcessSubmissionResponse = {
  submission_id: number;
  qr_payload: string | null;
  extracted_roll_number: string | null;
  ocr_confidence: number | null;
  status: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

async function requestJsonWithBody<T>(path: string, payload: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchStudentReport(examId: string, rollNumber: string): Promise<StudentReport> {
  const params = new URLSearchParams({ exam_id: examId, roll_number: rollNumber });
  return requestJson<StudentReport>(`/api/v1/grading/report/student?${params.toString()}`);
}

export function fetchClassReport(examId: string): Promise<ClassReport> {
  const params = new URLSearchParams({ exam_id: examId });
  return requestJson<ClassReport>(`/api/v1/grading/report/exam?${params.toString()}`);
}

export function fetchManualReviewQueue(): Promise<ManualReviewItem[]> {
  return requestJson<ManualReviewItem[]>("/api/v1/capture/manual-review");
}

export function verifyManualReviewSubmission(
  submissionId: number,
  reviewerId: string,
  correctedRollNumber: string,
  notes: string
): Promise<VerifySubmissionResponse> {
  return requestJsonWithBody<VerifySubmissionResponse>(
    `/api/v1/capture/${submissionId}/manual-review/verify`,
    {
      reviewer_id: reviewerId,
      corrected_roll_number: correctedRollNumber,
      notes
    }
  );
}

export function generateSheet(
  examId: string,
  sheetSessionId: string,
  totalQuestions: number,
  includeRollNumberBox: boolean
): Promise<GenerateSheetResponse> {
  return requestJsonWithBody<GenerateSheetResponse>("/api/v1/sheets/generate", {
    exam_id: examId,
    sheet_session_id: sheetSessionId,
    total_questions: totalQuestions,
    include_roll_number_box: includeRollNumberBox
  });
}

export async function uploadSheet(sheetSessionId: string, file: File): Promise<CaptureUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/api/v1/capture/upload?sheet_session_id=${encodeURIComponent(sheetSessionId)}`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Upload failed with status ${response.status}`);
  }
  return response.json();
}

export function processSubmission(submissionId: number): Promise<ProcessSubmissionResponse> {
  return requestJsonWithBody<ProcessSubmissionResponse>(`/api/v1/capture/${submissionId}/process`, {});
}

export function gradeSubmissionExact(
  submissionId: number,
  liberality: string,
  questions: GradeQuestion[]
): Promise<GradeSubmissionResponse> {
  return requestJsonWithBody<GradeSubmissionResponse>(`/api/v1/grading/${submissionId}/exact`, {
    liberality,
    questions
  });
}

export function gradeSubmissionLlm(
  submissionId: number,
  liberality: string,
  questions: GradeQuestion[]
): Promise<GradeSubmissionResponse> {
  return requestJsonWithBody<GradeSubmissionResponse>(`/api/v1/grading/${submissionId}/llm`, {
    liberality,
    questions
  });
}
