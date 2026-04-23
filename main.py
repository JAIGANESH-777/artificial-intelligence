import os
import requests
import json
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load API keys
load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# NEW SDK INITIALIZATION (Replaces genai.configure)
client = genai.Client(api_key=GEMINI_API_KEY)

import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

def fetch_reviews_using_placeid(business_query, target_amount=1000):
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    # --- STEP 1: Get the placeId from the /maps endpoint ---
    print(f"🔍 Step 1: Finding placeId for '{business_query}'...")
    maps_url = "https://google.serper.dev/maps"
    
    # Just like the playground, you can add coordinates here if needed:
    # {"q": business_query, "ll": "@13.04,80.16,14z"}
    maps_payload = json.dumps({"q": business_query}) 
    
    maps_response = requests.post(maps_url, headers=headers, data=maps_payload).json()
    
    if 'places' not in maps_response or len(maps_response['places']) == 0:
        print("⚠️ Could not find business on Maps.")
        return []
        
    # Extract the placeId (Exactly what you saw in your Results JSON)
    place_id = maps_response['places'][0].get('placeId')
    print(f"✅ Found business! placeId: {place_id}")
    
    # --- STEP 2: Loop the /reviews endpoint ---
    print(f"\n📥 Step 2: Fetching reviews using placeId...")
    reviews_url = "https://google.serper.dev/reviews"
    
    all_reviews_list = []
    page = 1
    
    while len(all_reviews_list) < target_amount:
        print(f"   Fetching page {page}...")
        
        # Inject the placeId we just found into the reviews payload
        review_payload = json.dumps({
            "placeId": place_id,
            "page": page
        })
        
        rev_response = requests.post(reviews_url, headers=headers, data=review_payload).json()
        
        # Check if this page has reviews
        if 'reviews' in rev_response and len(rev_response['reviews']) > 0:
            for rev in rev_response['reviews']:
                # Filter out ratings that don't have a written snippet
                if rev.get('snippet'):  
                    all_reviews_list.append(f"[{rev.get('rating')} Stars]: {rev.get('snippet')}")
            
            page += 1
            time.sleep(1) # Crucial: Don't spam the API too fast
        else:
            print("   🏁 Reached the end of available reviews.")
            break
            
    print(f"✅ Successfully scraped {len(all_reviews_list)} text reviews!\n")
    return all_reviews_list[:target_amount]

def chunk_reviews(reviews_list, chunk_size=500):
    """Breaks a large list into smaller lists of 'chunk_size'."""
    return [reviews_list[i:i + chunk_size] for i in range(0, len(reviews_list), chunk_size)]

def safe_llm_call(prompt, max_retries=3):
    """Wraps the Gemini call in a smart retry loop for quota limits."""
    for attempt in range(max_retries):
        try:
            # NEW SDK SYNTAX
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return response.text
            
        except Exception as e:
            error_msg = str(e).lower()
            # Catch 429 Too Many Requests or Quota Exhausted limits
            if "429" in error_msg or "quota" in error_msg or "exhausted" in error_msg:
                wait_time = (2 ** attempt) * 5 
                print(f"⚠️ Quota hit. Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                print(f"❌ Unexpected error: {e}")
                break 
                
    return None

def map_reduce_summarizer(all_reviews):
    if not all_reviews:
        return None
        
    print(f"Total reviews to process: {len(all_reviews)}")
    
    # Chunk by 500 to stay under the 15 RPM limit
    chunks = chunk_reviews(all_reviews, 500) 
    mini_summaries = []
    
    # --- PHASE 1: MAP ---
    for i, chunk in enumerate(chunks):
        print(f"🧠 Summarizing chunk {i + 1}/{len(chunks)}...")
        chunk_text = "\n".join(chunk)
        prompt = f"Extract the top pros and cons as JSON from these reviews:\n{chunk_text}"
        
        chunk_summary = safe_llm_call(prompt)
        if chunk_summary:
            mini_summaries.append(chunk_summary)
            
        # Polite delay to avoid hammering the API
        time.sleep(4) 
        
    # --- PHASE 2: REDUCE ---
    print("\nSynthesizing final master report...")
    combined_summaries_text = "\n---\n".join(mini_summaries)
    
    master_prompt = f"""
    Synthesize these mini-summaries into one final list of the top 5 pros and 5 cons.
    Output as strict JSON with a "pros" array and a "cons" array.
    Mini-Summaries:\n{combined_summaries_text}
    """
    
    return safe_llm_call(master_prompt)


if __name__ == "__main__":
    # 1. Provide the name (and optionally the city to be safe)
    target_business = "Apple Store Chennai" 
    
    # 2. Run the two-step Serper scraper
    reviews_list = fetch_reviews_using_placeid(target_business, target_amount=50)
    
    # 3. Pass that massive list to Gemini for the Map-Reduce summary
    if reviews_list:
        summary_json = map_reduce_summarizer(reviews_list)
        print(summary_json)