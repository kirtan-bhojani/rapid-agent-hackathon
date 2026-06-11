// src/pages/Profile.jsx

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";
import "../pages/Documents.css";     // reuse .profile-empty styles
import "./Profile.css";

const API = import.meta.env.VITE_API_URL;

export default function Profile() {

    // --- profile state ---
    const [profile, setProfile]     = useState(null);
    const [notFound, setNotFound]   = useState(false);
    const [showAllCourses, setShowAllCourses] = useState(false);

    // --- mount fetch (unchanged) ---
    useEffect(() => {

        const userId = localStorage.getItem("user_id");

        if (!userId) {
            setNotFound(true);
            return;
        }

        fetch(`${API}/profile/${userId}`)
            .then((res) => {

                if (res.status === 404) {
                    setNotFound(true);
                    return null;
                }

                return res.json();

            })
            .then((data) => {

                if (data) {
                    setProfile(data.profile);
                    setNotFound(false);
                }

            })
            .catch(() => {
                setNotFound(true);
            });

    }, []);

    // --- notFound branch: CTA to Documents page ---
    if (notFound) {

        return (

            <Layout>

                <div className="profile-empty">

                    <div className="profile-empty__icon">📋</div>

                    <h2>No profile yet</h2>

                    <p>
                        Upload your documents to build your profile.
                        We support resumes, transcripts, passports, IELTS reports, SOPs, and LORs.
                    </p>

                    <Link to="/documents" className="profile-empty__cta">
                        Upload Documents to Get Started →
                    </Link>

                </div>

            </Layout>

        );

    }

    // --- loading branch ---
    if (!profile) {

        return (

            <Layout>

                <div className="profile-loading">

                    <div className="profile-loading__spinner" />

                    <p>Loading profile…</p>

                </div>

            </Layout>

        );

    }

    // --- helpers ---
    const initials = (profile.personal.full_name || "?")
        .split(" ")
        .map((w) => w[0])
        .slice(0, 2)
        .join("");

    const courses    = profile.academic.courses || [];
    const skills     = profile.professional.skills || [];
    const experience = profile.professional.experience || [];
    const projects   = profile.professional.projects || [];

    const COURSE_LIMIT   = 8;
    const visibleCourses = showAllCourses ? courses : courses.slice(0, COURSE_LIMIT);
    const hasHiddenCourses = courses.length > COURSE_LIMIT;

    // --- full profile view ---
    return (

        <Layout>

            <div className="profile-page">

                {/* ── Header Card ──────────────────────────────── */}

                <div className="prof-card prof-header">

                    <div className="prof-header__avatar">
                        {initials}
                    </div>

                    <div className="prof-header__info">

                        <h1 className="prof-header__name">
                            {profile.personal.full_name}
                        </h1>

                        <div className="prof-header__meta">

                            {profile.academic.institution && (
                                <span className="prof-header__meta-item">
                                    <span className="prof-header__meta-icon">🏛</span>
                                    {profile.academic.institution}
                                </span>
                            )}

                            {profile.academic.gpa && (
                                <span className="prof-header__meta-item">
                                    <span className="prof-header__meta-icon">📊</span>
                                    CGPA: {profile.academic.gpa}
                                </span>
                            )}

                            {profile.academic.graduation_date && (
                                <span className="prof-header__meta-item">
                                    <span className="prof-header__meta-icon">🎓</span>
                                    Expected: {profile.academic.graduation_date}
                                </span>
                            )}

                        </div>

                    </div>

                </div>

                {/* ── Academic Card ────────────────────────────── */}

                <div className="prof-card">

                    <h2 className="prof-section-title">Academic</h2>

                    <div className="prof-academic__grid">

                        {profile.academic.institution && (
                            <div className="prof-academic__item">
                                <span className="prof-academic__label">Institution</span>
                                <span className="prof-academic__value">{profile.academic.institution}</span>
                            </div>
                        )}

                        {profile.academic.degree && (
                            <div className="prof-academic__item">
                                <span className="prof-academic__label">Degree</span>
                                <span className="prof-academic__value">{profile.academic.degree}</span>
                            </div>
                        )}

                        {profile.academic.major && (
                            <div className="prof-academic__item">
                                <span className="prof-academic__label">Major</span>
                                <span className="prof-academic__value">{profile.academic.major}</span>
                            </div>
                        )}

                        {profile.academic.gpa && (
                            <div className="prof-academic__item">
                                <span className="prof-academic__label">GPA</span>
                                <span className="prof-academic__value">{profile.academic.gpa}</span>
                            </div>
                        )}

                        {profile.academic.graduation_date && (
                            <div className="prof-academic__item">
                                <span className="prof-academic__label">Graduation</span>
                                <span className="prof-academic__value">{profile.academic.graduation_date}</span>
                            </div>
                        )}

                    </div>

                </div>

                {/* ── Skills Card ──────────────────────────────── */}

                {skills.length > 0 && (

                    <div className="prof-card">

                        <h2 className="prof-section-title">Skills</h2>

                        <div className="prof-chips">

                            {skills.map((skill, index) => (

                                <span key={index} className="prof-chip">
                                    {skill}
                                </span>

                            ))}

                        </div>

                    </div>

                )}

                {/* ── Experience Section ───────────────────────── */}

                {experience.length > 0 && (

                    <div className="prof-card">

                        <h2 className="prof-section-title">Experience</h2>

                        <div className="prof-experience-list">

                            {experience.map((exp, index) => (

                                <div key={index} className="prof-exp-card">

                                    <div className="prof-exp-card__title">
                                        {exp.title || exp.role || "Untitled Role"}
                                    </div>

                                    {(exp.organization || exp.company) && (
                                        <div className="prof-exp-card__org">
                                            {exp.organization || exp.company}
                                        </div>
                                    )}

                                    {(exp.dates || exp.duration) && (
                                        <div className="prof-exp-card__dates">
                                            {exp.dates || exp.duration}
                                        </div>
                                    )}

                                    {exp.description && (
                                        <div className="prof-exp-card__desc">
                                            {exp.description}
                                        </div>
                                    )}

                                </div>

                            ))}

                        </div>

                    </div>

                )}

                {/* ── Projects Section ─────────────────────────── */}

                {projects.length > 0 && (

                    <div className="prof-card">

                        <h2 className="prof-section-title">Projects</h2>

                        <div className="prof-projects-grid">

                            {projects.map((proj, index) => (

                                <div key={index} className="prof-project-card">

                                    <div className="prof-project-card__title">
                                        {proj.title || proj.name || "Untitled Project"}
                                    </div>

                                    {proj.description && (
                                        <div className="prof-project-card__desc">
                                            {proj.description}
                                        </div>
                                    )}

                                </div>

                            ))}

                        </div>

                    </div>

                )}

                {/* ── Courses Section ──────────────────────────── */}

                {courses.length > 0 && (

                    <div className="prof-card">

                        <h2 className="prof-section-title">Relevant Courses</h2>

                        <div className="prof-chips">

                            {visibleCourses.map((course, index) => {

                                const label = typeof course === "string"
                                    ? course
                                    : course.name || course.code || "Course";

                                return (
                                    <span key={index} className="prof-chip prof-chip--course">
                                        {label}
                                    </span>
                                );

                            })}

                            {hasHiddenCourses && (

                                <button
                                    className="prof-chips-toggle"
                                    onClick={() => setShowAllCourses(!showAllCourses)}
                                >
                                    {showAllCourses
                                        ? "Show less"
                                        : `+${courses.length - COURSE_LIMIT} more`
                                    }
                                </button>

                            )}

                        </div>

                    </div>

                )}

            </div>

        </Layout>

    );

}
