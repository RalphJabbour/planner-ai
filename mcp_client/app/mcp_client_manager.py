# mcp_client_manager.py
import asyncio
from typing import Dict
from mcp.client.sse     import sse_client
from mcp.client.session import ClientSession

# In-memory store: chat_id → (read, write, session)
CLIENTS: Dict[str, ClientSession] = {}

async def get_or_create_client(chat_id: str, server_url: str):
    if chat_id in CLIENTS:
        return CLIENTS[chat_id]
    # 1) Open SSE transport (trailing slash to avoid redirect)
    read, write = await sse_client(f"{server_url}/mcp/")  # ––– :contentReference[oaicite:3]{index=3}  
    # 2) Initialize MCP session
    session = await ClientSession(read, write).initialize() # returns self :contentReference[oaicite:4]{index=4}  
    CLIENTS[chat_id] = session
    return session
