"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  ClassReport,
  ManualReviewItem,
  StudentReport,
  GradeQuestion,
  fetchClassReport,
  fetchManualReviewQueue,
  fetchStudentReport,
  generateSheet,
  gradeSubmissionExact,
  gradeSubmissionLlm,
  processSubmission,
  uploadSheet,
  verifyManualReviewSubmission
} from "../lib/api";

type TabId = "generate-sheet" | "capture" | "grading" | "analytics" | "manual-review";
type FormState = { reviewerId: string; correctedRollNumber: string; notes: string };

export default function TeacherDashboard({ initialTab = "analytics" }: { initialTab?: TabId }) {
  const [activeTab, setActiveTab] = useState<TabId>(initialTab);
  const [examId, setExamId] = useState("");
  const [rollNumber, setRollNumber] = useState("");
  const [studentReport, setStudentReport] = useState<StudentReport | null>(null);
  const [classReport, setClassReport] = useState<ClassReport | null>(null);
  const [analyticsError, setAnalyticsError] = useState("");
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [queueItems, setQueueItems] = useState<ManualReviewItem[]>([]);
  const [queueForms, setQueueForms] = useState<Record<number, FormState>>({});
  const [queueError, setQueueError] = useState("");
  const [queueMessage, setQueueMessage] = useState("");
  const [queueLoading, setQueueLoading] = useState(false);

  // Generate Sheet State
  const [genExamId, setGenExamId] = useState("");
  const [genSessionId, setGenSessionId] = useState("");
  const [genTotalQuestions, setGenTotalQuestions] = useState(10);
  const [genIncludeRoll, setGenIncludeRoll] = useState(true);
  const [genLoading, setGenLoading] = useState(false);
  const [genError, setGenError] = useState("");
  const [genPdfUrl, setGenPdfUrl] = useState<{ url: string; filename: string } | null>(null);

  // Capture State
  const [capSessionId, setCapSessionId] = useState("");
  const [capFile, setCapFile] = useState<File | null>(null);
  const [capPreviewUrl, setCapPreviewUrl] = useState("");
  const [capLoading, setCapLoading] = useState(false);
  const [capError, setCapError] = useState("");
  const [capResult, setCapResult] = useState<any>(null);

  // Grading State
  const [gradSubmissionId, setGradSubmissionId] = useState("");
  const [gradLiberality, setGradLiberality] = useState("moderate");
  const [gradQuestions, setGradQuestions] = useState<GradeQuestion[]>([
    { question_no: 1, model_answer: "", student_answer: "", max_marks: 10 }
  ]);
  const [gradLoading, setGradLoading] = useState(false);
  const [gradError, setGradError] = useState("");
  const [gradResult, setGradResult] = useState<any>(null);

  function handleGradQuestionChange(index: number, field: keyof GradeQuestion, value: any) {
    const newQuestions = [...gradQuestions];
    newQuestions[index] = { ...newQuestions[index], [field]: value };
    setGradQuestions(newQuestions);
  }

  function addGradQuestion() {
    setGradQuestions([
      ...gradQuestions,
      { question_no: gradQuestions.length + 1, model_answer: "", student_answer: "", max_marks: 10 }
    ]);
  }

  async function handleGradingSubmit(mode: "exact" | "llm") {
    if (!gradSubmissionId) return;
    setGradError("");
    setGradLoading(true);
    setGradResult(null);
    try {
      const subIdNum = parseInt(gradSubmissionId, 10);
      let res;
      if (mode === "exact") {
        res = await gradeSubmissionExact(subIdNum, gradLiberality, gradQuestions);
      } else {
        res = await gradeSubmissionLlm(subIdNum, gradLiberality, gradQuestions);
      }
      setGradResult(res);
    } catch (err) {
      setGradError(err instanceof Error ? err.message : "Failed to grade submission");
    } finally {
      setGradLoading(false);
    }
  }

  function handleCapFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      setCapFile(file);
      setCapPreviewUrl(URL.createObjectURL(file));
      setCapResult(null);
    }
  }

  async function handleCaptureSubmit(event: FormEvent) {
    event.preventDefault();
    if (!capFile || !capSessionId) return;
    setCapError("");
    setCapLoading(true);
    setCapResult(null);
    try {
      const uploadRes = await uploadSheet(capSessionId, capFile);
      const procRes = await processSubmission(uploadRes.submission_id);
      setCapResult(procRes);
    } catch (err) {
      setCapError(err instanceof Error ? err.message : "Failed to process image");
    } finally {
      setCapLoading(false);
    }
  }

  async function handleGenerateSheet(event: FormEvent) {
    event.preventDefault();
    setGenError("");
    setGenLoading(true);
    setGenPdfUrl(null);
    try {
      const response = await generateSheet(genExamId, genSessionId, genTotalQuestions, genIncludeRoll);
      // Convert base64 to Blob URL
      const byteCharacters = atob(response.pdf_base64);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      setGenPdfUrl({ url, filename: response.filename });
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Failed to generate sheet");
    } finally {
      setGenLoading(false);
    }
  }

  async function loadQueue() {
    setQueueLoading(true);
    setQueueError("");
    try {
      const queue = await fetchManualReviewQueue();
      setQueueItems(queue);
      const nextForms: Record<number, FormState> = {};
      queue.forEach((item) => {
        nextForms[item.submission_id] = {
          reviewerId: "teacher-001",
          correctedRollNumber: item.extracted_roll_number || "",
          notes: ""
        };
      });
      setQueueForms(nextForms);
    } catch (err) {
      setQueueError(err instanceof Error ? err.message : "Failed to load manual review queue");
    } finally {
      setQueueLoading(false);
    }
  }

  useEffect(() => {
    if (activeTab === "manual-review") {
      loadQueue();
    }
  }, [activeTab]);

  function updateQueueForm(submissionId: number, patch: Partial<FormState>) {
    setQueueForms((prev) => ({
      ...prev,
      [submissionId]: { ...prev[submissionId], ...patch }
    }));
  }

  async function handleQueueVerify(event: FormEvent, submissionId: number) {
    event.preventDefault();
    const form = queueForms[submissionId];
    if (!form) return;
    setQueueError("");
    setQueueMessage("");
    try {
      await verifyManualReviewSubmission(
        submissionId,
        form.reviewerId,
        form.correctedRollNumber,
        form.notes
      );
      setQueueMessage(`Submission ${submissionId} verified.`);
      await loadQueue();
    } catch (err) {
      setQueueError(err instanceof Error ? err.message : "Failed to verify submission");
    }
  }

  async function handleStudentReport(event: FormEvent) {
    event.preventDefault();
    setAnalyticsError("");
    setAnalyticsLoading(true);
    try {
      const report = await fetchStudentReport(examId, rollNumber);
      setStudentReport(report);
    } catch (err) {
      setStudentReport(null);
      setAnalyticsError(err instanceof Error ? err.message : "Failed to fetch student report");
    } finally {
      setAnalyticsLoading(false);
    }
  }

  async function handleClassReport(event: FormEvent) {
    event.preventDefault();
    setAnalyticsError("");
    setAnalyticsLoading(true);
    try {
      const report = await fetchClassReport(examId);
      setClassReport(report);
    } catch (err) {
      setClassReport(null);
      setAnalyticsError(err instanceof Error ? err.message : "Failed to fetch class report");
    } finally {
      setAnalyticsLoading(false);
    }
  }

  return (
    <main>
      <div className="row nav-row">
        <button
          className={activeTab === "generate-sheet" ? "tab active-tab" : "tab"}
          onClick={() => setActiveTab("generate-sheet")}
          type="button"
        >
          Generate Sheet
        </button>
        <button
          className={activeTab === "capture" ? "tab active-tab" : "tab"}
          onClick={() => setActiveTab("capture")}
          type="button"
        >
          Capture Photo
        </button>
        <button
          className={activeTab === "grading" ? "tab active-tab" : "tab"}
          onClick={() => setActiveTab("grading")}
          type="button"
        >
          Grading
        </button>
        <button
          className={activeTab === "analytics" ? "tab active-tab" : "tab"}
          onClick={() => setActiveTab("analytics")}
          type="button"
        >
          Analytics
        </button>
        <button
          className={activeTab === "manual-review" ? "tab active-tab" : "tab"}
          onClick={() => setActiveTab("manual-review")}
          type="button"
        >
          Manual Review Queue
        </button>
      </div>
      {activeTab === "generate-sheet" ? (
        <>
          <h1>Generate Answer Sheet</h1>
          <p>Create a printable PDF answer sheet embedded with a unique QR code for the specific session.</p>
          <section className="card">
            <form className="col" onSubmit={handleGenerateSheet}>
              <div className="row">
                <label>
                  Exam ID:
                  <input
                    placeholder="e.g. CS101-Midterm"
                    value={genExamId}
                    onChange={(e) => setGenExamId(e.target.value)}
                    required
                  />
                </label>
                <label>
                  Session ID:
                  <input
                    placeholder="e.g. Sheet-001"
                    value={genSessionId}
                    onChange={(e) => setGenSessionId(e.target.value)}
                    required
                  />
                </label>
              </div>
              <div className="row">
                <label>
                  Total Questions:
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={genTotalQuestions}
                    onChange={(e) => setGenTotalQuestions(parseInt(e.target.value, 10))}
                    required
                  />
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <input
                    type="checkbox"
                    checked={genIncludeRoll}
                    onChange={(e) => setGenIncludeRoll(e.target.checked)}
                  />
                  Include Roll Number Box
                </label>
              </div>
              <button type="submit" disabled={genLoading}>
                {genLoading ? "Generating..." : "Generate PDF"}
              </button>
            </form>
            {genError && <p className="error">{genError}</p>}
            {genPdfUrl && (
              <div style={{ marginTop: "20px" }}>
                <a href={genPdfUrl.url} download={genPdfUrl.filename} className="button-link">
                  Download {genPdfUrl.filename}
                </a>
              </div>
            )}
          </section>
        </>
      ) : activeTab === "capture" ? (
        <>
          <h1>Capture Photo</h1>
          <p>Take a photo of a completed answer sheet to extract roll number and grade it.</p>
          <section className="card">
            <form className="col" onSubmit={handleCaptureSubmit}>
              <div className="row">
                <label>
                  Sheet Session ID:
                  <input
                    placeholder="e.g. Sheet-001"
                    value={capSessionId}
                    onChange={(e) => setCapSessionId(e.target.value)}
                    required
                  />
                </label>
              </div>
              <div className="row">
                <label>
                  Upload or Take Photo:
                  <input
                    type="file"
                    accept="image/*"
                    capture="environment"
                    onChange={handleCapFileChange}
                    required
                  />
                </label>
              </div>
              {capPreviewUrl && (
                <div style={{ margin: "10px 0" }}>
                  <img
                    src={capPreviewUrl}
                    alt="Preview"
                    style={{ maxWidth: "100%", maxHeight: "300px", borderRadius: "8px" }}
                  />
                </div>
              )}
              <button type="submit" disabled={capLoading || !capFile || !capSessionId}>
                {capLoading ? "Processing..." : "Upload & Process"}
              </button>
            </form>
            {capError && <p className="error">{capError}</p>}
            {capResult && (
              <div style={{ marginTop: "20px", padding: "10px", border: "1px solid #4CAF50", borderRadius: "8px" }}>
                <h3 style={{ color: "#4CAF50" }}>Process Complete</h3>
                <p><strong>Status:</strong> {capResult.status}</p>
                <p><strong>QR Payload:</strong> {capResult.qr_payload || "Not detected"}</p>
                <p><strong>Extracted Roll No:</strong> {capResult.extracted_roll_number || "Not found"}</p>
                <p><strong>OCR Confidence:</strong> {capResult.ocr_confidence}</p>
              </div>
            )}
          </section>
        </>
      ) : activeTab === "grading" ? (
        <>
          <h1>Grading Engine</h1>
          <p>Grade extracted answers against model answers using exact matching or LLM.</p>
          <section className="card">
            <div className="row">
              <label>
                Submission ID:
                <input
                  type="number"
                  placeholder="e.g. 1"
                  value={gradSubmissionId}
                  onChange={(e) => setGradSubmissionId(e.target.value)}
                  required
                />
              </label>
              <label>
                Liberality:
                <select value={gradLiberality} onChange={(e) => setGradLiberality(e.target.value)}>
                  <option value="strict">Strict</option>
                  <option value="moderate">Moderate</option>
                  <option value="liberal">Liberal</option>
                </select>
              </label>
            </div>
            
            <div style={{ marginTop: "20px" }}>
              <h3>Questions & Answers</h3>
              {gradQuestions.map((q, idx) => (
                <div key={idx} style={{ padding: "10px", border: "1px solid #ccc", marginBottom: "10px", borderRadius: "5px" }}>
                  <h4>Question {q.question_no}</h4>
                  <div className="row">
                    <label>
                      Max Marks:
                      <input
                        type="number"
                        value={q.max_marks}
                        onChange={(e) => handleGradQuestionChange(idx, "max_marks", parseFloat(e.target.value))}
                      />
                    </label>
                  </div>
                  <div className="row">
                    <label style={{ flex: 1 }}>
                      Model Answer:
                      <textarea
                        rows={3}
                        value={q.model_answer}
                        onChange={(e) => handleGradQuestionChange(idx, "model_answer", e.target.value)}
                        style={{ width: "100%" }}
                      />
                    </label>
                    <label style={{ flex: 1 }}>
                      Student Answer:
                      <textarea
                        rows={3}
                        value={q.student_answer}
                        onChange={(e) => handleGradQuestionChange(idx, "student_answer", e.target.value)}
                        style={{ width: "100%" }}
                      />
                    </label>
                  </div>
                </div>
              ))}
              <button type="button" onClick={addGradQuestion} style={{ marginBottom: "20px" }}>+ Add Question</button>
            </div>

            <div className="row">
              <button type="button" onClick={() => handleGradingSubmit("exact")} disabled={gradLoading || !gradSubmissionId}>
                {gradLoading ? "Grading..." : "Grade via Exact Match"}
              </button>
              <button type="button" onClick={() => handleGradingSubmit("llm")} disabled={gradLoading || !gradSubmissionId}>
                {gradLoading ? "Grading..." : "Grade via LLM"}
              </button>
            </div>

            {gradError && <p className="error">{gradError}</p>}
            {gradResult && (
              <div style={{ marginTop: "20px", padding: "10px", border: "1px solid #4CAF50", borderRadius: "8px" }}>
                <h3 style={{ color: "#4CAF50" }}>Grading Complete ({gradResult.grading_mode})</h3>
                <p><strong>Total Awarded:</strong> {gradResult.total_awarded} / {gradResult.total_max}</p>
                <table style={{ width: "100%", marginTop: "10px" }}>
                  <thead>
                    <tr>
                      <th>Q No</th>
                      <th>Awarded</th>
                      <th>Max</th>
                      <th>Feedback</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gradResult.grades.map((g: any) => (
                      <tr key={g.question_no}>
                        <td>{g.question_no}</td>
                        <td>{g.awarded_marks}</td>
                        <td>{g.max_marks}</td>
                        <td>{g.feedback}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : activeTab === "analytics" ? (
        <>
          <h1>Teacher Analytics Dashboard</h1>
          <p>Use exam ID and roll number to inspect reports from the grading APIs.</p>

          <section className="card">
            <h2>Student Report</h2>
            <form className="row" onSubmit={handleStudentReport}>
              <input
                placeholder="Exam ID"
                value={examId}
                onChange={(event) => setExamId(event.target.value)}
                required
              />
              <input
                placeholder="Roll Number"
                value={rollNumber}
                onChange={(event) => setRollNumber(event.target.value)}
                required
              />
              <button type="submit" disabled={analyticsLoading}>
                {analyticsLoading ? "Loading..." : "Fetch Student Report"}
              </button>
            </form>
            {studentReport && (
              <div>
                <p>
                  Submission #{studentReport.submission_id} | Score {studentReport.total_awarded}/
                  {studentReport.total_max}
                </p>
                <table>
                  <thead>
                    <tr>
                      <th>Question</th>
                      <th>Awarded</th>
                      <th>Max</th>
                      <th>Mode</th>
                    </tr>
                  </thead>
                  <tbody>
                    {studentReport.grades.map((grade) => (
                      <tr key={grade.question_no}>
                        <td>{grade.question_no}</td>
                        <td>{grade.awarded_marks}</td>
                        <td>{grade.max_marks}</td>
                        <td>{grade.grading_mode}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="card">
            <h2>Class Report</h2>
            <form className="row" onSubmit={handleClassReport}>
              <input
                placeholder="Exam ID"
                value={examId}
                onChange={(event) => setExamId(event.target.value)}
                required
              />
              <button type="submit" disabled={analyticsLoading}>
                {analyticsLoading ? "Loading..." : "Fetch Class Report"}
              </button>
            </form>

            {classReport && (
              <div>
                <p>Students: {classReport.student_count}</p>
                <h3>Leaderboard</h3>
                <table>
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Roll Number</th>
                      <th>Score</th>
                      <th>Percentage</th>
                    </tr>
                  </thead>
                  <tbody>
                    {classReport.leaderboard.map((item) => (
                      <tr key={item.submission_id}>
                        <td>{item.rank}</td>
                        <td>{item.roll_number}</td>
                        <td>
                          {item.total_awarded}/{item.total_max}
                        </td>
                        <td>{item.percentage}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <h3>Question Averages</h3>
                <table>
                  <thead>
                    <tr>
                      <th>Question</th>
                      <th>Avg Awarded</th>
                      <th>Avg Max</th>
                      <th>Avg %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {classReport.question_averages.map((item) => (
                      <tr key={item.question_no}>
                        <td>{item.question_no}</td>
                        <td>{item.average_awarded}</td>
                        <td>{item.average_max}</td>
                        <td>{item.average_percentage}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
          {analyticsError && <p className="error">{analyticsError}</p>}
        </>
      ) : (
        <>
          <h1>Manual Review Queue</h1>
          <p>Review low-confidence captures, correct roll number, and verify submission.</p>
          <button onClick={loadQueue} disabled={queueLoading}>
            {queueLoading ? "Refreshing..." : "Refresh Queue"}
          </button>
          {queueMessage && <p>{queueMessage}</p>}
          {queueError && <p className="error">{queueError}</p>}
          {queueItems.length === 0 && !queueLoading ? (
            <p>No submissions awaiting manual review.</p>
          ) : (
            queueItems.map((item) => {
              const form = queueForms[item.submission_id];
              return (
                <section key={item.submission_id} className="card">
                  <h2>Submission #{item.submission_id}</h2>
                  <p>
                    OCR Confidence: {item.ocr_confidence ?? "N/A"} | Status: {item.status}
                  </p>
                  <p>QR Payload: {item.qr_payload || "Unavailable"}</p>
                  {form && (
                    <form className="row" onSubmit={(event) => handleQueueVerify(event, item.submission_id)}>
                      <input
                        placeholder="Reviewer ID"
                        value={form.reviewerId}
                        onChange={(event) =>
                          updateQueueForm(item.submission_id, { reviewerId: event.target.value })
                        }
                        required
                      />
                      <input
                        placeholder="Corrected Roll Number"
                        value={form.correctedRollNumber}
                        onChange={(event) =>
                          updateQueueForm(item.submission_id, {
                            correctedRollNumber: event.target.value
                          })
                        }
                        required
                      />
                      <input
                        placeholder="Notes"
                        value={form.notes}
                        onChange={(event) =>
                          updateQueueForm(item.submission_id, { notes: event.target.value })
                        }
                      />
                      <button type="submit">Verify Submission</button>
                    </form>
                  )}
                </section>
              );
            })
          )}
        </>
      )}
    </main>
  );
}
