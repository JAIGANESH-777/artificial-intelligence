# AI Review Summarizer Project

## 1. Introduction

The AI Review Summarizer is a web-based application designed to help users analyze customer reviews for businesses. By leveraging AI and external APIs, the application extracts the top pros and cons from reviews, providing users with a concise summary of customer feedback. This project is built using FastAPI for the backend and a responsive HTML interface for the frontend.

### Key Features:
- Search for businesses using Google Maps API.
- Analyze customer reviews to extract pros and cons.
- Display results in a user-friendly interface.

---

## 2. Frontend Design

The frontend of the application is implemented in the `index.html` file. It provides a clean and responsive user interface using Tailwind CSS. The main components of the frontend include:

### 2.1. Search Bar
- **Purpose**: Allows users to input the name of a business they want to analyze.
- **Implementation**: An input field and a search button trigger the `findLocations()` function.

```html
<div class="flex gap-2 mb-6">
    <input type="text" id="searchInput" placeholder="e.g., Apple Store Chennai" 
           class="flex-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
    <button onclick="findLocations()" id="searchBtn"
            class="bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition">
        Search
    </button>
</div>
```

### 2.2. Results Display
- **Location Selector**: Displays multiple locations if the search query matches more than one business.
- **Pros and Cons Section**: Shows the summarized pros and cons of the selected business.

```html
<div id="results" class="hidden mt-6">
    <div id="selectedStoreHeader" class="text-center mb-6 border-b pb-4">
        <!-- Business details will be dynamically populated here -->
    </div>
    <div class="flex flex-col md:flex-row gap-6">
        <div class="flex-1 bg-green-50 p-4 rounded-lg border border-green-200">
            <h2 class="text-xl font-bold text-green-700 mb-3">✅ Pros</h2>
            <ul id="prosList" class="list-disc pl-5 space-y-2 text-green-900"></ul>
        </div>
        <div class="flex-1 bg-red-50 p-4 rounded-lg border border-red-200">
            <h2 class="text-xl font-bold text-red-700 mb-3">❌ Cons</h2>
            <ul id="consList" class="list-disc pl-5 space-y-2 text-red-900"></ul>
        </div>
    </div>
</div>
```

### 2.3. JavaScript Functions
The frontend uses JavaScript to handle user interactions and communicate with the backend API.
- **`findLocations()`**: Sends a search query to the backend and displays matching locations.
- **`analyzeSpecificPlace()`**: Fetches and displays the pros and cons of the selected business.

---

## 3. Backend Implementation

The backend is implemented in the `main.py` file using FastAPI. It provides two main API endpoints:

### 3.1. `/api/search_places`
- **Method**: POST
- **Purpose**: Searches for businesses based on the user query.
- **Implementation**: Sends a request to the Google Maps API via Serper API and returns the top 3 results.

```python
@app.post("/api/search_places")
def search_places(request: SearchRequest):
    headers = {'X-API-KEY': SERPER_API_KEY, 'Content-Type': 'application/json'}
    maps_res = requests.post("https://google.serper.dev/maps", headers=headers, json={"q": request.query}).json()
    
    if 'places' not in maps_res or not maps_res['places']:
        raise HTTPException(status_code=404, detail="Could not find any businesses matching that query.")
        
    top_3 = maps_res['places'][:3]
    clean_places = [
        {
            "place_id": place.get('placeId'),
            "name": place.get('title', 'Unknown Location'),
            "address": place.get('address', 'No address provided'),
            "rating": place.get('rating', 'N/A'),
            "total_ratings": place.get('ratingCount', 0)
        }
        for place in top_3
    ]
    
    return {"places": clean_places}
```

### 3.2. `/api/summarize`
- **Method**: POST
- **Purpose**: Fetches reviews for a selected business and summarizes them into pros and cons.
- **Implementation**: Uses the Groq API to analyze reviews and extract insights.

```python
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
```

---

## 4. Integration

The frontend and backend communicate via RESTful API calls. The JavaScript functions in the frontend send HTTP POST requests to the backend endpoints, and the backend processes the requests and returns JSON responses. The responses are then dynamically rendered on the frontend.

### Workflow:
1. User enters a business name and clicks "Search."
2. The frontend sends a request to `/api/search_places`.
3. The backend fetches matching locations and returns them to the frontend.
4. User selects a location, triggering a request to `/api/summarize`.
5. The backend fetches reviews, summarizes them, and sends the results to the frontend.
6. The frontend displays the pros and cons to the user.

---

## 5. Conclusion

The AI Review Summarizer is a powerful tool for analyzing customer feedback. By combining a responsive frontend with a robust backend, the application provides users with valuable insights into customer opinions. This project demonstrates the effective use of modern web development technologies and APIs to solve real-world problems.