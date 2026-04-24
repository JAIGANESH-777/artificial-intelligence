import os
import json
import time
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

# Load keys & initialize clients
load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Initialize FastAPI app
app = FastAPI(title="Review Summarizer API")

# Allow the frontend to talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define what the frontend will send us
class SearchRequest(BaseModel):
    query: str

def get_reviews(query: str, target=50):
    """Scrapes Serper for reviews."""
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    
    # Get Place ID
    maps_res = requests.post("https://google.serper.dev/maps", headers=headers, json={"q": query}).json()
    if 'places' not in maps_res or not maps_res['places']:
        return None
        
    place_id = maps_res['places'][0].get('placeId')
    
    # Get Reviews
    reviews = []
    page = 1
    while len(reviews) < target:
        rev_res = requests.post("https://google.serper.dev/reviews", headers=headers, json={"placeId": place_id, "page": page}).json()
        if 'reviews' in rev_res and rev_res['reviews']:
            for r in rev_res['reviews']:
                if r.get('snippet'):
                    reviews.append(f"[{r.get('rating')} Stars]: {r.get('snippet')}")
            page += 1
        else:
            break
    return reviews[:target]

@app.post("/api/summarize")
def summarize_endpoint(request: SearchRequest):
    """The main API endpoint that the frontend calls."""
    reviews = get_reviews(request.query, target=40)
    
    if not reviews:
        raise HTTPException(status_code=404, detail="Could not find business or reviews.")
        
    reviews_text = "\n".join(reviews)
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
                        "Translate non-English to English."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant", # Using the fast model to prevent timeouts
            response_format={"type": "json_object"}
        )
        # Parse the string into actual JSON and return it
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))