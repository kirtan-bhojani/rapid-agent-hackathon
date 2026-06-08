import "./Dashboard.css";
import Layout from "../components/Layout";
export default function Dashboard() {

    return (

      <Layout>

        <div className="dashboard">

            <div className="header">

                <h1>
                    Welcome, Kirtan 👋
                </h1>

                <p>
                    ML Engineer in Germany
                </p>

            </div>

            <div className="cards">

                <div className="card">

                    <h3>
                        Profile Completion
                    </h3>

                    <h2>
                        78%
                    </h2>

                </div>

                <div className="card">

                    <h3>
                        Roadmap Progress
                    </h3>

                    <h2>
                        42%
                    </h2>

                </div>

                <div className="card">

                    <h3>
                        Universities Tracked
                    </h3>

                    <h2>
                        12
                    </h2>

                </div>

            </div>

            <div className="deadline">

                <h2>
                    Upcoming Deadline
                </h2>

                <p>
                    SECAI AI Scholarship
                </p>

                <p>
                    June 30, 2026
                </p>

            </div>

        </div>

        </Layout>

    );

}