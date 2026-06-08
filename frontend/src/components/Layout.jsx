import Sidebar from "./Sidebar";
import "./Layout.css";
export default function Layout({ children }) {

    return (

        <div className="app-layout">

            <Sidebar />

            <main className="content">

                {children}

            </main>

        </div>

    );

}