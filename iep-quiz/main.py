from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import pdfplumber, io, os, httpx, json

HF_API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"

HF_API_TOKEN = os.environ.get("HF_API_TOKEN") # Read token from environment

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
    if not HF_API_TOKEN:
        raise HTTPException(status_code=500, detail="Hugging Face API token not configured.")
    
    max_chunk_size = 1000
    text_chunks = [text[i:i+max_chunk_size] for i in range(0, len(text), max_chunk_size)]

    generated_questions = []

    headers = {"Authorization": f"Bearer {HF_API_TOKEN}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        #Generate one question per chunk (example) (CAN CHANGE THIS LOGIC LATER ON)
        for chunk in text_chunks[:3]:
            qg_payload = {
                "inputs": f"Generate a question based on the following text: \n\n{chunk}",
                "parameters" : {"max_length": 50, "num_return_sequences": 1}
            }

            try:
                response_qg = await client.post(HF_API_URL, headers=headers, json=qg_payload)
                response_qg.raise_for_status() # Raise an exception for bad status codes
                qg_result = response_qg.json()

                if not qg_result or not isinstance(qg_result, list) or not qg_result[0].get("generated_text"):
                    print(f"Warining: Unexpected QG API response format: {qg_result}")
                    continue # Skip this chunk if the response is unexpected

                generated_question_text = qg_result[0]["generated_text"].strip()

                # --- 2. Generate Answer for the generated question ---
                qa_payload = {
                    "inputs": {
                        "question": generated_question_text,
                        "context": chunk #use the same chunk as context
                    },
                    "task": "question-answering" #Specify task for QA models if needed, T5 might infer
                }
                # Note: QA models might not be needed here, we can use the T5 model for this task
                response_qa = await client.post(HF_API_URL, headers=headers, json=qa_payload)
                response_qa.raise_for_status()
                qa_result = response_qa.json()

                # T5 QA response structure might differ, adjust parsing as needed
                # Example assuming a structure like : {"answer": "the answer"} or {"generated_text": "the answer"}
                generated_answer = qa_result.get("answer") or qa_result.get("generated_text", "N/A")

                if generated_question_text:
                    generated_questions.append(
                        QuizQuestion(question=generated_question_text, answer=generated_answer.strip())
                    )
            except httpx.HTTPStatusError as e:
                print(f"Error generating question/answer for chunk: {e.response.status_code} - {e.response.text}")
            except httpx.RequestError as e:
                 print(f"Network error calling Hugging Face API: {e}")
            except json.JSONDecodeError:
                 print(f"Error decoding JSON response from API.")
            except Exception as e:
                 print(f"An unexpected error occurred: {e}")

        if not generated_questions:
            # Fallback or raise error if no questions were generated
            return [QuizQuestion(question="Could not generate questions from the provided text.", answer="N/A")]

        return generated_questions    


@app.post("/generate-quiz", response_model=QuizResponse)
async def generate_quiz(student_id: int, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files allowed.")
    data = await file.read()
    text = pdf_to_text(data)
    questions = await generate_questions(text)
    quiz_id = f"quiz-{student_id}-{os.urandom(4).hex()}"
    return QuizResponse(quiz_id=quiz_id, questions=questions)
