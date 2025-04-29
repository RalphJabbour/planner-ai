# Use the official Python slim image
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y curl build-essential && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy only dependency files first
COPY pyproject.toml ./

# Install Python dependencies with uv
RUN uv sync

# Copy the rest of the project files
COPY . .

# Set default environment variable for the MCP server URL
ENV MCP_SERVER_URL="http://mcp-server:3001"

# Run the client
CMD ["uv", "run", "main.py"]