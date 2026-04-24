import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def parse_user_request(user_text):
    """
    Acts as a smart filter before running the heavy review scraper.
    Takes what the user typed and outputs a structured JSON action plan.
    """
    system_prompt = """
    You are an intelligent routing assistant for a Business Review Summarizer app.
    Your job is to read the user's input and determine if they have provided enough 
    information to search Google Maps for a specific business.
    
    You must classify the input into one of these categories and output strict JSON:
    
    1. Unrelated: {"status": "error", "message": "I can only summarize local business reviews. Please provide a business and location."}
    2. Missing Location: {"status": "incomplete", "message": "Which city or neighborhood is that business in?"}
    3. Missing Business: {"status": "incomplete", "message": "I see the location, but which specific business do you want reviews for?"}
    4. Perfect (Has Business + Location): {"status": "success", "search_query": "<Business Name> in <Location>"}
    
    Output ONLY raw JSON.
    """
    
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            model="llama-3.3-70b-versatile", # You can use the 8b model here for even faster routing!
            response_format={"type": "json_object"}
        )
        
        # Parse the string back into a Python dictionary
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        return {"status": "error", "message": f"Routing failed: {e}"}

# --- Testing the 4 Edge Cases ---
if __name__ == "__main__":
    test_cases = [
        "Can you write a poem about dogs?",          # Case 1: Random
        "Can you summarize reviews for Starbucks?",  # Case 2: Business only
        "What are the reviews like in Chennai?",     # Case 3: Location only
        "Get me the pros and cons of the Apple Store in Chennai" # Case 4: Perfect
    ]
    
    print("🧠 Testing Intent Router...\n")
    for test in test_cases:
        print(f"User typed: '{test}'")
        decision = parse_user_request(test)
        print(f"Router Output: {json.dumps(decision, indent=2)}\n")