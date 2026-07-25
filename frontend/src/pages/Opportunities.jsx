// src/pages/Opportunities.jsx — Eligibility tier-based opportunity browser

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import "./Opportunities.css";

const API = import.meta.env.VITE_API_URL;

const TIER_CONFIG = {
    safe:               { label: "Safe",         icon: "🟢", desc: "You comfortably meet all known requirements.", class: "tier--safe"     },
    target:             { label: "Target",        icon: "🎯", desc: "You meet requirements with a small margin.",   class: "tier--target"   },
    ambitious:          { label: "Ambitious",     icon: "🚀", desc: "Highly competitive — admission is uncertain.", class: "tier--ambitious" },
    near_eligible:      { label: "Near Eligible", icon: "🔶", desc: "1–2 minor gaps to close.",                    class: "tier--near"      },
    long_term_stretch:  { label: "Stretch Goal",  icon: "📈", desc: "Significant gaps — long-term target.",         class: "tier--stretch"   },
};

const TAB_CONFIG = [
    { key: "eligible", label: "Eligible", icon: "✅", tiers: ["safe", "target", "ambitious"] },
    { key: "growth",   label: "Growth",   icon: "📈", tiers: ["near_eligible", "long_term_stretch"] },
];

function OpportunityCard({ opp, tier }) {
    const cfg = TIER_CONFIG[tier] || {};
    const [expanded, setExpanded] = useState(false);

    return (
        <div className={`opp-card ${cfg.class || ""}`}>
            <div className="opp-card__header">
                <div className="opp-card__tier-badge">
                    {cfg.icon} {cfg.label}
                </div>
                <h3 className="opp-card__title">{opp.name || opp.title || "Opportunity"}</h3>
                <p className="opp-card__org">
                    {opp.institution || opp.organization || opp.company || ""}
                </p>
            </div>

            {/* Fit Reason — prominently shown */}
            {opp.fit_reason && (
                <div className="opp-card__fit-reason">
                    <span className="opp-card__fit-reason-label">Why this is relevant</span>
                    <p>{opp.fit_reason}</p>
                </div>
            )}

            {/* Key details */}
            <div className="opp-card__details">
                {opp.location && (
                    <span className="opp-detail-chip">📍 {opp.location}</span>
                )}
                {opp.deadline && (
                    <span className="opp-detail-chip opp-detail-chip--deadline">📅 {opp.deadline}</span>
                )}
                {(opp.qs_ranking || opp.ranking) && (
                    <span className="opp-detail-chip">🏆 QS #{opp.qs_ranking || opp.ranking}</span>
                )}
                {opp.amount && (
                    <span className="opp-detail-chip opp-detail-chip--funding">💰 {opp.amount}</span>
                )}
            </div>

            {/* Gap summary for growth tiers */}
            {opp.gap_summary && (
                <div className="opp-card__gap-summary">
                    ⚠️ {opp.gap_summary}
                </div>
            )}

            {/* Expandable details */}
            <button className="opp-card__expand-btn" onClick={() => setExpanded(e => !e)}>
                {expanded ? "▲ Hide details" : "▼ Show details"}
            </button>

            {expanded && (
                <div className="opp-card__expanded">
                    {opp.description && (
                        <p className="opp-card__expanded-desc">{opp.description}</p>
                    )}

                    {/* Known gaps */}
                    {opp.known_gaps?.length > 0 && (
                        <div className="opp-card__gaps">
                            <div className="opp-card__gaps-title">⚠️ Known Gaps</div>
                            {opp.known_gaps.map((gap, i) => (
                                <div key={i} className="opp-gap-row">
                                    <span className="opp-gap-row__req">{gap.requirement}</span>
                                    <span className="opp-gap-row__current">Have: {gap.current ?? "Unknown"}</span>
                                    <span className="opp-gap-row__required">Need: {gap.required ?? "Unknown"}</span>
                                    <span className={`opp-gap-row__severity opp-gap-row__severity--${gap.severity}`}>
                                        {gap.severity}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Unknown requirements */}
                    {opp.unknown_requirements?.length > 0 && (
                        <div className="opp-card__unknowns">
                            <div className="opp-card__unknowns-title">📋 Missing Profile Info</div>
                            <p className="opp-card__unknowns-sub">
                                Add this to your profile to complete eligibility check:
                            </p>
                            {opp.unknown_requirements.map((req, i) => (
                                <div key={i} className="opp-unknown-row">
                                    <span className="opp-unknown-row__req">{req.requirement}</span>
                                    {req.required && <span className="opp-unknown-row__val">Required: {req.required}</span>}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Documents required */}
                    {opp.required_documents?.length > 0 && (
                        <div className="opp-card__docs">
                            <div className="opp-card__docs-title">📄 Documents Required</div>
                            <div className="opp-doc-chips">
                                {opp.required_documents.map((doc, i) => (
                                    <span key={i} className="opp-doc-chip">{doc}</span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Actions */}
            <div className="opp-card__actions">
                {(opp.url || opp.application_url || opp.website) && (
                    <a
                        href={opp.url || opp.application_url || opp.website}
                        target="_blank"
                        rel="noreferrer"
                        className="btn-secondary"
                        style={{ fontSize: 13, padding: "8px 14px" }}
                    >
                        🔗 Official Page
                    </a>
                )}
            </div>
        </div>
    );
}

function TierSection({ tier, items }) {
    if (!items || items.length === 0) return null;
    const cfg = TIER_CONFIG[tier] || {};
    return (
        <div className="tier-section">
            <div className="tier-section__header">
                <span className="tier-section__icon">{cfg.icon}</span>
                <div>
                    <div className="tier-section__title">{cfg.label}</div>
                    <div className="tier-section__desc">{cfg.desc}</div>
                </div>
                <span className="tier-section__count">{items.length}</span>
            </div>
            <div className="opp-grid">
                {items.map((opp, i) => (
                    <OpportunityCard key={i} opp={opp} tier={tier} />
                ))}
            </div>
        </div>
    );
}

export default function Opportunities() {
    const [data,    setData]    = useState(null);
    const [loading, setLoading] = useState(true);
    const [error,   setError]   = useState(null);
    const [activeTab, setActiveTab] = useState("eligible");
    const navigate = useNavigate();

    useEffect(() => {
        const userId = localStorage.getItem("user_id");
        if (!userId) { setError("no_user"); setLoading(false); return; }

        fetch(`${API}/opportunities/${userId}`)
            .then(res => {
                if (!res.ok) {
                    return res.json().then(e => { throw new Error(e.detail || "fetch_failed"); });
                }
                return res.json();
            })
            .then(json => { setData(json); setLoading(false); })
            .catch(err => { setError(err.message); setLoading(false); });
    }, []);

    if (loading) {
        return (
            <Layout>
                <div className="opp-page">
                    <div className="empty-state" style={{ minHeight: "60vh" }}>
                        <div className="spinner" style={{ width: 40, height: 40, borderWidth: 3 }} />
                        <div className="empty-state__text" style={{ marginTop: 16 }}>
                            Searching opportunities and classifying them for your goal…<br />
                            This may take a moment.
                        </div>
                    </div>
                </div>
            </Layout>
        );
    }

    if (error?.includes("No goal") || error?.includes("Career Plan")) {
        return (
            <Layout>
                <div className="opp-page">
                    <div className="empty-state" style={{ minHeight: "60vh" }}>
                        <div className="empty-state__icon">🎯</div>
                        <div className="empty-state__title">Set your goal first</div>
                        <div className="empty-state__text">
                            RAPID needs to know your goal to find relevant opportunities.
                        </div>
                        <button className="btn-primary" style={{ marginTop: 16 }} onClick={() => navigate("/goal")}>
                            Set Your Goal →
                        </button>
                    </div>
                </div>
            </Layout>
        );
    }

    if (error) {
        return (
            <Layout>
                <div className="opp-page">
                    <div className="opp-error">⚠️ {error}</div>
                </div>
            </Layout>
        );
    }

    const eligible = data?.eligible || { safe: [], target: [], ambitious: [] };
    const growth   = data?.growth   || { near_eligible: [], long_term_stretch: [] };
    const metadata = data?.metadata || {};
    const goalSummary = data?.goal_summary || {};

    const eligibleCount = Object.values(eligible).flat().length;
    const growthCount   = Object.values(growth).flat().length;
    const totalCount    = eligibleCount + growthCount;

    const activeData = activeTab === "eligible" ? eligible : growth;
    const activeTiers = TAB_CONFIG.find(t => t.key === activeTab)?.tiers || [];

    return (
        <Layout>
            <div className="opp-page">
                {/* ── Header ─────────────────────────────────────── */}
                <div className="opp-header">
                    <div>
                        <h1 className="opp-header__title">Opportunities</h1>
                        {goalSummary.field && (
                            <p className="opp-header__goal">
                                🎯 {goalSummary.goal_type} in {goalSummary.field}
                                {goalSummary.country ? ` — ${goalSummary.country}` : ""}
                            </p>
                        )}
                    </div>
                    <div className="opp-header__stats">
                        <div className="opp-stat">
                            <span className="opp-stat__num" style={{ color: "var(--color-success)" }}>{eligibleCount}</span>
                            <span className="opp-stat__label">Eligible</span>
                        </div>
                        <div className="opp-stat">
                            <span className="opp-stat__num" style={{ color: "var(--color-warning)" }}>{growthCount}</span>
                            <span className="opp-stat__label">Growth</span>
                        </div>
                    </div>
                </div>

                {/* ── Tabs ───────────────────────────────────────── */}
                <div className="opp-tabs">
                    {TAB_CONFIG.map(tab => (
                        <button
                            key={tab.key}
                            className={`opp-tab ${activeTab === tab.key ? "opp-tab--active" : ""}`}
                            onClick={() => setActiveTab(tab.key)}
                        >
                            {tab.icon} {tab.label}
                            <span className="opp-tab__count">
                                {tab.key === "eligible" ? eligibleCount : growthCount}
                            </span>
                        </button>
                    ))}
                </div>

                {/* ── Content ────────────────────────────────────── */}
                {totalCount === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state__icon">🔍</div>
                        <div className="empty-state__title">No results found</div>
                        <div className="empty-state__text">
                            No opportunities were found for your goal. This may be due to search limits.
                            Check back or refine your goal.
                        </div>
                    </div>
                ) : (
                    <div className="opp-content">
                        {activeTiers.map(tier => (
                            <TierSection key={tier} tier={tier} items={activeData[tier]} />
                        ))}
                        {activeTiers.every(t => !activeData[t]?.length) && (
                            <div className="empty-state">
                                <div className="empty-state__icon">{activeTab === "eligible" ? "✅" : "📈"}</div>
                                <div className="empty-state__title">
                                    {activeTab === "eligible" ? "No eligible results" : "No growth results"}
                                </div>
                                <div className="empty-state__text">
                                    {activeTab === "eligible"
                                        ? "Switch to Growth tab to see opportunities to work towards."
                                        : "Switch to Eligible tab to see opportunities you qualify for now."}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </Layout>
    );
}