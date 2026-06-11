import { useState, useEffect } from "react";
import Layout from "../components/Layout";
import "./Roadmap.css";
import "./Chat.css"; // Reuse trace styles

const API = import.meta.env.VITE_API_URL;

export default function Roadmap() {
    const [plan, setPlan] = useState(null);
    const [loading, setLoading] = useState(true);
    const [updateText, setUpdateText] = useState("");
    const [updating, setUpdating] = useState(false);
    const [traces, setTraces] = useState([]);
    const [visibleTraces, setVisibleTraces] = useState([]);

    const fetchPlan = async () => {
        const userId = localStorage.getItem("user_id");
        if (!userId) return;
        try {
            const res = await fetch(`${API}/career-plan/${userId}`);
            const data = await res.json();
            if (res.ok) {
                setPlan(data.data);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPlan();
    }, []);

    // Sequential trace reveal
    useEffect(() => {
        if (traces.length === 0) return;
        let currentIndex = 0;
        setVisibleTraces([]);
        const intervalId = setInterval(() => {
            if (currentIndex < traces.length) {
                setVisibleTraces(prev => [...prev, traces[currentIndex]]);
                currentIndex++;
            } else {
                clearInterval(intervalId);
                // Refresh plan after trace finishes
                fetchPlan();
            }
        }, 800);
        return () => clearInterval(intervalId);
    }, [traces]);

    const handleUpdate = async (e) => {
        e.preventDefault();
        if (!updateText.trim()) return;

        setUpdating(true);
        setTraces([]);
        setVisibleTraces([]);

        const userId = localStorage.getItem("user_id");
        try {
            const res = await fetch(`${API}/career-plan/career-status-update`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId, update: updateText }),
            });
            const data = await res.json();
            if (res.ok) {
                setTraces(data.data.trace_logs || []);
                setUpdateText("");
            }
        } catch (err) {
            console.error(err);
        } finally {
            setUpdating(false);
        }
    };

    if (loading) return <Layout><h2>Loading your roadmap...</h2></Layout>;
    if (!plan) return <Layout><h2>No roadmap found. Create one in Chat!</h2></Layout>;

    const pending = plan.roadmap.filter(s => s.status !== "Completed");
    const completed = plan.roadmap.filter(s => s.status === "Completed");

    return (
        <Layout>
            <div className="roadmap-container">
                <div className="roadmap-header">
                    <h1>Target Role: {plan.goal.target_role}</h1>
                    <p>Timeline: {plan.goal.timeline}</p>
                </div>

                <div className="status-update-section">
                    <h3>Progress Agent</h3>
                    <p>Tell the agent what you've accomplished to update your roadmap.</p>
                    <form className="status-input-row" onSubmit={handleUpdate}>
                        <input
                            className="status-input"
                            type="text"
                            placeholder="e.g. I completed the TensorFlow certification"
                            value={updateText}
                            onChange={(e) => setUpdateText(e.target.value)}
                            disabled={updating || visibleTraces.length > 0 && visibleTraces.length < traces.length}
                        />
                        <button className="chat-btn" type="submit" disabled={updating || !updateText.trim()}>
                            {updating ? "Processing..." : "Update Progress"}
                        </button>
                    </form>

                    {visibleTraces.length > 0 && (
                        <div className="trace-overlay">
                            {visibleTraces.map((trace, idx) => (
                                <div key={idx} className={`trace-log trace-${trace?.type || 'unknown'}`}>
                                    <strong>[{(trace?.type || 'system').toUpperCase()}]</strong> {trace?.message || JSON.stringify(trace)}
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                <div className="kanban-board">
                    <div className="kanban-col">
                        <h2>Pending Steps</h2>
                        {pending.map(step => (
                            <div key={step.step_id} className="task-card pending">
                                <div className="task-title">Step {step.step_id}: {step.title}</div>
                                <div className="task-desc">{step.description}</div>
                                <button className="task-btn" onClick={() => setUpdateText(`I completed Step ${step.step_id}: ${step.title}`)}>
                                    Mark Complete
                                </button>
                            </div>
                        ))}
                    </div>
                    <div className="kanban-col">
                        <h2>Completed</h2>
                        {completed.map(step => (
                            <div key={step.step_id} className="task-card completed">
                                <div className="task-title">Step {step.step_id}: {step.title}</div>
                                <div className="task-desc">{step.description}</div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </Layout>
    );
}