# from fastapi import APIRouter, Depends, HTTPException, Request, Response
# from fastapi.responses import StreamingResponse
# from sqlalchemy.orm import Session
# from typing import List, Optional, Dict, Any
# from pydantic import BaseModel
# import os
# import json
# import asyncio
# from sse_starlette.sse import EventSourceResponse
# import httpx
# import logging

# from app.database import get_db
# from app.models.student import Student
# from app.auth.token import get_current_student

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Define router
# router = APIRouter(prefix="/chat", tags=["chat"])

# # Define message model
# class Message(BaseModel):
#     role: str
#     content: str

# class ChatRequest(BaseModel):
#     messages: List[Message]
#     page_context: Optional[Dict[str, Any]] = None
#     stream: bool = False

# # MCP client class
# class MCPClient:
#     def __init__(self, base_url: str = "http://localhost:8001"):
#         self.base_url = base_url
#         self.api_endpoint = f"{base_url}/mcp/api/v1"
#         self.operations_endpoint = f"{self.api_endpoint}/operations"
#         self.openapi_endpoint = f"{self.api_endpoint}/openapi.json"
        
#     async def get_available_operations(self, token: str):
#         """Get available operations from the MCP server"""
#         headers = {"Authorization": f"Bearer {token}"}
#         async with httpx.AsyncClient() as client:
#             response = await client.get(self.operations_endpoint, headers=headers)
#             if response.status_code != 200:
#                 logger.error(f"Error fetching operations: {response.text}")
#                 return None
#             return response.json()
    
#     async def get_openapi_spec(self, token: str):
#         """Get OpenAPI spec from the MCP server"""
#         headers = {"Authorization": f"Bearer {token}"}
#         async with httpx.AsyncClient() as client:
#             response = await client.get(self.openapi_endpoint, headers=headers)
#             if response.status_code != 200:
#                 logger.error(f"Error fetching OpenAPI spec: {response.text}")
#                 return None
#             return response.json()
    
#     async def call_operation(self, token: str, operation_id: str, params: Dict[str, Any] = None):
#         """Call an operation on the MCP server"""
#         headers = {"Authorization": f"Bearer {token}"}
#         params = params or {}
        
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{self.api_endpoint}/execute/{operation_id}", 
#                 headers=headers,
#                 json=params
#             )
#             if response.status_code != 200:
#                 logger.error(f"Error calling operation {operation_id}: {response.text}")
#                 return None
#             return response.json()

# # Azure OpenAI client
# class AzureOpenAIClient:
#     def __init__(self):
#         # Load Azure credentials from environment variables
#         self.api_key = os.environ.get("AZURE_OPENAI_API_KEY")
#         self.endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
#         self.deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        
#         if not self.api_key or not self.endpoint:
#             logger.warning("Azure OpenAI credentials not found in environment variables")
    
#     async def chat_completion(self, messages, stream=False):
#         """Get completion from Azure OpenAI API"""
#         if not self.api_key or not self.endpoint:
#             raise ValueError("Azure OpenAI credentials not configured")
        
#         headers = {
#             "Content-Type": "application/json",
#             "api-key": self.api_key
#         }
        
#         body = {
#             "messages": messages,
#             "model": self.deployment,
#             "stream": stream
#         }
        
#         async with httpx.AsyncClient() as client:
#             if not stream:
#                 response = await client.post(
#                     f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version=2023-05-15",
#                     headers=headers,
#                     json=body
#                 )
#                 if response.status_code != 200:
#                     logger.error(f"Error from Azure OpenAI: {response.text}")
#                     raise HTTPException(status_code=500, detail="Error communicating with AI service")
#                 return response.json()
#             else:
#                 async with client.stream(
#                     "POST",
#                     f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version=2023-05-15",
#                     headers=headers,
#                     json=body,
#                     timeout=60.0
#                 ) as response:
#                     if response.status_code != 200:
#                         error_detail = await response.aread()
#                         logger.error(f"Error from Azure OpenAI: {error_detail}")
#                         raise HTTPException(status_code=500, detail="Error communicating with AI service")
                    
#                     async for chunk in response.aiter_bytes():
#                         if chunk:
#                             decoded = chunk.decode('utf-8')
#                             if decoded.startswith("data: "):
#                                 decoded = decoded[6:]
#                             if decoded.strip() == "[DONE]":
#                                 break
#                             try:
#                                 if decoded.strip():
#                                     yield json.loads(decoded)
#                             except json.JSONDecodeError:
#                                 logger.error(f"Error decoding JSON: {decoded}")

# # Initialize clients
# mcp_client = MCPClient()
# azure_client = AzureOpenAIClient()

# # SSE event stream helper
# async def event_generator(request: Request, chat_request: ChatRequest, token: str):
#     """Generate SSE events from chat stream"""
#     try:
#         # Get available operations from MCP server
#         operations = await mcp_client.get_available_operations(token)
#         openapi_spec = await mcp_client.get_openapi_spec(token)
        
#         # Format messages for Azure OpenAI
#         formatted_messages = [{"role": msg.role, "content": msg.content} for msg in chat_request.messages]
        
#         # Add system message with tool information
#         system_message = {
#             "role": "system",
#             "content": f"You are a helpful AI assistant that helps students plan their university schedule and tasks. " +
#                       f"You have access to the student's courses, assignments, and schedule through the following API. "
#         }
        
#         # If we have operations data, add it to system message
#         if operations and openapi_spec:
#             system_message["content"] += f"\nAvailable operations: {json.dumps(operations)}"
#             # Include tool description
#             system_message["content"] += f"\nAPI specification: {json.dumps(openapi_spec)}"
        
#         # Add page context if provided
#         if chat_request.page_context:
#             context_message = {
#                 "role": "system",
#                 "content": f"Current page context: {json.dumps(chat_request.page_context)}"
#             }
#             formatted_messages.insert(0, context_message)
        
#         formatted_messages.insert(0, system_message)
        
#         # Stream response from Azure OpenAI
#         async for chunk in azure_client.chat_completion(formatted_messages, stream=True):
#             if await request.is_disconnected():
#                 logger.info("Client disconnected")
#                 break
                
#             # Format the chunk as SSE event
#             yield json.dumps(chunk)
#     except Exception as e:
#         logger.error(f"Error in event generator: {str(e)}")
#         yield json.dumps({"error": str(e)})

# @router.post("")
# async def chat(
#     chat_request: ChatRequest,
#     current_student: Student = Depends(get_current_student),
#     db: Session = Depends(get_db),
#     request: Request = None
# ):
#     """
#     Process a chat request from the user with optional page context.
    
#     If stream=True, returns a streaming response using SSE.
#     Otherwise, returns a standard JSON response.
#     """
#     token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
#     if not token:
#         raise HTTPException(status_code=401, detail="Not authenticated")
    
#     # Handle streaming response
#     if chat_request.stream:
#         return EventSourceResponse(
#             event_generator(request, chat_request, token),
#             media_type="text/event-stream"
#         )
    
#     # Handle standard response
#     try:
#         # Get available operations from MCP server
#         operations = await mcp_client.get_available_operations(token)
#         openapi_spec = await mcp_client.get_openapi_spec(token)
        
#         # Format messages for Azure OpenAI
#         formatted_messages = [{"role": msg.role, "content": msg.content} for msg in chat_request.messages]
        
#         # Add system message with tool information
#         system_message = {
#             "role": "system",
#             "content": f"You are a helpful AI assistant that helps students plan their university schedule and tasks. " +
#                       f"You have access to the student's courses, assignments, and schedule through the following API. "
#         }
        
#         # If we have operations data, add it to system message
#         if operations and openapi_spec:
#             system_message["content"] += f"\nAvailable operations: {json.dumps(operations)}"
#             # Include tool description
#             system_message["content"] += f"\nAPI specification: {json.dumps(openapi_spec)}"
        
#         # Add page context if provided
#         if chat_request.page_context:
#             context_message = {
#                 "role": "system",
#                 "content": f"Current page context: {json.dumps(chat_request.page_context)}"
#             }
#             formatted_messages.insert(0, context_message)
        
#         formatted_messages.insert(0, system_message)
        
#         # Get response from Azure OpenAI
#         response = await azure_client.chat_completion(formatted_messages)
#         return response
        
#     except Exception as e:
#         logger.error(f"Error in chat endpoint: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/stdio")
# async def chat_stdio(
#     chat_request: ChatRequest,
#     current_student: Student = Depends(get_current_student),
#     db: Session = Depends(get_db)
# ):
#     """
#     Process a chat request and return a standard response using stdio (non-streaming).
#     This is a simplified endpoint for clients that don't support SSE.
#     """
#     # Set stream to False to ensure non-streaming response
#     chat_request.stream = False
    
#     # Reuse the main chat endpoint logic
#     return await chat(chat_request, current_student, db)