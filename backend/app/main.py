from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import app.models
from app.database import engine, Base
from app.routers import auth, survey, dashboard

# Create tables if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Student Planner API")

# CORS middleware
origins = [
    "http://localhost:5173",  # React development server default port
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(survey.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to the Student Planner API"}