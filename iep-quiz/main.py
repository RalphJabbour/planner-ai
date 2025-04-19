from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import pdfplumber, io, os, httpx, json

AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")  # e.g., "https://your-resource.openai.azure.com"
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT")  # e.g., "gpt-35-turbo" or your deployment name
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION")  # Update to your API version

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

    generated_questions = []

    # API URL with deployment name and version
    api_url = f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"

    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_KEY
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Generate questions from each chunk
        for chunk in text_chunks[:3]:
            try:
                # Generate question
                qg_payload = {
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that creates quiz questions."},
                        {"role": "user", "content": f"Generate a clear, concise question based on the following text: \n\n{chunk}"}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 50
                }

                response_qg = await client.post(api_url, headers=headers, json=qg_payload)
                response_qg.raise_for_status()
                qg_result = response_qg.json()

                if not qg_result.get("choices") or len(qg_result["choices"]) == 0:
                    print(f"Warning: Unexpected QG API response format: {qg_result}")
                    continue

                generated_question_text = qg_result["choices"][0]["message"]["content"].strip()

                # Generate answer
                qa_payload = {
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that answers questions accurately."},
                        {"role": "user", "content": f"Answer this question based on the following context: \nQuestion: {generated_question_text}\nContext: {chunk}"}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 100
                }

                response_qa = await client.post(api_url, headers=headers, json=qa_payload)
                response_qa.raise_for_status()
                qa_result = response_qa.json()

                if not qa_result.get("choices") or len(qa_result["choices"]) == 0:
                    generated_answer = "N/A"
                else:
                    generated_answer = qa_result["choices"][0]["message"]["content"].strip()

                if generated_question_text:
                    generated_questions.append(
                        QuizQuestion(question=generated_question_text, answer=generated_answer)
                    )
            except httpx.HTTPStatusError as e:
                print(f"Error generating question/answer for chunk: {e.response.status_code} - {e.response.text}")
            except httpx.RequestError as e:
                print(f"Network error calling Azure OpenAI API: {e}")
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
