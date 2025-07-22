import streamlit as st
import json
import os
from typing import List
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime

# --- CONFIG ---
ROUTE_FILE = "route.json"
CURRENT_LOCATION_FILE = "current_location.json"
HOST_ID = "admin"
HOST_PASS = "heritage123"
GEMINI_API_KEY = "AIzaSyCc2HPWwk4YqF4iC3H8ceJNn8YHBUDwLkw"  # Replace with your Gemini API key
HF_TOKEN = "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"  # Replace with your Hugging Face token
GROQ_API_KEY = "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"  # Replace with your Groq API key
TOGETHER_API_KEY = "tgp_v1_PMi3Pvc3z0vlW-lM5eStXtO26VOHO31TOSO0xq3YRaU"  # Replace with your Together API key
UNSPLASH_ACCESS_KEY = "wTQeL98lH4lohWZkTw9Jdg4_ACKbZf7EVr_3pMvXvmk"  # Replace with your Unsplash Access Key

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
    if not os.path.exists(ROUTE_FILE):
        with open(ROUTE_FILE, "w") as f:
            json.dump(DEFAULT_ROUTE, f)
    with open(ROUTE_FILE, "r") as f:
        return json.load(f)

def save_route(route: List[str]):
    with open(ROUTE_FILE, "w") as f:
        json.dump(route, f)

def load_current_location() -> str:
    if not os.path.exists(CURRENT_LOCATION_FILE):
        with open(CURRENT_LOCATION_FILE, "w") as f:
            json.dump("", f)
    with open(CURRENT_LOCATION_FILE, "r") as f:
        return json.load(f)

def save_current_location(location: str):
    with open(CURRENT_LOCATION_FILE, "w") as f:
        json.dump(location, f)

def load_previous_location() -> str:
    if os.path.exists("previous_location.json"):
        with open("previous_location.json", "r") as f:
            return json.load(f)
    return ""

def save_previous_location(location: str):
    with open("previous_location.json", "w") as f:
        json.dump(location, f)

def load_previous_locations() -> list:
    if os.path.exists("previous_locations.json"):
        with open("previous_locations.json", "r") as f:
            return json.load(f)
    return []

def save_previous_locations(locations: list):
    with open("previous_locations.json", "w") as f:
        json.dump(locations, f)

def gemini_chat(prompt: str) -> str:
    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    params = {"key": GEMINI_API_KEY}
    try:
        response = requests.post(url, headers=headers, params=params, json=data)
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            try:
                error_msg = response.json().get('error', {}).get('message', str(response.text))
            except Exception:
                error_msg = response.text
            return f"Gemini API Error: {error_msg} (Status code: {response.status_code})"
    except Exception as e:
        return f"Exception occurred: {str(e)}"

def groq_chat(prompt: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"Groq API Error: {response.text} (Status code: {response.status_code})"
    except Exception as e:
        return f"Exception occurred: {str(e)}"

def together_chat(prompt: str) -> str:
    url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"Together API Error: {response.text} (Status code: {response.status_code})"
    except Exception as e:
        return f"Exception occurred: {str(e)}"

def get_ai_response(prompt: str, model_choice: str) -> str:
    if model_choice == "Gemini (Google)":
        return gemini_chat(prompt)
    elif model_choice == "Groq (Llama-3)":
        return groq_chat(prompt)
    else:
        return together_chat(prompt)

@st.cache_data(show_spinner=False)
def get_site_info(site: str, model_choice: str) -> str:
    prompt = f"Give a short, engaging, and informative description (max 80 words) about the heritage site: {site} in Ahmedabad."
    info = get_ai_response(prompt, model_choice)
    if info.startswith("Gemini API Error") or info.startswith("Groq API Error") or info.startswith("Together API Error") or info.startswith("Exception occurred"):
        st.warning(info)
    return info

def get_unsplash_image(query):
    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "client_id": UNSPLASH_ACCESS_KEY,
        "per_page": 1
    }
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        if data.get("results"):
            return data["results"][0]["urls"]["regular"]
    except Exception:
        pass
    return "https://placehold.co/400x200?text=No+Image"

# --- DATA FOR MAP, IMAGES, AND TRIVIA ---
STOP_COORDS = {
    "Swaminarayan Temple, Kalupur": (23.0286, 72.6036),
    "Kavi Dalpatram Chowk": (23.0292, 72.6041),
    "Lambeshwar Ni Pol": (23.0297, 72.6045),
    "Calico Dome": (23.0301, 72.6050),
    "Kala Ramji Mandir": (23.0305, 72.6054),
    "Shantinathji Mandir, Haja Patel Ni Pol": (23.0309, 72.6058),
    "Kuvavala Khancha, Doshivada Ni Pol": (23.0313, 72.6062),
    "Secret Passage, Shantinath Ni Pol": (23.0317, 72.6066),
    "Zaveri Vad": (23.0321, 72.6070),
    "Sambhavnath Ni Khadki": (23.0325, 72.6074),
    "Chaumukhji Ni Pol": (23.0329, 72.6078),
    "Astapadji Derasar": (23.0333, 72.6082),
    "Harkunvar Shethani Ni Haveli": (23.0337, 72.6086),
    "Dodiya Haveli": (23.0341, 72.6090),
    "Fernandez Bridge (Gandhi Road)": (23.0345, 72.6094),
    "Chandla Ol": (23.0349, 72.6098),
    "Muharat Pol": (23.0353, 72.6102),
    "Ahmedabad Stock Exchange": (23.0357, 72.6106),
    "Manek Chowk": (23.0361, 72.6110),
    "Rani-no-Haziro": (23.0365, 72.6114),
    "Badshah-no-Haziro": (23.0369, 72.6118),
    "Jami Masjid": (23.0373, 72.6122),
}
STOP_IMAGES = {
    stop: f"https://placehold.co/400x200?text={stop.replace(' ', '+')}" for stop in STOP_COORDS
}
STOP_TRIVIA = {
    "Swaminarayan Temple, Kalupur": ("In which year was the Swaminarayan Temple built?", "1822"),
    "Kavi Dalpatram Chowk": ("Who was Kavi Dalpatram?", "Poet"),
    "Lambeshwar Ni Pol": ("What is a 'Pol' in Ahmedabad?", "Traditional housing cluster"),
    "Calico Dome": ("What was the Calico Dome famous for?", "Textiles"),
    # ... add more trivia for other stops as needed ...
}

# --- TIMER HELPERS ---
START_TIME_FILE = "walk_start_time.json"
def load_start_time():
    if os.path.exists(START_TIME_FILE):
        with open(START_TIME_FILE, "r") as f:
            return json.load(f)
    return None

def save_start_time(start_time):
    with open(START_TIME_FILE, "w") as f:
        json.dump(start_time, f)

# --- MAP ---
def render_walk_map(current_location, previous_locations):
    coords = [STOP_COORDS[stop] for stop in STOP_COORDS]
    stops = list(STOP_COORDS.keys())
    # Find index of current location
    if current_location in stops:
        curr_idx = stops.index(current_location)
    else:
        curr_idx = -1
    # Create folium map centered on the route
    avg_lat = sum([lat for lat, lon in coords]) / len(coords)
    avg_lon = sum([lon for lat, lon in coords]) / len(coords)
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=16)
    # Add all pins
    for i, (stop, (lat, lon)) in enumerate(STOP_COORDS.items()):
        color = "red" if stop == current_location else ("blue" if stop in previous_locations else "gray")
        folium.Marker([lat, lon], popup=f"{i+1}. {stop}", icon=folium.Icon(color=color)).add_to(m)
    # Draw route up to current location
    if curr_idx >= 0:
        folium.PolyLine(coords[:curr_idx+1], color="green", weight=5, opacity=0.8).add_to(m)
        if curr_idx < len(coords)-1:
            folium.PolyLine(coords[curr_idx:len(coords)], color="gray", weight=3, opacity=0.5, dash_array="5,10").add_to(m)
    else:
        folium.PolyLine(coords, color="gray", weight=3, opacity=0.5, dash_array="5,10").add_to(m)
    return m

# --- TIMER DISPLAY ---
def display_timer():
    start_time = load_start_time()
    if start_time:
        start_dt = datetime.datetime.fromisoformat(start_time)
        elapsed = datetime.datetime.now() - start_dt
        st.info(f"⏱️ Walk started at {start_dt.strftime('%H:%M:%S')}. Elapsed: {str(elapsed).split('.')[0]}")
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
    if st.sidebar.button("Login"):
        if host_id == HOST_ID and host_pass == HOST_PASS:
            st.session_state["is_admin"] = True
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
        edited_route = st.experimental_data_editor(route, num_rows="dynamic", key="route_editor")
        if st.button("Save Route"):
            save_route(edited_route)
            st.success("Route updated! All clients will see the changes.")
        st.write("Current Route:")
        for i, stop in enumerate(route, 1):
            col1, col2 = st.columns([8,2])
            with col1:
                is_current = (stop == current_location)
                is_previous = (stop in previous_locations)
                style = "current-location" if is_current else ("previous-location" if is_previous else "")
                label = " (Current Location)" if is_current else (" (Previous Location)" if is_previous else "")
                st.markdown(f"<span class='{style}'><b>{i}. {stop}</b>{label}</span>" if style else f"{i}. {stop}", unsafe_allow_html=True)
            with col2:
                if st.button("Set as Current", key=f"set_{i}"):
                    if stop != current_location and current_location:
                        prevs = load_previous_locations()
                        if current_location not in prevs:
                            prevs.append(current_location)
                            save_previous_locations(prevs)
                    save_current_location(stop)
                    st.session_state["current_location"] = stop
                    st.experimental_rerun()
else:
    st.sidebar.markdown(f"**Current Location:**\n\n<span class='current-location'>{current_location or 'Not set'}</span>", unsafe_allow_html=True)
    st.sidebar.markdown("**Previous Locations:**", unsafe_allow_html=True)
    if previous_locations:
        for loc in previous_locations:
            st.sidebar.markdown(f"<span class='previous-location'>{loc}</span>", unsafe_allow_html=True)
    else:
        st.sidebar.markdown("<span class='previous-location'>None</span>", unsafe_allow_html=True)
    st.subheader("Heritage Walk Route")
    route = load_route()
    for i, stop in enumerate(route, 1):
        is_current = (stop == current_location)
        is_previous = (stop in previous_locations)
        style = "current-location" if is_current else ("previous-location" if is_previous else "")
        label = " (Current Location)" if is_current else (" (Previous Location)" if is_previous else "")
        with st.container():
            st.markdown(f"<div class='heritage-stop'><span class='{style}'><b>{i}. {stop}</b>{label}</span></div>" if style else f"<div class='heritage-stop'>{i}. <b>{stop}</b></div>", unsafe_allow_html=True)
            if is_current or is_previous:
                with st.expander("Show info about this site"):
                    # Show image
                    unsplash_img = get_unsplash_image(f"{stop} Ahmedabad")
                    st.image(unsplash_img, use_column_width=True)
                    with st.spinner("Fetching info..."):
                        info = get_site_info(stop, model_choice)
                    st.markdown(info)
                    # Trivia/Quiz
                    q_and_a = STOP_TRIVIA.get(stop)
                    if q_and_a:
                        question, correct_answer = q_and_a
                        st.markdown(f"**Trivia:** {question}")
                        user_key = f"trivia_{stop}".replace(" ", "_")
                        user_answer = st.text_input("Your answer:", key=user_key)
                        if st.button("Submit", key=f"submit_{user_key}"):
                            if "trivia_answers" not in st.session_state:
                                st.session_state["trivia_answers"] = {}
                            st.session_state["trivia_answers"][user_key] = user_answer
                        # Show feedback
                        if "trivia_answers" in st.session_state and user_key in st.session_state["trivia_answers"]:
                            given = st.session_state["trivia_answers"][user_key]
                            if given.strip().lower() == correct_answer.strip().lower():
                                st.success("Correct!")
                            else:
                                st.error(f"Wrong! Correct answer: {correct_answer}")
            else:
                st.markdown("<span class='locked-info'>🔒 Info locked until you reach this stop</span>", unsafe_allow_html=True)

    # --- ADMIN: Show all trivia answers ---
    if user_type == "Host (Admin)" and st.session_state.get("is_admin"):
        st.markdown("---")
        st.subheader("Trivia Answers (All Users)")
        if "trivia_answers" in st.session_state:
            for key, ans in st.session_state["trivia_answers"].items():
                stop_name = key.replace("trivia_", "").replace("_", " ")
                q_and_a = STOP_TRIVIA.get(stop_name)
                if q_and_a:
                    _, correct_answer = q_and_a
                    correct = ans.strip().lower() == correct_answer.strip().lower()
                    st.markdown(f"**{stop_name}:** {ans} - {'✅' if correct else '❌'} (Correct: {correct_answer})")
        else:
            st.info("No trivia answers submitted yet.")

    st.markdown("---")
    st.subheader("Ask about the Heritage Walk (Chatbot)")
    st.markdown("<i>Chatbot will answer only about the current or previous location, or general walk info.</i>", unsafe_allow_html=True)
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    user_query = st.text_input("Type your question here", key="chat_input")
    if st.button("Ask", key="ask_btn") and user_query:
        # Add context about the walk and restrict to current/previous location
        context = f"Ahmedabad Heritage Walk route: {', '.join(route)}. "
        if current_location:
            context += f"Current location: {current_location}. "
        if previous_locations:
            context += f"Previous locations: {', '.join(previous_locations)}. "
        prompt = context + "User question: " + user_query
        with st.spinner("Thinking..."):
            answer = get_ai_response(prompt, model_choice)
        st.session_state["chat_history"].append((user_query, answer))
    # Display chat history
    for q, a in st.session_state["chat_history"][-10:]:
        st.markdown(f"<div class='chat-bubble-user'>{q}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='chat-bubble-bot'>{a}</div>", unsafe_allow_html=True)

    st.info("You can ask about the current or previous stop, or general info about Ahmedabad's heritage walk.")

display_timer()
st.subheader("🗺️ Heritage Walk Map")
try:
    m = render_walk_map(current_location, previous_locations)
    st_folium(m, width=700, height=400)
except Exception as e:
    st.warning(f"Map could not be rendered: {e}")
    st.map(pd.DataFrame([
        {"lat": lat, "lon": lon, "stop": stop} for stop, (lat, lon) in STOP_COORDS.items()
    ]), latitude="lat", longitude="lon")

# --- HOST: START WALK BUTTON ---
if user_type == "Host (Admin)" and st.session_state.get("is_admin"):
    if not load_start_time():
        if st.button("Start Walk 🏁"):
            now = datetime.datetime.now().isoformat()
            save_start_time(now)
            st.experimental_rerun()

st.caption("Made with ❤️ of Team Neev India")
