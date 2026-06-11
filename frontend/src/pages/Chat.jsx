import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import "./Chat.css";

const API = import.meta.env.VITE_API_URL;

export default function Chat() {
    const [goal, setGoal] = useState("");
    const [loading, setLoading] = useState(false);
    const [traces, setTraces] = useState([]);
    const [visibleTraces, setVisibleTraces] = useState([]);
    const [isComplete, setIsComplete] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!goal.trim()) return;

        setLoading(true);
        setTraces([]);
        setVisibleTraces([]);
        setIsComplete(false);

        const userId = localStorage.getItem("user_id");

        try {
            const res = await fetch(`${API}/career-plan/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId, goal }),
            });

            const data = await res.json();

            if (res.ok && data.status === "success") {
                setTraces(data.trace_logs || []);
            } else {
                setTraces([{ type: "agent", message: "Error: " + (data.detail || "Failed to generate plan.") }]);
            }
        } catch (err) {
            setTraces([{ type: "agent", message: "Error: Could not connect to server." }]);
        } finally {
            setLoading(false);
        }
    };

    // Sequentially reveal trace logs
    useEffect(() => {
        if (traces.length === 0) return;

        let currentIndex = 0;
        const intervalId = setInterval(() => {
            if (currentIndex < traces.length) {
                setVisibleTraces(prev => [...prev, traces[currentIndex]]);
                currentIndex++;
            } else {
                clearInterval(intervalId);
                setIsComplete(true);
            }
        }, 800); // 800ms delay to simulate "thinking"

        return () => clearInterval(intervalId);
    }, [traces]);

    return (
        <Layout>
            <div className="chat-container">
                <h1 className="chat-title">Career Copilot</h1>
                
                <form className="chat-input-area" onSubmit={handleSubmit}>
                    <input
                        className="chat-input"
                        type="text"
                        placeholder="What is your career goal? (e.g. I want to be an ML Engineer in 6 months)"
                        value={goal}
                        onChange={(e) => setGoal(e.target.value)}
                        disabled={loading || traces.length > 0}
                    />
                    <button className="chat-btn" type="submit" disabled={loading || !goal.trim() || traces.length > 0}>
                        {loading ? "Generating..." : "Generate Plan"}
                    </button>
                </form>

                {visibleTraces.length > 0 && (
                    <div className="trace-viewer">
                        {visibleTraces.map((trace, idx) => (
                            <div key={idx} className={`trace-log trace-${trace?.type || 'unknown'}`}>
                                <strong>[{(trace?.type || 'system').toUpperCase()}]</strong> {trace?.message || JSON.stringify(trace)}
                            </div>
                        ))}
                    </div>
                )}

                {isComplete && (
                    <div className="roadmap-btn-container">
                        <button className="chat-btn" onClick={() => navigate("/roadmap")}>
                            View My Roadmap
                        </button>
                    </div>
                )}
            </div>
        </Layout>
    );
}
