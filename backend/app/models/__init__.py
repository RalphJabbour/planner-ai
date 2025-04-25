from app.models.student import Student
from app.models.course import Course, StudentCourse
from app.models.academic import AcademicTask, StudyMaterial
from app.models.schedule import FixedObligation, FlexibleObligation, PersonalizedStudySession, CalendarEvent, Notification, TaskProgress
from app.models.logging import DailyLog
from app.models.behavior import SessionEvent, ContextSignal, ProductivityProfile

# This allows importing all models from app.models