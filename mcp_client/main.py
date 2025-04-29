"""
This file is the entry point for the MCP client.
It imports and runs the client from the app package.
"""
import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=3002, reload=True)

