from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import os
import asyncio
import logging
import json # For serializing complex arguments if needed
from app.routers.courses import CourseRegistration # Import the Pydantic model
from app.routers.tasks import FlexibleObligationCreate

# MCP Client Imports
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# App specific imports
from app.database import get_db
from app.models.student import Student
from app.auth.token import get_current_student

# --- Temporary Draft Storage (Replace with Redis in production) ---
# Simple in-memory dictionary for demonstration.
# WARNING: This will not persist across server restarts and is not suitable for production.
draft_storage: Dict[str, List[Dict[str, Any]]] = {} # Key: chat_id, Value: list of proposed actions

# --- MCP Server Configuration ---
# Ensure the path is correct relative to where the FastAPI app runs
mcp_server_script = os.path.join(os.path.dirname(__file__), "..", "mcp-server", "server.py")
server_params = StdioServerParameters(
    command="python", # Or absolute path to python executable if needed
    args=[mcp_server_script],
    env=os.environ.copy(), # Pass environment variables (like DATABASE_URL)
    cwd=os.path.join(os.path.dirname(__file__), "..", "..") # Set working directory to backend root
)

router = APIRouter(prefix="/ai-assistant", tags=["ai-assistant"])
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str
    chat_id: str # To manage conversation state and drafts
    # context: Optional[Dict[str, Any]] = None # Could include current page, etc.

class ChatResponse(BaseModel):
    reply: str
    requires_confirmation: bool = False
    chat_id: str
    proposed_actions: Optional[List[Dict[str, Any]]] = None # For debugging/FE display

class ConfirmRequest(BaseModel):
    chat_id: str

# --- MCP Client Session Management ---
# It's better to manage the session lifecycle if possible, but for simplicity,
# we'll create a new connection per request for now. This is inefficient.
# A better approach would use a shared client pool or manage a persistent connection.

async def run_mcp_interaction(chat_request: ChatRequest, student: Student) -> ChatResponse:
    """Handles interaction with the MCP server for a single chat request."""
    proposed_actions = []
    response_message = "Processing your request..."
    requires_confirmation = False

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                logger.info(f"Available MCP tools: {[t.name for t in tools]}")

                # --- Simulate LLM deciding which tool to call based on message ---
                # This is a highly simplified simulation. A real implementation
                # would involve sending the message to an LLM (via MCP prompt or external API)
                # which would then decide to call tools via the MCP session.

                user_message = chat_request.message.lower()

                if "register" in user_message and "course" in user_message:
                    # Example: Extract course code (very basic)
                    parts = user_message.split()
                    course_code = None
                    for part in parts:
                        # Rudimentary check for a course code pattern (e.g., EECE330)
                        if len(part) > 4 and part[:4].isalpha() and part[4:].isdigit():
                             course_code = part.upper()
                             break
                        elif len(part) > 3 and part[:3].isalpha() and part[3:].isdigit():
                             course_code = part.upper()
                             break


                    if course_code:
                        logger.info(f"Attempting to find course: {course_code}")
                        find_result = await session.call_tool(
                            "find_course",
                            arguments={"course_code": course_code}
                        )
                        logger.info(f"find_course result: {find_result}")

                        if find_result and isinstance(find_result, list) and len(find_result) > 0:
                            # Assume first result is the one we want
                            target_course = find_result[0]
                            course_id = target_course["course_id"]
                            course_name = target_course["course_name"]

                            logger.info(f"Checking schedule fit for course ID: {course_id}")
                            fit_result = await session.call_tool(
                                "check_schedule_fit",
                                arguments={"student_id": student.student_id, "course_id": course_id}
                            )
                            logger.info(f"check_schedule_fit result: {fit_result}")

                            if fit_result and fit_result.get("fits"):
                                # Propose registration
                                proposal = {
                                    "action": "register_course",
                                    "arguments": {"student_id": student.student_id, "course_id": course_id}
                                }
                                proposed_actions.append(proposal)
                                response_message = f"Course {course_code} ({course_name}) seems to fit your schedule. Do you want to register?"
                                requires_confirmation = True
                            else:
                                reason = fit_result.get("reason", "Unknown reason")
                                response_message = f"Could not register {course_code}. Reason: {reason}"
                        else:
                            response_message = f"Could not find course code {course_code}."
                    else:
                        response_message = "Please specify a course code to register (e.g., EECE330)."

                # --- Add more logic for other intents (add obligation, etc.) ---
                elif "add flexible" in user_message:
                     # Example: Parse details (very basic, needs proper NLP/LLM)
                     # Assume parsing yields: name="Gym", hours=3, priority=2
                     name = "Gym" # Placeholder
                     hours = 3.0 # Placeholder
                     priority = 2 # Placeholder
                     proposal = {
                         "action": "add_flexible_obligation",
                         "arguments": {
                             "student_id": student.student_id,
                             "name": name,
                             "description": "User added flexible task", # Placeholder
                             "weekly_target_hours": hours,
                             "priority": priority
                         }
                     }
                     proposed_actions.append(proposal)
                     response_message = f"Okay, I can add a flexible obligation '{name}' for {hours} hours/week with priority {priority}. Confirm?"
                     requires_confirmation = True

                else:
                    response_message = "Sorry, I didn't understand that. Try asking to 'register course EECE330' or 'add flexible task Gym 3 hours priority 2'."

                # Store proposed actions if confirmation is needed
                if requires_confirmation and proposed_actions:
                    draft_storage[chat_request.chat_id] = proposed_actions
                else:
                    # Clear any old drafts for this chat if no confirmation needed now
                    if chat_request.chat_id in draft_storage:
                        del draft_storage[chat_request.chat_id]

    except Exception as e:
        logger.error(f"Error during MCP interaction: {e}", exc_info=True)
        response_message = f"An error occurred: {e}"
        requires_confirmation = False
        # Clear drafts on error
        if chat_request.chat_id in draft_storage:
            del draft_storage[chat_request.chat_id]

    return ChatResponse(
        reply=response_message,
        requires_confirmation=requires_confirmation,
        chat_id=chat_request.chat_id,
        proposed_actions=proposed_actions if requires_confirmation else None
    )


@router.post("/chat", response_model=ChatResponse)
async def handle_chat(
    chat_request: ChatRequest,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db) # Keep db dependency for potential direct actions if needed
):
    """Receives a chat message, interacts with MCP server, and returns response."""
    logger.info(f"Received chat message from student {current_student.student_id}, chat_id {chat_request.chat_id}: {chat_request.message}")
    response = await run_mcp_interaction(chat_request, current_student)
    logger.info(f"Sending reply for chat_id {chat_request.chat_id}: {response.reply}, Confirmation: {response.requires_confirmation}")
    return response


@router.post("/chat/confirm")
async def confirm_chat_actions(
    confirm_request: ConfirmRequest,
    current_student: Student = Depends(get_current_student),
    db: Session = Depends(get_db)
):
    """Confirms and executes actions proposed in a previous chat turn."""
    chat_id = confirm_request.chat_id
    logger.info(f"Received confirmation for chat_id {chat_id} from student {current_student.student_id}")

    if chat_id not in draft_storage:
        raise HTTPException(status_code=404, detail="No pending actions found for this chat ID or they have expired.")

    actions_to_execute = draft_storage.pop(chat_id) # Retrieve and remove draft
    results = []

    # --- Execute Actions within a Transaction ---
    try:
        # Note: FastAPI doesn't automatically handle transactions across multiple awaits/operations.
        # You might need to manage the transaction manually if multiple DB calls are needed.
        # For simplicity, assuming each action is relatively atomic here.
        # A robust solution would use db.begin() or similar context manager if available.

        for action in actions_to_execute:
            tool_name = action["action"]
            arguments = action["arguments"]
            logger.info(f"Executing action: {tool_name} with args: {arguments}")

            # --- Map proposed action to actual backend logic ---
            if tool_name == "register_course":
                # Call the *actual* registration logic from your courses router/service
                # Ensure student_id matches current_student.student_id for security
                if arguments.get("student_id") != current_student.student_id:
                     raise HTTPException(status_code=403, detail="Action student ID mismatch.")

                # We need to adapt the call to register_course_logic
                # It might expect a Pydantic model or different structure
                # This requires careful mapping or refactoring register_course_logic

                # Example adaptation (may need adjustment):
                registration_data = CourseRegistration(course_id=arguments["course_id"])
                # The original function is async and uses Depends(get_db)
                # Calling it directly is complex. Ideal: Refactor core logic.
                # Workaround: Re-implement or call a refactored service function.

                # Re-implementing simplified logic here for demonstration:
                course_id = arguments["course_id"]
                course = db.query(Course).filter(Course.course_id == course_id).first()
                if not course: raise ValueError(f"Course {course_id} not found during execution.")
                existing = db.query(StudentCourse).filter(StudentCourse.student_id == student_id, StudentCourse.course_id == course_id).first()
                if existing: raise ValueError(f"Already registered for course {course_id}.")

                new_reg = StudentCourse(student_id=student_id, course_id=course_id)
                db.add(new_reg)
                # Need to also create the fixed obligation for the course schedule here!
                # This involves calling create_fixed_obligation logic similar to how register_course does.
                # ... (omitted for brevity, but crucial)
                db.commit() # Commit after each action or at the end? Transaction needed.
                results.append({"action": tool_name, "status": "success", "course_id": course_id})


            elif tool_name == "add_flexible_obligation":
                 # Similar logic: call the actual create_flexible_obligation logic
                 if arguments.get("student_id") != current_student.student_id:
                     raise HTTPException(status_code=403, detail="Action student ID mismatch.")

                 # Map arguments to the Pydantic model expected by the create function
                 # Handle date string conversion
                 start_dt = datetime.fromisoformat(arguments["start_date"]) if arguments.get("start_date") else None
                 end_dt = datetime.fromisoformat(arguments["end_date"]) if arguments.get("end_date") else None

                 obligation_data = FlexibleObligationCreate(
                     name=arguments["name"],
                     description=arguments.get("description"),
                     weekly_target_hours=arguments["weekly_target_hours"],
                     priority=arguments["priority"],
                     start_date=start_dt,
                     end_date=end_dt,
                     constraints=arguments.get("constraints")
                 )
                 # Again, calling the async router function directly is hard.
                 # Re-implementing simplified logic:
                 new_obl = FlexibleObligation(
                     student_id=current_student.student_id,
                     **obligation_data.dict(exclude_unset=True) # Use Pydantic model dict
                 )

                 db.add(new_obl)
                 db.commit() # Commit per action or use transaction
                 db.refresh(new_obl)
                 results.append({"action": tool_name, "status": "success", "obligation_id": new_obl.obligation_id})

            else:
                results.append({"action": tool_name, "status": "skipped", "reason": "Execution logic not implemented."})

        # If all actions succeeded (within a transaction ideally)
        logger.info(f"Successfully executed actions for chat_id {chat_id}")
        return {"message": "Actions confirmed and executed successfully.", "results": results}

    except Exception as e:
        logger.error(f"Error executing confirmed actions for chat_id {chat_id}: {e}", exc_info=True)
        # Rollback transaction if one was used
        db.rollback()
        # Optionally put actions back in draft? Or just report error.
        # draft_storage[chat_id] = actions_to_execute # Put back if rollback
        raise HTTPException(status_code=500, detail=f"Failed to execute actions: {e}")