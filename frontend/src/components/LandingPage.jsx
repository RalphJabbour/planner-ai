import React from "react";
import { useNavigate } from "react-router-dom";
import "./LandingPage.css";

function LandingPage() {
  const navigate = useNavigate();

  return (
    <div
      className="landing-page"
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
        width: "100%",
      }}
    >
      <nav className="navbar">
        <div className="logo">
          {/* <img src="/logo.png" alt="planner.ai logo" /> */}
          <span>planner.ai</span>
        </div>
        <div className="nav-links">
          <a href="#home">Home</a>
          <a href="#blog">Blog</a>
          <a href="#team">Team</a>
          <a href="#info">Info</a>
          <a href="/login">Login/Signup</a>
        </div>
      </nav>

      <main
        className="hero-section"
        style={{
          display: "flex",
          width: "100%",
          justifyContent: "space-between",
        }}
      >
        <div
          className="hero-content"
          style={{
            flex: "1",
            padding: "2rem",
          }}
        >
          <h1>planner.ai</h1>
          <p className="tagline">
            Unlock the productivity you always hoped for as a student.
          </p>

          <div className="features">
            <div>Smart schedule optimization based on your study habits</div>
            <div>Automatic deadline tracking and reminders</div>
            <div>AI-powered suggestions for time management</div>
            <div>Seamless integration with your academic calendar</div>
          </div>

          <button
            onClick={() => navigate("/signup")}
            className="get-started-btn"
          >
            Get Started
          </button>
        </div>

        <div
          className="hero-image"
          style={{
            flex: "1",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <img
            src="src\assets\LandingPageImage.png"
            alt="Student planning"
            style={{
              maxWidth: "100%",
              height: "auto",
            }}
          />
        </div>
      </main>
    </div>
  );
}

export default LandingPage;
