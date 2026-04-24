import streamlit as st
import json

# Import your custom logic from the other files
from tool import parse_user_request
from main import fetch_reviews_using_placeid, map_reduce_summarizer

# --- PAGE SETUP ---
st.set_page_config(
    page_title="Review Summarizer AI",
    page_icon="⭐",
    layout="centered"
)

st.title("⭐ AI Local Business Summarizer")
st.write("Find out what people *really* think about a place before you go.")

# --- USER INPUT ---
user_query = st.text_input(
    "What business are you looking for?", 
    placeholder="e.g., Apple Store in Chennai'"
)

# --- EXECUTION FLOW ---
if st.button("Analyze Reviews", type="primary"):
    
    if not user_query:
        st.warning("Please enter a business to search for.")
    else:
        # STEP 1: The Router (tool.py)
        with st.spinner("🤖 Routing request..."):
            routing_decision = parse_user_request(user_query)
            
        # Handle bad/incomplete inputs
        if routing_decision.get("status") in ["error", "incomplete"]:
            st.warning(routing_decision.get("message"))
            
        # Handle the perfect input
        elif routing_decision.get("status") == "success":
            search_target = routing_decision.get("search_query")
            st.info(f"📍 Target locked: **{search_target}**")
            
            # STEP 2: The Scraper (main.py)
            with st.spinner(f"📥 Scraping top 50 reviews for {search_target}..."):
                reviews_list = fetch_reviews_using_placeid(search_target, target_amount=50)
                
            if not reviews_list:
                st.error("Could not find enough reviews for this location. Try being more specific.")
            else:
                st.success(f"Successfully scraped {len(reviews_list)} reviews!")
                
                # STEP 3: The Summarizer (main.py)
                with st.spinner("🧠 Analyzing sentiments with Llama 3.3..."):
                    summary_json_string = map_reduce_summarizer(reviews_list)
                    
                # STEP 4: Display the Results Beautifully
                if summary_json_string:
                    st.markdown("---")
                    st.subheader("📊 Final Consensus")
                    
                    try:
                        # Parse the JSON so we can split Pros and Cons
                        summary_data = json.loads(summary_json_string)
                        
                        # Create two side-by-side columns
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.success("### ✅ Pros")
                            for pro in summary_data.get("pros", []):
                                st.write(f"- {pro}")
                                
                        with col2:
                            st.error("### ❌ Cons")
                            for con in summary_data.get("cons", []):
                                st.write(f"- {con}")
                                
                    except json.JSONDecodeError:
                        st.error("The AI returned an invalid format. Here is the raw output:")
                        st.write(summary_json_string)