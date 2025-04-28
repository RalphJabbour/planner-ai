import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import WeeklyCalendar from '../WeeklyCalendar/WeeklyCalendar';
import InfoSidebar from '../InfoSidebar/InfoSidebar';
import Modal from '../Modal/Modal';
// Import icons
import { FiLogOut, FiSettings, FiUser, FiGrid, FiUploadCloud, FiMenu } from 'react-icons/fi'; // Add FiMenu
import styles from './Home.module.css';

// --- Navbar Component Updated ---
const Navbar = ({ handleLogout, toggleInfoSidebar }) => { // Add toggleInfoSidebar prop
  const navigate = useNavigate();

  const handleExport = () => {
    alert("Export to Google Calendar (Not Implemented Yet)");
  };

  return (
    <nav className={styles.navbar}>
      <div className={styles.navbarLeft}>
        {/* Sidebar Toggle Button */}
        <button
          onClick={toggleInfoSidebar}
          className={`${styles.navButton} ${styles.sidebarToggleButton}`}
          title="Toggle Sidebar"
        >
          <FiMenu className={styles.navIcon} />
        </button>
        <Link to="/" className={styles.navbarBrand}>
          Planner AI
        </Link>
        {/* Removed Dashboard link from here as it might be redundant with sidebar/home */}
        {/* <Link to="/dashboard" className={styles.navLink}>
          <FiGrid className={styles.navIcon} /> Dashboard
        </Link> */}
      </div>
      <div className={styles.navbarRight}>
        <button onClick={handleExport} className={`${styles.navButton} ${styles.exportButton}`} title="Export to Google Calendar">
          <FiUploadCloud className={styles.navIcon} /> Export
        </button>
        <button onClick={() => navigate('/profile')} className={styles.navButton} title="Account Settings">
          <FiUser className={styles.navIcon} /> Account
        </button>
        <button onClick={() => navigate('/settings')} className={styles.navButton} title="Settings">
          <FiSettings className={styles.navIcon} /> Settings
        </button>
        <button onClick={handleLogout} className={`${styles.navButton} ${styles.logoutButton}`} title="Logout">
          <FiLogOut className={styles.navIcon} /> Logout
        </button>
      </div>
    </nav>
  );
};
// --- End Navbar Update ---

const ChatInterface = () => {
  // Basic chat structure - replace with your actual implementation
  const [messages, setMessages] = useState([{ text: "Hello! How can I help?", sender: "ai" }]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMessage = { text: input, sender: "user" };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // Simulate AI response
    await new Promise(resolve => setTimeout(resolve, 1000));
    const aiResponse = { text: `You said: ${userMessage.text}`, sender: "ai" };
    setMessages(prev => [...prev, aiResponse]);
    setIsLoading(false);
  };

  return (
    <div className={styles.chatContainer}>
      <div className={styles.chatMessages}>
        {messages.map((msg, index) => (
          <div key={index} className={`${styles.chatMessage} ${styles[msg.sender]}`}>
            {msg.text}
          </div>
        ))}
        {isLoading && <div className={styles.chatMessage}>Thinking...</div>}
      </div>
      <div className={styles.chatInputArea}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the AI..."
          disabled={isLoading}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
        />
        <button onClick={handleSend} disabled={isLoading}>
          Send
        </button>
      </div>
    </div>
  );
};
const IconSidebar = ({ onIconClick }) => (
  <aside className={styles.iconSidebar}>
    <div className={styles.iconSidebarContent}>
      {/* Add more icons here as needed */}
      <div
        className={styles.sidebarItem}
        title="Register Courses" // Tooltip on hover
        onClick={() => onIconClick('courses')} // Trigger opening the course browser
      >
        <span className={styles.sidebarIcon}>📚</span> {/* Example Icon */}
      </div>
      {/* Add other icons like chat, tasks etc. */}
       <div
        className={styles.sidebarItem}
        title="AI Chat"
        onClick={() => onIconClick('chat')}
      >
        <span className={styles.sidebarIcon}>💬</span> {/* Example Icon */}
      </div>
    </div>
  </aside>
);
const SecondarySidebar = ({ activePanel, onClose, children }) => {
  if (!activePanel) return null;

  return (
    <aside className={styles.secondarySidebar}>
      <button onClick={onClose} className={styles.closeSecondarySidebarButton}>
        &times; {/* Close button */}
      </button>
      <div className={styles.secondarySidebarContent}>
        {children}
      </div>
    </aside>
  );
};
const CourseBrowser = ({ registeredCourses, fetchUserData }) => {
  const [courses, setCourses] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [coursesLoading, setCoursesLoading] = useState(false);
  const [coursesError, setCoursesError] = useState(null);
  const [selectedSemester, setSelectedSemester] = useState("Summer 2024-2025"); // Default or load from user prefs
  const [registrationInProgress, setRegistrationInProgress] = useState({});
  const navigate = useNavigate(); // Needed for error handling potentially

  // Function to fetch courses from the API
  const fetchCourses = async (semester) => {
    try {
      setCoursesLoading(true);
      setCoursesError(null); // Clear previous errors
      const token = localStorage.getItem("accessToken");
      if (!token) {
        navigate("/login"); // Redirect if no token
        return;
      }

      const response = await fetch(`/api/courses?semester=${encodeURIComponent(semester)}`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
        }
      });

      if (!response.ok) {
        throw new Error(`Error ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setCourses(data);
    } catch (err) {
      console.error("Course fetch error:", err);
      setCoursesError(err.message);
    } finally {
      setCoursesLoading(false);
    }
  };

  // Effect to fetch courses when semester changes
  useEffect(() => {
    fetchCourses(selectedSemester);
  }, [selectedSemester]);

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
      await fetchUserData();
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
      await fetchUserData();
      alert("Course unregistered successfully!");
    } catch (err) {
      console.error("Unregistration error:", err);
      alert(`Failed to unregister: ${err.message}`);
    } finally {
      setRegistrationInProgress(prev => ({ ...prev, [courseId]: false }));
    }
  };

  // Check if a course is already registered
  const isRegistered = (courseId) => {
    // Ensure registeredCourses is an array before calling .some()
    return Array.isArray(registeredCourses) && registeredCourses.some(course => course.course_id === courseId);
  };


  // Filter courses based on search term
  const filteredCourses = courses.filter(
    (course) =>
      course.course_code?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      course.course_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (course.instructor && course.instructor.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Pagination logic (adjust as needed)
  const coursesPerPage = 50;
  const indexOfLastCourse = currentPage * coursesPerPage;
  const indexOfFirstCourse = indexOfLastCourse - coursesPerPage;
  const currentCourses = filteredCourses.slice(indexOfFirstCourse, indexOfLastCourse);
  const totalPages = Math.ceil(filteredCourses.length / coursesPerPage);

  // Handle page change
  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
  };

  return (
    // Use a container class specific to this component if needed, or rely on secondarySidebarContent
    <>
      {/* Header - Close button is handled by SecondarySidebar */}
      <div className={styles.courseBrowserHeader}>
        <h2>Course Browser</h2>
      </div>

      {/* Controls */}
      <div className={styles.courseBrowserControls}>
        <div className={styles.searchContainer}> {/* Use styles object */}
          <input
            type="text"
            placeholder="Search courses..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1); // Reset to first page on search
            }}
            className={styles.searchInput} // Use styles object
          />
        </div>
        <div className={styles.semesterSelectorContainer}> {/* Use styles object */}
          <select
            value={selectedSemester}
            onChange={(e) => {
              setSelectedSemester(e.target.value);
              setCurrentPage(1); // Reset to first page on semester change
            }}
            className={styles.semesterSelector} // Use styles object
          >
            <option value="Summer 2024-2025">Summer 2024-2025</option>
            <option value="Fall 2024-2025">Fall 2024-2025</option>
            <option value="Spring 2024-2025">Spring 2024-2025</option>
          </select>
        </div>
      </div>

      {/* Loading/Error/Content */}
      {coursesLoading ? (
        <div className={styles.coursesLoading}> {/* Use styles object */}
          <div className={styles.spinner}></div> {/* Use styles object */}
          <p>Loading courses...</p>
        </div>
      ) : coursesError ? (
        <div className={styles.coursesError}> {/* Use styles object */}
          <p>Error loading courses: {coursesError}</p>
          <button onClick={() => fetchCourses(selectedSemester)}>
            Retry
          </button>
        </div>
      ) : (
        <>
          <div className={styles.coursesCount}> {/* Use styles object */}
            Showing {currentCourses.length} of {filteredCourses.length} courses
          </div>

          <div className={styles.courseList}> {/* Use styles object */}
            {currentCourses.length === 0 ? (
              <div className={styles.noCourses}> {/* Use styles object */}
                <p>No courses match your search criteria.</p>
              </div>
            ) : (
              currentCourses.map((course) => {
                const alreadyRegistered = isRegistered(course.course_id);
                return (
                  <div className={styles.courseListItem} key={course.course_id}> {/* Use styles object */}
                    <div className={styles.courseListHeader}> {/* Use styles object */}
                      <span className={styles.courseListCode}>{course.course_code}</span> {/* Use styles object */}
                      <span className={styles.courseListSection}>Section {course.course_section}</span> {/* Use styles object */}
                    </div>
                    <h3 className={styles.courseListName}>{course.course_name}</h3> {/* Use styles object */}
                    <div className={styles.courseListDetails}> {/* Use styles object */}
                      <p className={styles.courseListInstructor}> {/* Use styles object */}
                        <strong>Instructor:</strong> {course.instructor || "TBA"}
                      </p>
                      <p className={styles.courseListEnrollment}> {/* Use styles object */}
                        <strong>Enrollment:</strong> {course.actual_enrollment}/{course.max_enrollment}
                      </p>
                      <p className={styles.courseListCredits}> {/* Use styles object */}
                        <strong>Credits:</strong> {course.course_credits}
                      </p>
                    </div>
                    <div className={styles.courseListActions}> {/* Use styles object */}
                      {alreadyRegistered ? (
                        <button
                          className={styles.unregisterCourseBtn} // Use styles object
                          onClick={() => handleCourseUnregistration(course.course_id)}
                          disabled={registrationInProgress[course.course_id]}
                        >
                          {registrationInProgress[course.course_id] ? "Processing..." : "Unregister"}
                        </button>
                      ) : (
                        <button
                          className={styles.registerCourseBtn} // Use styles object
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

          {/* Pagination */}
          {totalPages > 1 && (
            <div className={styles.pagination}> {/* Use styles object */}
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className={styles.paginationBtn} // Use styles object
              >
                &lt; Prev
              </button>
              <span className={styles.paginationInfo}> {/* Use styles object */}
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className={styles.paginationBtn} // Use styles object
              >
                Next &gt;
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
};


const Home = () => {
  const [isInfoSidebarExpanded, setIsInfoSidebarExpanded] = useState(true);
  const [activeSecondarySidebar, setActiveSecondarySidebar] = useState(null);
  const [registeredCourses, setRegisteredCourses] = useState([]);
  const [fixedObligations, setFixedObligations] = useState([]);
  const [flexibleObligations, setFlexibleObligations] = useState([]);
  const [academicTasks, setAcademicTasks] = useState([]);
  const [calendarDate, setCalendarDate] = useState(new Date());
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState(null);
  const [modalTitle, setModalTitle] = useState('');
  const [registrationInProgress, setRegistrationInProgress] = useState({}); // Add state for registration status
  const navigate = useNavigate();

  // --- Fetch Data (fetchHomeData remains the same) ---
  const fetchHomeData = async () => {
    try {
      const token = localStorage.getItem("accessToken");
      if (!token) {
        navigate("/login"); // Redirect if not logged in
        return;
      }

      const headers = { Authorization: `Bearer ${token}` };

      // Fetch all data concurrently
      const [coursesRes, fixedRes, flexibleRes, tasksRes] = await Promise.all([
        fetch("/api/courses/registered", { headers }),
        fetch("/api/tasks/fixed", { headers }),
        fetch("/api/tasks/flexible", { headers }),
        fetch("/api/tasks/academic-tasks", { headers }) // Assuming this endpoint exists
      ]);

      // Process responses
      if (coursesRes.ok) {
        const coursesData = await coursesRes.json();
        setRegisteredCourses(coursesData.courses || coursesData || []);
      } else {
        console.error(`Error fetching registered courses: ${coursesRes.status}`);
        setRegisteredCourses([]);
      }

      if (fixedRes.ok) {
        const fixedData = await fixedRes.json();
        setFixedObligations(fixedData || []);
      } else {
        console.error(`Error fetching fixed obligations: ${fixedRes.status}`);
        setFixedObligations([]);
      }

      if (flexibleRes.ok) {
        const flexibleData = await flexibleRes.json();
        setFlexibleObligations(flexibleData || []);
      } else {
        console.error(`Error fetching flexible obligations: ${flexibleRes.status}`);
        setFlexibleObligations([]);
      }

      if (tasksRes.ok) {
        const tasksData = await tasksRes.json();
        setAcademicTasks(tasksData || []);
      } else {
        console.error(`Error fetching academic tasks: ${tasksRes.status}`);
        setAcademicTasks([]);
      }

    } catch (err) {
      console.error("Error fetching home data:", err);
      // Handle error appropriately, maybe show a notification
      // Reset states on error
      setRegisteredCourses([]);
      setFixedObligations([]);
      setFlexibleObligations([]);
      setAcademicTasks([]);
    }
  };

  useEffect(() => {
    fetchHomeData();
  }, [navigate]);

  // --- Course Unregistration Handler ---
  const handleCourseUnregistration = async (courseId) => {
    // Confirmation dialog
    if (!window.confirm("Are you sure you want to unregister from this course?")) {
      return;
    }
    try {
      setRegistrationInProgress(prev => ({ ...prev, [courseId]: true }));
      const token = localStorage.getItem("accessToken");
      const response = await fetch(`/api/courses/unregister?course_id=${courseId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error ${response.status}: ${response.statusText}`);
      }
      await fetchHomeData(); // Refresh all data including registered courses
      alert("Course unregistered successfully!");
    } catch (err) {
      console.error("Unregistration error:", err);
      alert(`Failed to unregister: ${err.message}`);
    } finally {
      setRegistrationInProgress(prev => ({ ...prev, [courseId]: false }));
    }
  };

  // --- Logout Handler ---
  const handleLogout = () => {
    localStorage.removeItem("accessToken");
    navigate("/login");
    // Optionally: Clear other user-related state
  };

  // --- Sidebar Toggles ---
  const toggleInfoSidebar = () => {
    setIsInfoSidebarExpanded(!isInfoSidebarExpanded);
  };

  const handleIconClick = (panelName) => {
    setActiveSecondarySidebar(prev => prev === panelName ? null : panelName);
  };

  const closeSecondarySidebar = () => {
    setActiveSecondarySidebar(null);
  };

  // --- Calendar Date Change ---
  const handleInfoCalendarDateChange = (newDate) => {
    setCalendarDate(newDate);
  };

  // --- Modal Handling (Simplified - only for non-course/obligation items now) ---
  const openModal = (title, content) => {
    setModalTitle(title);
    setModalContent(content);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setModalContent(null);
    setModalTitle('');
  };

  // Handle clicks on items in InfoSidebar (e.g., Academic Tasks)
  const handleItemClick = (itemType, itemData) => {
    let title = '';
    let content = null;

    switch (itemType) {
      case 'academic': // Example for academic tasks if you want modals for them
        title = `Task: ${itemData.title}`;
        content = (
          <div>
            <p className={styles.detailItem}>
              <span className={styles.detailLabel}>Course:</span>
              <span className={styles.detailValue}>{itemData.course_code || 'N/A'}</span>
            </p>
            <p className={styles.detailItem}>
              <span className={styles.detailLabel}>Type:</span>
              <span className={styles.detailValue}>{itemData.type}</span>
            </p>
            <p className={styles.detailItem}>
              <span className={styles.detailLabel}>Deadline:</span>
              <span className={styles.detailValue}>{new Date(itemData.deadline).toLocaleString()}</span>
            </p>
            <p className={styles.detailItem}>
              <span className={styles.detailLabel}>Status:</span>
              <span className={styles.detailValue}>{itemData.status}</span>
            </p>
            {/* Add more details */}
          </div>
        );
        break;
      // Removed 'course', 'fixed', 'flexible' cases as they now use navigation/direct actions
      default:
        console.warn("Modal not configured for item type:", itemType);
        return;
    }
    openModal(title, content);
  };


  return (
    <div className={styles.homeLayout}>
      {/* Pass toggleInfoSidebar to Navbar */}
      <Navbar handleLogout={handleLogout} toggleInfoSidebar={toggleInfoSidebar} />
      <div className={styles.mainContainer}>
        {/* Info Sidebar (Left, Toggable) */}
        <InfoSidebar
          isExpanded={isInfoSidebarExpanded}
          // toggleSidebar={toggleInfoSidebar} // Remove this prop
          registeredCourses={registeredCourses}
          academicTasks={academicTasks}
          fixedObligations={fixedObligations}
          flexibleObligations={flexibleObligations}
          onDateChange={handleInfoCalendarDateChange}
          onItemClick={handleItemClick}
          handleCourseUnregistration={handleCourseUnregistration} // Pass handler
          registrationInProgress={registrationInProgress} // Pass status
          setActiveSecondarySidebar={setActiveSecondarySidebar} // Pass function to open secondary sidebar
        />

        {/* Main content area */}
        <div className={`${styles.contentArea} ${!isInfoSidebarExpanded ? styles.contentAreaFullWidth : ''} ${activeSecondarySidebar ? styles.contentAreaShiftedForSecondary : ''}`}>
           <div className={styles.calendarWrapper}>
             <WeeklyCalendar currentDate={calendarDate} />
           </div>
         </div>

        {/* Secondary Sidebar (Course Browser, Chat - Right) */}
        <SecondarySidebar activePanel={activeSecondarySidebar} onClose={closeSecondarySidebar}>
          {activeSecondarySidebar === 'courses' && (
            <CourseBrowser
              registeredCourses={registeredCourses}
              fetchUserData={fetchHomeData} // Pass fetchHomeData to refresh all data
            />
          )}
          {activeSecondarySidebar === 'chat' && <ChatInterface />}
        </SecondarySidebar>

        {/* Icon Sidebar (Right) */}
        <IconSidebar onIconClick={handleIconClick} />

        {/* Modal for Item Details (e.g., Academic Tasks) */}
        <Modal isOpen={isModalOpen} onClose={closeModal} title={modalTitle}>
          {modalContent}
        </Modal>
      </div>
    </div>
  );
};

export default Home;