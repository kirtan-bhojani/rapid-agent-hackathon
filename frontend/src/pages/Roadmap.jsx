// src/pages/Roadmap.jsx — Enriched roadmap with reason, effort, priority, deadline

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import "./Roadmap.css";

const API = import.meta.env.VITE_API_URL;

const PRIORITY_CONFIG = {
    critical: { label: "Critical",  color: "var(--color-danger)",  bg: "var(--color-danger-dim)" },
    high:     { label: "High",      color: "#f97316",               bg: "rgba(249,115,22,0.12)"   },
    medium:   { label: "Medium",    color: "var(--color-warning)", bg: "var(--color-warning-dim)" },
    low:      { label: "Low",       color: "var(--color-success)", bg: "var(--color-success-dim)" },
};

function PriorityBadge({ priority }) {
    const cfg = PRIORITY_CONFIG[priority?.toLowerCase()] || PRIORITY_CONFIG.medium;
    return (
        <span className="priority-badge" style={{ color: cfg.color, background: cfg.bg }}>
            {cfg.label}
        </span>
    );
}

function StepCard({ step, onComplete }) {
    const isCompleted = step.status === "Completed";
    const [expanded, setExpanded] = useState(!isCompleted);

    return (
        <div className={`step-card ${isCompleted ? "step-card--completed" : ""}`}>
            <div className="step-card__header" onClick={() => setExpanded(e => !e)}>
                <div className="step-card__status-icon">
                    {isCompleted ? "✅" : "⭕"}
                </div>
                <div className="step-card__title-area">
                    <div className="step-card__title">
                        <span className="step-card__num">Step {step.step_id}</span>
                        {step.title}
                    </div>
                    <div className="step-card__meta">
                        {step.priority && <PriorityBadge priority={step.priority} />}
                        {step.estimated_effort && (
                            <span className="step-meta-chip">⏱ {step.estimated_effort}</span>
                        )}
                        {step.deadline_hint && step.deadline_hint !== "No fixed deadline" && step.deadline_hint !== "Check university portal" && (
                            <span className="step-meta-chip step-meta-chip--deadline">📅 {step.deadline_hint}</span>
                        )}
                    </div>
                </div>
                <button className="step-card__expand" aria-label={expanded ? "Collapse" : "Expand"}>
                    {expanded ? "▲" : "▼"}
                </button>
            </div>

            {expanded && (
                <div className="step-card__body">
                    <p className="step-card__description">{step.description}</p>

                    {step.reason && (
                        <div className="step-card__reason">
                            <span className="step-card__reason-label">Why this step</span>
                            <span className="step-card__reason-text">{step.reason}</span>
                        </div>
                    )}

                    {Array.isArray(step.dependencies) && step.dependencies.length > 0 && (
                        <div className="step-card__deps">
                            <span className="step-card__deps-label">Depends on</span>
                            <div className="step-card__deps-list">
                                {step.dependencies.map((dep, i) => (
                                    <span key={i} className="step-dep-chip">{dep}</span>
                                ))}
                            </div>
                        </div>
                    )}

                    {!isCompleted && (
                        <button
                            className="btn-primary step-card__complete-btn"
                            onClick={() => onComplete(step)}
                        >
                            ✓ Mark Complete
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}

function TraceItem({ trace }) {
    const icons = { agent: "🤖", mcp: "🔌", error: "⚠️" };
    return (
        <div className={`trace-item trace-item--${trace.type || "agent"}`}>
            <span className="trace-item__icon">{icons[trace.type] || "•"}</span>
            <span>{trace.message}</span>
        </div>
    );
}

export default function Roadmap() {
    const [plan,    setPlan]    = useState(null);
    const [loading, setLoading] = useState(true);
    const [updateText,   setUpdateText]   = useState("");
    const [updating,     setUpdating]     = useState(false);
    const [traces,       setTraces]       = useState([]);
    const [visibleTraces, setVisibleTraces] = useState([]);
    const navigate = useNavigate();

    const fetchPlan = async () => {
        const userId = localStorage.getItem("user_id");
        if (!userId) return;
        try {
            const res  = await fetch(`${API}/career-plan/${userId}`);
            const data = await res.json();
            if (res.ok) setPlan(data.data);
        } catch {}
        finally { setLoading(false); }
    };

    useEffect(() => { fetchPlan(); }, []);

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
                fetchPlan();
            }
        }, 700);
        return () => clearInterval(id);
    }, [traces]);

    const handleComplete = (step) => {
        setUpdateText(`I completed Step ${step.step_id}: ${step.title}`);
    };

    const handleUpdate = async (e) => {
        e.preventDefault();
        if (!updateText.trim()) return;
        setUpdating(true);
        setTraces([]);
        setVisibleTraces([]);
        const userId = localStorage.getItem("user_id");
        try {
            const res  = await fetch(`${API}/career-plan/career-status-update`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId, update: updateText }),
            });
            const data = await res.json();
            if (res.ok) {
                setTraces(data.data?.trace_logs || []);
                setUpdateText("");
            }
        } catch {}
        finally { setUpdating(false); }
    };

    if (loading) {
        return (
            <Layout>
                <div className="roadmap-loading">
                    <div className="spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
                    <span>Loading your roadmap…</span>
                </div>
            </Layout>
        );
    }

    if (!plan) {
        return (
            <Layout>
                <div className="roadmap-page">
                    <div className="empty-state" style={{ minHeight: "60vh" }}>
                        <div className="empty-state__icon">🗺️</div>
                        <div className="empty-state__title">No roadmap yet</div>
                        <div className="empty-state__text">
                            Set your goal and complete the analysis to generate a personalised, justified roadmap.
                        </div>
                        <button className="btn-primary" style={{ marginTop: 16 }} onClick={() => navigate("/goal")}>
                            Set Your Goal →
                        </button>
                    </div>
                </div>
            </Layout>
        );
    }

    const safeRoadmap = Array.isArray(plan.roadmap) ? plan.roadmap : [];
    const pending   = safeRoadmap.filter(s => s.status !== "Completed");
    const completed = safeRoadmap.filter(s => s.status === "Completed");
    const progress  = plan.roadmap?.length > 0
        ? Math.round(completed.length / plan.roadmap.length * 100)
        : 0;

    const goal = plan.goal || {};

    return (
        <Layout>
            <div className="roadmap-page">

                {/* ── Header ─────────────────────────────────────── */}
                <div className="roadmap-header">
                    <div>
                        <h1 className="roadmap-header__title">
                            {goal.degree && goal.degree !== "N/A"
                                ? `${goal.degree} in ${goal.field}`
                                : goal.target_role || "My Roadmap"}
                        </h1>
                        <div className="roadmap-header__meta">
                            {goal.destination && <span>📍 {goal.destination}</span>}
                            {goal.timeline    && <span>⏱ {goal.timeline}</span>}
                        </div>
                    </div>
                    <div className="roadmap-progress-chip">
                        <span className="roadmap-progress-chip__num">{progress}%</span>
                        <span className="roadmap-progress-chip__label">Complete</span>
                    </div>
                </div>

                {/* ── Progress Bar ──────────────────────────────── */}
                <div className="roadmap-progress-bar">
                    <div className="roadmap-progress-bar__fill" style={{ width: `${progress}%` }} />
                </div>
                <div className="roadmap-progress-text">
                    {completed.length} of {plan.roadmap?.length || 0} steps completed
                </div>

                {/* ── Progress Agent ────────────────────────────── */}
                <div className="roadmap-update-card">
                    <div className="roadmap-update-card__title">Progress Agent</div>
                    <p className="roadmap-update-card__sub">
                        Tell the agent what you've accomplished. It will update your roadmap and suggest the next step.
                    </p>
                    <form className="roadmap-update-form" onSubmit={handleUpdate}>
                        <input
                            className="roadmap-update-input"
                            type="text"
                            placeholder="e.g. I registered for IELTS Academic, test on August 20"
                            value={updateText}
                            onChange={e => setUpdateText(e.target.value)}
                            disabled={updating}
                        />
                        <button
                            className="btn-primary"
                            type="submit"
                            disabled={updating || !updateText.trim()}
                        >
                            {updating
                                ? <><span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Updating…</>
                                : "Update Progress"}
                        </button>
                    </form>

                    {visibleTraces.length > 0 && (
                        <div className="trace-list" style={{ marginTop: 16 }}>
                            {visibleTraces.map((t, i) => <TraceItem key={i} trace={t} />)}
                        </div>
                    )}
                </div>

                {/* ── Pending Steps ─────────────────────────────── */}
                {pending.length > 0 && (
                    <div className="roadmap-section">
                        <div className="roadmap-section__header">
                            <span className="roadmap-section__title">Pending</span>
                            <span className="roadmap-section__count">{pending.length}</span>
                        </div>
                        <div className="roadmap-steps">
                            {pending.map(step => (
                                <StepCard key={step.step_id} step={step} onComplete={handleComplete} />
                            ))}
                        </div>
                    </div>
                )}

                {/* ── Completed Steps ───────────────────────────── */}
                {completed.length > 0 && (
                    <div className="roadmap-section">
                        <div className="roadmap-section__header">
                            <span className="roadmap-section__title">Completed</span>
                            <span className="roadmap-section__count roadmap-section__count--green">{completed.length}</span>
                        </div>
                        <div className="roadmap-steps">
                            {completed.map(step => (
                                <StepCard key={step.step_id} step={step} onComplete={() => {}} />
                            ))}
                        </div>
                    </div>
                )}

            </div>
        </Layout>
    );
}