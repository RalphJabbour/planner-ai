# OR-Tools Scheduling API

This project provides two main scheduling APIs using FastAPI + Google OR-Tools:

## Project Structure

or_tools/
├── __init__.py
│   └── (empty – package marker)
│
├── main.py
│   └── FastAPI entry‑point (includes scheduler router)
│
├── optimizer.py
│   └── All OR‑Tools logic with rich comments
│
├── router.py
│   └── REST endpoints that call service functions
│
├── service.py
│   └── Thin layer that orchestrates I/O, DB hooks and optimizer
│
├── schemas.py
│   └── Pydantic models for requests / responses / preferences
│
├── utils.py
│   └── Generic helpers (datetime, slot generation etc.)
│
└── README.md
    └── Project overview & setup guide


Run locally:
```bash
pip install fastapi "uvicorn[standard]" ortools pydantic
uvicorn or_tools.main:app --reload
```
Then open http://localhost:8000/docs.

## Files
* **optimizer.py** – heavy lifting (constraint model)
* **schemas.py**  – Pydantic models (API contracts)
* **service.py**  – Orchestrates DB ↔ solver
* **router.py**   – FastAPI endpoints
* **main.py**     – application entry point

## Integration points (TODO)
* Persist / delete events in **service.py** where marked.
* Replace in‑memory dicts with your **SQLAlchemy models**.
* Inject user preferences from the *behavioural agent* before calling `/generate`.
```