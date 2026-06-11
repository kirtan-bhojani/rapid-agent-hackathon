// src/pages/Register.jsx

import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./auth.css";

export default function Register() {

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);

    const navigate = useNavigate();

    const handleSubmit = async (e) => {

        e.preventDefault();
        setError(null);
        setLoading(true);

        try {

            const API = import.meta.env.VITE_API_URL;
            const res = await fetch(`${API}/auth/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password }),
            });

            const data = await res.json();

            if (!res.ok || data.status !== "success") {
                setError(data.detail || "Registration failed. Please try again.");
                setLoading(false);
                return;
            }

            navigate("/login");

        } catch (err) {

            setError("Could not connect to server. Try again.");
            setLoading(false);

        }

    };

    return (

        <div className="auth-page">

            <div className="auth-card">

                <h1 className="auth-title">Create account</h1>

                <p className="auth-subtitle">Start your journey</p>

                <form className="auth-form" onSubmit={handleSubmit}>

                    <div className="auth-field">
                        <label>Email</label>
                        <input
                            type="email"
                            placeholder="you@example.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>

                    <div className="auth-field">
                        <label>Password</label>
                        <input
                            type="password"
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>

                    {error && <p className="auth-error">{error}</p>}

                    <button type="submit" className="auth-btn" disabled={loading}>
                        {loading ? "Creating account..." : "Register"}
                    </button>

                </form>

                <p className="auth-link">
                    Already have an account?{" "}
                    <Link to="/login">Sign in</Link>
                </p>

            </div>

        </div>

    );

}
