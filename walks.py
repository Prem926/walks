import streamlit as st
import json
import os
from typing import List
import requests
import pandas as pd
import datetime

# --- CONFIG ---
# Use .streamlit/secrets.toml for API keys in Streamlit Cloud
# For local testing, you can set them as environment variables or temporarily hardcode.
# IMPORTANT: DO NOT COMMIT ACTUAL KEYS TO GITHUB
# Example of .streamlit/secrets.toml:
# GEMINI_API_KEY = "your_gemini_api_key"
# HF_TOKEN = "your_hf_token"
# GROQ_API_KEY = "your_groq_api_key"
# TOGETHER_API_KEY = "your_together_api_key"
# UNSPLASH_ACCESS_KEY = "your_unsplash_access_key"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCc2HPWwk4YqF4iC3H8ceJNn8YHBUDwLkw")  # Replace with your Gemini API key
HF_TOKEN = os.getenv("HF_TOKEN", "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")  # Replace with your Hugging Face token
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")  # Replace with your Groq API key
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "tgp_v1_PMi3Pvc3z0vlW-lM5eStXtXvO26VOHO31TOSO0xq3YRaU")  # Replace with your Together API key
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "wTQeL98lH4lohWZkTw9Jdg4_ACKbZf7EVr_3pMvXvmk")  # Replace with your Unsplash Access Key

HOST_ID = "admin"
HOST_PASS = "123"

# --- FILE PATHS FOR DATA (Ephemeral on Streamlit Cloud unless external persistence is used) ---
ROUTE_FILE = "route.json"
CURRENT_LOCATION_FILE = "current_location.json"
PREVIOUS_LOCATION_FILE = "previous_location.json" # This seems to be redundant with previous_locations.json
PREVIOUS_LOCATIONS_FILE = "previous_locations.json"
START_TIME_FILE = "walk_start_time.json"

# Ensure files exist for local development, on Streamlit Cloud these will be new on each deploy/restart
for f_path in [ROUTE_FILE, CURRENT_LOCATION_FILE, PREVIOUS_LOCATION_FILE, PREVIOUS_LOCATIONS_FILE, START_TIME_FILE]:
    if not os.path.exists(f_path):
        with open(f_path, "w") as f:
            if f_path == ROUTE_FILE:
                json.dump([], f) # Will be populated by DEFAULT_ROUTE if empty
            elif f_path == PREVIOUS_LOCATIONS_FILE:
                json.dump([], f)
            else:
                json.dump("", f)

# --- MODEL CHOICE ---
MODEL_OPTIONS = ["Gemini (Google)", "Groq (Llama-3)", "Together (Mixtral-8x7B)"]

# --- INITIAL ROUTE DATA ---
DEFAULT_ROUTE = [
    "Swaminarayan Temple, Kalupur",
    "Kavi Dalpatram Chowk",
    "Lambeshwar Ni Pol",
    "Calico Dome",
    "Kala Ramji Mandir",
    "Shantinathji Mandir, Haja Patel Ni Pol",
    "Kuvavala Khancha, Doshivada Ni Pol",
    "Secret Passage, Shantinath Ni Pol",
    "Zaveri Vad",
    "Sambhavnath Ni Khadki",
    "Chaumukhji Ni Pol",
    "Astapadji Derasar",
    "Harkunvar Shethani Ni Haveli",
    "Dodiya Haveli",
    "Fernandez Bridge (Gandhi Road)",
    "Chandla Ol",
    "Muharat Pol",
    "Ahmedabad Stock Exchange",
    "Manek Chowk",
    "Rani-no-Haziro",
    "Badshah-no-Haziro",
    "Jami Masjid"
]

# --- HELPERS ---
def load_route() -> List[str]:
    """Loads the route from a JSON file. If file is empty, initializes with DEFAULT_ROUTE."""
    try:
        with open(ROUTE_FILE, "r") as f:
            route_data = json.load(f)
            if not route_data: # If file is empty list, populate with default
                save_route(DEFAULT_ROUTE)
                return DEFAULT_ROUTE
            return route_data
    except (json.JSONDecodeError, FileNotFoundError):
        save_route(DEFAULT_ROUTE)
        return DEFAULT_ROUTE

def save_route(route: List[str]):
    """Saves the route to a JSON file."""
    with open(ROUTE_FILE, "w") as f:
        json.dump(route, f)

def load_current_location() -> str:
    """Loads the current location from a JSON file."""
    try:
        with open(CURRENT_LOCATION_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return ""

def save_current_location(location: str):
    """Saves the current location to a JSON file."""
    with open(CURRENT_LOCATION_FILE, "w") as f:
        json.dump(location, f)

# Redundant with previous_locations.json, consider removing this one if not specifically used
def load_previous_location() -> str:
    """Loads the last previous location from a JSON file."""
    try:
        if os.path.exists(PREVIOUS_LOCATION_FILE):
            with open(PREVIOUS_LOCATION_FILE, "r") as f:
                return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        pass # Return default empty string
    return ""

def save_previous_location(location: str):
    """Saves the last previous location to a JSON file."""
    with open(PREVIOUS_LOCATION_FILE, "w") as f:
        json.dump(location, f)

def load_previous_locations() -> list:
    """Loads all previous locations from a JSON file."""
    try:
        with open(PREVIOUS_LOCATIONS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_previous_locations(locations: list):
    """Saves all previous locations to a JSON file."""
    with open(PREVIOUS_LOCATIONS_FILE, "w") as f:
        json.dump(locations, f)

def gemini_chat(prompt: str) -> str:
    """Sends a prompt to the Gemini API and returns the response."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        return "Gemini API key is not set. Please configure it in .streamlit/secrets.toml or as an environment variable."

    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    params = {"key": GEMINI_API_KEY}
    try:
        response = requests.post(url, headers=headers, params=params, json=data)
        response.raise_for_status() # Raise an exception for HTTP errors
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except requests.exceptions.RequestException as e:
        error_msg = f"Gemini API Request Error: {e}"
        if response is not None:
            try:
                error_details = response.json()
                error_msg += f" - Details: {error_details}"
            except json.JSONDecodeError:
                error_msg += f" - Response: {response.text}"
        return error_msg
    except KeyError:
        return f"Gemini API Response Error: Unexpected response format. Response: {response.json()}"
    except Exception as e:
        return f"An unexpected error occurred with Gemini API: {str(e)}"

def groq_chat(prompt: str) -> str:
    """Sends a prompt to the Groq API and returns the response."""
    if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY":
        return "Groq API key is not set. Please configure it in .streamlit/secrets.toml or as an environment variable."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}]
    }
    response = None # Initialize response
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        error_msg = f"Groq API Request Error: {e}"
        if response is not None:
            try:
                error_details = response.json()
                error_msg += f" - Details: {error_details}"
            except json.JSONDecodeError:
                error_msg += f" - Response: {response.text}"
        return error_msg
    except KeyError:
        return f"Groq API Response Error: Unexpected response format. Response: {response.json()}"
    except Exception as e:
        return f"An unexpected error occurred with Groq API: {str(e)}"

def together_chat(prompt: str) -> str:
    """Sends a prompt to the Together API and returns the response."""
    if not TOGETHER_API_KEY or TOGETHER_API_KEY == "YOUR_TOGETHER_API_KEY":
        return "Together API key is not set. Please configure it in .streamlit/secrets.toml or as an environment variable."

    url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "messages": [{"role": "user", "content": prompt}]
    }
    response = None # Initialize response
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        error_msg = f"Together API Request Error: {e}"
        if response is not None:
            try:
                error_details = response.json()
                error_msg += f" - Details: {error_details}"
            except json.JSONDecodeError:
                error_msg += f" - Response: {response.text}"
        return error_msg
    except KeyError:
        return f"Together API Response Error: Unexpected response format. Response: {response.json()}"
    except Exception as e:
        return f"An unexpected error occurred with Together API: {str(e)}"

def get_ai_response(prompt: str, model_choice: str) -> str:
    """Routes the prompt to the chosen AI model."""
    if model_choice == "Gemini (Google)":
        return gemini_chat(prompt)
    elif model_choice == "Groq (Llama-3)":
        return groq_chat(prompt)
    else: # Together (Mixtral-8x7B)
        return together_chat(prompt)

@st.cache_data(show_spinner=False, ttl=3600) # Cache for 1 hour
def get_site_info(site: str, model_choice: str) -> str:
    """Fetches and caches engaging information about a heritage site."""
    prompt = f"Give a short, engaging, and informative description (max 80 words) about the heritage site: {site} in Ahmedabad."
    info = get_ai_response(prompt, model_choice)
    # Don't directly show API error messages as info; instead, let the calling function decide
    # if info.startswith("Gemini API Error") or info.startswith("Groq API Error") or info.startswith("Together API Error") or info.startswith("An unexpected error occurred"):
    #     st.warning(info) # This would put warning inside cached expander. Better to handle outside.
    return info

@st.cache_data(show_spinner=False, ttl=86400) # Cache images for a day
def get_unsplash_image(query: str) -> str:
    """Fetches an image URL from Unsplash based on a query."""
    if not UNSPLASH_ACCESS_KEY or UNSPLASH_ACCESS_KEY == "YOUR_UNSPLASH_ACCESS_KEY":
        return "https://placehold.co/400x200?text=Unsplash+Key+Missing"

    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "client_id": UNSPLASH_ACCESS_KEY,
        "per_page": 1
    }
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("results"):
            return data["results"][0]["urls"]["regular"]
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching image from Unsplash: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching Unsplash image: {e}")
    return "https://placehold.co/400x200?text=No+Image"

# --- DATA FOR TRIVIA ---
STOP_TRIVIA = {
    "Swaminarayan Temple, Kalupur": ("In which year was the Swaminarayan Temple built?", "1822"),
    "Kavi Dalpatram Chowk": ("Who was Kavi Dalpatram?", "Poet"),
    "Lambeshwar Ni Pol": ("What is a 'Pol' in Ahmedabad?", "Traditional housing cluster"),
    "Calico Dome": ("What was the Calico Dome famous for?", "Textiles"),
    "Kala Ramji Mandir": ("What makes Kala Ramji Mandir unique?", "Black idol of Lord Rama"),
    "Shantinathji Mandir, Haja Patel Ni Pol": ("Which Tirthankara is Shantinathji Mandir dedicated to?", "Shantinath"),
    "Kuvavala Khancha, Doshivada Ni Pol": ("What is a 'Khancha'?", "A narrow lane or alleyway"),
    "Secret Passage, Shantinath Ni Pol": ("What was the purpose of secret passages in old pol houses?", "Escape routes or storage"),
    "Zaveri Vad": ("What type of businesses were traditionally found in Zaveri Vad?", "Jewellery businesses"),
    "Sambhavnath Ni Khadki": ("What is a 'Khadki'?", "A small, gated entrance to a cluster of houses"),
    "Chaumukhji Ni Pol": ("What does 'Chaumukhji' refer to?", "Four-faced deity"),
    "Astapadji Derasar": ("What is a 'Derasar'?", "Jain temple"),
    "Harkunvar Shethani Ni Haveli": ("What is a 'Haveli'?", "Traditional mansion"),
    "Dodiya Haveli": ("Which architectural style is prominent in Dodiya Haveli?", "Mughal and Maratha influences"),
    "Fernandez Bridge (Gandhi Road)": ("Who was Fernandez Bridge named after?", "Named after a British officer"),
    "Chandla Ol": ("What does 'Chandla' mean?", "Bangles"),
    "Muharat Pol": ("What does 'Muharat' signify in this context?", "Auspicious beginning"),
    "Ahmedabad Stock Exchange": ("In which year was the Ahmedabad Stock Exchange established?", "1894"),
    "Manek Chowk": ("What is Manek Chowk famous for at night?", "Street food market"),
    "Rani-no-Haziro": ("Who is buried at Rani-no-Haziro?", "Queens and royal women"),
    "Badshah-no-Haziro": ("Who is buried at Badshah-no-Haziro?", "Sultans and royal men"),
    "Jami Masjid": ("When was Jami Masjid built?", "1424")
}

# --- TIMER HELPERS ---
def load_start_time():
    """Loads the walk start time from a JSON file."""
    try:
        with open(START_TIME_FILE, "r") as f:
            start_time_str = json.load(f)
            return start_time_str if start_time_str else None
    except (json.JSONDecodeError, FileNotFoundError):
        return None

def save_start_time(start_time_iso: str):
    """Saves the walk start time to a JSON file."""
    with open(START_TIME_FILE, "w") as f:
        json.dump(start_time_iso, f)

# --- TIMER DISPLAY ---
def display_timer():
    """Displays the elapsed time since the walk started."""
    start_time = load_start_time()
    if start_time:
        try:
            start_dt = datetime.datetime.fromisoformat(start_time)
            elapsed = datetime.datetime.now() - start_dt
            st.info(f"⏱️ Walk started at {start_dt.strftime('%H:%M:%S')}. Elapsed: {str(elapsed).split('.')[0]}")
        except ValueError:
            st.error("Invalid start time format recorded.")
    else:
        st.info("⏱️ Walk not started yet.")

# --- MAIN APP ---
st.set_page_config(page_title="Ahmedabad Heritage Walk", layout="wide")
st.markdown("""
    <style>
    .current-location {
        background-color: #ffe082;
        border-radius: 8px;
        padding: 8px;
        font-weight: bold;
        color: #6d4c00;
    }
    .previous-location {
        background-color: #b3e5fc;
        border-radius: 8px;
        padding: 8px;
        font-weight: bold;
        color: #01579b;
    }
    .locked-info {
        color: #bdbdbd;
        font-style: italic;
        font-size: 0.95em;
    }
    .heritage-stop {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        margin-bottom: 8px;
        padding: 8px;
        background: #fafafa;
    }
    .chat-bubble-user {
        background: #e3f2fd;
        border-radius: 12px;
        padding: 8px 12px;
        margin-bottom: 4px;
        text-align: right;
    }
    .chat-bubble-bot {
        background: #fffde7;
        border-radius: 12px;
        padding: 8px 12px;
        margin-bottom: 8px;
        text-align: left;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏛️ Ahmedabad Heritage Walk")
st.markdown("---")

# Initialize session state variables
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "trivia_answers" not in st.session_state:
    st.session_state["trivia_answers"] = {}
# Ensure current_location and previous_locations are loaded once per rerun for consistency
# Load them from disk and then use session_state to manage UI updates if needed
# However, for multi-user scenario where host changes affect all, disk is the current implementation target
# (even if ephemeral on Streamlit Cloud).

# --- LEGEND ---
with st.expander("Legend / Info", expanded=False):
    st.markdown("""
    <span class='current-location'>Current Location</span>  
    <span class='previous-location'>Previous Location</span>  
    <span class='locked-info'>🔒 Info locked until you reach this stop</span>
    """, unsafe_allow_html=True)

# --- SIDEBAR: LOGIN & CURRENT LOCATION ---
st.sidebar.header("Login")
user_type = st.sidebar.radio("I am a...", ["Client", "Host (Admin)"])

# --- SIDEBAR: MODEL CHOICE ---
st.sidebar.markdown("---")
st.sidebar.subheader("AI Model")
model_choice = st.sidebar.selectbox("Choose AI Model", MODEL_OPTIONS, index=0)

current_location = load_current_location()
previous_locations = load_previous_locations()

if user_type == "Host (Admin)":
    host_id = st.sidebar.text_input("Host ID")
    host_pass = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login", key="admin_login_btn"):
        if host_id == HOST_ID and host_pass == HOST_PASS:
            st.session_state["is_admin"] = True
            st.rerun() # Rerun to update the main content based on login status
        else:
            st.sidebar.error("Invalid credentials")
    
    if st.session_state.get("is_admin"):
        st.success("Logged in as Host/Admin")
        st.sidebar.markdown(f"**Current Location:**\n\n<span class='current-location'>{current_location or 'Not set'}</span>", unsafe_allow_html=True)
        st.sidebar.markdown("**Previous Locations:**", unsafe_allow_html=True)
        if previous_locations:
            for loc in previous_locations:
                st.sidebar.markdown(f"<span class='previous-location'>{loc}</span>", unsafe_allow_html=True)
        else:
            st.sidebar.markdown("<span class='previous-location'>None</span>", unsafe_allow_html=True)
        
        st.subheader("Edit Heritage Walk Route")
        route = load_route()
        
        # Streamlit's data_editor requires a list of dicts for more complex editing,
        # but for a simple list of strings, direct list editing with `num_rows="dynamic"` is fine.
        edited_route = st.data_editor(route, num_rows="dynamic", key="route_editor")
        
        if st.button("Save Route", key="save_route_btn"):
            # Ensure no empty strings are saved if user adds empty rows
            cleaned_route = [stop.strip() for stop in edited_route if stop.strip()]
            save_route(cleaned_route)
            st.success("Route updated! All clients will see the changes (after their next app reload).")
            st.rerun() # Rerun to display updated route immediately

        st.markdown("---")
        st.subheader("Manage Current Location")
        
        current_route_stops = load_route() # Load the potentially updated route
        for i, stop in enumerate(current_route_stops, 1):
            col1, col2 = st.columns([8,2])
            with col1:
                is_current = (stop == current_location)
                is_previous = (stop in previous_locations)
                style = "current-location" if is_current else ("previous-location" if is_previous else "")
                label = " (Current Location)" if is_current else (" (Previous Location)" if is_previous else "")
                st.markdown(f"<span class='{style}'><b>{i}. {stop}</b>{label}</span>" if style else f"{i}. {stop}", unsafe_allow_html=True)
            with col2:
                if st.button("Set as Current", key=f"set_current_{stop.replace(' ', '_')}_{i}"):
                    if stop != current_location and current_location:
                        # Add previous current location to previous_locations if it's not already there
                        prevs = load_previous_locations()
                        if current_location not in prevs:
                            prevs.append(current_location)
                            save_previous_locations(prevs)
                    save_current_location(stop)
                    st.rerun() # Rerun to update the current location display for everyone

        # Admin: Clear current location and previous locations
        if st.button("Clear Current Location", key="clear_current_btn"):
            save_current_location("")
            st.rerun()
        if st.button("Clear All Previous Locations", key="clear_previous_btn"):
            save_previous_locations([])
            st.rerun()

    else: # If admin is not logged in, display the login prompt
        st.sidebar.info("Log in as Host to manage the route.")

else: # Client View
    st.sidebar.markdown(f"**Current Location:**\n\n<span class='current-location'>{current_location or 'Not set'}</span>", unsafe_allow_html=True)
    st.sidebar.markdown("**Previous Locations:**", unsafe_allow_html=True)
    if previous_locations:
        for loc in previous_locations:
            st.sidebar.markdown(f"<span class='previous-location'>{loc}</span>", unsafe_allow_html=True)
    else:
        st.sidebar.markdown("<span class='previous-location'>None</span>", unsafe_allow_html=True)
    
    st.subheader("Heritage Walk Route")
    route = load_route() # Clients also load the route
    for i, stop in enumerate(route, 1):
        is_current = (stop == current_location)
        is_previous = (stop in previous_locations)
        
        # Determine if info should be displayed
        show_info = is_current or is_previous

        with st.container():
            st.markdown(f"<div class='heritage-stop'><span class='{'current-location' if is_current else ('previous-location' if is_previous else '')}'><b>{i}. {stop}</b>{' (Current Location)' if is_current else (' (Previous Location)' if is_previous else '')}</span></div>", unsafe_allow_html=True)
            
            if show_info:
                with st.expander("Show info about this site"):
                    # Show image
                    unsplash_img = get_unsplash_image(f"{stop} Ahmedabad heritage site")
                    st.image(unsplash_img, use_container_width=True, caption=f"Image of {stop}")
                    
                    with st.spinner("Fetching info..."):
                        info = get_site_info(stop, model_choice)
                    
                    # Display info and handle API errors gracefully
                    if info.startswith(("Gemini API Error", "Groq API Error", "Together API Error", "An unexpected error occurred")):
                        st.warning(info)
                    else:
                        st.markdown(info)
                    
                    # Trivia/Quiz
                    q_and_a = STOP_TRIVIA.get(stop)
                    if q_and_a:
                        question, correct_answer = q_and_a
                        st.markdown(f"**Trivia:** {question}")
                        user_key = f"trivia_{stop}".replace(" ", "_").replace(",", "") # Clean key
                        
                        # Only show input if not already answered or if answer is wrong
                        if user_key not in st.session_state["trivia_answers"] or \
                           st.session_state["trivia_answers"].get(user_key, "").strip().lower() != correct_answer.strip().lower():
                            user_answer = st.text_input("Your answer:", key=user_key)
                            if st.button("Submit Answer", key=f"submit_{user_key}"):
                                st.session_state["trivia_answers"][user_key] = user_answer
                                st.rerun() # Rerun to show feedback immediately
                        
                        # Show feedback if an answer has been submitted
                        if user_key in st.session_state["trivia_answers"]:
                            given = st.session_state["trivia_answers"][user_key]
                            if given.strip().lower() == correct_answer.strip().lower():
                                st.success("Correct!")
                            else:
                                st.error(f"Wrong! Correct answer: **{correct_answer}**")
            else:
                st.markdown("<span class='locked-info'>🔒 Info locked until you reach this stop</span>", unsafe_allow_html=True)

    # --- ADMIN: Show all trivia answers ---
    # This section needs to be accessible to admin regardless of client/host radio button choice
    # since it's displaying global answers. Moved outside the client/host if-else for better logic.
    # It will only display if st.session_state["is_admin"] is True.

st.markdown("---")
if st.session_state.get("is_admin"):
    st.subheader("Trivia Answers (All Submitted)")
    if st.session_state["trivia_answers"]:
        # Create a DataFrame for better display of trivia answers
        trivia_data = []
        for key, ans in st.session_state["trivia_answers"].items():
            stop_name = key.replace("trivia_", "").replace("_", " ")
            q_and_a = STOP_TRIVIA.get(stop_name)
            if q_and_a:
                question, correct_answer = q_and_a
                correct = ans.strip().lower() == correct_answer.strip().lower()
                trivia_data.append({
                    "Stop": stop_name,
                    "Question": question,
                    "Your Answer": ans,
                    "Correct Answer": correct_answer,
                    "Correct?": "✅" if correct else "❌"
                })
            else:
                trivia_data.append({
                    "Stop": stop_name,
                    "Question": "N/A",
                    "Your Answer": ans,
                    "Correct Answer": "N/A",
                    "Correct?": "N/A"
                })
        
        df_trivia = pd.DataFrame(trivia_data)
        st.dataframe(df_trivia, hide_index=True)
    else:
        st.info("No trivia answers submitted yet by any client.")

st.markdown("---")
st.subheader("Ask about the Heritage Walk (Chatbot)")
st.markdown("<i>Chatbot will answer only about the current or previous location, or general walk info.</i>", unsafe_allow_html=True)

user_query = st.text_input("Type your question here", key="chat_input")
if st.button("Ask", key="ask_btn"): # Changed condition to trigger on button click instead of just `user_query`
    if user_query:
        # Add context about the walk and restrict to current/previous location
        route_for_context = load_route() # Ensure latest route is used for context
        context = f"You are an AI assistant helping with the Ahmedabad Heritage Walk. The route includes: {', '.join(route_for_context)}. "
        if current_location:
            context += f"The current location is: {current_location}. "
        if previous_locations:
            context += f"Previous locations visited: {', '.join(previous_locations)}. "
        context += "Please answer user questions based on this information and general knowledge about Ahmedabad's heritage walk. Be concise and helpful. If the question is about a future location, you can mention it's part of the route but don't provide details, as that information is 'locked' until the user reaches it."
        
        prompt = f"{context}\nUser question: {user_query}"
        
        with st.spinner("Thinking..."):
            answer = get_ai_response(prompt, model_choice)
        st.session_state["chat_history"].append((user_query, answer))
        # Clear the text input after sending
        st.session_state.chat_input = "" # This will clear the input box

# Display chat history (reverse order to show latest at bottom)
for q, a in st.session_state["chat_history"]:
    st.markdown(f"<div class='chat-bubble-user'>{q}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='chat-bubble-bot'>{a}</div>", unsafe_allow_html=True)

st.info("You can ask about the current or previous stop, or general info about Ahmedabad's heritage walk.")

display_timer()

# --- HOST: START WALK BUTTON ---
if user_type == "Host (Admin)" and st.session_state.get("is_admin"):
    if not load_start_time(): # Only show button if walk hasn't started
        if st.button("Start Walk 🏁", key="start_walk_btn"):
            now = datetime.datetime.now().isoformat()
            save_start_time(now)
            st.rerun()
    else:
        if st.button("Reset Walk Timer 🔄", key="reset_walk_btn"):
            save_start_time("") # Clear the start time
            save_current_location("") # Also clear current and previous locations for a fresh start
            save_previous_locations([])
            st.session_state["chat_history"] = [] # Clear chat history
            st.session_state["trivia_answers"] = {} # Clear trivia answers
            st.rerun()

st.caption("Made with ❤️ of Team Neev India")
