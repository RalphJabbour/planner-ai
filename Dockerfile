# Use the official Python slim image
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y curl build-essential && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# ENV PATH="/root/.cargo/bin:${PATH}"
ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy only dependency files first
COPY pyproject.toml uv.lock* ./

# Install Python dependencies with uv using the lock file
RUN uv sync --frozen --no-dev

# Copy the rest of the project files
COPY . .

# Expose the port FastAPI will run on
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
