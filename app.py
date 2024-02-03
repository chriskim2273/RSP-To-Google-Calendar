import base64
import streamlit as st
from streamlit_oauth import OAuth2Component
import os
import json

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Set environment variables
AUTHORIZE_URL = os.environ.get('AUTHORIZE_URL',st.secrets["AUTHORIZE_URL"])
TOKEN_URL = os.environ.get('TOKEN_URL',st.secrets["TOKEN_URL"])
REFRESH_TOKEN_URL = os.environ.get('REFRESH_TOKEN_URL',st.secrets["REFRESH_TOKEN_URL"])
REVOKE_TOKEN_URL = os.environ.get('REVOKE_TOKEN_URL',st.secrets["REVOKE_TOKEN_URL"])
CLIENT_ID = os.environ.get('CLIENT_ID',st.secrets["CLIENT_ID"])
CLIENT_SECRET = os.environ.get('CLIENT_SECRET',st.secrets["CLIENT_SECRET"])
REDIRECT_URI = 'https://rsp-to-app-calendar-cy7d5hqhrsdu64brgr2knj.streamlit.app'#os.environ.get('REDIRECT_URI',st.secrets["REDIRECT_URI"])
SCOPE = os.environ.get('SCOPE',st.secrets["SCOPE"])

if "auth" not in st.session_state:
    # create a button to start the OAuth2 flow
    oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_URL, TOKEN_URL, REFRESH_TOKEN_URL, REVOKE_TOKEN_URL)
    result = oauth2.authorize_button(
        name="Continue with Google",
        icon="https://www.google.com.tw/favicon.ico",
        redirect_uri=REDIRECT_URI, #"http://localhost:8501",
        scope=SCOPE, #"openid email profile",
        key="google",
        extras_params={"prompt": "consent"},#, "access_type": "offline"},
        use_container_width=True,
        pkce='S256',
    )
    
    if result:
        st.write(result)
        # decode the id_token jwt and get the user's email address
        id_token = result["token"]["access_token"]
        # verify the signature is an optional step for security
        payload = id_token.split(".")[1]
        # add padding to the payload if needed
        payload += "=" * (-len(payload) % 4)
        # replace url-safe characters
        payload = payload.replace('-', '+').replace('_', '/')
        payload = json.loads(base64.b64decode(payload))
        email = payload["email"]
        st.session_state["auth"] = email
        st.session_state["token"] = result["token"]
        st.rerun()
else:
    st.write("You are logged in!")
    st.write(st.session_state["auth"])
    st.write(st.session_state["token"])
    st.button("Logout")
    del st.session_state["auth"]
    del st.session_state["token"]