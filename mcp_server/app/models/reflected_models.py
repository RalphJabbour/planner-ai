from sqlalchemy.ext.automap import automap_base
from sqlalchemy import MetaData
from app.database import engine, ReflectedBase

# Map reflected tables to model classes
Course = ReflectedBase.classes.courses
Student = ReflectedBase.classes.students
StudentCourse = ReflectedBase.classes.student_courses
FixedObligation = ReflectedBase.classes.fixed_obligations
FlexibleObligation = ReflectedBase.classes.flexible_obligations
AcademicTask = ReflectedBase.classes.academic_tasks
CalendarEvent = ReflectedBase.classes.calendar_events