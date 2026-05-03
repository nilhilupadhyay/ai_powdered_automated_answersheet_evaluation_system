"use client";

import { FormEvent, useState } from "react";
import { StudentReport, fetchStudentReport } from "../lib/api";

export default function StudentDashboard() {
  const [examId, setExamId] = useState("");
  const [rollNumber, setRollNumber] = useState("");
  const [report, setReport] = useState<StudentReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    setReport(null);
    try {
      const res = await fetchStudentReport(examId, rollNumber);
      setReport(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch results");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <h1>Student Results Dashboard</h1>
      <p>Enter your Exam ID and Roll Number to view your graded answer sheet.</p>

      <section className="card">
        <form className="row" onSubmit={handleSubmit}>
          <input
            placeholder="Exam ID"
            value={examId}
            onChange={(e) => setExamId(e.target.value)}
            required
          />
          <input
            placeholder="Roll Number"
            value={rollNumber}
            onChange={(e) => setRollNumber(e.target.value)}
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? "Loading..." : "View Results"}
          </button>
        </form>
        {error && <p className="error">{error}</p>}
        {report && (
          <div style={{ marginTop: "20px" }}>
            <h2>Results for {report.roll_number}</h2>
            <div style={{ display: "flex", gap: "20px", marginBottom: "20px" }}>
              <div style={{ padding: "15px", backgroundColor: "#f0f8ff", borderRadius: "8px", flex: 1 }}>
                <h3>Score</h3>
                <p style={{ fontSize: "24px", margin: "10px 0" }}>
                  <strong>{report.total_awarded} / {report.total_max}</strong>
                </p>
              </div>
              <div style={{ padding: "15px", backgroundColor: "#f5f5f5", borderRadius: "8px", flex: 1 }}>
                <h3>Grading Mode</h3>
                <p style={{ fontSize: "20px", margin: "10px 0" }}>{report.grading_mode}</p>
              </div>
            </div>

            <h3>Detailed Feedback</h3>
            {report.grades.map((g) => (
              <div key={g.question_no} style={{ padding: "15px", border: "1px solid #ddd", borderRadius: "8px", marginBottom: "10px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h4>Question {g.question_no}</h4>
                  <span style={{ fontWeight: "bold", color: g.awarded_marks === g.max_marks ? "green" : "inherit" }}>
                    {g.awarded_marks} / {g.max_marks} marks
                  </span>
                </div>
                {g.feedback && (
                  <div style={{ marginTop: "10px", padding: "10px", backgroundColor: "#fff9e6", borderRadius: "4px" }}>
                    <strong>Feedback:</strong> {g.feedback}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
