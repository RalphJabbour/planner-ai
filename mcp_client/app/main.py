import asyncio
import os
import logging
import time
import sys

from dotenv import load_dotenv
import httpx

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:3001")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "30"))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "2"))
INITIAL_BACKOFF = float(os.getenv("INITIAL_BACKOFF", "1"))  # Start with a short delay

async def run_client():
    retry_count = 0
    
    # Initial backoff to give server time to start
    logger.info(f"Waiting {INITIAL_BACKOFF} seconds before first connection attempt...")
    await asyncio.sleep(INITIAL_BACKOFF)
    
    while retry_count < MAX_RETRIES:
        try:
            logger.info(f"Attempting to connect to MCP server at {MCP_SERVER_URL} (attempt {retry_count+1}/{MAX_RETRIES})")
            
            # Use the sse_client as a context manager directly within the retry loop
            async with sse_client(f"{MCP_SERVER_URL}/sse") as (read_stream, write_stream):
                logger.info(f"Successfully connected to SSE at {MCP_SERVER_URL}/sse")
                
                # Once connected, proceed with the session
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    logger.info("↔ Handshake complete")

                    # List tools
                    tools_result = await session.list_tools()
                    tools = tools_result.tools
                    logger.info(f"Found {len(tools)} tools:")
                    for idx, tool in enumerate(tools, start=1):
                        logger.info(f" {idx}. {tool.name}: {tool.description}")

                    # Test the greeting resource
                    try:
                        greeting = await session.read_resource("greeting://ChatGPT")
                        logger.info(f"greeting://ChatGPT → {greeting}")
                    except Exception as e:
                        logger.error(f"Error calling greeting resource: {e}")
                
                logger.info("Session closed.")
                return  # Exit the retry loop on success
                
        except Exception as e:
            retry_count += 1
            # Check for ExceptionGroup or TaskGroup in the error message
            error_str = str(e)
            is_connection_error = (
                "ConnectError" in error_str or 
                "Connection refused" in error_str or
                "TaskGroup" in error_str or 
                "ExceptionGroup" in error_str
            )
            
            if is_connection_error:
                logger.warning(f"Connection attempt {retry_count}/{MAX_RETRIES} failed: Server not ready")
            else:
                logger.warning(f"Connection attempt {retry_count}/{MAX_RETRIES} failed: {e}")
            
            if retry_count < MAX_RETRIES:
                wait_time = RETRY_DELAY * min(10, (1 + (retry_count * 0.2)))  # Progressive backoff, max 10x
                logger.info(f"Retrying in {wait_time:.1f} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"Failed to connect after {MAX_RETRIES} attempts.")
                sys.exit(1)  # Exit with error code

if __name__ == "__main__":
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
