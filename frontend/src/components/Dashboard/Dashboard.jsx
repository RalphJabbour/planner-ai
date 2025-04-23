// src/components/Dashboard/Dashboard.jsx
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";

const Dashboard = () => {
  const [studentData, setStudentData] = useState(null);
  const [registeredCourses, setRegisteredCourses] = useState([]);
  const [fixedObligations, setFixedObligations] = useState([]);
  const [flexibleObligations, setFlexibleObligations] = useState([]);
  const [upcomingTasks, setUpcomingTasks] = useState([]);
  const [upcomingEvents, setUpcomingEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  
  // Course browser state
  const [courses, setCourses] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [coursesLoading, setCoursesLoading] = useState(false);
  const [coursesError, setCoursesError] = useState(null);
  const [showCourseBrowser, setShowCourseBrowser] = useState(false);
  const [selectedSemester, setSelectedSemester] = useState("Summer 2024-2025");
  const [registrationInProgress, setRegistrationInProgress] = useState({});
  
  // Function to fetch courses from the API
  const fetchCourses = async (semester) => {
    try {
      setCoursesLoading(true);
      const token = localStorage.getItem("accessToken");
      
      // Change this to a GET request with query param
      const response = await fetch(`/api/courses?semester=${encodeURIComponent(semester)}`, {
        method: "GET", // Changed from POST to GET
        headers: {
          Authorization: `Bearer ${token}`,
        }
      });
      
      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setCourses(data);
      setCoursesLoading(false);
    } catch (err) {
      console.error("Course fetch error:", err);
      setCoursesError(err.message);
      setCoursesLoading(false);
    }
  };
  
  // Fetch user data
  const fetchUserData = async () => {
    try {
      const token = localStorage.getItem("accessToken");
      
      if (!token) {
        navigate("/login");
        return;
      }
      
      // Fetch student information
      const studentResponse = await fetch("/api/users/me", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (studentResponse.status === 401) {
        localStorage.removeItem("accessToken");
        navigate("/login");
        return;
      }
      
      if (!studentResponse.ok) {
        throw new Error(`Error ${studentResponse.status}: ${studentResponse.statusText}`);
      }
      
      const studentData = await studentResponse.json();
      setStudentData(studentData);
      
      // Fetch registered courses
      const coursesResponse = await fetch("/api/courses/registered", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (!coursesResponse.ok) {
        throw new Error(`Error ${coursesResponse.status}: ${coursesResponse.statusText}`);
      }
      
      const coursesData = await coursesResponse.json();
      setRegisteredCourses(coursesData.courses || []);
      
      // Fetch fixed obligations
      const fixedObligationsResponse = await fetch("/api/tasks/fixed", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (!fixedObligationsResponse.ok) {
        throw new Error(`Error ${fixedObligationsResponse.status}: ${fixedObligationsResponse.statusText}`);
      }
      
      const fixedObligationsData = await fixedObligationsResponse.json();
      setFixedObligations(fixedObligationsData || []);
      
      // Fetch flexible obligations
      const flexibleObligationsResponse = await fetch("/api/tasks/flexible", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (!flexibleObligationsResponse.ok) {
        throw new Error(`Error ${flexibleObligationsResponse.status}: ${flexibleObligationsResponse.statusText}`);
      }
      
      const flexibleObligationsData = await flexibleObligationsResponse.json();
      setFlexibleObligations(flexibleObligationsData || []);
      
      // Fetch upcoming academic tasks
      const tasksResponse = await fetch("/api/tasks/academic-tasks", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (!tasksResponse.ok) {
        throw new Error(`Error ${tasksResponse.status}: ${tasksResponse.statusText}`);
      }
      
      const tasksData = await tasksResponse.json();
      setUpcomingTasks(tasksData || []);
      
      // For now, we'll just use an empty array for events since we don't have that endpoint yet
      setUpcomingEvents([]);
      
      setLoading(false);
    } catch (err) {
      console.error("Error fetching user data:", err);
      setError(err.message);
      setLoading(false);
    }
  };
  
  // Effect to fetch courses when the sidebar is opened or semester changes
  useEffect(() => {
    if (showCourseBrowser) {
      fetchCourses(selectedSemester);
    }
  }, [showCourseBrowser, selectedSemester]);
  
  // Effect to fetch user data on component mount
  useEffect(() => {
    fetchUserData();
  }, [navigate]);
  
  // Register for course
  const handleCourseRegistration = async (courseId) => {
    try {
      setRegistrationInProgress(prev => ({ ...prev, [courseId]: true }));
      
      const token = localStorage.getItem("accessToken");
      const response = await fetch("/api/courses/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ course_id: courseId }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error ${response.status}: ${response.statusText}`);
      }
      
      // Refresh registered courses
      await fetchUserData();
      
      // Show success message
      alert("Course registered successfully!");
    } catch (err) {
      console.error("Registration error:", err);
      alert(`Failed to register: ${err.message}`);
    } finally {
      setRegistrationInProgress(prev => ({ ...prev, [courseId]: false }));
    }
  };
  
  // Unregister from course
  const handleCourseUnregistration = async (courseId) => {
    try {
      setRegistrationInProgress(prev => ({ ...prev, [courseId]: true }));
      
      const token = localStorage.getItem("accessToken");
      const response = await fetch(`/api/courses/unregister?course_id=${courseId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error ${response.status}: ${response.statusText}`);
      }
      
      // Refresh registered courses
      await fetchUserData();
      
      // Show success message
      alert("Course unregistered successfully!");
    } catch (err) {
      console.error("Unregistration error:", err);
      alert(`Failed to unregister: ${err.message}`);
    } finally {
      setRegistrationInProgress(prev => ({ ...prev, [courseId]: false }));
    }
  };
  
  // Filter courses based on search term
  const filteredCourses = courses.filter(
    (course) =>
      course.course_code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      course.course_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
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

  const formatDate = (dateString) => {
    if (!dateString) return "";
    
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

  // Check if a course is already registered by the student
  const isRegistered = (courseId) => {
    return registeredCourses.some(course => course.course_id === courseId);
  };

  return (
    <div className="app-container">
      {/* Main dashboard content */}
      <div className={`dashboard-container ${showCourseBrowser ? 'with-sidebar' : ''}`}>
        <header className="dashboard-header">
          <div className="student-info">
            <h1>Welcome, {studentData?.name || "Student"}</h1>
            <p className="student-details">
              <span>{studentData?.program}</span>
              {studentData?.year && (
                <span> • Year {studentData.year}</span>
              )}
            </p>
          </div>
          <div className="header-actions">
            <button 
              className="view-schedule-btn"
              onClick={() => navigate("/schedule")}
            >
              View Schedule
            </button>
            <button 
              className="browse-courses-btn"
              onClick={() => setShowCourseBrowser(!showCourseBrowser)}
            >
              {showCourseBrowser ? "Hide Courses" : "Browse Courses"}
            </button>
          </div>
        </header>

        <div className="dashboard-grid">
          {/* My Courses Section */}
          <section className="dashboard-card courses-section">
            <h2>My Courses</h2>
            {registeredCourses.length === 0 ? (
              <div className="empty-state">
                <p>You haven't registered for any courses yet.</p>
                <button onClick={() => setShowCourseBrowser(true)}>
                  Browse Courses
                </button>
              </div>
            ) : (
              <div className="courses-grid">
                {registeredCourses.map((course) => (
                  <div className="course-card" key={course.course_id}>
                    <div className="course-code">{course.course_code}</div>
                    <h3>{course.course_name}</h3>
                    <p className="instructor">
                      Instructor: {course.instructor || "TBD"}
                    </p>
                    <p className="semester">{course.semester}</p>
                    <button 
                      className="unregister-btn"
                      onClick={() => handleCourseUnregistration(course.course_id)}
                      disabled={registrationInProgress[course.course_id]}
                    >
                      {registrationInProgress[course.course_id] ? "Unregistering..." : "Unregister"}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Fixed Obligations Section */}
          <section className="dashboard-card fixed-obligations-section">
            <div className="section-header">
              <h2>Fixed Obligations</h2>
              <button 
                className="add-btn"
                onClick={() => navigate("/obligations/fixed/add")}
              >
                + Add
              </button>
            </div>
            {fixedObligations.length === 0 ? (
              <div className="empty-state">
                <p>You don't have any fixed obligations yet.</p>
                <button onClick={() => navigate("/obligations/fixed/add")}>
                  Add Obligation
                </button>
              </div>
            ) : (
              <div className="obligations-list">
                {fixedObligations.map((obligation) => (
                  <div className="obligation-item" key={obligation.obligation_id}>
                    <div className="obligation-info">
                      <div className="obligation-title">{obligation.name}</div>
                      <div className="obligation-details">
                        <span>{obligation.day_of_week}</span>
                        <span>{`${obligation.start_time} - ${obligation.end_time}`}</span>
                      </div>
                    </div>
                    <div className="obligation-actions">
                      <button 
                        onClick={() => navigate(`/obligations/fixed/edit/${obligation.obligation_id}`)}
                        className="edit-btn"
                      >
                        Edit
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Flexible Obligations Section */}
          <section className="dashboard-card flexible-obligations-section">
            <div className="section-header">
              <h2>Flexible Obligations</h2>
              <button 
                className="add-btn"
                onClick={() => navigate("/obligations/flexible/add")}
              >
                + Add
              </button>
            </div>
            {flexibleObligations.length === 0 ? (
              <div className="empty-state">
                <p>You don't have any flexible obligations yet.</p>
                <button onClick={() => navigate("/obligations/flexible/add")}>
                  Add Obligation
                </button>
              </div>
            ) : (
              <div className="obligations-list">
                {flexibleObligations.map((obligation) => (
                  <div className="obligation-item" key={obligation.obligation_id}>
                    <div className="obligation-info">
                      <div className="obligation-title">{obligation.description}</div>
                      <div className="obligation-details">
                        <span>{obligation.weekly_target_hours} hours/week</span>
                      </div>
                    </div>
                    <div className="obligation-actions">
                      <button 
                        onClick={() => navigate(`/obligations/flexible/edit/${obligation.obligation_id}`)}
                        className="edit-btn"
                      >
                        Edit
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Upcoming Tasks Section */}
          <section className="dashboard-card tasks-section">
            <h2>Upcoming Tasks</h2>
            {upcomingTasks.length === 0 ? (
              <div className="empty-state">
                <p>No upcoming tasks for the next 7 days.</p>
              </div>
            ) : (
              <div className="tasks-list">
                {upcomingTasks.map((task) => (
                  <div className="task-item" key={task.task_id}>
                    <div className={`task-status ${task.status}`}>
                      {task.status === "completed" ? "✓" : ""}
                    </div>
                    <div className="task-info">
                      <div className="task-title">{task.title}</div>
                      <div className="task-details">
                        <span className="task-course">
                          {task.course_code || "Unknown course"}
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
                ))}
              </div>
            )}
          </section>

          {/* Profile Section */}
          <section className="dashboard-card profile-section">
            <h2>Profile Information</h2>
            <div className="profile-details">
              <div className="profile-item">
                <span className="profile-label">Name:</span>
                <span className="profile-value">
                  {studentData?.name}
                </span>
              </div>
              <div className="profile-item">
                <span className="profile-label">Email:</span>
                <span className="profile-value">
                  {studentData?.email}
                </span>
              </div>
              <div className="profile-item">
                <span className="profile-label">Program:</span>
                <span className="profile-value">
                  {studentData?.program || "Not set"}
                </span>
              </div>
              <div className="profile-item">
                <span className="profile-label">Year:</span>
                <span className="profile-value">
                  {studentData?.year || "Not set"}
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
      
      {/* Course browser sidebar */}
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
                  currentCourses.map((course) => {
                    const alreadyRegistered = isRegistered(course.course_id);
                    return (
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
                          {alreadyRegistered ? (
                            <button 
                              className="unregister-course-btn"
                              onClick={() => handleCourseUnregistration(course.course_id)}
                              disabled={registrationInProgress[course.course_id]}
                            >
                              {registrationInProgress[course.course_id] ? "Processing..." : "Unregister"}
                            </button>
                          ) : (
                            <button 
                              className="register-course-btn"
                              onClick={() => handleCourseRegistration(course.course_id)}
                              disabled={registrationInProgress[course.course_id]}
                            >
                              {registrationInProgress[course.course_id] ? "Processing..." : "Register"}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })
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