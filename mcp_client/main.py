"""
This file is the entry point for the MCP client.
It imports and runs the client from the app package.
"""
import asyncio
from app.main import run_client

if __name__ == "__main__":
    asyncio.run(run_client())