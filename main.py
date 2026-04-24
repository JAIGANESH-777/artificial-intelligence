import os
import requests
import json
import time
from groq import Groq
from dotenv import load_dotenv

# Load API keys
load_dotenv()
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize ONLY the Groq (Llama) client
client = Groq(api_key=GROQ_API_KEY)

def fetch_reviews_using_placeid(business_query, target_amount=1000):
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    
    # --- STEP 1: Get the placeId from the /maps endpoint ---
    print(f"🔍 Step 1: Finding placeId for '{business_query}'...")
    maps_url = "https://google.serper.dev/maps"
    maps_payload = json.dumps({"q": business_query}) 
    
    maps_response = requests.post(maps_url, headers=headers, data=maps_payload).json()
    
    if 'places' not in maps_response or len(maps_response['places']) == 0:
        print("⚠️ Could not find business on Maps.")
        return []
        
    place_id = maps_response['places'][0].get('placeId')
    print(f"✅ Found business! placeId: {place_id}")
    
    # --- STEP 2: Loop the /reviews endpoint ---
    print(f"\n📥 Step 2: Fetching reviews using placeId...")
    reviews_url = "https://google.serper.dev/reviews"
    
    all_reviews_list = []
    page = 1
    
    while len(all_reviews_list) < target_amount:
        print(f"   Fetching page {page}...")
        
        review_payload = json.dumps({
            "placeId": place_id,
            "page": page
        })
        
        rev_response = requests.post(reviews_url, headers=headers, data=review_payload).json()
        
        if 'reviews' in rev_response and len(rev_response['reviews']) > 0:
            for rev in rev_response['reviews']:
                if rev.get('snippet'):  
                    all_reviews_list.append(f"[{rev.get('rating')} Stars]: {rev.get('snippet')}")
            
            page += 1
            time.sleep(1) 
        else:
            print("   🏁 Reached the end of available reviews.")
            break
            
    print(f"✅ Successfully scraped {len(all_reviews_list)} text reviews!\n")
    return all_reviews_list[:target_amount]

def chunk_reviews(reviews_list, chunk_size=500):
    """Breaks a large list into smaller lists of 'chunk_size'."""
    return [reviews_list[i:i + chunk_size] for i in range(0, len(reviews_list), chunk_size)]

def safe_llm_call(prompt, max_retries=3):
    """Uses Llama 3 via Groq instead of Gemini."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "system", 
                        "content": (
                            "You are an expert data analyst. Read the provided reviews and extract dont hallucinate the things , just maintain zero creativity, just give me from the reviews i had fetched"
                            "the top pros and cons. If any reviews are in a non-English language "
                            "(such as Tamil or Tanglish), translate them to English internally before "
                            "summarizing. Your final output MUST be entirely in English. "
                            "Output ONLY strict JSON. Do not include markdown code blocks, just raw JSON."
                        )
                    },
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"⚠️ Groq API issue. Retrying... Error: {e}")
            time.sleep(2)
                
    return None

def map_reduce_summarizer(all_reviews):
    if not all_reviews:
        return None
        
    print(f"Total reviews to process: {len(all_reviews)}")
    chunks = chunk_reviews(all_reviews, 500) 
    mini_summaries = []
    
    for i, chunk in enumerate(chunks):
        print(f"🧠 Summarizing chunk {i + 1}/{len(chunks)}...")
        chunk_text = "\n".join(chunk)
        prompt = f"Extract the top pros and cons as JSON from these reviews:\n{chunk_text}"
        
        chunk_summary = safe_llm_call(prompt)
        if chunk_summary:
            mini_summaries.append(chunk_summary)
            
        time.sleep(2) 
        
    print("\nSynthesizing final master report...")
    combined_summaries_text = "\n---\n".join(mini_summaries)
    
    master_prompt = f"""
    Synthesize these mini-summaries into one final list of the top 5 pros and 5 cons.
    Output as strict JSON with a "pros" array and a "cons" array.
    Mini-Summaries:\n{combined_summaries_text}
    """
    
    return safe_llm_call(master_prompt)


if __name__ == "__main__":
    target_business = "Apple Store Chennai" 
    
    # Fetch 50 reviews
    reviews_list = fetch_reviews_using_placeid(target_business, target_amount=50)
    
    if reviews_list:
        
        # --- NEW: Beautifully formatted raw reviews ---
        print("\n" + "="*50)
        print(" RAW CUSTOMER REVIEWS (SNIPPETS ONLY)")
        print("="*50)
        
        for index, review in enumerate(reviews_list, 1):
            print(f"\nReview {index}:")
            print(f"\"{review}\"")
            print("-" * 50)
            
        print("\n" + "="*50 + "\n")
        
        # Run the Summarizer
        summary_json = map_reduce_summarizer(reviews_list)
        
        print("\n🎉 Final Summary:")
        try:
            parsed_summary = json.loads(summary_json)
            print(json.dumps(parsed_summary, indent=4))
        except:
            print(summary_json)