import { BrowserRouter, Routes, Route } from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import Profile from "./pages/Profile";
import Opportunities from "./pages/Opportunities";
import Roadmap from "./pages/Roadmap";
import Chat from "./pages/Chat";

function App() {

  return (

    <BrowserRouter>

      <Routes>

        <Route path="/" element={<Dashboard />} />

        <Route path="/profile" element={<Profile />} />

        <Route path="/opportunities" element={<Opportunities />} />

        <Route path="/roadmap" element={<Roadmap />} />

        <Route path="/chat" element={<Chat />} />

      </Routes>

    </BrowserRouter>

  );

}

export default App;