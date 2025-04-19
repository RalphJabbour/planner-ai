from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import pdfplumber, io, os

app = FastAPI(title="Quiz Generation IEP")

class QuizQuestion(BaseModel):
    question: str
    options: list[str] | None = None
    answer: str | None = None

class QuizResponse(BaseModel):
    quiz_id: str
    questions: list[QuizQuestion]

def pdf_to_text(pdf_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

async def generate_questions(text: str) -> list[QuizQuestion]:
    # TODO: wire in real API calls here
    return [
        QuizQuestion(question="What is 2+2?", options=["3","4","5"], answer="4"),
        QuizQuestion(question="Define integral.", answer="An integral is…"),
    ]

@app.post("/generate-quiz", response_model=QuizResponse)
async def generate_quiz(student_id: int, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files allowed.")
    data = await file.read()
    text = pdf_to_text(data)
    questions = await generate_questions(text)
    quiz_id = f"quiz-{student_id}-{os.urandom(4).hex()}"
    return QuizResponse(quiz_id=quiz_id, questions=questions)
