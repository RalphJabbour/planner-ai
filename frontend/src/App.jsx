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
import FixedObligationForm from "./components/Obligations/FixedObligationForm";
import FlexibleObligationForm from "./components/Obligations/FlexibleObligationForm";
import MaterialsQuizPage from "./components/MaterialsQuiz/MaterialsQuizPage";
import StudyTimeEstimator from "./components/MaterialsQuiz/StudyTimeEstimator";
// import Schedule from "./components/Schedule/Schedule";
import WeeklyCalendar from "./components/WeeklyCalendar/WeeklyCalendar";
import Home from "./components/Home/Home";

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
          path="/home"
          element={
            // <ProtectedRoute>
              <Home />
            // </ProtectedRoute>
          }
        />
        <Route
          path="/materials-quiz"
          element={
            <ProtectedRoute>
              <MaterialsQuizPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/study-time-estimator"
          element={
            <ProtectedRoute>
              <StudyTimeEstimator />
            </ProtectedRoute>
          }
        />
        <Route
          path="/obligations/fixed/add"
          element={
            <ProtectedRoute>
              <FixedObligationForm />
            </ProtectedRoute>
          }
        />
        <Route
          path="/obligations/fixed/edit/:id"
          element={
            <ProtectedRoute>
              <FixedObligationForm />
            </ProtectedRoute>
          }
        />
        <Route
          path="/obligations/flexible/add"
          element={
            <ProtectedRoute>
              <FlexibleObligationForm />
            </ProtectedRoute>
          }
        />
        <Route
          path="/obligations/flexible/edit/:id"
          element={
            <ProtectedRoute>
              <FlexibleObligationForm />
            </ProtectedRoute>
          }
        />
        {/* Redirect any unknown routes to home if logged in, otherwise to landing page */}
        <Route
          path="*"
          element={
            localStorage.getItem("accessToken") ? (
              <Navigate to="/home" />
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