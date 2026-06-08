// src/components/Sidebar.jsx

import { Link, useLocation, useNavigate } from "react-router-dom";

const NAV_ITEMS = [
    { to: "/dashboard", icon: "📊", label: "Dashboard" },
    { to: "/profile",   icon: "👤", label: "Profile" },
    { to: "/documents", icon: "📄", label: "Documents" },
    { to: "/opportunities", icon: "🔍", label: "Opportunities" },
    { to: "/roadmap",   icon: "🗺️", label: "Roadmap" },
    { to: "/chat",      icon: "💬", label: "Advisor" },
];

export default function Sidebar() {

    const location = useLocation();
    const navigate = useNavigate();

    const userId = localStorage.getItem("user_id");
    const initial = userId ? userId.charAt(0).toUpperCase() : "?";
    const displayId = userId
        ? (userId.length > 20 ? userId.slice(0, 18) + "…" : userId)
        : "Not signed in";

    const handleSignOut = () => {
        localStorage.clear();
        navigate("/login");
    };

    return (

        <div className="sidebar">

            {/* ── Brand ────────────────────────────────────── */}

            <div className="sidebar__brand">
                <span className="sidebar__brand-accent">◆</span>
                <span className="sidebar__brand-rapid">Rapid</span>
                <span className="sidebar__brand-agent">Agent</span>
            </div>

            {/* ── Navigation ──────────────────────────────── */}

            <nav className="sidebar__nav">

                {NAV_ITEMS.map((item) => {

                    const isActive = location.pathname === item.to;

                    return (
                        <Link
                            key={item.to}
                            to={item.to}
                            className={
                                "sidebar__link" +
                                (isActive ? " sidebar__link--active" : "")
                            }
                        >
                            <span className="sidebar__link-icon">{item.icon}</span>
                            <span className="sidebar__link-label">{item.label}</span>
                        </Link>
                    );

                })}

            </nav>

            {/* ── User Section ────────────────────────────── */}

            <div className="sidebar__user">

                <div className="sidebar__user-info">

                    <div className="sidebar__user-avatar">
                        {initial}
                    </div>

                    <span className="sidebar__user-id" title={userId || ""}>
                        {displayId}
                    </span>

                </div>

                {userId && (
                    <button
                        className="sidebar__signout"
                        onClick={handleSignOut}
                    >
                        Sign Out
                    </button>
                )}

            </div>

        </div>

    );

}