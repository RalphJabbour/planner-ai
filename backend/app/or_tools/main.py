from fastapi import APIRouter
from .router import router as scheduler_router

# Create a router for OR-Tools
or_tools_router = APIRouter()
or_tools_router.include_router(scheduler_router)