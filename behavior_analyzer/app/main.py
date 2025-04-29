from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from app.database import engine
from app.routers import behavior

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Behavior Analyzer API")

# CORS middleware
origins = [
    "http://localhost:5173",  # React development server default port
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(behavior.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to the Behavior Analyzer API"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "behavior-analyzer"}