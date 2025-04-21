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

app = FastAPI(title="PDF→Images Ideas Extractor")

class Idea(BaseModel):
    concept: str
    description: str

class IdeasResponse(BaseModel):
    document_id: str
    ideas: list[Idea]

def pdf_to_data_urls(pdf_bytes: bytes, dpi: int = 150) -> list[str]:
    """Convert PDF pages to data URLs with lower DPI to reduce size"""
    pil_images = convert_from_bytes(pdf_bytes, dpi=dpi)
    data_urls: list[str] = []
    for img in pil_images:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)  # Use JPEG with lower quality
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
            # Add initial delay before first attempt to avoid immediate rate limiting
            if attempt > 0:
                # Exponential backoff with jitter: 2^attempt + random(0-1s)
                delay = (2 ** attempt) + random.random()
                print(f"Retry attempt {attempt+1}, waiting {delay:.2f} seconds...")
                await asyncio.sleep(delay)
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 429:
                    # Specific handling for rate limits
                    print(f"Rate limited (429). Attempt {attempt+1}/{max_retries}")
                    continue
                
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices") or []
                return choices[0]["message"]["content"].strip() if choices else ""
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                # Already handled above, continue to next retry
                continue
            else:
                print(f"HTTP error: {e.response.status_code} - {e.response.text}")
                raise
        except Exception as e:
            print(f"Error calling API: {str(e)}")
            raise
    
    raise HTTPException(500, "Maximum retries exceeded due to rate limiting")

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

async def process_sample_pages(data_urls: list[str], max_pages: int = 6) -> list[Idea]:
    """Process only a sample of pages from the document to avoid rate limits"""
    if len(data_urls) > max_pages:
        # Take evenly distributed samples if document is large
        step = max(1, len(data_urls) // max_pages)
        sampled_urls = [data_urls[i] for i in range(0, len(data_urls), step)][:max_pages]
        print(f"Sampling {len(sampled_urls)} pages out of {len(data_urls)} total pages")
    else:
        sampled_urls = data_urls
    
    # Process one page at a time to avoid rate limits
    all_ideas = []
    for i, url in enumerate(sampled_urls):
        try:
            print(f"Processing page {i+1}/{len(sampled_urls)}")
            
            # Extract ideas from a single page
            segments = [
                {
                    "type": "text",
                    "text": "Extract 3 key concepts or ideas from this document page. Respond using:\nIDEA: [concept]\nDESCRIPTION: [brief description]\n\n"
                },
                {
                    "type": "image_url",
                    "image_url": {"url": url, "detail": "low"}  # Use lower detail to reduce tokens
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
            
            # Allow some time between API calls even with retry logic
            if i > 0:
                await asyncio.sleep(2)
                
            raw = await call_openai_with_retry(payload)
            page_ideas = parse_ideas(raw)
            all_ideas.extend(page_ideas)
            
        except Exception as e:
            print(f"Error processing page {i+1}: {str(e)}")
    
    return all_ideas

async def synthesize_ideas(ideas: list[Idea]) -> list[Idea]:
    """Synthesize collected ideas into main document themes"""
    if not ideas:
        return [Idea(concept="No Content", description="No ideas could be extracted from the document.")]
    
    # Create a summary of all extracted ideas
    all_ideas_text = "\n".join(f"- {idea.concept}: {idea.description}" for idea in ideas)
    
    payload = {
        "messages": [
            {
                "role": "system",
                "content": "You are an expert at synthesizing concepts into main themes."
            },
            {
                "role": "user",
                "content": (
                    "Based on these extracted points from a document:\n\n"
                    f"{all_ideas_text}\n\n"
                    "Identify 3-5 main ideas or themes. Respond using:\n"
                    "IDEA: [main theme]\n"
                    "DESCRIPTION: [comprehensive description of this theme]"
                )
            }
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    raw = await call_openai_with_retry(payload)
    return parse_ideas(raw)

@app.post("/extract-ideas", response_model=IdeasResponse)
async def extract_pdf_as_images(document_id: str = None, file: UploadFile = File(...)):
    # Validate PDF
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted.")

    # Generate document_id if needed
    if not document_id:
        document_id = f"doc-{os.urandom(4).hex()}"

    try:
        pdf_bytes = await file.read()
        # Convert PDF to images with lower quality to reduce size
        data_urls = pdf_to_data_urls(pdf_bytes)
        
        if not data_urls:
            return IdeasResponse(
                document_id=document_id,
                ideas=[Idea(concept="Empty PDF", description="No pages could be extracted from the PDF.")]
            )
        
        # Process a sample of pages to avoid rate limits
        page_ideas = await process_sample_pages(data_urls)
        
        if not page_ideas:
            return IdeasResponse(
                document_id=document_id,
                ideas=[Idea(concept="Extraction Failed", description="No ideas could be extracted from the document pages.")]
            )
        
        # Synthesize the main ideas
        main_ideas = await synthesize_ideas(page_ideas)
        return IdeasResponse(document_id=document_id, ideas=main_ideas)
        
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        return IdeasResponse(
            document_id=document_id,
            ideas=[Idea(concept="Processing Error", description=f"An error occurred: {str(e)}")]
        )