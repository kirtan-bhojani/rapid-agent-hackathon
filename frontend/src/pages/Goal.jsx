// src/pages/Goal.jsx — Goal Entry & Analysis Page
// Replaces Chat.jsx as the primary goal-setting experience.
// Flow: Input goal → Goal Analysis → Gap Analysis → Roadmap (all in one pipeline)

import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import "./Goal.css";

const API = import.meta.env.VITE_API_URL;

const GOAL_EXAMPLES = [
    "Master's in Germany in Microelectronics",
    "PhD in AI at a top US university",
    "Software Engineer at Google",
    "Embedded Engineer at Qualcomm",
    "DAAD Scholarship 2025",
    "Research Internship in Robotics",
];

const REQ_GROUPS = [
    { key: "required_qualifications", label: "Qualifications", icon: "🎓" },
    { key: "required_exams",          label: "Exams & Tests",  icon: "📝" },
    { key: "required_documents",      label: "Documents",       icon: "📋" },
    { key: "language_requirements",   label: "Language",        icon: "🌍" },
    { key: "visa_requirements",       label: "Visa & APS",      icon: "🛂" },
    { key: "financial_requirements",  label: "Finances",        icon: "💰" },
    { key: "experience_expectations", label: "Experience",      icon: "💼" },
    { key: "scholarships",            label: "Scholarships",    icon: "🏅" },
];

function TraceItem({ trace }) {
    const icons = { agent: "🤖", mcp: "🔌", error: "⚠️" };
    return (
        <div className={`trace-item trace-item--${trace.type || "agent"}`}>
            <span className="trace-item__icon">{icons[trace.type] || "•"}</span>
            <span>{trace.message}</span>
        </div>
    );
}

function RequirementGroup({ title, icon, items }) {
    if (!Array.isArray(items) || items.length === 0) return null;
    return (
        <div className="req-group">
            <div className="req-group__title">
                <span className="req-group__icon">{icon}</span>
                {title}
            </div>
            {items.map((item, i) => (
                <div key={i} className="req-item">
                    <div className={`req-item__indicator ${item.is_optional ? "req-item__indicator--optional" : "req-item__indicator--required"}`} />
                    <div className="req-item__content">
                        <div className="req-item__name">{item.item}</div>
                        {item.detail && <div className="req-item__detail">{item.detail}</div>}
                    </div>
                    {item.is_optional && <span className="req-item__optional-tag">Optional</span>}
                </div>
            ))}
        </div>
    );
}

export default function Goal() {
    const [goalText, setGoalText] = useState("");
    const [loading, setLoading]   = useState(false);
    const [error, setError]       = useState(null);
    const [traces, setTraces]     = useState([]);
    const [visibleTraces, setVisibleTraces] = useState([]);
    const [analysisResult, setAnalysisResult] = useState(null);
    const [existingAnalysis, setExistingAnalysis] = useState(null);
    const textareaRef = useRef(null);
    const navigate = useNavigate();

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = textareaRef.current.scrollHeight + "px";
        }
    }, [goalText]);

    // Load existing analysis on mount
    useEffect(() => {
        const userId = localStorage.getItem("user_id");
        if (!userId) return;
        fetch(`${API}/goal-analysis/${userId}`)
            .then(r => r.ok ? r.json() : null)
            .then(data => {
                if (data && data.goal_analysis) {
                    setExistingAnalysis(data);
                }
            })
            .catch(() => {});
    }, []);

    // Sequential trace reveal
    useEffect(() => {
        if (traces.length === 0) return;
        let idx = 0;
        setVisibleTraces([]);
        const id = setInterval(() => {
            if (idx < traces.length) {
                setVisibleTraces(prev => [...prev, traces[idx]]);
                idx++;
            } else {
                clearInterval(id);
            }
        }, 600);
        return () => clearInterval(id);
    }, [traces]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!goalText.trim()) return;

        const userId = localStorage.getItem("user_id");
        if (!userId) {
            setError("Please log in first.");
            return;
        }

        setLoading(true);
        setError(null);
        setTraces([]);
        setVisibleTraces([]);
        setAnalysisResult(null);

        try {
            const res = await fetch(`${API}/goal-analysis/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId, goal: goalText }),
            });
            const data = await res.json();

            if (res.ok && data.status === "success") {
                setTraces(data.trace_logs || []);
                setAnalysisResult(data);
                setExistingAnalysis(data);
            } else {
                setError(data.detail || "Failed to run goal analysis. Please try again.");
            }
        } catch {
            setError("Could not connect to server. Please check your connection.");
        } finally {
            setLoading(false);
        }
    };

    const displayedAnalysis = analysisResult || existingAnalysis;
    const goalAnalysis = displayedAnalysis?.goal_analysis?.analysis;
    const isRunning = loading || (visibleTraces.length > 0 && visibleTraces.length < traces.length);

    return (
        <Layout>
            <div className="goal-page">
                <div className="goal-page__header">
                    <h1 className="goal-page__title">Set Your Goal</h1>
                    <p className="goal-page__subtitle">
                        Describe your ambition. RAPID will decompose it into every requirement,
                        compare it against your profile, and build a justified roadmap.
                    </p>
                </div>

                {/* ── Input Card ─────────────────────────────────────── */}
                <form onSubmit={handleSubmit}>
                    <div className="goal-input-card">
                        <span className="goal-input-card__label">Your Goal</span>

                        <div className="goal-input-card__examples">
                            {GOAL_EXAMPLES.map(ex => (
                                <button
                                    type="button"
                                    key={ex}
                                    className="goal-example"
                                    onClick={() => setGoalText(ex)}
                                    disabled={isRunning}
                                >
                                    {ex}
                                </button>
                            ))}
                        </div>

                        <textarea
                            ref={textareaRef}
                            className="goal-textarea"
                            value={goalText}
                            onChange={e => setGoalText(e.target.value)}
                            placeholder="e.g. I want to pursue a Master's in Germany in Microelectronics by Winter 2026..."
                            disabled={isRunning}
                            rows={3}
                        />

                        <div className="goal-input-card__footer">
                            <span className="goal-char-count">{goalText.length} characters</span>
                            <button
                                type="submit"
                                className="btn-primary"
                                disabled={isRunning || !goalText.trim()}
                            >
                                {loading ? (
                                    <><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Analysing...</>
                                ) : (
                                    <>🎯 Analyse Goal</>
                                )}
                            </button>
                        </div>
                    </div>
                </form>

                {/* ── Error ─────────────────────────────────────────── */}
                {error && <div className="goal-error">⚠️ {error}</div>}

                {/* ── Trace Viewer ──────────────────────────────────── */}
                {visibleTraces.length > 0 && (
                    <div className="goal-trace">
                        <div className="goal-trace__header">
                            {isRunning && <div className="goal-trace__dot" />}
                            {isRunning ? "Analysing your goal..." : "Analysis complete"}
                        </div>
                        <div className="trace-list">
                            {visibleTraces.map((t, i) => (
                                <TraceItem key={i} trace={t} />
                            ))}
                        </div>
                    </div>
                )}

                {/* ── Analysis Result ───────────────────────────────── */}
                {goalAnalysis && (
                    <div className="goal-analysis-result">

                        {/* Header */}
                        <div className="analysis-header">
                            <div className="analysis-header__goal-type">
                                🎯 {goalAnalysis.goal_type}
                            </div>
                            <div className="analysis-header__title">
                                {goalAnalysis.degree && goalAnalysis.degree !== "N/A"
                                    ? `${goalAnalysis.degree} in ${goalAnalysis.field}`
                                    : goalAnalysis.target_role}
                            </div>
                            <div className="analysis-header__meta">
                                {goalAnalysis.destination && (
                                    <div className="analysis-meta-item">
                                        <span className="analysis-meta-item__label">Destination</span>
                                        <span className="analysis-meta-item__value">📍 {goalAnalysis.destination}</span>
                                    </div>
                                )}
                                {goalAnalysis.timeline && (
                                    <div className="analysis-meta-item">
                                        <span className="analysis-meta-item__label">Timeline</span>
                                        <span className="analysis-meta-item__value">⏱ {goalAnalysis.timeline}</span>
                                    </div>
                                )}
                                {goalAnalysis.field && (
                                    <div className="analysis-meta-item">
                                        <span className="analysis-meta-item__label">Field</span>
                                        <span className="analysis-meta-item__value">🔬 {goalAnalysis.field}</span>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Requirement Groups */}
                        <div className="req-groups">
                            {REQ_GROUPS.map(group => (
                                <RequirementGroup
                                    key={group.key}
                                    title={group.label}
                                    icon={group.icon}
                                    items={goalAnalysis[group.key]}
                                />
                            ))}
                        </div>

                        {/* Additional Notes */}
                        {Array.isArray(goalAnalysis.additional_notes) && goalAnalysis.additional_notes.length > 0 && (
                            <div className="req-group" style={{ gridColumn: "1 / -1" }}>
                                <div className="req-group__title">
                                    <span className="req-group__icon">💡</span>
                                    Additional Notes
                                </div>
                                {goalAnalysis.additional_notes.map((note, i) => (
                                    <div key={i} className="req-item">
                                        <div className="req-item__indicator" style={{ background: "var(--color-info)" }} />
                                        <div className="req-item__content">
                                            <div className="req-item__detail" style={{ color: "var(--color-info)", fontSize: 13 }}>{note}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* CTAs */}
                        <div className="goal-cta-row">
                            <button className="btn-primary" onClick={() => navigate("/gap-analysis")}>
                                📊 View Gap Analysis →
                            </button>
                            <button className="btn-secondary" onClick={() => navigate("/roadmap")}>
                                🗺️ View Roadmap
                            </button>
                        </div>
                    </div>
                )}

                {/* ── Show existing if no new run ───────────────────── */}
                {!goalAnalysis && existingAnalysis && !loading && (
                    <div style={{ textAlign: "center", padding: "32px 0", color: "var(--color-text-secondary)" }}>
                        <p style={{ marginBottom: 16, fontSize: 14 }}>
                            You have a previous goal analysis. Enter a new goal above to update it, or view your existing analysis.
                        </p>
                        <div className="goal-cta-row" style={{ justifyContent: "center" }}>
                            <button className="btn-primary" onClick={() => navigate("/gap-analysis")}>
                                📊 View Gap Analysis →
                            </button>
                            <button className="btn-secondary" onClick={() => navigate("/roadmap")}>
                                🗺️ View Roadmap
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </Layout>
    );
}
