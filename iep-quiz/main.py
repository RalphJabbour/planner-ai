from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import os, io, httpx, json, base64, mimetypes, time, random
from pdf2image import convert_from_bytes
from PIL import Image
import asyncio

# Azure OpenAI settings from env
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

app = FastAPI(title="PDF→Images Concepts Extractor")

class Idea(BaseModel):
    concept: str

class IdeasResponse(BaseModel):
    document_id: str
    ideas: list[Idea]

def pdf_to_data_urls(pdf_bytes: bytes, dpi: int = 150) -> list[str]:
    """Convert PDF pages to data URLs with lower DPI to reduce size"""
    pil_images = convert_from_bytes(pdf_bytes, dpi=dpi)
    data_urls: list[str] = []
    for img in pil_images:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        data_urls.append(f"data:image/jpeg;base64,{b64}")
    return data_urls

async def call_openai_with_retry(payload: dict, max_retries: int = 5) -> str:
    """Call Azure OpenAI with exponential backoff retry logic"""
    if not AZURE_OPENAI_KEY or not AZURE_OPENAI_ENDPOINT:
        raise HTTPException(500, "Azure OpenAI credentials not configured.")
    
    url = (
        f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/"
        f"{AZURE_OPENAI_DEPLOYMENT}/chat/completions"
        f"?api-version={AZURE_OPENAI_API_VERSION}"
    )
    headers = {"Content-Type":"application/json", "api-key":AZURE_OPENAI_KEY}
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                delay = (2 ** attempt) + random.random()
                print(f"Retry attempt {attempt+1}, waiting {delay:.2f} seconds...")
                await asyncio.sleep(delay)
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 429:
                    print(f"Rate limited (429). Attempt {attempt+1}/{max_retries}")
                    continue
                
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices") or []
                return choices[0]["message"]["content"].strip() if choices else ""
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                continue
            else:
                print(f"HTTP error: {e.response.status_code} - {e.response.text}")
                raise
        except Exception as e:
            print(f"Error calling API: {str(e)}")
            raise
    
    raise HTTPException(500, "Maximum retries exceeded due to rate limiting")

def parse_concepts(raw: str) -> list[Idea]:
    """Parses concept list into Idea objects"""
    ideas = []
    
    # Check for CONCEPT: format
    if "CONCEPT:" in raw:
        for line in raw.splitlines():
            if line.strip().startswith("CONCEPT:"):
                concept = line.split("CONCEPT:", 1)[1].strip()
                if concept:
                    ideas.append(Idea(concept=concept))
    # Check for IDEA: format
    elif "IDEA:" in raw:
        for block in raw.split("IDEA:")[1:]:
            if "DESCRIPTION:" in block:
                concept = block.split("DESCRIPTION:", 1)[0].strip()
                ideas.append(Idea(concept=concept))
            else:
                concept = block.strip().split("\n", 1)[0].strip()
                if concept:
                    ideas.append(Idea(concept=concept))
    # Simple bullet point fallback
    elif "-" in raw or "•" in raw:
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("-") or line.startswith("•"):
                concept = line[1:].strip()
                if concept:
                    ideas.append(Idea(concept=concept))
    
    return ideas

async def process_sample_pages(data_urls: list[str], max_pages: int = 6) -> list[Idea]:
    """Process only a sample of pages from the document to avoid rate limits"""
    if len(data_urls) > max_pages:
        step = max(1, len(data_urls) // max_pages)
        sampled_urls = [data_urls[i] for i in range(0, len(data_urls), step)][:max_pages]
        print(f"Sampling {len(sampled_urls)} pages out of {len(data_urls)} total pages")
    else:
        sampled_urls = data_urls
    
    all_ideas = []
    for i, url in enumerate(sampled_urls):
        try:
            print(f"Processing page {i+1}/{len(sampled_urls)}")
            
            segments = [
                {
                    "type": "text",
                    "text": "Extract 3 key concepts or ideas from this document page. Respond using:\nCONCEPT: [concept]\n"
                },
                {
                    "type": "image_url",
                    "image_url": {"url": url, "detail": "low"}
                }
            ]
            
            payload = {
                "messages": [
                    {"role": "system", "content": "You are an expert at extracting key concepts from document images."},
                    {"role": "user", "content": segments}
                ],
                "temperature": 0.5,
                "max_tokens": 300
            }
            
            if i > 0:
                await asyncio.sleep(2)
                
            raw = await call_openai_with_retry(payload)
            page_ideas = parse_concepts(raw)
            all_ideas.extend(page_ideas)
            
        except Exception as e:
            print(f"Error processing page {i+1}: {str(e)}")
    
    return all_ideas

async def synthesize_concepts(ideas: list[Idea]) -> list[Idea]:
    """Synthesize collected concepts into main document concepts"""
    if not ideas:
        return [Idea(concept="No concepts extracted")]
    
    # Create a list of concepts
    concepts_text = "\n".join(f"- {idea.concept}" for idea in ideas)
    
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "You are an expert at synthesizing concepts into main themes."
            },
            {
                "role": "user",
                "content": (
                    "Based on these concepts extracted from a document:\n\n"
                    f"{concepts_text}\n\n"
                    "Identify 3-5 main concepts or themes. List ONLY the concept names.\n"
                    "Format:\nCONCEPT: [main theme]\nCONCEPT: [main theme]\nCONCEPT: [main theme]"
                )
            }
        ],
        "temperature": 0.7,
        "max_tokens": 200
    }
    
    raw = await call_openai_with_retry(payload)
    return parse_concepts(raw)

@app.post("/extract-ideas", response_model=IdeasResponse)
async def extract_pdf_as_images(document_id: str = None, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")

    if not document_id:
        document_id = f"doc-{os.urandom(4).hex()}"

    try:
        pdf_bytes = await file.read()
        data_urls = pdf_to_data_urls(pdf_bytes)
        
        if not data_urls:
            return IdeasResponse(
                document_id=document_id,
                ideas=[Idea(concept="Empty PDF")]
            )
        
        page_ideas = await process_sample_pages(data_urls)
        
        if not page_ideas:
            return IdeasResponse(
                document_id=document_id,
                ideas=[Idea(concept="No concepts extracted")]
            )
        
        main_concepts = await synthesize_concepts(page_ideas)
        return IdeasResponse(document_id=document_id, ideas=main_concepts)
        
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        return IdeasResponse(
            document_id=document_id,
            ideas=[Idea(concept=f"Error: {str(e)}")]
        )