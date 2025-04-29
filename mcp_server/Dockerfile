# Use the official Python slim image
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update \
 && apt-get install -y curl build-essential \
 && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# ensure uv itself is on PATH
ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy only dependency files first
COPY pyproject.toml ./

# Install Python dependencies with uv (creates .venv/)
RUN uv sync

# Expose the venv’s bin so ‘mcp’ is found
ENV PATH="/app/.venv/bin:${PATH}"

# Copy the rest of your code
COPY . .

EXPOSE 3001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3001"]
