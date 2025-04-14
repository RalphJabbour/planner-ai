from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow CORS so your React app can talk to your FastAPI backend
origins = [
    "http://localhost:5173",  # React development server default port
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request bodies
class User(BaseModel):
    name: str = None
    email: str
    password: str

@app.post("/signup")
async def signup(user: User):
    print(user)
    return {"message": f"User {user.email} signed up successfully."}

@app.post("/login")
async def login(user: User):
    if user.email == "test@example.com" and user.password == "password":
        return {"message": "Login successful."}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/survey-questions")
async def get_survey_questions():
    sample_questions = [
        {
            "id": 1,
            "question": "What time do you prefer to study?",
            "type": "mcq",
            "options": ["Morning", "Afternoon", "Evening", "Late night"],
        },
        {
            "id": 2,
            "question": "What time do you usually wake up?",
            "type": "time",
        },
        {
            "id": 3,
            "question": "How long can you study before needing a break?",
            "type": "mcq",
            "options": ["30 minutes", "1 hour", "2 hours", "More than 2 hours"],
        },
        {
            "id": 4,
            "question": "What's your preferred study environment?",
            "type": "mcq",
            "options": ["Library", "Coffee shop", "Home", "Outdoors"],
        },
        {
            "id": 5,
            "question": "Do you have any specific times you're unavailable to study?",
            "type": "text",
        },
    ]
    return sample_questions

@app.post("/api/survey-answers")
async def submit_survey_answers(answers: dict):
    # Here you would typically save the answers to a database
    print("Received survey answers:", answers)
    return {"message": "Survey answers submitted successfully."}

