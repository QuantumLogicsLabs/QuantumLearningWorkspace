import { useState } from "react";

function Dashboard() {
  // This is our FAKE list of uploads, just for now.
  // It has the exact same shape we expect the real /uploads
  // endpoint to send us later (filename, upload_date, etc.)
  const [uploads, setUploads] = useState([
    {
      filename: "chapter1-notes.pdf",
      upload_date: "2026-07-15T10:00:00",
    },
    {
      filename: "physics-lecture.pdf",
      upload_date: "2026-07-16T14:30:00",
    },
    {
      filename: "research-paper.pdf",
      upload_date: "2026-07-17T09:15:00",
    },
  ]);

  return (
    <div style={{ padding: "2rem" }}>
      <h2>Dashboard — Uploaded Files</h2>

      <ul>
        {uploads.map((upload) => (
          <li key={upload.filename}>
            {upload.filename} — {upload.upload_date}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default Dashboard;