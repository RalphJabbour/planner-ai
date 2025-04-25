from sqlalchemy.ext.automap import automap_base
from sqlalchemy import MetaData
from app.database import engine

# Reflect existing tables from the backend database
metadata = MetaData()
metadata.reflect(bind=engine)
ReflectedBase = automap_base(metadata=metadata)
ReflectedBase.prepare()

# Map reflected tables to model classes
SessionEvent = ReflectedBase.classes.behavior_session_events
ContextSignal = ReflectedBase.classes.context_signals
ProductivityProfile = ReflectedBase.classes.behavior_productivity_profiles