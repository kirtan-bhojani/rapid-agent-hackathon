// src/components/Sidebar.jsx

import { Link, useLocation, useNavigate } from "react-router-dom";

const NAV_ITEMS = [
    { to: "/dashboard",     icon: "📊", label: "Dashboard"      },
    { to: "/goal",          icon: "🎯", label: "Set Goal"       },
    { to: "/gap-analysis",  icon: "📉", label: "Gap Analysis"   },
    { to: "/roadmap",       icon: "🗺️", label: "Roadmap"        },
    { to: "/opportunities", icon: "🔍", label: "Opportunities"  },
    { to: "/documents",     icon: "📄", label: "Documents"      },
    { to: "/profile",       icon: "👤", label: "Profile"        },
];

export default function Sidebar() {
    const location = useLocation();
    const navigate  = useNavigate();

    const userId = localStorage.getItem("user_id");
    const email  = localStorage.getItem("user_email") || "";
    const displayName = email
        ? email.split("@")[0]
        : (userId ? userId.slice(0, 14) + "…" : "Not signed in");
    const initial = (email || userId || "?")[0].toUpperCase();

    const handleSignOut = () => {
        localStorage.clear();
        navigate("/login");
    };

    return (
        <div className="sidebar">
            {/* ── Brand ───────────────────────────────────────── */}
            <div className="sidebar__brand">
                <span className="sidebar__brand-accent">◆</span>
                <span className="sidebar__brand-rapid">Rapid</span>
                <span className="sidebar__brand-agent">Agent</span>
            </div>

            {/* ── Navigation ──────────────────────────────────── */}
            <nav className="sidebar__nav">
                {NAV_ITEMS.map((item) => {
                    const isActive = location.pathname === item.to;
                    return (
                        <Link
                            key={item.to}
                            to={item.to}
                            className={"sidebar__link" + (isActive ? " sidebar__link--active" : "")}
                        >
                            <span className="sidebar__link-icon">{item.icon}</span>
                            <span className="sidebar__link-label">{item.label}</span>
                        </Link>
                    );
                })}
            </nav>

            {/* ── User Section ────────────────────────────────── */}
            <div className="sidebar__user">
                <div className="sidebar__user-info">
                    <div className="sidebar__user-avatar">{initial}</div>
                    <span className="sidebar__user-id" title={email || userId || ""}>
                        {displayName}
                    </span>
                </div>
                {userId && (
                    <button className="sidebar__signout" onClick={handleSignOut}>
                        Sign Out
                    </button>
                )}
            </div>
        </div>
    );
}