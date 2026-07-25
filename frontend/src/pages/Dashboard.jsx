// src/pages/Dashboard.jsx — Real data dashboard, no hardcoded values

import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import "./Dashboard.css";

const API = import.meta.env.VITE_API_URL;

const DOC_TYPE_CONFIG = {
    resume:     { icon: "📄", label: "Resume" },
    transcript: { icon: "📋", label: "Transcript" },
    passport:   { icon: "🛂", label: "Passport" },
    ielts:      { icon: "🌍", label: "IELTS" },
    sop:        { icon: "✍️", label: "Statement of Purpose" },
    lor:        { icon: "📝", label: "Letter of Recommendation" },
};

const PRIORITY_COLOR = {
    critical: "var(--color-danger)",
    high:     "#f97316",
    medium:   "var(--color-warning)",
    low:      "var(--color-success)",
};

function StatCard({ icon, label, value, sub, color, progress }) {
    return (
        <div className="dash-card" style={{ borderTop: `3px solid ${color}` }}>
            <div className="dash-card__header">
                <span className="dash-card__icon">{icon}</span>
                <span className="dash-card__label">{label}</span>
            </div>
            <div className="dash-card__value" style={{ color }}>{value}</div>
            {sub && <div className="dash-card__sub">{sub}</div>}
            {progress != null && (
                <div className="dash-progress">
                    <div className="dash-progress__track">
                        <div
                            className="dash-progress__fill"
                            style={{ width: `${progress}%`, background: color }}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}

export default function Dashboard() {
    const [dashData, setDashData]   = useState(null);
    const [profile,  setProfile]    = useState(null);
    const [status,   setStatus]     = useState("loading");
    const navigate = useNavigate();

    useEffect(() => {
        const userId = localStorage.getItem("user_id");
        if (!userId) { setStatus("no_user"); return; }

        // Parallel: fetch dashboard stats + profile
        Promise.all([
            fetch(`${API}/dashboard/${userId}`).then(r => r.ok ? r.json() : null),
            fetch(`${API}/profile/${userId}`).then(r => r.status === 404 ? null : r.ok ? r.json() : null),
        ])
            .then(([dash, prof]) => {
                setDashData(dash);
                setProfile(prof?.profile || null);
                setStatus("success");
            })
            .catch(() => setStatus("error"));
    }, []);

    if (status === "loading") {
        return (
            <Layout>
                <div className="dashboard-loading">
                    <div className="spinner" style={{ width: 36, height: 36, borderWidth: 3 }} />
                    <span>Loading dashboard…</span>
                </div>
            </Layout>
        );
    }

    if (status === "no_user") {
        return (
            <Layout>
                <div className="empty-state" style={{ minHeight: "60vh" }}>
                    <div className="empty-state__icon">🔐</div>
                    <div className="empty-state__title">Not signed in</div>
                    <button className="btn-primary" style={{ marginTop: 16 }} onClick={() => navigate("/login")}>Sign In</button>
                </div>
            </Layout>
        );
    }

    const name = profile?.personal?.full_name || localStorage.getItem("user_email") || "there";
    const profileCompletion = dashData?.profile_completion ?? 0;
    const roadmapProgress   = dashData?.roadmap_progress ?? { completed: 0, total: 0, percentage: 0 };
    const gapScore          = dashData?.gap_score;
    const goal              = dashData?.goal_summary;
    const nextAction        = dashData?.next_critical_action;
    const deadlines         = dashData?.upcoming_deadlines ?? [];
    const docsUploaded      = dashData?.documents_uploaded ?? [];
    const hasGoal           = dashData?.has_goal ?? false;

    return (
        <Layout>
            <div className="dashboard">

                {/* ── Header ─────────────────────────────────────── */}
                <div className="dash-header">
                    <div>
                        <h1 className="dash-header__title">Welcome back, {name.split(" ")[0]} 👋</h1>
                        {goal ? (
                            <p className="dash-header__goal">
                                🎯 {goal.degree && goal.degree !== "N/A"
                                    ? `${goal.degree} in ${goal.field} — ${goal.destination}`
                                    : goal.target_role || goal.raw_query}
                            </p>
                        ) : (
                            <p className="dash-header__sub">Set your goal to activate your personalised roadmap.</p>
                        )}
                    </div>
                    {!hasGoal && (
                        <button className="btn-primary" onClick={() => navigate("/goal")}>
                            🎯 Set Your Goal
                        </button>
                    )}
                </div>

                {/* ── Stat Cards ─────────────────────────────────── */}
                <div className="dash-cards">
                    <StatCard
                        icon="👤"
                        label="Profile Completion"
                        value={`${profileCompletion}%`}
                        sub={docsUploaded.length > 0
                            ? `${docsUploaded.length} document${docsUploaded.length !== 1 ? "s" : ""} uploaded`
                            : "Upload documents to build your profile"}
                        color="var(--color-brand)"
                        progress={profileCompletion}
                    />

                    {hasGoal ? (
                        <StatCard
                            icon="🗺️"
                            label="Roadmap Progress"
                            value={roadmapProgress.total > 0
                                ? `${roadmapProgress.completed}/${roadmapProgress.total}`
                                : "0 steps"}
                            sub={roadmapProgress.total > 0
                                ? `${roadmapProgress.percentage}% complete`
                                : "No roadmap generated yet"}
                            color="var(--color-success)"
                            progress={roadmapProgress.percentage}
                        />
                    ) : (
                        <div className="dash-card dash-card--empty">
                            <div className="dash-card__header">
                                <span className="dash-card__icon">🗺️</span>
                                <span className="dash-card__label">Roadmap Progress</span>
                            </div>
                            <div className="dash-card__placeholder">Set a goal to generate your roadmap</div>
                            <button className="btn-secondary dash-card__cta" onClick={() => navigate("/goal")}>Set Goal →</button>
                        </div>
                    )}

                    {gapScore != null ? (
                        <StatCard
                            icon="📊"
                            label="Readiness Score"
                            value={`${gapScore}%`}
                            sub={gapScore >= 70 ? "Strong profile match"
                               : gapScore >= 40 ? "Significant gaps to close"
                               : "Critical requirements missing"}
                            color={gapScore >= 70 ? "var(--color-success)"
                                 : gapScore >= 40 ? "var(--color-warning)"
                                 : "var(--color-danger)"}
                            progress={gapScore}
                        />
                    ) : (
                        <div className="dash-card dash-card--empty">
                            <div className="dash-card__header">
                                <span className="dash-card__icon">📊</span>
                                <span className="dash-card__label">Readiness Score</span>
                            </div>
                            <div className="dash-card__placeholder">Set a goal to see your readiness</div>
                        </div>
                    )}
                </div>

                {/* ── Next Critical Action ──────────────────────── */}
                {nextAction && (
                    <div className="dash-next-action">
                        <span className="dash-next-action__icon">🚀</span>
                        <div>
                            <div className="dash-next-action__label">Next Critical Action</div>
                            <div className="dash-next-action__text">{nextAction}</div>
                        </div>
                        <button className="btn-secondary" onClick={() => navigate("/roadmap")} style={{ flexShrink: 0 }}>
                            View Roadmap
                        </button>
                    </div>
                )}

                {/* ── Quick Actions ─────────────────────────────── */}
                <div className="dash-section">
                    <div className="section-title">Quick Actions</div>
                    <div className="dash-actions__grid">
                        <Link to="/goal" className="dash-action">
                            <span className="dash-action__icon">🎯</span>
                            <div>
                                <div className="dash-action__label">{hasGoal ? "Update Goal" : "Set Goal"}</div>
                                <div className="dash-action__sub">
                                    {hasGoal ? "Modify your current goal" : "Start goal analysis"}
                                </div>
                            </div>
                        </Link>
                        <Link to="/gap-analysis" className="dash-action">
                            <span className="dash-action__icon">📊</span>
                            <div>
                                <div className="dash-action__label">Gap Analysis</div>
                                <div className="dash-action__sub">See what you're missing</div>
                            </div>
                        </Link>
                        <Link to="/roadmap" className="dash-action">
                            <span className="dash-action__icon">🗺️</span>
                            <div>
                                <div className="dash-action__label">My Roadmap</div>
                                <div className="dash-action__sub">Track and update progress</div>
                            </div>
                        </Link>
                        <Link to="/opportunities" className="dash-action">
                            <span className="dash-action__icon">🔍</span>
                            <div>
                                <div className="dash-action__label">Opportunities</div>
                                <div className="dash-action__sub">Universities, scholarships, jobs</div>
                            </div>
                        </Link>
                        <Link to="/documents" className="dash-action">
                            <span className="dash-action__icon">📄</span>
                            <div>
                                <div className="dash-action__label">Documents</div>
                                <div className="dash-action__sub">Upload or manage files</div>
                            </div>
                        </Link>
                        <Link to="/profile" className="dash-action">
                            <span className="dash-action__icon">👤</span>
                            <div>
                                <div className="dash-action__label">Profile</div>
                                <div className="dash-action__sub">View your unified profile</div>
                            </div>
                        </Link>
                    </div>
                </div>

                {/* ── Documents Uploaded ────────────────────────── */}
                {docsUploaded.length > 0 && (
                    <div className="dash-section">
                        <div className="section-title">Documents Uploaded</div>
                        <div className="dash-doc-chips">
                            {docsUploaded.map((type, i) => {
                                const cfg = DOC_TYPE_CONFIG[type] || { icon: "📁", label: type };
                                return (
                                    <div key={i} className="dash-doc-chip">
                                        <span>{cfg.icon}</span>
                                        <span>{cfg.label}</span>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* ── Upcoming Deadlines ────────────────────────── */}
                {deadlines.length > 0 && (
                    <div className="dash-section">
                        <div className="section-title">Upcoming Deadlines</div>
                        <div className="dash-deadlines">
                            {deadlines.map((d, i) => (
                                <div key={i} className="dash-deadline-item">
                                    <div
                                        className="dash-deadline-item__dot"
                                        style={{ background: PRIORITY_COLOR[d.priority] || "var(--color-brand)" }}
                                    />
                                    <div className="dash-deadline-item__info">
                                        <div className="dash-deadline-item__task">{d.task}</div>
                                        <div className="dash-deadline-item__date">⏱ {d.deadline}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

            </div>
        </Layout>
    );
}
