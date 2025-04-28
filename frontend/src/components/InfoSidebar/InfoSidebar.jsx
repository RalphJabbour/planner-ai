import React, { useState } from 'react';
import Calendar from 'react-calendar';
import 'react-calendar/dist/Calendar.css';
import styles from './InfoSidebar.module.css'; // Use sidebar-specific styles
import { useNavigate } from 'react-router-dom'; // Import useNavigate

const formatDateSimple = (date) => {
  if (!date) return "";
  // Ensure date is a Date object
  const dateObj = date instanceof Date ? date : new Date(date);
  if (isNaN(dateObj.getTime())) return "Invalid Date"; // Check if date is valid
  return dateObj.toLocaleDateString("en-US", { month: 'short', day: 'numeric' });
};


const InfoSidebar = ({
  registeredCourses = [],
  academicTasks = [], // Keep academic tasks as is for now
  fixedObligations = [],
  flexibleObligations = [],
  onDateChange,
  isExpanded,
  toggleSidebar,
  onItemClick, // Keep for potential other uses (like academic tasks)
  handleCourseUnregistration, // <-- New prop for unregistering
  registrationInProgress = {}, // <-- Pass registration status
  setActiveSecondarySidebar, // <-- New prop for setting active sidebar
}) => {
  const [expandedSections, setExpandedSections] = useState({
    courses: true,
    academicTasks: false, // Keep this collapsible
    fixedTasks: true,
    flexibleTasks: true,
  });
  const navigate = useNavigate(); // Hook for navigation

  const toggleSection = (sectionName) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionName]: !prev[sectionName]
    }));
  };

  const handleCalendarClick = (e) => {
    if (!isExpanded) {
      e.stopPropagation();
    }
  };

  return (
    <aside className={`${styles.infoSidebar} ${!isExpanded ? styles.infoSidebarCollapsed : ''}`}>
      <div className={styles.sidebarContent} style={{ display: isExpanded ? 'flex' : 'none' }}>
        {/* Month Calendar */}
        <div className={styles.monthCalendarSection} onClick={handleCalendarClick}>
          <Calendar
            onChange={onDateChange}
            value={new Date()}
            className={styles.monthCalendar}
          />
        </div>

        {/* Sections Container */}
        <div className={styles.sectionsContainer}>

          {/* My Courses */}
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <h3>My Courses</h3>
              {/* Navigate to course browser or a dedicated page */}
              <button className={styles.addBtn} onClick={() => setActiveSecondarySidebar('courses')}>+ Add</button>
            </div>
            <div className={styles.sectionContent}>
              {registeredCourses.length === 0 ? (
                <div className={styles.emptyState}>
                  <p>No registered courses.</p>
                  <button onClick={() => setActiveSecondarySidebar('courses')}>Browse Courses</button>
                </div>
              ) : (
                <div className={styles.coursesList}>
                  {registeredCourses.map((course) => (
                    <div className={styles.courseCard} key={course.course_id}>
                      <div className={styles.courseCode}>{course.course_code}</div>
                      <div className={styles.courseNameSmall}>{course.course_name}</div>
                      <div className={styles.instructorSmall}>
                        Inst: {course.instructor || "TBD"}
                      </div>
                      <button
                        className={styles.unregisterBtnSmall}
                        onClick={() => handleCourseUnregistration(course.course_id)}
                        disabled={registrationInProgress[course.course_id]}
                      >
                        {registrationInProgress[course.course_id] ? "..." : "Drop"}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Fixed Obligations */}
          <div className={styles.section}>
             <div className={styles.sectionHeader}>
               <h3>Fixed Tasks</h3>
               <button className={styles.addBtn} onClick={() => navigate('/obligations/fixed/add')}>+ Add</button>
             </div>
             <div className={styles.sectionContent}>
               {fixedObligations.length === 0 ? (
                 <div className={styles.emptyState}>
                   <p>No fixed tasks.</p>
                   <button onClick={() => navigate('/obligations/fixed/add')}>Add Task</button>
                 </div>
               ) : (
                 <div className={styles.obligationsList}>
                   {fixedObligations.map((obligation) => (
                     <div className={styles.obligationItem} key={obligation.obligation_id}>
                       <div className={styles.obligationInfo}>
                         <div className={styles.obligationTitleSmall}>{obligation.name}</div>
                         <div className={styles.obligationDetailsSmall}>
                           {/* Safely access the first day from the array and get its abbreviation */}
                           <span>{obligation.days_of_week?.[0]?.substring(0, 3) || 'N/A'}</span>
                           <span>{`${obligation.start_time} - ${obligation.end_time}`}</span>
                         </div>
                       </div>
                       <div className={styles.obligationActions}>
                         <button
                           onClick={() => navigate(`/obligations/fixed/edit/${obligation.obligation_id}`)}
                           className={styles.editBtnSmall}
                         >
                           Edit
                         </button>
                       </div>
                     </div>
                   ))}
                 </div>
               )}
             </div>
           </div>

          {/* Flexible Obligations */}
          <div className={styles.section}>
             <div className={styles.sectionHeader}>
               <h3>Flexible Tasks</h3>
               <button className={styles.addBtn} onClick={() => navigate('/obligations/flexible/add')}>+ Add</button>
             </div>
             <div className={styles.sectionContent}>
               {flexibleObligations.length === 0 ? (
                 <div className={styles.emptyState}>
                   <p>No flexible tasks.</p>
                   <button onClick={() => navigate('/obligations/flexible/add')}>Add Task</button>
                 </div>
               ) : (
                 <div className={styles.obligationsList}>
                   {flexibleObligations.map((obligation) => (
                     <div className={styles.obligationItem} key={obligation.obligation_id}>
                       <div className={styles.obligationInfo}>
                         <div className={styles.obligationTitleSmall}>{obligation.description}</div>
                         <div className={styles.obligationDetailsSmall}>
                           <span>{obligation.weekly_target_hours} hrs/wk</span>
                         </div>
                       </div>
                       <div className={styles.obligationActions}>
                         <button
                           onClick={() => navigate(`/obligations/flexible/edit/${obligation.obligation_id}`)}
                           className={styles.editBtnSmall}
                         >
                           Edit
                         </button>
                       </div>
                     </div>
                   ))}
                 </div>
               )}
             </div>
           </div>

           {/* Academic Tasks (Kept collapsible for now) */}
           <div className={styles.section}>
             <button
               className={styles.collapsibleHeader} // Use a different style for collapsible ones
               onClick={() => toggleSection('academicTasks')}
               aria-expanded={expandedSections.academicTasks}
             >
               Academic Tasks
               <span className={styles.toggleIcon}>{expandedSections.academicTasks ? '−' : '+'}</span>
             </button>
             {expandedSections.academicTasks && (
               <div className={styles.sectionContent}>
                 {academicTasks.length === 0 ? (
                   <p className={styles.emptyState}>No upcoming academic tasks.</p>
                 ) : (
                   <ul className={styles.list}> {/* Keep original list style for this */}
                     {academicTasks.map(task => (
                       <li key={task.task_id} className={styles.listItem} onClick={() => onItemClick('academic', task)}>
                         <span className={styles.taskTitle}>{task.title}</span>
                         <span className={styles.taskDeadline}>
                           Due: {formatDateSimple(task.deadline)}
                         </span>
                       </li>
                     ))}
                   </ul>
                 )}
               </div>
             )}
           </div>

        </div>
      </div>
    </aside>
  );
};

export default InfoSidebar;