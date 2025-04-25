# """
# This file is used to run the MCP server separately.
# """

# from app.main import app
# from fastapi_mcp import FastApiMCP
# from fastapi.security import HTTPBearer
# from fastapi import Depends
# from fastapi_mcp import AuthConfig
# from app.auth.token import get_current_student
# from fastapi import FastAPI
# import re

# # Define excluded paths - we don't want to expose the chat endpoint via MCP
# exclude_tags = ["chat"]

# # Create the MCP instance
# mcp = FastApiMCP(
#     app,
#     name = "FastAPI-MCP",
#     description = "FastAPI-MCP server providing tools to the chatbot of planner-ai",
#     # auth_config=AuthConfig(
#     #     dependencies=[Depends(get_current_student)],
#     # ),
#     describe_full_response_schema=True,
#     describe_all_responses=True,
#     exclude_tags=exclude_tags # Exclude the chat endpoint
# )



# mcp_app = FastAPI()
# mcp.mount(mcp_app)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(mcp_app, host="0.0.0.0", port=8001)