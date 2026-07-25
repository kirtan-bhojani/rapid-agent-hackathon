// src/pages/GapAnalysis.jsx — Gap Analysis Page
// Central feature: "What exactly am I missing?"

import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import Layout from "../components/Layout";
import "./GapAnalysis.css";

const API = import.meta.env.VITE_API_URL;

const STATUS_CONFIG = {
    completed:            { icon: "✅", label: "Completed",    sectionClass: "completed" },
    missing_critical:     { icon: "❌", label: "Missing",       sectionClass: "critical"  },
    missing_recommended:  { icon: "⚠️", label: "Recommended",  sectionClass: "recommended" },
    partial:              { icon: "🔶", label: "Partial",       sectionClass: "partial"   },
};

function ScoreRing({ score }) {
    const radius = 40;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;

    // Colour ramp
    const color = score >= 70 ? "#22c55e"
                : score >= 40 ? "#f59e0b"
                : "#ef4444";

    return (
        <div className="gap-score-ring">
            <svg viewBox="0 0 96 96">
                <circle className="gap-score-ring__bg" cx="48" cy="48" r={radius} />
                <circle
                    className="gap-score-ring__fill"
                    cx="48" cy="48" r={radius}
                    stroke={color}
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                />
            </svg>
            <div className="gap-score-ring__label">
                {score}%<span className="gap-score-ring__sub">Ready</span>
            </div>
        </div>
    );
}

function GapItem({ item }) {
    const cfg = STATUS_CONFIG[item.status] || { icon: "•", label: item.status };
    return (
        <div className={`gap-item gap-item--${item.status}`}>
            <span className="gap-item__icon">{cfg.icon}</span>
            <div className="gap-item__body">
                <div className="gap-item__name">{item.item}</div>
                {item.evidence && (
                    <div className="gap-item__evidence">{item.evidence}</div>
                )}
                {item.reason && (
                    <div className="gap-item__reason">{item.reason}</div>
                )}
                {item.action && item.status !== "completed" && (
                    <div className="gap-item__action">
                        <span>→</span> {item.action}
                    </div>
                )}
            </div>
        </div>
    );
}

function GapSection({ status, items }) {
    const cfg = STATUS_CONFIG[status];
    if (!Array.isArray(items) || items.length === 0) return null;
    return (
        <div className="gap-section">
            <div className={`gap-section__header gap-section--${cfg.sectionClass}`}>
                <span className="gap-section__icon">{cfg.icon}</span>
                <span className="gap-section__title">{cfg.label}</span>
                <span className="gap-section__count">{items.length}</span>
            </div>
            <div className="gap-items">
                {items.map((item, i) => (
                    <GapItem key={i} item={{ ...item, status }} />
                ))}
            </div>
        </div>
    );
}

export default function GapAnalysis() {
    const [data, setData]       = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError]     = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        const userId = localStorage.getItem("user_id");
        if (!userId) {
            setError("Please log in first.");
            setLoading(false);
            return;
        }

        fetch(`${API}/goal-analysis/${userId}`)
            .then(res => {
                if (!res.ok) {
                    if (res.status === 404) throw new Error("not_found");
                    throw new Error("server_error");
                }
                return res.json();
            })
            .then(json => {
                setData(json);
                setLoading(false);
            })
            .catch(err => {
                if (err.message === "not_found") {
                    setError("no_goal");
                } else {
                    setError("Failed to load gap analysis.");
                }
                setLoading(false);
            });
    }, []);

    // ── Loading ──────────────────────────────────────────────────
    if (loading) {
        return (
            <Layout>
                <div className="gap-page">
                    <div className="gap-loading">
                        <div className="spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
                        <span>Loading your gap analysis…</span>
                    </div>
                </div>
            </Layout>
        );
    }

    // ── No goal set ──────────────────────────────────────────────
    if (error === "no_goal") {
        return (
            <Layout>
                <div className="gap-page">
                    <div className="empty-state">
                        <div className="empty-state__icon">🎯</div>
                        <div className="empty-state__title">No goal set yet</div>
                        <div className="empty-state__text">
                            Set your goal first and RAPID will analyse what you need and what you're missing.
                        </div>
                        <button className="btn-primary" style={{ marginTop: 16 }} onClick={() => navigate("/goal")}>
                            Set Your Goal →
                        </button>
                    </div>
                </div>
            </Layout>
        );
    }

    // ── Other errors ─────────────────────────────────────────────
    if (error) {
        return (
            <Layout>
                <div className="gap-page">
                    <div className="goal-error">⚠️ {error}</div>
                </div>
            </Layout>
        );
    }

    const goalAnalysis = data?.goal_analysis?.analysis || {};
    const gapAnalysis  = data?.gap_analysis?.gap_analysis || {};

    const { completed = [], missing_critical = [], missing_recommended = [],
            partial = [], gap_score = 0, summary = "", next_critical_action = "" } = gapAnalysis;

    const totalRequirements = completed.length + missing_critical.length + missing_recommended.length + partial.length;

    return (
        <Layout>
            <div className="gap-page">
                {/* ── Header ──────────────────────────────────────── */}
                <div className="gap-page__header">
                    <h1 className="gap-page__title">Gap Analysis</h1>
                    <p className="gap-page__subtitle">
                        Your profile compared against every requirement for your goal.
                    </p>
                </div>

                {/* ── Score Banner ─────────────────────────────────── */}
                <div className="gap-score-banner">
                    <ScoreRing score={gap_score} />
                    <div className="gap-score-info">
                        <div className="gap-score-info__goal">
                            {goalAnalysis.degree && goalAnalysis.degree !== "N/A"
                                ? `${goalAnalysis.degree} in ${goalAnalysis.field} — ${goalAnalysis.destination}`
                                : goalAnalysis.target_role || "Your Goal"}
                        </div>
                        {summary && (
                            <div className="gap-score-info__summary">{summary}</div>
                        )}
                        <div className="gap-score-counters">
                            <div className="gap-counter gap-counter--completed">
                                <span className="gap-counter__number">{completed.length}</span>
                                <span className="gap-counter__label">Completed</span>
                            </div>
                            <div className="gap-counter gap-counter--critical">
                                <span className="gap-counter__number">{missing_critical.length}</span>
                                <span className="gap-counter__label">Critical Gaps</span>
                            </div>
                            <div className="gap-counter gap-counter--recommended">
                                <span className="gap-counter__number">{missing_recommended.length}</span>
                                <span className="gap-counter__label">Recommended</span>
                            </div>
                            {partial.length > 0 && (
                                <div className="gap-counter gap-counter--partial">
                                    <span className="gap-counter__number">{partial.length}</span>
                                    <span className="gap-counter__label">Partial</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* ── Next Action ──────────────────────────────────── */}
                {next_critical_action && (
                    <div className="next-action-banner">
                        <span className="next-action-banner__icon">🚀</span>
                        <div className="next-action-banner__content">
                            <div className="next-action-banner__label">Next Critical Action</div>
                            <div className="next-action-banner__text">{next_critical_action}</div>
                        </div>
                    </div>
                )}

                {/* ── Sections ─────────────────────────────────────── */}
                <GapSection status="missing_critical"    items={missing_critical}    />
                <GapSection status="partial"             items={partial}             />
                <GapSection status="missing_recommended" items={missing_recommended} />
                <GapSection status="completed"           items={completed}           />

                {/* ── Empty State ──────────────────────────────────── */}
                {totalRequirements === 0 && (
                    <div className="empty-state">
                        <div className="empty-state__icon">📊</div>
                        <div className="empty-state__title">No analysis data available</div>
                        <div className="empty-state__text">
                            Upload more documents to your profile so RAPID can compare them against your goal requirements.
                        </div>
                        <button className="btn-secondary" style={{ marginTop: 16 }} onClick={() => navigate("/documents")}>
                            Upload Documents
                        </button>
                    </div>
                )}

                {/* ── CTA Row ──────────────────────────────────────── */}
                {totalRequirements > 0 && (
                    <div className="gap-cta-row">
                        <button className="btn-primary" onClick={() => navigate("/roadmap")}>
                            🗺️ View Justified Roadmap →
                        </button>
                        <button className="btn-secondary" onClick={() => navigate("/documents")}>
                            📄 Upload Missing Documents
                        </button>
                        <button className="btn-secondary" onClick={() => navigate("/opportunities")}>
                            🔍 Find Opportunities
                        </button>
                    </div>
                )}
            </div>
        </Layout>
    );
}
