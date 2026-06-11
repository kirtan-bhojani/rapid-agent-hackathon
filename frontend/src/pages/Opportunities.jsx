import { useState, useEffect } from "react";
import Layout from "../components/Layout";
import "./Opportunities.css";

export default function Opportunities() {
    const [opportunities, setOpportunities] = useState([]);
    const [loading, setLoading] = useState(false);
    const [category, setCategory] = useState("job");
    const [traces, setTraces] = useState([]);
    const [visibleTraces, setVisibleTraces] = useState([]);
    const [error, setError] = useState(null);

    const categories = ["job", "internship", "university", "scholarship", "certification", "course"];

    const fetchOpportunities = async (cat) => {
        const userId = localStorage.getItem("user_id");
        if (!userId) {
            setError("No Profile. Please login and upload a resume.");
            return;
        }

        setLoading(true);
        setError(null);
        setTraces([]);
        setVisibleTraces([]);
        setOpportunities([]);

        try {
            const res = await fetch(`http://127.0.0.1:8000/opportunities/${userId}?category=${cat}`);
            const data = await res.json();

            if (res.ok && data.status === "success") {
                setTraces(data.trace_logs || []);
                setOpportunities(data.data || []);
            } else {
                if (res.status === 404) {
                    setError(data.detail);
                } else {
                    setError("Failed to fetch opportunities.");
                }
            }
        } catch (err) {
            setError("Error: Could not connect to server.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchOpportunities(category);
    }, [category]);

    // Trace viewer sequence
    useEffect(() => {
        if (traces.length === 0) return;
        let currentIndex = 0;
        const intervalId = setInterval(() => {
            if (currentIndex < traces.length) {
                setVisibleTraces(prev => [...prev, traces[currentIndex]]);
                currentIndex++;
            } else {
                clearInterval(intervalId);
            }
        }, 800);
        return () => clearInterval(intervalId);
    }, [traces]);

    return (
        <Layout>
            <div className="opp-container">
                <h1 className="opp-title">Opportunity Intelligence</h1>

                <div className="opp-filters">
                    {categories.map(cat => (
                        <button 
                            key={cat} 
                            className={`filter-btn ${category === cat ? 'active' : ''}`}
                            onClick={() => setCategory(cat)}
                        >
                            {cat.charAt(0).toUpperCase() + cat.slice(1)}s
                        </button>
                    ))}
                </div>

                {error && <div className="opp-error">{error}</div>}

                {visibleTraces.length > 0 && opportunities.length === 0 && (
                    <div className="trace-viewer">
                        {visibleTraces.map((trace, idx) => (
                            <div key={idx} className={`trace-log trace-${trace?.type || 'unknown'}`}>
                                <strong>[{(trace?.type || 'system').toUpperCase()}]</strong> {trace?.message || JSON.stringify(trace)}
                            </div>
                        ))}
                    </div>
                )}

                <div className="opp-grid">
                    {opportunities.map(opp => (
                        <div key={opp._id} className="opp-card">
                            <div className="opp-header">
                                <span className="opp-badge">{opp.category}</span>
                                <h3>{opp.title}</h3>
                                <p className="opp-org">{opp.organization}</p>
                            </div>
                            
                            <div className="opp-intelligence">
                                <div className="fit-score-container">
                                    <div className="fit-score" style={{ color: opp.fit_score >= 80 ? '#22c55e' : opp.fit_score >= 60 ? '#eab308' : '#ef4444' }}>
                                        {opp.fit_score}%
                                    </div>
                                    <span>Fit Score</span>
                                </div>
                                <p className="opp-reasoning">{opp.reasoning}</p>
                            </div>

                            <div className="opp-details">
                                <details>
                                    <summary>View Intelligence Details</summary>
                                    <div className="details-content">
                                        <h4>Strengths</h4>
                                        <ul>{opp.strengths?.map((s, i) => <li key={i}>✅ {s}</li>)}</ul>
                                        <h4>Risks</h4>
                                        <ul>{opp.risks?.map((r, i) => <li key={i}>⚠️ {r}</li>)}</ul>
                                        <h4>Missing Requirements</h4>
                                        <ul>{opp.missing_requirements?.map((m, i) => <li key={i}>❌ {m}</li>)}</ul>
                                        <h4>Improvement Actions</h4>
                                        <ul>{opp.improvement_actions?.map((a, i) => <li key={i}>🚀 {a}</li>)}</ul>
                                    </div>
                                </details>
                            </div>

                            <div className="opp-actions">
                                <a href={opp.application_url} target="_blank" rel="noreferrer" className="btn-secondary">
                                    View Original
                                </a>
                                <button className="btn-primary" onClick={() => alert("Prepare Application feature coming soon!")}>
                                    Prepare Application
                                </button>
                            </div>
                        </div>
                    ))}
                </div>

                {!loading && !error && opportunities.length === 0 && visibleTraces.length === traces.length && traces.length > 0 && (
                    <div className="opp-empty">No opportunities found for this category.</div>
                )}
            </div>
        </Layout>
    );
}