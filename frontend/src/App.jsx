import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import LandingPage from "./components/LandingPage/LandingPage";
import LoginPage from "./components/Login-Signup/LoginPage";
import SignupPage from "./components/Login-Signup/SignupPage";
import SurveyPage from "./components/Survey/SurveyPage";
import Dashboard from "./components/Dashboard/Dashboard";

// Simple protected route implementation
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem("accessToken");

  if (!token) {
    return <Navigate to="/login" />;
  }

  return children;
};

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/survey" element={<SurveyPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/schedule"
          element={<div>Schedule Page (Coming Soon)</div>}
        />
        {/* Redirect any unknown routes to dashboard if logged in, otherwise to landing page */}
        <Route
          path="*"
          element={
            localStorage.getItem("accessToken") ? (
              <Navigate to="/dashboard" />
            ) : (
              <Navigate to="/" />
            )
          }
        />
      </Routes>
    </Router>
  );
}

export default App;
