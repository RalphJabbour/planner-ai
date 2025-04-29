"""
This file is used to run the MCP server from the root directory.
It imports and runs the MCP server from the app package.
"""
import uvicorn
from app.main import mcp_server

# Create the app using sse_app instead of asgi_app
app = mcp_server.sse_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3001, reload=True)
    # mcp_server.run()