// src/components/Dashboard/Dashboard.jsx
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDashboardData = async () => {
      const token = localStorage.getItem("accessToken");

      if (!token) {
        navigate("/login");
        return;
      }

      try {
        setLoading(true);
        const response = await fetch("/api/dashboard/", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.status === 401) {
          // Token expired or invalid
          localStorage.removeItem("accessToken");
          navigate("/login");
          return;
        }

        if (!response.ok) {
          throw new Error(`Error ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        setDashboardData(data);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, [navigate]);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Loading your dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error">
        <h2>Something went wrong</h2>
        <p>{error}</p>
        <button onClick={() => navigate("/login")}>Go back to login</button>
      </div>
    );
  }

  if (!dashboardData) return null;

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="student-info">
          <h1>Welcome, {dashboardData.student.name}</h1>
          <p className="student-details">
            <span>{dashboardData.student.program}</span>
            {dashboardData.student.year && (
              <span> • Year {dashboardData.student.year}</span>
            )}
          </p>
        </div>
        <div className="last-login">
          <p>Last login: {formatDate(dashboardData.last_login)}</p>
        </div>
      </header>

      <div className="dashboard-grid">
        <section className="dashboard-card courses-section">
          <h2>My Courses</h2>
          {dashboardData.courses.length === 0 ? (
            <div className="empty-state">
              <p>You haven't registered for any courses yet.</p>
              <button onClick={() => navigate("/courses")}>
                Browse Courses
              </button>
            </div>
          ) : (
            <div className="courses-grid">
              {dashboardData.courses.map((course) => (
                <div className="course-card" key={course.id}>
                  <div className="course-code">{course.code}</div>
                  <h3>{course.name}</h3>
                  <p className="instructor">
                    Instructor: {course.instructor || "TBD"}
                  </p>
                  <p className="semester">{course.semester}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="dashboard-card tasks-section">
          <h2>Upcoming Tasks</h2>
          {dashboardData.upcoming_tasks.length === 0 ? (
            <div className="empty-state">
              <p>No upcoming tasks for the next 7 days.</p>
            </div>
          ) : (
            <div className="tasks-list">
              {dashboardData.upcoming_tasks.map((task) => {
                const courseInfo = dashboardData.courses.find(
                  (c) => c.id === task.course_id
                );
                return (
                  <div className="task-item" key={task.id}>
                    <div className={`task-status ${task.status}`}>
                      {task.status === "completed" ? "✓" : ""}
                    </div>
                    <div className="task-info">
                      <div className="task-title">{task.title}</div>
                      <div className="task-details">
                        <span className="task-course">
                          {courseInfo?.code || "Unknown course"}
                        </span>
                        <span className="task-type">{task.type}</span>
                      </div>
                    </div>
                    <div className="task-deadline">
                      <div className="deadline-date">
                        {formatDate(task.deadline)}
                      </div>
                      <div className="deadline-label">Due</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <section className="dashboard-card calendar-section">
          <h2>Upcoming Events</h2>
          {dashboardData.upcoming_events.length === 0 ? (
            <div className="empty-state">
              <p>No upcoming events scheduled.</p>
              <button onClick={() => navigate("/schedule")}>
                Manage Schedule
              </button>
            </div>
          ) : (
            <div className="events-list">
              {dashboardData.upcoming_events.map((event) => (
                <div className="event-item" key={event.id}>
                  <div className={`event-type ${event.type}`}>
                    {event.type === "class" && "📚"}
                    {event.type === "study_session" && "📝"}
                    {event.type === "fixed_obligation" && "📅"}
                    {event.type === "flexible_obligation" && "⏱️"}
                  </div>
                  <div className="event-info">
                    <div className="event-title">
                      {event.type.replace("_", " ")}
                    </div>
                    <div className="event-time">
                      {formatDate(event.start_time)} -{" "}
                      {formatDate(event.end_time)}
                    </div>
                  </div>
                  <div className={`event-priority priority-${event.priority}`}>
                    {Array(event.priority).fill("•").join("")}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="dashboard-card profile-section">
          <h2>Profile Information</h2>
          <div className="profile-details">
            <div className="profile-item">
              <span className="profile-label">Name:</span>
              <span className="profile-value">
                {dashboardData.student.name}
              </span>
            </div>
            <div className="profile-item">
              <span className="profile-label">Email:</span>
              <span className="profile-value">
                {dashboardData.student.email}
              </span>
            </div>
            <div className="profile-item">
              <span className="profile-label">Program:</span>
              <span className="profile-value">
                {dashboardData.student.program || "Not set"}
              </span>
            </div>
            <div className="profile-item">
              <span className="profile-label">Year:</span>
              <span className="profile-value">
                {dashboardData.student.year || "Not set"}
              </span>
            </div>
          </div>
          <button
            className="edit-profile-btn"
            onClick={() => navigate("/profile")}
          >
            Edit Profile
          </button>
        </section>
      </div>
    </div>
  );
};

export default Dashboard;
