import requests
import json

def fetch_google_reviews(business_query, serper_api_key):
    print(f"🔍 Searching Google Maps for: {business_query}...")
    url = "https://google.serper.dev/places"
    
    payload = json.dumps({"q": business_query})
    headers = {
        'X-API-KEY': serper_api_key,
        'Content-Type': 'application/json'
    }
    
    response = requests.post(url, headers=headers, data=payload)
    data = response.json()
    
    reviews_text = ""
    
    # Check if we got places data back
    if 'places' in data and len(data['places']) > 0:
        # Get the first (most relevant) place match
        top_place = data['places'][0] 
        print(f"✅ Found: {top_place.get('title')} at {top_place.get('address')}")
        
        # Serper sometimes includes recent reviews in the initial payload
        # Note: For hundreds of reviews, you would need Serper's dedicated reviews endpoint/pagination
        if 'reviews' in top_place:
            for i, review in enumerate(top_place['reviews'], 1):
                reviews_text += f"Review {i} ({review.get('rating')} stars): {review.get('snippet', '')}\n\n"
        else:
            return "No reviews found in the initial search payload."
    else:
        return "Could not find this business."
        
    return reviews_text