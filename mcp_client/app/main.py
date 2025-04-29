import asyncio
import os
import logging

from dotenv import load_dotenv

from mcp.client.session import ClientSession
from mcp.client.sse     import sse_client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:3001")

async def run_client():
    # 1) Open an SSE connection to /sse and get the paired streams
    async with sse_client(f"{MCP_SERVER_URL}/sse") as (read_stream, write_stream):
        logger.info(f"Connected to SSE at {MCP_SERVER_URL}/sse")
        
        # 2) Wrap those streams in a ClientSession
        async with ClientSession(read_stream, write_stream) as session:
            # Handshake: initialize + notifications/initialized happens under the hood
            await session.initialize()
            logger.info("↔ Handshake complete")

            # 3) List tools
            tools_result = await session.list_tools()       # returns ListToolsResult
            tools = tools_result.tools                      # extract the actual list
            logger.info(f"Found {len(tools)} tools:")
            for idx, tool in enumerate(tools, start=1):
                logger.info(f" {idx}. {tool.name}: {tool.description}")

            # 4) (Optional) Test the greeting resource
            try:
                greeting = await session.read_resource("greeting://ChatGPT")
                logger.info(f"greeting://ChatGPT → {greeting}")
            except Exception as e:
                logger.error(f"Error calling greeting resource: {e}")

        logger.info("Session closed.")

if __name__ == "__main__":
    asyncio.run(run_client())
