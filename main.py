import os
import json
import time
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

# Load keys & initialize clients
load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI(title="Review Summarizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for Data Validation ---
class SearchRequest(BaseModel):
    query: str

class SummarizeRequest(BaseModel):
    place_id: str

# --- The Front Door ---
@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

# --- Endpoint 1: Search for Locations ---
@app.post("/api/search_places")
def search_places(request: SearchRequest):
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    maps_res = requests.post("https://google.serper.dev/maps", headers=headers, json={"q": request.query}).json()
    
    if 'places' not in maps_res or not maps_res['places']:
        raise HTTPException(status_code=404, detail="Could not find any businesses matching that query.")
        
    # Grab up to the top 3 places
    top_3 = maps_res['places'][:3]
    
    # Clean up the data to send to the frontend
    clean_places = []
    for place in top_3:
        clean_places.append({
            "place_id": place.get('placeId'),
            "name": place.get('title', 'Unknown Location'),
            "address": place.get('address', 'No address provided'),
            "rating": place.get('rating', 'N/A'),
            "total_ratings": place.get('ratingCount', 0)
        })
        
    return {"places": clean_places}

# --- Endpoint 2: Fetch Reviews and Summarize ---
@app.post("/api/summarize")
def summarize_endpoint(request: SummarizeRequest):
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    
    reviews = []
    page = 1
    target = 30 # Keeping it at 30 to prevent Groq TPM errors
    
    # We already have the place_id, so we go straight to fetching reviews!
    while len(reviews) < target:
        rev_res = requests.post("https://google.serper.dev/reviews", headers=headers, json={"placeId": request.place_id, "page": page}).json()
        if 'reviews' in rev_res and rev_res['reviews']:
            for r in rev_res['reviews']:
                snippet = r.get('snippet')
                if snippet:
                    short_snippet = snippet[:250] + "..." if len(snippet) > 250 else snippet
                    reviews.append(f"[{r.get('rating')} Stars]: {short_snippet}")
            page += 1
            time.sleep(1)
        else:
            break
            
    if not reviews:
        raise HTTPException(status_code=404, detail="Not enough written reviews to analyze.")
        
    reviews_text = "\n".join(reviews[:target])
    prompt = f"Extract the top 5 pros and cons as JSON from these reviews:\n{reviews_text}"
    
    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "You are a strict data analyst. Extract the top 5 pros and cons based ONLY on the provided reviews. "
                        "Do NOT invent, assume, or hallucinate any information. If a pro or con is not explicitly mentioned "
                        "in the text, do not include it. Output strict JSON with 'pros' and 'cons' arrays. "
                        "CRITICAL: The arrays MUST contain plain text strings only (e.g., [\"pro 1\", \"pro 2\"]). Do NOT use nested objects. "
                        "Translate non-English to English."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))