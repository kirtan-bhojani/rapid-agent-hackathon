// src/pages/ApplicationAssistant.jsx — Application Readiness Report
// Paste field labels from a real application form; RAPID maps them against
// your stored profile. No browser extension, no live-site automation — you
// stay in control and paste the values yourself.

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import "./ApplicationAssistant.css";

const API = import.meta.env.VITE_API_URL;

const STATUS_CONFIG = {
    can_autofill:     { icon: "✅", label: "Can Autofill",     sectionClass: "autofill" },
    warning:          { icon: "⚠️", label: "Warnings",         sectionClass: "warning"  },
    missing_document: { icon: "📄", label: "Missing Document", sectionClass: "document" },
    missing:          { icon: "❌", label: "Missing",          sectionClass: "missing"  },
};

const SECTION_ORDER = ["warning", "missing_document", "missing", "can_autofill"];

function CopyButton({ value }) {
    const [copied, setCopied] = useState(false);
    const handleCopy = () => {
        navigator.clipboard.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    };
    return (
        <button className="copy-btn" onClick={handleCopy} type="button">
            {copied ? "Copied ✓" : "Copy"}
        </button>
    );
}

function FieldRow({ field, onGoToDocuments }) {
    const cfg = STATUS_CONFIG[field.status] || { icon: "•", label: field.status };
    return (
        <div className={`field-row field-row--${field.status}`}>
            <span className="field-row__icon">{cfg.icon}</span>
            <div className="field-row__body">
                <div className="field-row__label">{field.field_label}</div>
                {field.message && <div className="field-row__message">{field.message}</div>}
                {field.reasoning && <div className="field-row__reasoning">{field.reasoning}</div>}
                {field.status === "missing_document" && field.action_needed && (
                    <button className="field-row__action" onClick={onGoToDocuments}>
                        → {field.action_needed}
                    </button>
                )}
            </div>
            {field.status === "can_autofill" && field.value && (
                <div className="field-row__value">
                    <span className="field-row__value-text">{field.value}</span>
                    <CopyButton value={field.value} />
                </div>
            )}
        </div>
    );
}

function FieldSection({ status, fields, onGoToDocuments }) {
    const cfg = STATUS_CONFIG[status];
    if (!fields || fields.length === 0) return null;
    return (
        <div className="field-section">
            <div className={`field-section__header field-section--${cfg.sectionClass}`}>
                <span className="field-section__icon">{cfg.icon}</span>
                <span className="field-section__title">{cfg.label}</span>
                <span className="field-section__count">{fields.length}</span>
            </div>
            <div className="field-rows">
                {fields.map((f, i) => (
                    <FieldRow key={i} field={f} onGoToDocuments={onGoToDocuments} />
                ))}
            </div>
        </div>
    );
}

export default function ApplicationAssistant() {
    const [rawText, setRawText] = useState("");
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(false);
    const [initialLoad, setInitialLoad] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();
    const userId = localStorage.getItem("user_id");

    useEffect(() => {
        if (!userId) {
            setInitialLoad(false);
            return;
        }
        fetch(`${API}/application_prep/${userId}`)
            .then(res => (res.ok ? res.json() : null))
            .then(json => {
                if (json?.report?.report) setReport(json.report.report);
            })
            .catch(() => {})
            .finally(() => setInitialLoad(false));
    }, [userId]);

    const handleAnalyze = () => {
        if (!userId) {
            setError("Please log in first.");
            return;
        }
        if (!rawText.trim()) {
            setError("Paste at least one field label first.");
            return;
        }
        setError(null);
        setLoading(true);
        fetch(`${API}/application_prep/analyze`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: userId, raw_text: rawText }),
        })
            .then(res => {
                if (!res.ok) {
                    if (res.status === 404) throw new Error("no_profile");
                    throw new Error("server_error");
                }
                return res.json();
            })
            .then(json => setReport(json.report.report))
            .catch(err => {
                setError(err.message === "no_profile"
                    ? "Profile not found. Please upload at least a resume first."
                    : "Analysis failed. Please try again.");
            })
            .finally(() => setLoading(false));
    };

    const fieldsByStatus = {};
    if (report?.fields) {
        for (const f of report.fields) {
            (fieldsByStatus[f.status] ||= []).push(f);
        }
    }

    return (
        <Layout>
            <div className="app-assist-page">
                <div className="app-assist-page__header">
                    <h1 className="app-assist-page__title">Application Assistant</h1>
                    <p className="app-assist-page__subtitle">
                        Paste the field labels from a real application form. RAPID checks each one
                        against your profile — you copy the values in yourself. No autofill on the
                        live page, no browser extension: you stay fully in control.
                    </p>
                </div>

                <div className="app-assist-input">
                    <textarea
                        className="app-assist-textarea"
                        placeholder={"Full Name\nEmail Address\nPassport Number\nIELTS Overall Score\nStatement of Purpose\n..."}
                        value={rawText}
                        onChange={e => setRawText(e.target.value)}
                        rows={6}
                    />
                    <div className="app-assist-input__row">
                        <button className="btn-primary" onClick={handleAnalyze} disabled={loading}>
                            {loading ? "Analyzing…" : "Analyze Fields"}
                        </button>
                        {error && <span className="app-assist-error">⚠️ {error}</span>}
                    </div>
                </div>

                {initialLoad && (
                    <div className="app-assist-loading">
                        <div className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
                    </div>
                )}

                {!initialLoad && !report && !loading && (
                    <div className="empty-state">
                        <div className="empty-state__icon">📝</div>
                        <div className="empty-state__title">No report yet</div>
                        <div className="empty-state__text">
                            Paste field labels above and analyze to see what you can autofill,
                            what's missing, and any warnings before you apply.
                        </div>
                    </div>
                )}

                {report && (
                    <>
                        <div className="app-assist-summary">
                            <div className="app-assist-summary__pct">
                                {report.estimated_completion_pct}%
                                <span>Ready</span>
                            </div>
                            <div className="app-assist-summary__counts">
                                <div className="summary-count summary-count--autofill">
                                    <span className="summary-count__number">{report.can_autofill_count}</span>
                                    <span className="summary-count__label">Can Autofill</span>
                                </div>
                                <div className="summary-count summary-count--warning">
                                    <span className="summary-count__number">{report.warning_count}</span>
                                    <span className="summary-count__label">Warnings</span>
                                </div>
                                <div className="summary-count summary-count--document">
                                    <span className="summary-count__number">{report.missing_document_count}</span>
                                    <span className="summary-count__label">Missing Docs</span>
                                </div>
                                <div className="summary-count summary-count--missing">
                                    <span className="summary-count__number">{report.missing_count}</span>
                                    <span className="summary-count__label">Missing</span>
                                </div>
                            </div>
                            {report.overall_reasoning && (
                                <div className="app-assist-summary__reasoning">{report.overall_reasoning}</div>
                            )}
                        </div>

                        {SECTION_ORDER.map(status => (
                            <FieldSection
                                key={status}
                                status={status}
                                fields={fieldsByStatus[status]}
                                onGoToDocuments={() => navigate("/documents")}
                            />
                        ))}
                    </>
                )}
            </div>
        </Layout>
    );
}
