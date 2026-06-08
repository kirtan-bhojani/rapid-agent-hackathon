import { Link } from "react-router-dom";

export default function Sidebar() {

    return (

        <div className="sidebar">

            <h2>Rapid Agent</h2>

            <nav>

                <Link to="/">Dashboard</Link>

                <Link to="/profile">Profile</Link>

                <Link to="/opportunities">Opportunities</Link>

                <Link to="/roadmap">Roadmap</Link>

                <Link to="/chat">Advisor</Link>

            </nav>

        </div>

    );

}