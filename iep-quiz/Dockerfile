FROM python:3.12-slim

# 1. Install native deps for pdfplumber & cffi
RUN apt-get update \
 && apt-get install -y poppler-utils build-essential libffi-dev \
 && rm -rf /var/lib/apt/lists/*

# 2. Install uv via pip so 'uv' is on PATH
RUN pip install --no-cache-dir uv

WORKDIR /app

# 3. Copy manifest & lock
COPY pyproject.toml uv.lock ./

# 4. Install all deps
RUN uv sync --frozen --no-dev

# 5. Copy service code & test PDF
COPY main.py sample.pdf ./

EXPOSE 9001

# 6. Run via uv
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9001"]
