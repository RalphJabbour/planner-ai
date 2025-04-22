# OR-Tools Scheduling API

This project provides two main scheduling APIs using FastAPI + Google OR-Tools:

## Project Structure
```
or_tools/
├── optimizer.py        # Core OR-Tools logic
├── schemas.py          # Pydantic models
├── service.py          # API logic handler
├── router.py           # FastAPI route handlers
├── utils.py            # Helper functions
main.py                 # FastAPI entry
Dockerfile              # Run with Docker
```

## API Endpoints

### `POST /schedule/generate`
Takes a 2-week schedule input with fixed and flexible obligations.
Returns optimized list of calendar events.

### `POST /schedule/update`
Takes an old schedule and new tasks/obligations to re-optimize.
Returns an updated list of calendar events.

## How to Run

**Locally**:
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

**With Docker**:
```bash
docker build -t scheduler-app .
docker run -p 8000:8000 scheduler-app
```

Then open http://localhost:8000/docs to access Swagger UI.

## Requirements
- Python 3.11
- OR-Tools
- FastAPI
- Uvicorn