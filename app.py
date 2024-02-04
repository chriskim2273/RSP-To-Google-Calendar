import base64
import csv
import streamlit as st
from streamlit_oauth import OAuth2Component
import os
import json
import requests
from datetime import datetime
import pandas as pd
import re

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Set environment variables
AUTHORIZE_URL = os.environ.get('AUTHORIZE_URL')#,st.secrets["AUTHORIZE_URL"])
TOKEN_URL = os.environ.get('TOKEN_URL')#,st.secrets["TOKEN_URL"])
REFRESH_TOKEN_URL = os.environ.get('REFRESH_TOKEN_URL')#,st.secrets["REFRESH_TOKEN_URL"])
REVOKE_TOKEN_URL = os.environ.get('REVOKE_TOKEN_URL')#,st.secrets["REVOKE_TOKEN_URL"])
CLIENT_ID = os.environ.get('CLIENT_ID')#,st.secrets["CLIENT_ID"])
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')#,st.secrets["CLIENT_SECRET"])
REDIRECT_URI = 'https://rsp-to-app-calendar-cy7d5hqhrsdu64brgr2knj.streamlit.app'#os.environ.get('REDIRECT_URI',st.secrets["REDIRECT_URI"])
SCOPE = os.environ.get('SCOPE')#,st.secrets["SCOPE"])

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

        nested_data = df.values.tolist()
        for row in nested_data:
            for item in row:
                print(item)
                st.write(item)
        bytes_data = uploaded_file.read()
        st.write("Filename:", uploaded_file.name)
        st.write(bytes_data)
    logout = st.button("Logout")
    if logout:
        del st.session_state["token"]

class Shift():
    def __init__(self, day_of_week, date, worker, start_time, end_time, location):
        self.day_of_week = day_of_week
        self.date = date
        self.worker = worker
        self.start_time = start_time
        self.end_time = end_time
        self.location = location

    def change_times(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time

    def __str__(self):
        return f"[Shift: {self.day_of_week} - {self.date} : {self.worker} > ({self.start_time} - {self.end_time}) > {self.location} & {self.shift_detail}]"



uploaded_file = st.file_uploader("Choose a CSV file", type='csv', key = "test")

DAYS_OF_WEEK = {"SUNDAY","MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY"}
rows_to_cols = {}
# Process the uploaded file
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.dataframe(df)

    nested_data = df.values.tolist()
    for i, row in enumerate(nested_data):
        for j, item in enumerate(row):
            print(f"({str(i)},{str(j)}): {str(item)}")
            item = str(item)
            if len(item) > 0:
                if item == "nan":
                    continue
                if item[0] == '[' and item[-1] == ']':
                    j = j - 1
                if j not in rows_to_cols:
                    rows_to_cols[j] = []
                rows_to_cols[j].append(item)
            #st.write(f"({str(i)},{str(j)}): {item}")

    st.write(str(rows_to_cols))

    current_day = ""
    date = ""
    all_shifts = []
    shift_workers = [] 
    shift_detail = ""
    shift_start = ""
    shift_end = ""
    shift_location = ""
    for _ in rows_to_cols:
        for text in rows_to_cols[_]:
            if text.upper() in DAYS_OF_WEEK:
                current_day = text
            date_pattern = r"^\d{1,2}/\d{1,2}"
            if re.match(date_pattern, text):
                date = text
            time_and_location_pattern = r"(\d{1,2}(?::\d{2})?(?:AM|PM)?)\s*-\s*(\d{1,2}(?::\d{2})?(?:AM|PM)?)\s*\((.*?)\)"
            match = re.match(time_and_location_pattern, text)
            if match:
                start_time, end_time, shift_location = match.groups()
            shift_time_pattern = r"\w+:\s\w+"
            if re.match(shift_time_pattern, text):
                split_text = text.split(':')
                shift_detail = "".join(split_text[0].split()) # remove whitepace
                shift_workers = "".join(split_text[1].split()) # remove whitespace
                shift_workers = shift_workers.split(',')

            # Try to implement time change in shifts (specified afterwards)
            time_change_pattern = r'\[(\d{1,2}[APMapm]{2})-(\d{1,2}[APMapm]{2})\]'
            match = re.match(time_change_pattern, text)
            if match:
                start_time, end_time = match.groups()
                all_shifts[-1].change_times(start_time, end_time)
                shift_workers = []
                shift_details = ""
                continue

            if current_day and date and shift_workers and shift_detail and shift_start and shift_end and shift_location:
                for shift_worker in shift_workers:
                    all_shifts.append(Shift(current_day, date, shift_worker, shift_start, shift_end, shift_location, shift_detail))
                shift_workers = []
                shift_detail = ""
        
    st.write(rows_to_cols)
    st.write(str(all_shifts))

class Shift():
    def __init__(self, day_of_week, date, worker, start_time, end_time, location, shift_detail):
        self.day_of_week = day_of_week
        self.date = date
        self.worker = worker
        self.start_time = start_time
        self.end_time = end_time
        self.location = location
        self.shift_detail = shift_detail
    
    def change_times(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time

    def __str__(self):
        return f"[Shift: {self.day_of_week} - {self.date} : {self.worker} > ({self.start_time} - {self.end_time}) > {self.location} & {self.shift_detail}]"


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
