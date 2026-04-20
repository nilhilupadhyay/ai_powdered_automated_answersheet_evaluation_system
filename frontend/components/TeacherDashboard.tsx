"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  ClassReport,
  ManualReviewItem,
  StudentReport,
  fetchClassReport,
  fetchManualReviewQueue,
  fetchStudentReport,
  verifyManualReviewSubmission
} from "../lib/api";

type TabId = "analytics" | "manual-review";
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
      {activeTab === "analytics" ? (
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
