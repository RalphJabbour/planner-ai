import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./AuthPages.css";

function SignupPage() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    // // Basic validation
    // if (formData.password !== formData.confirmPassword) {
    //   setError("Passwords don't match");
    //   return;
    // }

    // if (formData.password.length < 8) {
    //   setError("Password must be at least 8 characters");
    //   return;
    // }

    try {
      // Simulate API call
      console.log("Signing up with:", formData);
      // Navigate to survey page instead of dashboard
      navigate("/survey");
    } catch (err) {
      setError("Failed to create account. Please try again.");
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
          <Link to="/login" className="auth-link active">
            Login/Signup
          </Link>
        </div>
      </nav>

      <div className="auth-content">
        <div className="auth-card">
          <h1>Create Account</h1>
          <p className="tagline auth-subtitle">
            Join planner.ai to boost your productivity
          </p>

          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="form-group">
              <label htmlFor="name">Full Name</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="John Doe"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="your@email.com"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="••••••••"
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm Password</label>
              <input
                type="password"
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="••••••••"
                required
              />
            </div>

            <button type="submit" className="get-started-btn auth-button">
              Create Account
            </button>
          </form>

          <div className="auth-redirect">
            Already have an account? <Link to="/login">Log in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SignupPage;
