// src/App.jsx

import { BrowserRouter, Routes, Route } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import Documents from "./pages/Documents";
import Opportunities from "./pages/Opportunities";
import Roadmap from "./pages/Roadmap";
import Goal from "./pages/Goal";
import GapAnalysis from "./pages/GapAnalysis";
import ApplicationAssistant from "./pages/ApplicationAssistant";
import Login from "./pages/Login";
import Register from "./pages/Register";

function App() {

  return (

    <BrowserRouter>

      <Routes>

        <Route path="/" element={<Login />} />

        <Route path="/dashboard" element={<Dashboard />} />

        <Route path="/profile" element={<Profile />} />

        <Route path="/documents" element={<Documents />} />

        <Route path="/opportunities" element={<Opportunities />} />

        <Route path="/roadmap" element={<Roadmap />} />

        <Route path="/goal" element={<Goal />} />

        <Route path="/gap-analysis" element={<GapAnalysis />} />

        <Route path="/application-assistant" element={<ApplicationAssistant />} />

        <Route path="/login" element={<Login />} />

        <Route path="/register" element={<Register />} />

      </Routes>

    </BrowserRouter>

  );

}

export default App;
