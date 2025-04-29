import asyncio
import os
import logging
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from openai import AzureOpenAI, RateLimitError, APIError
from pydantic import BaseModel
import json # For parsing tool arguments

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:3001")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5")) # Reduced retries for faster feedback
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "2"))
INITIAL_BACKOFF = float(os.getenv("INITIAL_BACKOFF", "1"))

# Corrected environment variable names (ensure they match your .env)
AZURE_API_BASE = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_KEY")
model = os.getenv("AZURE_OPENAI_DEPLOYMENT") # Ensure this is the deployment name
AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

# Initialize FastAPI app
app = FastAPI()

class MCPClient:
    def __init__(self):
        """Initialize the MCPClient with an exit stack and session."""
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.tools: List[Dict[str, Any]] = [] # Store tools fetched from server
        if not all([AZURE_API_BASE, AZURE_API_KEY, model, AZURE_API_VERSION]):
             logger.error("Missing Azure OpenAI environment variables!")
             # Consider raising an error or handling this state
        self.openai = AzureOpenAI(
            azure_endpoint=AZURE_API_BASE,
            api_key=AZURE_API_KEY,
            api_version=AZURE_API_VERSION
        )

    async def connect_to_server(self):
        """Connect to the MCP server using SSE and initialize the session."""
        retry_count = 0
        logger.info(f"Waiting {INITIAL_BACKOFF} seconds before first connection attempt...")
        await asyncio.sleep(INITIAL_BACKOFF)

        while retry_count < MAX_RETRIES:
            try:
                logger.info(f"Attempting to connect to MCP server at {MCP_SERVER_URL} (attempt {retry_count+1}/{MAX_RETRIES})")
                # Enter the sse_client context manager and push its exit to the stack
                read_stream, write_stream = await self.exit_stack.enter_async_context(
                    sse_client(f"{MCP_SERVER_URL}/sse")
                )
                logger.info(f"Successfully connected to SSE at {MCP_SERVER_URL}/sse")

                # Enter the ClientSession context manager and push its exit to the stack
                self.session = await self.exit_stack.enter_async_context(
                    ClientSession(read_stream, write_stream)
                )
                await self.session.initialize()

                # List available tools and store them
                response = await self.session.list_tools()
                # Store tools in a format suitable for OpenAI API if needed later
                self.tools = [
                     {"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.inputSchema}}
                     for tool in response.tools
                ]
                logger.info(f"Connected to server with tools: {[tool['function']['name'] for tool in self.tools]}")
                return  # Exit the retry loop and function on success

            except Exception as e:
                retry_count += 1
                # Clean up partially entered contexts before retrying
                logger.warning(f"Cleaning up potentially partial connection state after error: {e}")
                await self.exit_stack.aclose() # Reset stack for next attempt
                self.exit_stack = AsyncExitStack() # Recreate stack
                self.session = None # Reset session
                self.tools = [] # Clear tools

                logger.warning(f"Connection attempt {retry_count}/{MAX_RETRIES} failed: {e}")
                if retry_count < MAX_RETRIES:
                    wait_time = RETRY_DELAY * min(5, (1 + (retry_count * 0.2))) # Limit backoff multiplier
                    logger.info(f"Retrying in {wait_time:.1f} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to connect after {MAX_RETRIES} attempts.")
                    # No need to call cleanup here, finally block in endpoint will handle it
                    raise HTTPException(status_code=503, detail="Service Unavailable: Failed to connect to MCP server after multiple attempts.")

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI and MCP server tools, handling multiple tool calls."""
        if not self.session:
            raise HTTPException(status_code=500, detail="Internal Server Error: No active session with MCP server.")

        messages = [{"role": "user", "content": query}]
        final_text_parts = [] # Store parts of the final response text

        max_tool_iterations = 20 # Limit iterations to prevent infinite loops
        current_iteration = 0

        while current_iteration < max_tool_iterations:
            current_iteration += 1
            logger.info(f"--- OpenAI Call Iteration {current_iteration} ---")
            logger.debug(f"Messages sent to OpenAI: {messages}")

            try:
                response = self.openai.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=1000,
                    tools=self.tools,
                    tool_choice="auto"
                )
                logger.info("OpenAI call successful.")
                response_message = response.choices[0].message

            except RateLimitError as e:
                 logger.error(f"OpenAI Rate Limit Error: {e}")
                 raise HTTPException(status_code=429, detail=f"OpenAI API rate limit exceeded: {e}")
            except APIError as e:
                 logger.error(f"OpenAI API Error: {e}")
                 raise HTTPException(status_code=502, detail=f"OpenAI API error: {e}")
            except Exception as e:
                 logger.error(f"Error calling OpenAI API: {e}")
                 raise HTTPException(status_code=500, detail=f"Internal Server Error: Failed to call OpenAI API: {e}")

            # Append the assistant's response (whether it has tool calls or just content)
            messages.append(response_message)

            # Check if there are tool calls
            if response_message.tool_calls:
                logger.info(f"OpenAI requested tool calls: {[tc.function.name for tc in response_message.tool_calls]}")

                # Execute all tool calls requested in this iteration
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args_str = tool_call.function.arguments
                    tool_call_id = tool_call.id

                    try:
                        tool_args = json.loads(tool_args_str)
                        logger.info(f"Calling tool '{tool_name}' with args: {tool_args}")

                        # Call the actual tool via MCP session
                        tool_result = await self.session.call_tool(tool_name, tool_args)
                        logger.info(f"Tool '{tool_name}' executed successfully.")
                        tool_content = tool_result.content # Get the content returned by the tool

                        # Prepare the content string for the OpenAI message list.
                        content_str = ""
                        try:
                            # Serialize the actual tool result data to a JSON string.
                            content_str = json.dumps(tool_content)
                        except TypeError as json_error:
                            logger.error(f"Tool '{tool_name}' result could not be JSON serialized directly: {json_error}. Content type: {type(tool_content)}. Content: {tool_content}")
                            content_str = json.dumps({"error": "Tool returned non-serializable content", "details": str(tool_content)})

                        # Append the tool result message for the next OpenAI call
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": content_str # Pass the JSON string representation
                        })
                        # Optionally add a user-facing note about tool execution
                        # final_text_parts.append(f"[Tool '{tool_name}' executed.]")

                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode JSON arguments for tool {tool_name}: {tool_args_str}")
                        # final_text_parts.append(f"[Error: Could not understand arguments for tool '{tool_name}']")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": json.dumps({"error": f"Invalid arguments format received: {tool_args_str}"})
                        })
                    except Exception as e:
                        logger.error(f"Error processing tool call for '{tool_name}': {e}", exc_info=True)
                        # final_text_parts.append(f"[Error executing tool '{tool_name}']")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "content": json.dumps({"error": f"Error executing tool: {e}"})
                        })
                # Continue the loop to call OpenAI again with the tool results
                continue

            else:
                # No tool calls in the response, this is the final answer
                logger.info("OpenAI response has no tool calls. Finishing.")
                if response_message.content:
                    final_text_parts.append(response_message.content)
                else:
                     # Handle cases where the final response might be empty after tool use
                     if not final_text_parts: # If nothing else was added
                         final_text_parts.append("[Processing complete, but no final text content generated.]")
                break # Exit the loop

        if current_iteration >= max_tool_iterations:
             logger.warning(f"Reached maximum tool iteration limit ({max_tool_iterations}). Returning intermediate results.")
             # Optionally add a message indicating the limit was reached
             final_text_parts.append("[Reached maximum processing iterations. The response might be incomplete.]")


        return "\n".join(final_text_parts) # Join all parts collected

    async def cleanup(self):
        """Clean up resources managed by the exit stack."""
        logger.info("Cleaning up MCPClient resources...")
        await self.exit_stack.aclose()
        logger.info("MCPClient cleanup complete.")


class ChatRequest(BaseModel):
    student_id: str
    query: str

@app.post("/chat")
async def chat(request: ChatRequest):
    """Handle chat requests by connecting, processing, and cleaning up."""
    client = MCPClient()
    try:
        # Connect to the server first
        await client.connect_to_server()
        # If connection successful, process the query
        response_text = await client.process_query(request.query)
        return JSONResponse(content={"response": response_text})
    except HTTPException as e:
        # Log the HTTPException details and re-raise
        logger.error(f"HTTPException in /chat endpoint: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        # Catch any other unexpected errors
        logger.exception("Unexpected error in /chat endpoint", exc_info=e) # Log full traceback
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred.")
    finally:
        # Ensure cleanup is always called
        await client.cleanup()