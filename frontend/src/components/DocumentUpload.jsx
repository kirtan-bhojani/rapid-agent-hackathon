// src/components/DocumentUpload.jsx

import { useState } from "react";

export default function DocumentUpload({ onUploadComplete }) {

    // --- upload state ---
    const [uploadStatus, setUploadStatus] = useState("idle");
    const [selectedFile, setSelectedFile] = useState(null);
    const [documentType, setDocumentType] = useState("");
    const [uploadError, setUploadError]   = useState(null);

    // --- 3-step upload handler ---
    const handleUpload = async () => {

        const userId = localStorage.getItem("user_id");

        // client-side validation
        if (!userId) {
            setUploadError("Please login first.");
            return;
        }

        if (!selectedFile) {
            setUploadError("Please select a file.");
            return;
        }

        if (!documentType) {
            setUploadError("Please select a document type.");
            return;
        }

        setUploadError(null);

        // Step 1 — Upload
        setUploadStatus("uploading");
        let filePath;

        try {

            const formData = new FormData();
            formData.append("file", selectedFile);
            formData.append("document_type", documentType);

            const uploadRes = await fetch("http://127.0.0.1:8000/upload/", {
                method: "POST",
                body: formData,
            });

            if (!uploadRes.ok) {
                setUploadStatus("error");
                setUploadError("Upload failed. Please try again.");
                return;
            }

            const uploadData = await uploadRes.json();
            filePath = uploadData.file_path;

        } catch {
            setUploadStatus("error");
            setUploadError("Unable to connect to server.");
            return;
        }

        // Step 2 — Extract
        setUploadStatus("extracting");

        try {

            const extractRes = await fetch("http://127.0.0.1:8000/extract/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    file_path: filePath,
                    document_type: documentType,
                    user_id: userId,
                }),
            });

            if (!extractRes.ok) {
                setUploadStatus("error");
                setUploadError("Extraction failed. Please try again.");
                return;
            }

        } catch {
            setUploadStatus("error");
            setUploadError("Unable to connect to server.");
            return;
        }

        // Step 3 — Build Profile
        setUploadStatus("building");

        try {

            const buildRes = await fetch("http://127.0.0.1:8000/profile/build", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId }),
            });

            if (!buildRes.ok) {
                setUploadStatus("error");
                setUploadError("Profile build failed. Please try again.");
                return;
            }

        } catch {
            setUploadStatus("error");
            setUploadError("Unable to connect to server.");
            return;
        }

        // Done — notify parent and show success
        setUploadStatus("success");
        if (onUploadComplete) onUploadComplete();

        // Reset form after a short delay so user sees the success state
        setTimeout(() => {
            setUploadStatus("idle");
            setSelectedFile(null);
            setDocumentType("");
        }, 3000);

    };

    const isProcessing = ["uploading", "extracting", "building"].includes(uploadStatus);

    let stepText = "Upload & Process";
    if (uploadStatus === "uploading")  stepText = "Step 1 of 3 — Uploading…";
    if (uploadStatus === "extracting") stepText = "Step 2 of 3 — Extracting…";
    if (uploadStatus === "building")   stepText = "Step 3 of 3 — Building profile…";

    // --- render ---
    return (

        <div className="doc-upload">

            {uploadStatus === "success" ? (

                <div className="doc-upload__success">

                    <div className="doc-upload__success-icon">✓</div>

                    <p>Document processed and profile updated successfully!</p>

                </div>

            ) : (

                <>

                    <div className="doc-upload__field">

                        <label htmlFor="doc-file">Document</label>

                        <input
                            id="doc-file"
                            type="file"
                            accept=".pdf"
                            onChange={(e) => setSelectedFile(e.target.files[0])}
                            disabled={isProcessing}
                        />

                    </div>

                    <div className="doc-upload__field">

                        <label htmlFor="doc-type">Document Type</label>

                        <select
                            id="doc-type"
                            value={documentType}
                            onChange={(e) => setDocumentType(e.target.value)}
                            disabled={isProcessing}
                        >
                            <option value="">Select document type</option>
                            <option value="resume">Resume</option>
                            <option value="transcript">Transcript</option>
                            <option value="passport">Passport</option>
                            <option value="ielts">IELTS</option>
                            <option value="sop">Statement of Purpose</option>
                            <option value="lor">Letter of Recommendation</option>
                        </select>

                    </div>

                    {/* Progress bar */}
                    {isProcessing && (

                        <div className="doc-upload__progress">

                            <div className="doc-upload__progress-track">

                                <div
                                    className="doc-upload__progress-fill"
                                    style={{
                                        width:
                                            uploadStatus === "uploading"  ? "33%" :
                                            uploadStatus === "extracting" ? "66%" :
                                            "95%",
                                    }}
                                />

                            </div>

                        </div>

                    )}

                    <div className="doc-upload__actions">

                        <button
                            id="upload-btn"
                            className="doc-upload__btn"
                            onClick={handleUpload}
                            disabled={isProcessing}
                        >
                            {isProcessing && <span className="doc-upload__spinner" />}
                            {stepText}
                        </button>

                    </div>

                    {uploadStatus === "error" && uploadError && (

                        <div className="doc-upload__error">

                            <p>{uploadError}</p>

                        </div>

                    )}

                </>

            )}

        </div>

    );

}
