-- -- 1. Students (User and Profile Management)
-- CREATE TABLE students (
--     student_id SERIAL PRIMARY KEY,
--     name VARCHAR(255) NOT NULL,
--     email VARCHAR(255) NOT NULL UNIQUE,
--     program VARCHAR(255),
--     year INTEGER,
--     -- Flexible JSONB column to store various scheduling preferences and onboarding responses
--     preferences JSONB,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- -- 2. Courses (Course Details and Timetable)
-- CREATE TABLE courses (
--     course_id SERIAL PRIMARY KEY,
--     course_code VARCHAR(50) UNIQUE NOT NULL,
--     course_name VARCHAR(255) NOT NULL,
--     instructor VARCHAR(255),
--     semester VARCHAR(50) NOT NULL,
--     -- Store timetable info as JSON (or later decompose into a separate table if needed)
--     timetable JSONB,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- -- 3. Student Courses (Mapping students to registered courses)
-- CREATE TABLE student_courses (
--     student_course_id SERIAL PRIMARY KEY,
--     student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
--     course_id INTEGER REFERENCES courses(course_id) ON DELETE CASCADE,
--     registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     UNIQUE (student_id, course_id)
-- );

-- -- 4. Academic Tasks (Assignments, Projects, Exams)
-- CREATE TABLE academic_tasks (
--     task_id SERIAL PRIMARY KEY,
--     course_id INTEGER REFERENCES courses(course_id) ON DELETE CASCADE,
--     task_type VARCHAR(50) CHECK (task_type IN ('assignment', 'project', 'exam')),
--     title VARCHAR(255) NOT NULL,
--     description TEXT,
--     deadline TIMESTAMP NOT NULL,
--     estimated_hours NUMERIC,
--     status VARCHAR(50) DEFAULT 'pending',
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- -- 5. Study Materials (Resources linked to courses or tasks)
-- CREATE TABLE study_materials (
--     material_id SERIAL PRIMARY KEY,
--     course_id INTEGER REFERENCES courses(course_id) ON DELETE CASCADE,
--     task_id INTEGER REFERENCES academic_tasks(task_id) ON DELETE SET NULL,
--     material_type VARCHAR(50) CHECK (material_type IN ('pdf', 'powerpoint', 'testbank', 'book_exercise')),
--     title VARCHAR(255),
--     url TEXT,
--     chapter VARCHAR(100),
--     expected_time NUMERIC,  -- Expected time to review the material in hours
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- -- 6. Fixed Obligations (Time-fixed events such as club meetings, practices, etc.)
-- CREATE TABLE fixed_obligations (
--     obligation_id SERIAL PRIMARY KEY,
--     student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
--     name VARCHAR(255) NOT NULL,
--     description TEXT,
--     start_time TIME NOT NULL,
--     end_time TIME NOT NULL,
--     day_of_week VARCHAR(20) NOT NULL,  -- e.g., 'Monday', 'Tuesday'
--     recurrence VARCHAR(50),           -- e.g., 'weekly', 'bi-weekly'
--     priority INTEGER CHECK (priority BETWEEN 1 AND 5),
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- -- 7. Flexible Obligations (Obligations with target hours, not pinned to fixed times)
-- CREATE TABLE flexible_obligations (
--     obligation_id SERIAL PRIMARY KEY,
--     student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
--     description TEXT NOT NULL,
--     weekly_target_hours NUMERIC NOT NULL,
--     -- Constraints/preferences stored in JSON (e.g., preferred hours, max per session, etc.)
--     constraints JSONB,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- -- 8. Daily Logs (Tracking planned vs. completed tasks and feedback)
-- CREATE TABLE daily_logs (
--     log_id SERIAL PRIMARY KEY,
--     student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
--     log_date DATE NOT NULL,
--     planned_schedule JSONB,    -- Snapshot of the schedule for the day
--     completed_schedule JSONB,  -- What was actually completed
--     progress_updates JSONB,    -- Key/value pairs for course progress (e.g., {"biology": "30%"} )
--     notes TEXT,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     UNIQUE (student_id, log_date)
-- );

-- -- 9. Study Sessions (Individual study session records; supports adaptive scheduling)
-- CREATE TABLE study_sessions (
--     session_id SERIAL PRIMARY KEY,
--     student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
--     task_id INTEGER REFERENCES academic_tasks(task_id) ON DELETE CASCADE,
--     course_id INTEGER REFERENCES courses(course_id) ON DELETE CASCADE,
--     chapter VARCHAR(100),
--     planned_start TIMESTAMP NOT NULL,
--     planned_end TIMESTAMP NOT NULL,
--     actual_start TIMESTAMP,
--     actual_end TIMESTAMP,
--     actual_hours NUMERIC,
--     feedback TEXT,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- -- 10. Calendar Events (Master schedule combining all events)
-- CREATE TABLE calendar_events (
--     event_id SERIAL PRIMARY KEY,
--     student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
--     event_type VARCHAR(50) CHECK (event_type IN ('class', 'study_session', 'fixed_obligation', 'flexible_obligation')),
--     -- reference_id indicates the associated record in its native table
--     reference_id INTEGER,
--     start_time TIMESTAMP NOT NULL,
--     end_time TIMESTAMP NOT NULL,
--     priority INTEGER CHECK (priority BETWEEN 1 AND 5),
--     status VARCHAR(50) DEFAULT 'scheduled',
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- -- 11. Notifications (Reminders and change alerts)
-- CREATE TABLE notifications (
--     notification_id SERIAL PRIMARY KEY,
--     student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
--     event_id INTEGER REFERENCES calendar_events(event_id) ON DELETE SET NULL,
--     notification_time TIMESTAMP NOT NULL,
--     message TEXT,
--     delivered BOOLEAN DEFAULT FALSE,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- CREATE TABLE course_progress (
--     progress_id SERIAL PRIMARY KEY,
    
--     -- Identify which student and course this record is for
--     student_id INTEGER REFERENCES students(student_id) ON DELETE CASCADE,
--     course_id INTEGER REFERENCES courses(course_id) ON DELETE CASCADE,
    
--     -- Optionally link this progress record to a specific academic task
--     task_id INTEGER REFERENCES academic_tasks(task_id) ON DELETE CASCADE,
    
--     -- This column specifies the kind of progress record; for chapter study it might be 'chapter_study',
--     -- for project work, 'project', for problem solving, 'problem_solving', etc.
--     task_type VARCHAR(50) CHECK (task_type IN ('chapter_study', 'project', 'problem_solving')),
    
--     -- If the progress is for a chapter study task, record the chapter number or identifier
--     chapter VARCHAR(100),
    
--     -- Track how complete the material or task is (e.g., 30 for 30% completion)
--     percentage_completed NUMERIC,
    
--     -- Accumulate the total hours the student has spent on this particular task or chapter.
--     hours_spent NUMERIC,
    
--     -- Optional: a proficiency score computed from tests/quizzes related to the material, ranging for example from 0 to 1.
--     proficiency_score NUMERIC,
    
--     -- Timestamp for the last update, useful for tracking progression over time
--     last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- ALTER TABLE study_sessions
--   ADD COLUMN start_chapter VARCHAR(100);

-- ALTER TABLE study_sessions
--   ADD COLUMN planned_chapters JSONB DEFAULT '[]';

-- ALTER TABLE study_sessions
--   ADD COLUMN actual_chapters JSONB DEFAULT '[]';


-- -- 1. Insert sample data into "students"
-- INSERT INTO students (name, email, program, year, preferences)
-- VALUES
--   ('John Doe', 'john.doe@example.com', 'Computer Science', 2, '{"wakeUpTime": "07:00", "preferredStudyTime": "evening", "gym": "afternoon"}'),
--   ('Jane Smith', 'jane.smith@example.com', 'Biology', 3, '{"wakeUpTime": "06:30", "preferredStudyTime": "morning", "gym": "none"}'),
--   ('Alice Johnson', 'alice.johnson@example.com', 'Business Administration', 1, '{"wakeUpTime": "08:00", "preferredStudyTime": "afternoon", "gym": "morning"}'),
--   ('Bob Brown', 'bob.brown@example.com', 'Mechanical Engineering', 4, '{"wakeUpTime": "07:30", "preferredStudyTime": "evening", "gym": "evening"}');

-- -- 2. Insert sample data into "courses"
-- INSERT INTO courses (course_code, course_name, instructor, semester, timetable)
-- VALUES
--   ('CS101', 'Introduction to Programming', 'Dr. Alan Turing', 'Fall 2023', '{"Monday": "09:00-10:30", "Wednesday": "09:00-10:30"}'),
--   ('BIO201', 'Molecular Biology', 'Dr. Rosalind Franklin', 'Fall 2023', '{"Tuesday": "11:00-12:30", "Thursday": "11:00-12:30"}'),
--   ('BUS101', 'Principles of Management', 'Prof. Peter Drucker', 'Fall 2023', '{"Monday": "14:00-15:30", "Wednesday": "14:00-15:30"}'),
--   ('ME301', 'Thermodynamics', 'Dr. Sadi Carnot', 'Fall 2023', '{"Tuesday": "09:00-10:30", "Thursday": "09:00-10:30"}');

-- -- 3. Insert sample data into "student_courses"
-- INSERT INTO student_courses (student_id, course_id)
-- VALUES
--   (1, 1),
--   (1, 2),
--   (2, 1),
--   (2, 2),
--   (3, 3),
--   (4, 4);

-- -- 4. Insert sample data into "academic_tasks"
-- INSERT INTO academic_tasks (course_id, task_type, title, description, deadline, estimated_hours, status)
-- VALUES
--   (1, 'assignment', 'Homework 1', 'Solve basic programming problems', '2023-10-15 23:59:00', 3, 'pending'),
--   (2, 'project', 'Lab Report', 'Complete the lab experiment and write a report', '2023-10-20 23:59:00', 5, 'pending'),
--   (3, 'exam', 'Midterm Exam', 'Covers chapters 1 to 5', '2023-10-25 09:00:00', 2, 'pending'),
--   (4, 'assignment', 'Problem Set 3', 'Thermodynamics problems', '2023-10-18 23:59:00', 4, 'pending');

-- -- 5. Insert sample data into "study_materials"
-- INSERT INTO study_materials (course_id, task_id, material_type, title, url, chapter, expected_time)
-- VALUES
--   (1, 1, 'pdf', 'Chapter 1: Basics', 'http://example.com/cs101/chapter1.pdf', '1', 2),
--   (1, 1, 'powerpoint', 'Lecture Slides Week 1', 'http://example.com/cs101/week1.ppt', '1', 1.5),
--   (2, 2, 'pdf', 'Molecular Biology - Introduction', 'http://example.com/bio201/chapter1.pdf', '1', 2),
--   (4, 4, 'book_exercise', 'Thermodynamics Problems', 'http://example.com/me301/exercises.pdf', '3', 3);

-- -- 6. Insert sample data into "fixed_obligations"
-- INSERT INTO fixed_obligations (student_id, name, description, start_time, end_time, day_of_week, recurrence, priority)
-- VALUES
--   (1, 'CS101 Lecture', 'Weekly lecture for CS101', '09:00', '10:30', 'Monday', 'weekly', 5),
--   (1, 'CS101 Lecture', 'Weekly lecture for CS101', '09:00', '10:30', 'Wednesday', 'weekly', 5),
--   (2, 'BIO201 Lab', 'Lab session for BIO201', '11:00', '12:30', 'Tuesday', 'weekly', 5),
--   (2, 'BIO201 Lab', 'Lab session for BIO201', '11:00', '12:30', 'Thursday', 'weekly', 5),
--   (3, 'BUS101 Class', 'Management principles class', '14:00', '15:30', 'Monday', 'weekly', 4),
--   (3, 'BUS101 Class', 'Management principles class', '14:00', '15:30', 'Wednesday', 'weekly', 4);

-- -- 7. Insert sample data into "flexible_obligations"
-- INSERT INTO flexible_obligations (student_id, description, weekly_target_hours, constraints)
-- VALUES
--   (1, 'Gym Sessions', 3, '{"preferredTime": "afternoon", "sessionDuration": 1}'),
--   (2, 'Club Project', 2, '{"preferredTime": "evening", "sessionDuration": 1}'),
--   (3, 'Volunteer Work', 2, '{"preferredTime": "morning", "sessionDuration": 2}'),
--   (4, 'Personal Study', 5, '{"preferredTime": "evening", "sessionDuration": 1.5}');

-- -- 8. Insert sample data into "daily_logs"
-- INSERT INTO daily_logs (student_id, log_date, planned_schedule, completed_schedule, progress_updates, notes)
-- VALUES
--   (1, '2023-10-10', '{"events": ["CS101 Lecture", "Gym", "Homework 1"]}', '{"events": ["CS101 Lecture", "Homework 1"]}', '{"CS101": "20%"}', 'Missed gym session'),
--   (2, '2023-10-10', '{"events": ["BIO201 Lab", "Club Project"]}', '{"events": ["BIO201 Lab"]}', '{"BIO201": "15%"}', 'Club project postponed'),
--   (3, '2023-10-10', '{"events": ["BUS101 Class", "Volunteer Work"]}', '{"events": ["BUS101 Class", "Volunteer Work"]}', '{"BUS101": "30%"}', 'Good day'),
--   (4, '2023-10-10', '{"events": ["ME301 Lecture", "Personal Study"]}', '{"events": ["ME301 Lecture"]}', '{"ME301": "10%"}', 'Did not complete study session');

-- -- 9. Insert sample data into "study_sessions"
-- INSERT INTO study_sessions (student_id, task_id, course_id, chapter, planned_start, planned_end, actual_start, actual_end, actual_hours, feedback)
-- VALUES
--   (1, 1, 1, '1', '2023-10-11 18:00:00', '2023-10-11 20:00:00', '2023-10-11 18:05:00', '2023-10-11 20:00:00', 1.92, 'Productive session'),
--   (2, 2, 2, '1', '2023-10-12 17:00:00', '2023-10-12 19:00:00', '2023-10-12 17:00:00', '2023-10-12 19:00:00', 2, 'Focused lab prep'),
--   (3, 3, 3, '2', '2023-10-13 20:00:00', '2023-10-13 21:30:00', '2023-10-13 20:15:00', '2023-10-13 21:30:00', 1.25, 'Needs to start earlier'),
--   (4, 4, 4, '3', '2023-10-14 16:00:00', '2023-10-14 18:00:00', '2023-10-14 16:00:00', '2023-10-14 18:00:00', 2, 'Smooth progress');

-- -- 10. Insert sample data into "calendar_events"
-- INSERT INTO calendar_events (student_id, event_type, reference_id, start_time, end_time, priority, status)
-- VALUES
--   (1, 'class', 1, '2023-10-16 09:00:00', '2023-10-16 10:30:00', 5, 'scheduled'),
--   (1, 'study_session', 1, '2023-10-16 18:00:00', '2023-10-16 20:00:00', 4, 'scheduled'),
--   (2, 'fixed_obligation', 3, '2023-10-17 11:00:00', '2023-10-17 12:30:00', 5, 'scheduled'),
--   (3, 'study_session', 3, '2023-10-18 20:00:00', '2023-10-18 21:30:00', 4, 'scheduled'),
--   (4, 'flexible_obligation', 1, '2023-10-19 17:00:00', '2023-10-19 18:00:00', 3, 'scheduled');

-- -- 11. Insert sample data into "notifications"
-- INSERT INTO notifications (student_id, event_id, notification_time, message, delivered)
-- VALUES
--   (1, 1, '2023-10-16 08:45:00', 'Reminder: CS101 Lecture starts in 15 minutes.', FALSE),
--   (1, 2, '2023-10-16 17:45:00', 'Reminder: Study session starts soon.', FALSE),
--   (2, 3, '2023-10-17 10:45:00', 'Reminder: BIO201 Lab is starting shortly.', TRUE),
--   (3, 4, '2023-10-18 19:45:00', 'Reminder: Upcoming study session for BUS101.', FALSE),
--   (4, 5, '2023-10-19 16:45:00', 'Reminder: Flexible obligation session starting soon.', FALSE);

-- -- Preview students
-- SELECT * FROM students LIMIT 5;

-- -- -- Preview courses
-- SELECT * FROM courses LIMIT 5;

-- -- -- Preview student_courses
-- SELECT * FROM student_courses LIMIT 5;

-- -- -- Preview academic_tasks
-- SELECT * FROM academic_tasks LIMIT 5;

-- -- -- Preview study_materials
-- SELECT * FROM study_materials LIMIT 5;

-- -- -- Preview fixed_obligations
-- SELECT * FROM fixed_obligations LIMIT 5;

-- -- -- Preview flexible_obligations
-- SELECT * FROM flexible_obligations LIMIT 5;

-- -- -- Preview daily_logs
-- SELECT * FROM daily_logs LIMIT 5;

-- -- -- Preview study_sessions
-- SELECT * FROM study_sessions LIMIT 5;

-- -- -- Preview calendar_events
-- SELECT * FROM calendar_events LIMIT 5;

-- -- -- Preview notifications
-- SELECT * FROM notifications LIMIT 5;

-- delete from notifications;

