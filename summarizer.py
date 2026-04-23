import google.genai as genai

def summarize_reviews_with_llm(reviews_text, gemini_api_key):
    print("🧠 Analyzing reviews and generating summary...")
    
    # Configure the Google Gemini API
    genai.configure(api_key=gemini_api_key)
    
    # Using Gemini 1.5 Flash as it is extremely fast and cost-effective for text tasks
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are an expert business analyst. Read the following customer reviews for a local business.
    Extract the main positive trends and negative complaints.
    
    Output your response as strict JSON in the following format:
    {{
        "pros": ["pro 1", "pro 2", "pro 3"],
        "cons": ["con 1", "con 2", "con 3"]
    }}
    
    Here are the reviews:
    {reviews_text}
    """
    
    # Force the model to return JSON
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    
    return response.text