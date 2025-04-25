# This file is kept for compatibility but no longer contains
# database connectivity code as all data is passed via requests

# Maintain Base for model imports if needed
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Import base models from backend
# Don't create tables here - backend is responsible for schema

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try: 
        yield db 
    finally:
        db.close()
