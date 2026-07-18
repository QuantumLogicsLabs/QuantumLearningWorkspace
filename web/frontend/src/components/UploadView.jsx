import { useState } from "react";

function UploadView() {
  // This "box" remembers which file the user picked.
  // Right now it's empty (null) because no file is chosen yet.
  const [selectedFile, setSelectedFile] = useState(null);

  // This function runs automatically when the user picks a file
  // using the file picker window.
  function handleFileChange(event) {
    const file = event.target.files[0]; // grab the first picked file
    setSelectedFile(file); // save it into our "box"
  }

  // This function runs when the user clicks the Upload button.
  // For now, it just shows the file name in the console —
  // we are NOT sending it to the backend yet.
  function handleUploadClick() {
    if (!selectedFile) {
      alert("Please choose a file first.");
      return;
    }
    console.log("File ready to upload:", selectedFile.name);
  }

  return (
    <div style={{ padding: "2rem" }}>
      <h2>Upload a File</h2>

      {/* This is the file picker itself */}
      <input type="file" onChange={handleFileChange} />

      {/* This button triggers the upload action */}
      <button onClick={handleUploadClick} style={{ marginLeft: "1rem" }}>
        Upload
      </button>

      {/* A little message showing what file is currently picked */}
      {selectedFile && <p>Selected file: {selectedFile.name}</p>}
    </div>
  );
}

export default UploadView;