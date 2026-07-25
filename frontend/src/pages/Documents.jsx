// src/pages/Documents.jsx — Document upload + real history

import { useState, useEffect } from "react";
import Layout from "../components/Layout";
import DocumentUpload from "../components/DocumentUpload";
import "./Documents.css";

const API = import.meta.env.VITE_API_URL;

const DOC_CONFIG = {
    resume:     { icon: "📄", label: "Resume",                   color: "var(--color-brand)" },
    transcript: { icon: "📋", label: "Transcript",               color: "var(--color-success)" },
    passport:   { icon: "🛂", label: "Passport",                 color: "var(--color-warning)" },
    ielts:      { icon: "🌍", label: "IELTS Score Report",       color: "#a855f7" },
    sop:        { icon: "✍️",  label: "Statement of Purpose",    color: "var(--color-info)" },
    lor:        { icon: "📝", label: "Letter of Recommendation", color: "#f97316" },
};

const SUPPORTED_TYPES = [
    { key: "resume",     label: "Resume",                   desc: "CV / Resume" },
    { key: "transcript", label: "Transcript",               desc: "Academic transcript with GPA" },
    { key: "passport",   label: "Passport",                 desc: "Identity & nationality" },
    { key: "ielts",      label: "IELTS",                    desc: "Language test score report" },
    { key: "sop",        label: "Statement of Purpose",     desc: "Motivation letter / SOP" },
    { key: "lor",        label: "Letter of Recommendation", desc: "Academic or professional LOR" },
];

function DocumentHistoryCard({ doc }) {
    const cfg = DOC_CONFIG[doc.document_type] || { icon: "📁", label: doc.document_type, color: "var(--color-text-muted)" };

    const getKeyInfo = () => {
        switch (doc.document_type) {
            case "resume":     return doc.institution ? `${doc.institution} · ${doc.skills_count || 0} skills` : `${doc.skills_count || 0} skills extracted`;
            case "transcript": return [doc.institution, doc.major, doc.gpa ? `GPA ${doc.gpa}` : ""].filter(Boolean).join(" · ");
            case "passport":   return [doc.full_name, doc.issuing_country].filter(Boolean).join(" · ");
            case "ielts":      return [doc.overall_band ? `Band ${doc.overall_band}` : "", doc.test_type, doc.validity_expiry ? `Valid until ${doc.validity_expiry}` : ""].filter(Boolean).join(" · ");
            case "sop":        return [doc.target_program, doc.target_university, doc.word_count ? `${doc.word_count} words` : ""].filter(Boolean).join(" · ");
            case "lor":        return [doc.recommender_name, doc.recommender_institution, doc.recommendation_strength ? `${doc.recommendation_strength} recommendation` : ""].filter(Boolean).join(" · ");
            default:           return "";
        }
    };

    const keyInfo = getKeyInfo();

    return (
        <div className="doc-history-card" style={{ borderLeft: `3px solid ${cfg.color}` }}>
            <span className="doc-history-card__icon">{cfg.icon}</span>
            <div className="doc-history-card__body">
                <div className="doc-history-card__type">{cfg.label}</div>
                {keyInfo && <div className="doc-history-card__info">{keyInfo}</div>}
            </div>
            <div className="doc-history-card__status">✅ Parsed</div>
        </div>
    );
}

export default function Documents() {
    const [history, setHistory] = useState([]);
    const [historyLoading, setHistoryLoading] = useState(true);

    const loadHistory = () => {
        const userId = localStorage.getItem("user_id");
        if (!userId) { setHistoryLoading(false); return; }

        fetch(`${API}/profile/${userId}/documents`)
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data?.documents) setHistory(data.documents);
                setHistoryLoading(false);
            })
            .catch(() => setHistoryLoading(false));
    };

    useEffect(() => { loadHistory(); }, []);

    return (
        <Layout>
            <div className="documents-page">

                {/* ── Header ──────────────────────────────────────── */}
                <div className="documents-page__header">
                    <h1>Documents</h1>
                    <p>
                        Upload your documents to build and enrich your profile.
                        Each document type contributes to your gap analysis and roadmap.
                    </p>
                </div>

                {/* ── Supported Types ──────────────────────────────── */}
                <div className="documents-page__types-grid">
                    {SUPPORTED_TYPES.map(type => {
                        const cfg = DOC_CONFIG[type.key];
                        const uploaded = history.some(h => h.document_type === type.key);
                        return (
                            <div key={type.key} className={`doc-type-card ${uploaded ? "doc-type-card--uploaded" : ""}`}>
                                <span className="doc-type-card__icon">{cfg.icon}</span>
                                <div>
                                    <div className="doc-type-card__label">{type.label}</div>
                                    <div className="doc-type-card__desc">{type.desc}</div>
                                </div>
                                {uploaded && <span className="doc-type-card__check">✅</span>}
                            </div>
                        );
                    })}
                </div>

                {/* ── Upload Component ─────────────────────────────── */}
                <div className="documents-page__upload-section">
                    <div className="section-title">Upload Document</div>
                    <DocumentUpload onUploadComplete={loadHistory} />
                </div>

                {/* ── Document History ─────────────────────────────── */}
                <div className="documents-page__history-section">
                    <div className="section-title">Upload History</div>
                    {historyLoading ? (
                        <div style={{ display: "flex", gap: 10, alignItems: "center", color: "var(--color-text-muted)", fontSize: 14 }}>
                            <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                            Loading…
                        </div>
                    ) : history.length > 0 ? (
                        <div className="doc-history-list">
                            {history.map((doc, i) => (
                                <DocumentHistoryCard key={i} doc={doc} />
                            ))}
                        </div>
                    ) : (
                        <div className="empty-state" style={{ padding: "32px 0" }}>
                            <div className="empty-state__icon" style={{ fontSize: 32 }}>📂</div>
                            <div className="empty-state__text">No documents uploaded yet.</div>
                        </div>
                    )}
                </div>

            </div>
        </Layout>
    );
}
