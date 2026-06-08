// src/pages/Dashboard.jsx

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import "./Dashboard.css";
import Layout from "../components/Layout";

export default function Dashboard() {

    const [profile, setProfile] = useState(null);
    const [status, setStatus] = useState("loading");

    useEffect(() => {

        const userId = localStorage.getItem("user_id");

        if (!userId) {
            setStatus("no_user");
            return;
        }

        fetch(`http://127.0.0.1:8000/profile/${userId}`)
            .then((res) => {

                if (res.status === 404) {
                    setStatus("not_found");
                    return null;
                }

                return res.json();

            })
            .then((data) => {

                if (data) {
                    setProfile(data.profile);
                    setStatus("success");
                }

            })
            .catch(() => {
                setStatus("error");
            });

    }, []);

    let headerText;
    if (status === "loading")   headerText = "Loading...";
    if (status === "no_user")   headerText = "Please login";
    if (status === "not_found") headerText = "No profile found. Upload documents to get started.";
    if (status === "error")     headerText = "Unable to connect to server.";
    if (status === "success")   headerText = `Welcome, ${profile.personal.full_name} 👋`;

    return (

        <Layout>

            <div className="dashboard">

                <div className="dash-header">

                    <h1>
                        {headerText}
                    </h1>

                    {status === "success" && (
                        <p>Your student profile dashboard</p>
                    )}

                </div>

                {/* ── Stat Cards ───────────────────────────────── */}

                <div className="dash-cards">

                    {/* Profile Completion */}
                    <div className="dash-card dash-card--blue">

                        <div className="dash-card__header">
                            <div className="dash-card__icon">📊</div>
                            <span className="dash-card__label">Profile Completion</span>
                        </div>

                        <div className="dash-card__value">78%</div>

                        <div className="dash-progress">
                            <div className="dash-progress__track">
                                <div
                                    className="dash-progress__fill"
                                    style={{ width: "78%" }}
                                />
                            </div>
                            <div className="dash-progress__text">78 / 100</div>
                        </div>

                    </div>

                    {/* Roadmap Progress */}
                    <div className="dash-card dash-card--purple">

                        <div className="dash-card__header">
                            <div className="dash-card__icon">🗺️</div>
                            <span className="dash-card__label">Roadmap Progress</span>
                        </div>

                        <div className="dash-card__value">42%</div>

                    </div>

                    {/* Universities Tracked */}
                    <div className="dash-card dash-card--green">

                        <div className="dash-card__header">
                            <div className="dash-card__icon">🏛️</div>
                            <span className="dash-card__label">Universities Tracked</span>
                        </div>

                        <div className="dash-card__value">12</div>

                    </div>

                </div>

                {/* ── Quick Actions ────────────────────────────── */}

                <div className="dash-actions">

                    <h2 className="dash-actions__title">Quick Actions</h2>

                    <div className="dash-actions__grid">

                        <Link to="/profile" className="dash-action">
                            <div className="dash-action__icon">👤</div>
                            <div className="dash-action__text">
                                <span className="dash-action__label">View Profile</span>
                                <span className="dash-action__sub">See your full profile</span>
                            </div>
                        </Link>

                        <Link to="/documents" className="dash-action">
                            <div className="dash-action__icon">📄</div>
                            <div className="dash-action__text">
                                <span className="dash-action__label">Upload Documents</span>
                                <span className="dash-action__sub">Add or update documents</span>
                            </div>
                        </Link>

                        <div className="dash-action dash-action--disabled">
                            <div className="dash-action__icon">🎯</div>
                            <div className="dash-action__text">
                                <span className="dash-action__label">Set Goal</span>
                                <span className="dash-action__sub">Coming Soon</span>
                            </div>
                        </div>

                    </div>

                </div>

                {/* ── Deadline Card ────────────────────────────── */}

                <div className="dash-deadline">

                    <div className="dash-deadline__header">
                        <div className="dash-deadline__icon">📅</div>
                        <span className="dash-deadline__title">Upcoming Deadline</span>
                    </div>

                    <p className="dash-deadline__name">
                        SECAI AI Scholarship
                    </p>

                    <span className="dash-deadline__date">
                        🕐 June 30, 2026
                    </span>

                </div>

            </div>

        </Layout>

    );

}
