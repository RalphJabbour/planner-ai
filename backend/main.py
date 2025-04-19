"""
This file is used to run the application from the root directory.
It simply imports and runs the FastAPI app from the app package.
"""
import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

