import streamlit as st
import requests

# Load from secrets.toml
TOKEN = st.secrets["gitlab"]["token"]
BASE_URL = st.secrets["gitlab"]["base_url"]
HEADERS = {"Private-Token": TOKEN}

st.set_page_config(layout="wide", page_title="GitLab Tracker")
st.title("🔍 GitLab User Search")

query = st.text_input("Enter GitLab Username, Email, or Name:")

if query:
    res = requests.get(f"{BASE_URL}/users?search={query}", headers=HEADERS)
    if res.status_code == 200:
        users = res.json()
        if users:
            st.write(f"Found {len(users)} matching user(s):")
            for user in users:
                if st.button(f"👤 {user['name']} ({user['username']})"):
                    st.session_state['selected_user_id'] = user['id']
                    st.switch_page("pages/1_User_Details.py")
        else:
            st.error("❌ No users found.")
    else:
        st.error("❌ Failed to fetch users.")
