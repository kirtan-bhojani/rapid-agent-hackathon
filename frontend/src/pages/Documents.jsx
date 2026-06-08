// src/pages/Documents.jsx

import Layout from "../components/Layout";
import DocumentUpload from "../components/DocumentUpload";
import "./Documents.css";

const SUPPORTED_TYPES = [
    "Resume",
    "Transcript",
    "Passport",
    "IELTS",
    "Statement of Purpose",
    "Letter of Recommendation",
];

export default function Documents() {

    return (

        <Layout>

            <div className="documents-page">

                <div className="documents-page__header">

                    <h1>My Documents</h1>

                    <p>
                        Upload your documents to build and enrich your profile.
                        You can upload additional documents at any time.
                    </p>

                    <div className="documents-page__types">

                        {SUPPORTED_TYPES.map((type) => (

                            <span key={type} className="documents-page__type-chip">
                                {type}
                            </span>

                        ))}

                    </div>

                </div>

                <DocumentUpload />

                <div className="documents-page__history">

                    <div className="documents-page__history-icon">📄</div>

                    <p>Document history will appear here.</p>

                </div>

            </div>

        </Layout>

    );

}
