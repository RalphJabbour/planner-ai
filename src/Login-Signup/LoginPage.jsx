import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./AuthPages.css";

function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    // Add your login logic here
    // For now just navigating to home
    try {
      // Simulate API call
      console.log("Logging in with:", { email, password });
      navigate("/dashboard");
    } catch (err) {
      setError("Invalid credentials. Please try again.");
    }
  };

  return (
    <div className="auth-page">
      <nav className="navbar">
        <div className="logo">
          <span onClick={() => navigate("/")}>planner.ai</span>
        </div>
        <div className="nav-links">
          <a href="/">Home</a>
          <a href="/#blog">Blog</a>
          <a href="/#team">Team</a>
          <a href="/#info">Info</a>
          <Link to="/signup" className="auth-link active">
            Login/Signup
          </Link>
        </div>
      </nav>

      <div className="auth-content">
        <div className="auth-card">
          <h1>Welcome Back</h1>
          <p className="tagline auth-subtitle">Log in to access your planner</p>

          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your@email.com"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>

            <div className="forgot-password">
              <Link to="/forgot-password">Forgot your password?</Link>
            </div>

            <button type="submit" className="get-started-btn auth-button">
              Log In
            </button>
          </form>

          <div className="auth-redirect">
            Don't have an account? <Link to="/signup">Sign up</Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;
