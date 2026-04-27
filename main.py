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
from tool import parse_user_request

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

class SearchRequest(BaseModel):
    query: str

class SummarizeRequest(BaseModel):
    place_id: str

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

# @app.post("/api/search_places")
# def search_places(request: SearchRequest):
#     # 1. Use the tool to validate the intent
#     plan = parse_user_request(request.query)
    
#     # 2. If the tool says it's incomplete or unrelated, stop and tell the user
#     if plan["status"] != "success":
#         raise HTTPException(status_code=400, detail=plan["message"])

#     # 3. Use the improved search_query from the tool
#     headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
#     maps_res = requests.post(
#         "https://google.serper.dev/maps", 
#         headers=headers, 
#         json={"q": plan["search_query"]} # Use the filtered query
#     ).json()

#     headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
#     maps_res = requests.post("https://google.serper.dev/maps", headers=headers, json={"q": request.query}).json()
    
#     if 'places' not in maps_res or not maps_res['places']:
#         raise HTTPException(status_code=404, detail="Could not find any businesses matching that query.")
        
#     top_3 = maps_res['places'][:3]
    
#     clean_places = []
#     for place in top_3:
#         clean_places.append({
#             "place_id": place.get('placeId'),
#             "name": place.get('title', 'Unknown Location'),
#             "address": place.get('address', 'No address provided'),
#             "rating": place.get('rating', 'N/A'),
#             "total_ratings": place.get('ratingCount', 0)
#         })
        
#     return {"places": clean_places}

@app.post("/api/search_places")
def search_places(request: SearchRequest):
    plan = parse_user_request(request.query)
    
    if plan["status"] != "success":
        raise HTTPException(status_code=400, detail=plan["message"])

    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    maps_res = requests.post(
        "https://google.serper.dev/maps", 
        headers=headers, 
        json={"q": plan["search_query"]}
    ).json()
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    maps_res = requests.post("https://google.serper.dev/maps", headers=headers, json={"q": request.query}).json()
    
    if 'places' not in maps_res or not maps_res['places']:
        raise HTTPException(status_code=404, detail="Could not find any businesses matching that query.")
        
    all_places = maps_res['places']
    
    processed_places = []
    for place in all_places:
        rating = place.get('rating', 0)
        try:
            rating_val = float(rating)
        except (ValueError, TypeError):
            rating_val = 0.0

        processed_places.append({
            "place_id": place.get('placeId'),
            "name": place.get('title', 'Unknown Location'),
            "address": place.get('address', 'No address provided'),
            "rating": rating_val,
            "total_ratings": place.get('ratingCount', 0)
        })
        
    sorted_places = sorted(processed_places, key=lambda x: x['rating'], reverse=True)
    
    return {"places": sorted_places[:3]}


@app.post("/api/summarize")
def summarize_endpoint(request: SummarizeRequest):
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    
    reviews = []
    page = 1
    target = 30 
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
                        "CRITICAL: Make each pro and con descriptive. Write 1 to 2 complete sentences explaining the specific context or reason behind the feedback, rather than just short phrases. "
                        "CRITICAL: Do NOT include any emojis in your response whatsoever. "
                        "Translate non-English to English."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



