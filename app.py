import base64
import csv
import streamlit as st
from streamlit_oauth import OAuth2Component
import os
import json
import requests
from datetime import datetime
import pandas as pd

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

if "token" not in st.session_state:
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
        """
        # verify the signature is an optional step for security
        payload = id_token.split(".")[1]
        # add padding to the payload if needed
        payload += "=" * (-len(payload) % 4)
        # encode the payload to bytes before decoding from base64url
        try:
            payload_bytes = base64.urlsafe_b64decode(payload.encode('utf-8').decode('utf-8'))
        except Exception as e:
            print(f"Error decoding payload: {e}")
            # handle non-base64 characters
            payload_bytes = base64.urlsafe_b64decode(payload.encode('utf-8').replace('-', '+').replace('_', '/').decode('utf-8'))
        email = payload["email"]
        """
        st.session_state["token"] = result["token"]
        st.rerun()
else:
    st.write("You are logged in!")
    st.write(st.session_state["token"])
    uploaded_file = st.file_uploader("Choose a CSV file", type='csv')

    # Process the uploaded file
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df)

        spamreader = csv.reader(uploaded_file, delimiter=',')
        for row in spamreader:
            st.write(row)
        bytes_data = uploaded_file.read()
        st.write("Filename:", uploaded_file.name)
        st.write(bytes_data)
    logout = st.button("Logout")
    if logout:
        del st.session_state["token"]


def create_events():
    # Define the URL
    url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'

    # Define the headers
    headers = {
        'Authorization': 'Bearer ' + str(st.session_state['token']),
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    # Define the event
    event = {
        'summary': 'New Event',
        'location': '800 Howard St., San Francisco, CA 94103',
        'description': 'A chance to hear more about Google\'s developer products.',
        'start': {
            'dateTime': '2024-02-28T09:00:00-07:00',
            'timeZone': 'America/Los_Angeles',
        },
        'end': {
            'dateTime': '2024-02-28T17:00:00-07:00',
            'timeZone': 'America/Los_Angeles',
        },
    }

    # Send the POST request
    response = requests.post(url, headers=headers, data=json.dumps(event))

    # Check the response
    if response.status_code == 200:
        print('Event created successfully')
    else:
        print('Failed to create event:', response.content)
