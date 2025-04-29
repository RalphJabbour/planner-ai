import httpx
import os
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.token import get_current_student
from app.models.student import Student
from app.database import get_db

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["ai_assistant"])

# Get MCP Client URL from environment variable, default if not set
MCP_CLIENT_URL = os.getenv("MCP_CLIENT_URL", "http://mcp-client:3002") # Use service name in Docker

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    response: str

@router.post("", response_model=ChatResponse)
async def handle_chat(
    request: ChatRequest,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db) # Keep db session if needed later, though not used here
):
    """
    Receives a chat query from the frontend, forwards it to the MCP client
    along with the student_id, and returns the response.
    """
    mcp_chat_url = f"{MCP_CLIENT_URL}/chat"
    payload = {
        "student_id": str(current_student.student_id), # Ensure student_id is a string if needed by MCP client
        "query": request.query
    }

    logger.info(f"Forwarding chat query for student {current_student.student_id} to MCP client at {mcp_chat_url}")
    logger.debug(f"Payload: {payload}")

    async with httpx.AsyncClient(timeout=60.0) as client: # Increased timeout
        try:
            response = await client.post(mcp_chat_url, json=payload)
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

            mcp_response_data = response.json()
            logger.info(f"Received response from MCP client: {mcp_response_data}")

            # Assuming the MCP client returns a JSON with a "response" field
            ai_response_text = mcp_response_data.get("response")
            if ai_response_text is None:
                 logger.error("MCP client response did not contain a 'response' field.")
                 raise HTTPException(status_code=500, detail="Received invalid response format from AI service.")

            return ChatResponse(response=ai_response_text)

        except httpx.ConnectError as e:
            logger.error(f"Connection to MCP client failed: {e}")
            raise HTTPException(status_code=503, detail="AI service is currently unavailable (connection error).")
        except httpx.TimeoutException as e:
            logger.error(f"Request to MCP client timed out: {e}")
            raise HTTPException(status_code=504, detail="AI service request timed out.")
        except httpx.HTTPStatusError as e:
            logger.error(f"MCP client returned an error: {e.response.status_code} - {e.response.text}")
            # Forward the error detail if possible, otherwise a generic message
            error_detail = f"AI service error: {e.response.status_code}"
            try:
                error_body = e.response.json()
                if "detail" in error_body:
                    error_detail = f"AI service error: {error_body['detail']}"
            except Exception:
                pass # Keep the generic error detail
            raise HTTPException(status_code=e.response.status_code, detail=error_detail)
        except Exception as e:
            logger.exception("An unexpected error occurred while communicating with the MCP client.")
            raise HTTPException(status_code=500, detail="An unexpected error occurred while processing your request.")
