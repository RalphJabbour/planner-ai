from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Reflect existing tables from the backend database
metadata = MetaData()
metadata.reflect(bind=engine)
ReflectedBase = automap_base(metadata=metadata)
ReflectedBase.prepare()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try: 
        yield db 
    finally:
        db.close()