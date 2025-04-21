from pydantic import BaseModel, Field
from typing import Optional, List 
from datetime import datetime 

class SessionLogBase(BaseModel):
    userId: str 
    startTime: datetime 
    endTime: datetime 
    pagesRead: int = Field(gt=0)
    focusRating: int = Field(ge=1, le=5)
    completed: bool
    device: Optional[str] = None 
    timezone: Optional[str] = None 

class SessionLogCreate(SessionLogBase):
    pass 

class SessionLog(SessionLogBase):
    logId: int 
    createdAt: datetime 
    
    class Config:
        from_attributes = True 

class RecommendationRequest(BaseModel):
    userId: str 

class RecommendationResponse(BaseModel):
    recommendedStart: datetime 
    recommendedDuration: int 
    predictedEfficiency: float 
    predictedCompletionProb: float 
    peakHours: List[int]

