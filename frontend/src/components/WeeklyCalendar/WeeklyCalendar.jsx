import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom'; // Make sure to import Link
import { format, startOfWeek, addDays, parseISO, getDay } from 'date-fns';
import styles from './WeeklyCalendar.module.css'; // Assuming you have a CSS module for styling

const slotHeight = 60; // px per hour slot
const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const hourLabels = Array.from({ length: 24 }, (_, i) => (i < 10 ? `0${i}:00` : `${i}:00`));

// Event type to color mapping
const typeColors = {
  'fixed_obligation': '#e63946', // Red
  'flexible_obligation': '#457b9d', // Blue
  'study_session': '#2a9d8f', // Teal
  'class': '#f4a261', // Orange
};

// Priority to opacity mapping (higher priority = more opacity)
const priorityOpacity = {
  1: 0.6,
  2: 0.7, 
  3: 0.8,
  4: 0.9,
  5: 1.0
};

const WeeklyCalendar = ({ style }) => {
  const [calendarEvents, setCalendarEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentWeekStart, setCurrentWeekStart] = useState(startOfWeek(new Date()));

  useEffect(() => {
    fetchCalendarEvents();
  }, [currentWeekStart]);

  const fetchCalendarEvents = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem("accessToken");
      
      // Calculate start and end dates for the query
      const startDate = format(currentWeekStart, 'yyyy-MM-dd');
      const endDate = format(addDays(currentWeekStart, 7), 'yyyy-MM-dd');
      
      const response = await fetch(
        `/api/tasks/calendar-events?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          }
        }
      );
      
      if (!response.ok) {
        throw new Error(`Failed to fetch calendar events: ${response.status}`);
      }
      
      const data = await response.json();
      setCalendarEvents(data);
      setLoading(false);
    } catch (err) {
      console.error("Failed to fetch calendar events:", err);
      setError(err.message);
      setLoading(false);
    }
  };

  const navigatePreviousWeek = () => {
    setCurrentWeekStart(prevWeek => addDays(prevWeek, -7));
  };

  const navigateNextWeek = () => {
    setCurrentWeekStart(prevWeek => addDays(prevWeek, 7));
  };

  const navigateToday = () => {
    setCurrentWeekStart(startOfWeek(new Date()));
  };

  // Add a refresh function that calls fetchCalendarEvents
  const handleRefresh = () => {
    fetchCalendarEvents();
  };

  // Prepare events for display
  const processedEvents = calendarEvents.map(event => {
    const startTime = parseISO(event.start_time);
    const endTime = parseISO(event.end_time);
    const eventDate = parseISO(event.date);
    
    return {
      id: event.event_id,
      type: event.event_type,
      title: event.event_type === 'fixed_obligation' ? 'Fixed: ' + event.name :
             event.event_type === 'flexible_obligation' ? 'Flexible: ' + event.description :
             event.event_type === 'study_session' ? 'Study: ' + event.description :
             'Class',
      day: getDay(eventDate), // 0 = Sunday, 6 = Saturday
      startTime: format(startTime, 'HH:mm'),
      endTime: format(endTime, 'HH:mm'),
      location: event.location || '',
      description: event.description || '',
      color: typeColors[event.event_type] || '#6c757d', // Default gray
      opacity: priorityOpacity[event.priority] || 0.8,
      priority: event.priority || 3,
      status: event.status
    };
  });

  // Group events by day
  const eventsByDay = {};
  processedEvents.forEach(ev => {
    if (!eventsByDay[ev.day]) eventsByDay[ev.day] = [];
    eventsByDay[ev.day].push(ev);
  });

  const parseTime = time => {
    const [h, m] = time.split(':').map(Number);
    return h + m / 60;
  };

  if (loading) {
    return <div className={styles.loadingContainer}>
      <div className={styles.loadingSpinner}></div>
    </div>;
  }

  if (error) {
    return <div className={styles.errorMessage}>
      Error loading calendar: {error}
    </div>;
  }

  return (
    <div className={styles.calendar} style={style}>
      {/* Calendar Controls */}
      <div className={styles.header}>
        <div className={styles.headerLeft || "flex items-center"}>
          <Link 
            to="/dashboard" 
            className={styles.linkButton || "mr-4 text-blue-600 font-medium hover:text-blue-800 flex items-center"}
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M9.707 14.707a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 1.414L7.414 9H15a1 1 0 110 2H7.414l2.293 2.293a1 1 0 010 1.414z" clipRule="evenodd" />
            </svg>
            Dashboard
          </Link>
          <button 
            onClick={navigatePreviousWeek}
            className={styles.button}
          >
            ← Previous Week
          </button>
        </div>
        
        <div className={styles.dateRange}>
          {format(currentWeekStart, 'MMMM d')} - {format(addDays(currentWeekStart, 6), 'MMMM d, yyyy')}
        </div>
        
        <div className={styles.buttonGroup}>
          <button 
            onClick={navigateToday}
            className={styles.primaryButton}
          >
            Today
          </button>
          <button 
            onClick={navigateNextWeek}
            className={styles.button}
            style={{marginLeft: '0.5rem'}}
          >
            Next Week →
          </button>
          {/* Add refresh button */}
          <button 
            onClick={handleRefresh}
            className={styles.refreshButton || styles.button} 
            style={{marginLeft: '0.5rem'}}
            title="Refresh calendar"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      </div>

      <div className={styles.calendarGrid}>
        {/* Day headers */}
        <div className={styles.gridHeader}></div>
        {dayNames.map((day, idx) => {
          const currentDate = addDays(currentWeekStart, idx);
          const isToday = format(new Date(), 'yyyy-MM-dd') === format(currentDate, 'yyyy-MM-dd');
          
          return (
            <div 
              key={idx} 
              className={`${styles.gridHeader} ${isToday ? styles.todayHeader : ''}`}
            >
              <div>{day}</div>
              <div>{format(currentDate, 'd')}</div>
            </div>
          );
        })}

        {/* Calendar body */}
        <div className={styles.timeColumn}>
          {hourLabels.map((hour, idx) => (
            <div key={idx} className={styles.timeSlot}>
              {hour}
            </div>
          ))}
        </div>
        
        {/* Days columns */}
        {dayNames.map((_, dayIdx) => (
          <div key={dayIdx} className={styles.dayColumn}>
            {/* Hourly grid lines */}
            {Array.from({ length: 24 }).map((_, hour) => (
              <div
                key={hour}
                className={`${styles.hourCell} ${hour >= 8 && hour < 18 ? styles.workHourCell : ''}`}
              />
            ))}

            {/* Events */}
            {(eventsByDay[dayIdx] || []).map(ev => {
              const start = parseTime(ev.startTime);
              const end = parseTime(ev.endTime);
              const top = start * slotHeight;
              const height = Math.max((end - start) * slotHeight, 20); // Min height for very short events

              const isPastEvent = ev.status === 'completed' || ev.status === 'overdue';

              return (
                <div
                  key={ev.id}
                  className={styles.event}
                  style={{
                    top: `${top}px`,
                    height: `${height}px`,
                    left: '4px',
                    right: '4px',
                    backgroundColor: ev.color,
                    opacity: isPastEvent ? 0.6 : ev.opacity,
                    borderLeft: `3px solid ${ev.color}`
                  }}
                  title={`${ev.title}${ev.location ? ` @ ${ev.location}` : ''}\n${ev.description || ''}`}
                >
                  <div style={{fontSize: '0.75rem', fontWeight: 'bold'}}>
                    {ev.startTime} - {ev.endTime}
                    {ev.priority >= 4 && <span style={{marginLeft: '4px'}}>⚠️</span>}
                  </div>
                  <div style={{fontWeight: 'bold', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                    {ev.title}
                  </div>
                  {ev.location && <div style={{fontSize: '0.75rem'}}>{ev.location}</div>}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      
      {/* Legend */}
      <div className={styles.legend}>
        <div style={{marginRight: '1rem', fontWeight: '500', fontSize: '0.875rem'}}>Event Types:</div>
        {Object.entries(typeColors).map(([type, color]) => (
          <div key={type} className={styles.legendItem}>
            <div className={styles.legendColor} style={{backgroundColor: color}}></div>
            <span className={styles.legendLabel}>
              {type.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
            </span>
          </div>
        ))}
        
        <div style={{marginLeft: '1rem', marginRight: '1rem', fontWeight: '500', fontSize: '0.875rem'}}>Priority:</div>
        {[5, 4, 3, 2, 1].map((priority) => (
          <div key={priority} className={styles.legendItem}>
            <div className={styles.legendColor} style={{
              backgroundColor: 'black', 
              opacity: priorityOpacity[priority]
            }}></div>
            <span className={styles.legendLabel}>
              {priority === 5 ? 'Highest' : 
               priority === 4 ? 'High' : 
               priority === 3 ? 'Medium' : 
               priority === 2 ? 'Low' : 'Lowest'}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default WeeklyCalendar;