// src/components/Dashboard/Dashboard.jsx
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  
  // New state variables for course browser
  const [courses, setCourses] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [coursesLoading, setCoursesLoading] = useState(false);
  const [coursesError, setCoursesError] = useState(null);
  const [showCourseBrowser, setShowCourseBrowser] = useState(false);
  const [selectedSemester, setSelectedSemester] = useState("Summer 2024-2025");
  
  // Function to fetch courses from the API
  const fetchCourses = async (semester) => {
    try {
      setCoursesLoading(true);
      const token = localStorage.getItem("accessToken");
      
      // Fixed: Using query parameter instead of request body
      const response = await fetch(`/api/courses?semester=${encodeURIComponent(semester)}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        }
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error("API error response:", errorText);
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log("Fetched courses - data:", data);
      setCourses(data);
      setCoursesLoading(false);
    } catch (err) {
      console.error("Course fetch error:", err);
      setCoursesError(err.message);
      setCoursesLoading(false);
    }
  };
  
  // Effect to fetch courses when the sidebar is opened or semester changes
  useEffect(() => {
    if (showCourseBrowser) {
      fetchCourses(selectedSemester);
    }
  }, [showCourseBrowser, selectedSemester]);
  
  // Filter courses based on search term
  const filteredCourses = courses.filter(
    (course) =>
      course.course_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
      course.course_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (course.instructor && course.instructor.toLowerCase().includes(searchTerm.toLowerCase()))
  );
  
  // Pagination logic
  const coursesPerPage = 100;
  const indexOfLastCourse = currentPage * coursesPerPage;
  const indexOfFirstCourse = indexOfLastCourse - coursesPerPage;
  const currentCourses = filteredCourses.slice(indexOfFirstCourse, indexOfLastCourse);
  const totalPages = Math.ceil(filteredCourses.length / coursesPerPage);

  // Handle page change
  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
  };

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
    <div className="app-container">
      {/* Main dashboard content */}
      <div className={`dashboard-container ${showCourseBrowser ? 'with-sidebar' : ''}`}>
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
          <div className="header-actions">
            <div className="last-login">
              <p>Last login: {formatDate(dashboardData.last_login)}</p>
            </div>
            <button 
              className="browse-courses-btn"
              onClick={() => setShowCourseBrowser(!showCourseBrowser)}
            >
              {showCourseBrowser ? "Hide Courses" : "Browse Courses"}
            </button>
          </div>
        </header>

        <div className="dashboard-grid">
          {/* Your existing dashboard sections */}
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
      
      {/* Course browser sidebar as a sibling to dashboard container */}
      {showCourseBrowser && (
        <div className="course-browser-sidebar">
          <div className="course-browser-header">
            <h2>Course Browser</h2>
            <button 
              className="close-sidebar" 
              onClick={() => setShowCourseBrowser(false)}
            >
              &times;
            </button>
          </div>
          
          <div className="course-browser-controls">
            <div className="search-container">
              <input
                type="text"
                placeholder="Search courses..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setCurrentPage(1); // Reset to first page on search
                }}
                className="search-input"
              />
            </div>
            <div className="semester-selector">
              <select 
                value={selectedSemester}
                onChange={(e) => {
                  setSelectedSemester(e.target.value);
                  setCurrentPage(1); // Reset to first page on semester change
                }}
              >
                <option value="Summer 2024-2025">Summer 2024-2025</option>
                <option value="Fall 2024-2025">Fall 2024-2025</option>
                <option value="Spring 2024-2025">Spring 2024-2025</option>
              </select>
            </div>
          </div>
          
          {coursesLoading ? (
            <div className="courses-loading">
              <div className="spinner"></div>
              <p>Loading courses...</p>
            </div>
          ) : coursesError ? (
            <div className="courses-error">
              <p>Error loading courses: {coursesError}</p>
              <button onClick={() => fetchCourses(selectedSemester)}>
                Retry
              </button>
            </div>
          ) : (
            <>
              <div className="courses-count">
                Showing {currentCourses.length} of {filteredCourses.length} courses
              </div>
              
              <div className="course-list">
                {currentCourses.length === 0 ? (
                  <div className="no-courses">
                    <p>No courses match your search criteria.</p>
                  </div>
                ) : (
                  currentCourses.map((course) => (
                    <div className="course-list-item" key={course.course_id}>
                      <div className="course-list-header">
                        <span className="course-list-code">{course.course_code}</span>
                        <span className="course-list-section">Section {course.course_section}</span>
                      </div>
                      <h3 className="course-list-name">{course.course_name}</h3>
                      <div className="course-list-details">
                        <p className="course-list-instructor">
                          <strong>Instructor:</strong> {course.instructor || "TBA"}
                        </p>
                        <p className="course-list-enrollment">
                          <strong>Enrollment:</strong> {course.actual_enrollment}/{course.max_enrollment}
                        </p>
                        <p className="course-list-credits">
                          <strong>Credits:</strong> {course.course_credits}
                        </p>
                      </div>
                      <div className="course-list-actions">
                        <button className="view-details-btn">View Details</button>
                      </div>
                    </div>
                  ))
                )}
              </div>
              
              {totalPages > 1 && (
                <div className="pagination">
                  <button 
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="pagination-btn"
                  >
                    &lt; Prev
                  </button>
                  <span className="pagination-info">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button 
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="pagination-btn"
                  >
                    Next &gt;
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default Dashboard;
