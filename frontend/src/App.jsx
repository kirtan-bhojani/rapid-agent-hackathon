// src/App.jsx

import { BrowserRouter, Routes, Route } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import Documents from "./pages/Documents";
import Opportunities from "./pages/Opportunities";
import Roadmap from "./pages/Roadmap";
import Chat from "./pages/Chat";
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

        <Route path="/chat" element={<Chat />} />

        <Route path="/login" element={<Login />} />

        <Route path="/register" element={<Register />} />

      </Routes>

    </BrowserRouter>

  );

}

export default App;
