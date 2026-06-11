// src/pages/Login.jsx

import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./auth.css";

const API = import.meta.env.VITE_API_URL;

export default function Login() {

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

            const res = await fetch(`${API}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password }),
            });

            const data = await res.json();

            if (!res.ok || data.status !== "success") {
                setError(data.detail || "Login failed. Please check your credentials.");
                setLoading(false);
                return;
            }

            localStorage.setItem("user_id", data.user_id);
            navigate("/dashboard");

        } catch (err) {

            setError("Could not connect to server. Try again.");
            setLoading(false);

        }

    };

    return (

        <div className="auth-page">

            <div className="auth-card">

                <h1 className="auth-title">Welcome back</h1>

                <p className="auth-subtitle">Sign in to your account</p>

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
                        {loading ? "Signing in..." : "Sign In"}
                    </button>

                </form>

                <p className="auth-link">
                    Don&apos;t have an account?{" "}
                    <Link to="/register">Register</Link>
                </p>

            </div>

        </div>

    );

}
