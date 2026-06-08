import { useEffect, useState } from "react";
import Layout from "../components/Layout";

export default function Profile() {

    const [profile, setProfile] = useState(null);

    useEffect(() => {

        fetch("http://127.0.0.1:8000/profile/omm_test")
            .then((res) => res.json())
            .then((data) => {
                setProfile(data.profile);
            });

    }, []);

    if (!profile) {

        return (

            <Layout>

                <h2>Loading Profile...</h2>

            </Layout>

        );

    }

    return (

        <Layout>

            <div>

                <h1>
                    {profile.personal.full_name}
                </h1>

                <p>
                    {profile.academic.institution}
                </p>

                <p>
                    CGPA: {profile.academic.gpa}
                </p>

                <hr />

                <h2>
                    Skills
                </h2>

                <ul>

                    {profile.professional.skills.map((skill, index) => (

                        <li key={index}>
                            {skill}
                        </li>

                    ))}

                </ul>

                <hr />

                <h2>
                    Experience
                </h2>

                {profile.professional.experience.map((exp, index) => (

                    <div key={index}>

                        <h3>
                            {exp.title}
                        </h3>

                        <p>
                            {exp.organization}
                        </p>

                    </div>

                ))}

            </div>

        </Layout>

    );

}