from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import os, io, httpx, json, base64, mimetypes
from pdf2image import convert_from_bytes  # pip install pdf2image
from PIL import Image                        # installed as a dependency of pdf2image

# Azure OpenAI settings from env
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")   # e.g. "gpt-4o-mini"
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")  # e.g. "2024-02-15-preview"

app = FastAPI(title="PDF→Images Ideas Extractor")

class Idea(BaseModel):
    concept: str
    description: str

class IdeasResponse(BaseModel):
    document_id: str
    ideas: list[Idea]

def pdf_to_data_urls(pdf_bytes: bytes, dpi: int = 200) -> list[str]:
    """
    Convert all PDF pages to PIL images, then to base64 data URLs.
    Requires poppler installed on the system for pdf2image to work.
    """
    pil_images = convert_from_bytes(pdf_bytes, dpi=dpi)
    data_urls: list[str] = []
    for img in pil_images:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        data_urls.append(f"data:image/png;base64,{b64}")
    return data_urls

async def call_openai(payload: dict) -> str:
    """Send chat/completions request to Azure OpenAI and return assistant content."""
    if not AZURE_OPENAI_KEY or not AZURE_OPENAI_ENDPOINT:
        raise HTTPException(500, "Azure OpenAI credentials not configured.")
    url = (
        f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/"
        f"{AZURE_OPENAI_DEPLOYMENT}/chat/completions"
        f"?api-version={AZURE_OPENAI_API_VERSION}"
    )
    headers = {"Content-Type":"application/json", "api-key":AZURE_OPENAI_KEY}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
    choices = data.get("choices") or []
    return choices[0]["message"]["content"].strip() if choices else ""

def parse_ideas(raw: str) -> list[Idea]:
    """Parses "IDEA: X\nDESCRIPTION: Y" blocks into Idea objects."""
    ideas: list[Idea] = []
    for block in raw.split("IDEA:")[1:]:
        if "DESCRIPTION:" not in block:
            continue
        concept, desc = block.split("DESCRIPTION:", 1)
        concept = concept.strip()
        description = " ".join(line.strip() for line in desc.strip().splitlines())
        ideas.append(Idea(concept=concept, description=description))
    return ideas

async def extract_from_image_batch(
    data_urls: list[str],
    ideas_per_image: int = 2
) -> list[Idea]:
    """
    Send one batch of up to N image URLs to the vision model,
    extracting a fixed number of ideas per image.
    """
    # Build mixed content: text + image_url segments
    segments = []
    segments.append({
        "type":"text",
        "text":(
            f"Extract exactly {ideas_per_image} main ideas from *each* of the following "
            f"{len(data_urls)} images. Respond using:\n"
            "IDEA: [concept]\nDESCRIPTION: [brief description]\n\n"
        )
    })
    for url in data_urls:
        segments.append({
            "type":"image_url",
            "image_url": {"url": url, "detail": "auto"}
        })

    payload = {
        "messages": [
            {
                "role":"system",
                "content":"You are an expert at extracting main ideas from images."
            },
            {
                "role":"user",
                "content": segments
            }
        ],
        "temperature": 0.5,
        "max_tokens": 500
    }

    raw = await call_openai(payload)
    return parse_ideas(raw)

@app.post("/extract-ideas", response_model=IdeasResponse)
async def extract_pdf_as_images(document_id: str = None, file: UploadFile = File(...)):
    # Validate PDF
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")

    # Generate document_id if needed
    if not document_id:
        document_id = f"doc-{os.urandom(4).hex()}"

    pdf_bytes = await file.read()
    # Convert PDF → list of data‑URLs
    data_urls = pdf_to_data_urls(pdf_bytes)

    # Batch pages (e.g. 3 pages per batch)
    batch_size = 3
    ideas: list[Idea] = []
    for i in range(0, len(data_urls), batch_size):
        batch = data_urls[i : i + batch_size]
        try:
            batch_ideas = await extract_from_image_batch(batch)
            ideas.extend(batch_ideas)
        except Exception as e:
            print(f"Warning processing pages {i}-{i+len(batch)-1}: {e}")
        # Optional: break after first few batches to cap cost

    if not ideas:
        ideas = [Idea(concept="No ideas extracted",
                      description="Could not extract ideas from the PDF images.")]

    return IdeasResponse(document_id=document_id, ideas=ideas)
