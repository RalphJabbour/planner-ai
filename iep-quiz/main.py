from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import pdfplumber, io, os, httpx, json

AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")  # e.g., "https://your-resource.openai.azure.com"
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT")  # e.g., "gpt-35-turbo"
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION")  # e.g., "2023-05-15"

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
    if not AZURE_OPENAI_KEY or not AZURE_OPENAI_ENDPOINT:
        raise HTTPException(status_code=500, detail="Azure OpenAI API credentials not configured.")
    
    max_chunk_size = 1000
    text_chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]

    generated_questions: list[QuizQuestion] = []

    api_url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"

    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_KEY
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        for chunk in text_chunks[:3]:
            try:
                qg_payload = {
                    "messages": [
                        {"role": "system", "content": "You are a quiz creator specializing in multiple-choice questions."},
                        {"role": "user", "content": (
                            "Create a multiple-choice question based on the following text. "
                            "Respond only in this format:\n"
                            "QUESTION: [the question]\n"
                            "OPTIONS:\n"
                            "A. [option1]\n"
                            "B. [option2]\n"
                            "C. [option3]\n"
                            "D. [option4]\n"
                            "CORRECT: [letter of correct answer]\n\n" + chunk
                        )}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 250
                }

                response_qg = await client.post(api_url, headers=headers, json=qg_payload)
                response_qg.raise_for_status()
                result = response_qg.json()

                choices = result.get("choices") or []
                if not choices:
                    print(f"Warning: Unexpected QG API response format: {result}")
                    continue

                mcq_text = choices[0]["message"]["content"].strip()

                # Initialize parsed values
                question_text = None
                options = []
                correct_answer = None

                # Parse question
                if "QUESTION:" in mcq_text and "OPTIONS:" in mcq_text:
                    question_segment = mcq_text.split("QUESTION:", 1)[1]
                    question_text = question_segment.split("OPTIONS:", 1)[0].strip()

                # Parse options
                if "OPTIONS:" in mcq_text and "CORRECT:" in mcq_text:
                    options_segment = mcq_text.split("OPTIONS:", 1)[1].split("CORRECT:", 1)[0].strip()
                    for line in options_segment.splitlines():
                        line = line.strip()
                        if line and line[0] in ('A', 'B', 'C', 'D') and line[1] == '.':
                            options.append(line[2:].strip())

                # Parse correct answer
                if "CORRECT:" in mcq_text:
                    correct_segment = mcq_text.split("CORRECT:", 1)[1].strip()
                    if correct_segment:
                        letter = correct_segment[0].upper()
                        idx = ord(letter) - ord('A')
                        if 0 <= idx < len(options):
                            correct_answer = options[idx]

                if question_text and options and correct_answer:
                    generated_questions.append(
                        QuizQuestion(question=question_text, options=options, answer=correct_answer)
                    )
                else:
                    print(f"Failed to parse MCQ components from: {mcq_text}")

            except httpx.HTTPStatusError as e:
                print(f"Error generating MCQ for chunk: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                print(f"Parsing or network error: {e}")

    if not generated_questions:
        return [QuizQuestion(question="Could not generate questions from the provided text.", answer="N/A")]

    return generated_questions


@app.post("/generate-quiz", response_model=QuizResponse)
async def generate_quiz(student_id: int, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed.")
    data = await file.read()
    text = pdf_to_text(data)
    questions = await generate_questions(text)
    quiz_id = f"quiz-{student_id}-{os.urandom(4).hex()}"
    return QuizResponse(quiz_id=quiz_id, questions=questions)
