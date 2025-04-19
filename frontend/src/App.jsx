import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import LandingPage from "./components/LandingPage";
import LoginPage from "./Login-Signup/LoginPage";
import SignupPage from "./Login-Signup/SignupPage";
import SurveyPage from "./components/Survey/SurveyPage";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/survey" element={<SurveyPage />} />
        {/* Add the schedule route when you create that component */}
        <Route path="/schedule" element={<div>Schedule Page (Coming Soon)</div>} />
      </Routes>
    </Router>
  );
}

export default App;
