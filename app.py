import base64
from calendar import calendar
import csv
from distutils.command.upload import upload
import time
from tracemalloc import start
import streamlit as st
from streamlit_oauth import OAuth2Component
import os
import json
import requests
from datetime import datetime
import pandas as pd
import re
from icalendar import Calendar, Event, vCalAddress, vText
import pytz
from datetime import datetime
import calendar

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

def convert_to_military_time(time_str):
    time_str = time_str.strip()
    #st.write(time_str)
    time = time_str[:-2]
    time_split = time.split(":")
    hour = int(time_split[0])
    minute = int(time_split[1]) if len(time_split) == 2 and time_split[1] else 0
    meridian = time_str[-2:].upper()

    if hour == 12:
        hour = 0  # Special case: 12AM becomes 00
    if meridian == "PM":
        hour += 12
    return hour, minute

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

    def get_worker(self):
        return self.worker

    def is_worker(self, worker):
        return self.worker == worker

    def get_start_datetime(self):
        month, day = self.date.split("/")
        start_hour, start_minute = convert_to_military_time(self.start_time)
        #st.write(f"{self.start_time} -> {str(start_hour)}")
        return datetime(datetime.now().year, int(month), int(day), start_hour, start_minute, 0)

    def get_end_datetime(self):
        month, day = self.date.split("/")
        day = int(day)
        month = int(month)
        year = datetime.now().year
        end_hour, end_minute = convert_to_military_time(self.end_time)
        if self.end_time[-2:] == "AM" and self.start_time[-2:] == "PM":
            day += 1
            max_days = calendar.monthrange(datetime.now().year, month)[1]
            # Increment to next month
            if day > max_days:
                day = 1
                month += 1
                if month > 12:
                    month = 1
                    year += 1

        #st.write(f"{self.end_time} -> {str(end_hour)}")
        return datetime(year, month, day, end_hour, end_minute, 0)

    def get_title(self):
        return f"RSP Shift ({self.worker}): {self.location} - {self.shift_detail}"

    def __str__(self):
        return f"[Shift: {self.day_of_week} - {self.date} : {self.worker} > ({self.start_time} - {self.end_time}) > {self.location} & {self.shift_detail}]"

def get_calendar_id():
    calendar_name = "RSP Shifts"
    # Define the base URL for calendar list
    calendar_list_url = 'https://www.googleapis.com/calendar/v3/users/me/calendarList'

    calendars_url = 'https://www.googleapis.com/calendar/v3/calendars/'

    # Define the headers
    headers = {
        'Authorization': 'Bearer ' + str(st.session_state['token']),
        'Accept': 'application/json',
    }

    # Send the GET request to retrieve calendar list
    response = requests.get(calendar_list_url, headers=headers)

    if response.status_code == 200:
        calendars = response.json().get('items', [])
        for calendar in calendars:
            if calendar.get('summary') == calendar_name:
                return calendar.get('id')
        print(f"Calendar '{calendar_name}' not found.")
        st.write(f"Calendar '{calendar_name}' not found.")
        st.write(f"Creating calendar '{calendar_name}'...")
        new_calendar = {
            'summary': calendar_name,  # Customize the calendar name
            'timeZone': 'America/New_York'
        }
        create_response = requests.post(calendars_url, headers=headers, data=json.dumps(new_calendar))
        if create_response.status_code == 200:
            time.sleep(5)
            st.write(f"Created calendar '{calendar_name}!")
            return create_response.json().get('id')
        else:
            print('Failed to create calendar:', create_response.content)
            st.write('Failed to create calendar:', create_response.content)
            return None
    else:
        print('Error retrieving calendar list:', response.content)
        st.write('Error retrieving calendar list:', response.content)
        return None


def create_event_on_google_cal(shift, calendar_id):
    # Define the base URL for calendars
    calendars_url = 'https://www.googleapis.com/calendar/v3/calendars/'

    # Define the headers
    headers = {
        'Authorization': 'Bearer ' + str(st.session_state['token']),
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    # Define the event
    event = {
        'summary': shift.get_title(),
        'location': shift.location,
        'description': str(shift),
        'start': {
            'dateTime': shift.get_start_datetime().strftime("%Y-%m-%dT%H:%M:%S%z"),
            'timeZone': 'America/New_York',
        },
        'end': {
            'dateTime': shift.get_end_datetime().strftime("%Y-%m-%dT%H:%M:%S%z"),
            'timeZone': 'America/New_York',
        },
    }
    #st.write(event)
    # Send the POST request to add the event
    events_url = calendars_url + f'{calendar_id}/events'
    response = requests.post(events_url, headers=headers, data=json.dumps(event))

    # Check the response
    if response.status_code == 200:
        st.write("Event created successfully!")
        #print('Event created successfully!')
        return True
    else:
        print('Failed to create event:', response.content)
        st.write('Failed to create event:', response.content)
        st.write('Failed event data: ', str(shift))
        return False

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
        #st.write(result)
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
        st.session_state["token"] = id_token
        st.rerun()
else:
    st.write("You are logged in! Refresh to log out or log back in!")
    #st.write(st.session_state["token"])

    uploaded_file = st.file_uploader("Choose a CSV file", type='csv', key = "test")

    all_shifts = []
    DAYS_OF_WEEK = {"SUNDAY","MONDAY","TUESDAY","WEDNESDAY","THURSDAY","FRIDAY","SATURDAY"}
    TYPES = {"Dispatch", "E/A", "E/SUP","Codispatch", "Field"}
    rows_to_cols = {}
    # Process the uploaded file
    if uploaded_file:
        df = pd.read_csv(uploaded_file)

        nested_data = df.values.tolist()
        for i, row in enumerate(nested_data):
            for j, item in enumerate(row):
                #print(f"({str(i)},{str(j)}): {str(item)}")
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

        #st.write(str(rows_to_cols))

        current_day = ""
        date = ""
        shift_workers = [] 
        shift_detail = ""
        shift_start = ""
        shift_end = ""
        time_adjustments = {
        }
        son = ""
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
                    shift_start, shift_end, shift_location = match.groups()
                if ':' in text and len(text.split(':')) == 2:
                    split_text = text.split(':')
                    shift_detail = "".join(split_text[0].split()) # remove whitepace
                    if shift_detail not in TYPES:
                        continue
                    shift_workers = "".join(split_text[1].split()) # remove whitespace
                    shift_workers = shift_workers.split(',')

                    # Handle Edge case of Time Adjustments
                    parenthesis_pattern = re.compile(r'\(([^)]+)\)$') #Dispatch: S15 (9PM)
                    for idx, shift_worker in enumerate(shift_workers):
                        match = parenthesis_pattern.search(shift_worker)
                        if match:
                            ##st.write(match)
                            content_inside_parentheses = match.group(1)
                            # Assuming we are fixing the start time...?
                            time_adjustment = content_inside_parentheses.strip()
                            time_adjustment_mil, _min = convert_to_military_time(time_adjustment)
                            if time_adjustment_mil <= 12:
                                time_adjustments[shift_worker] = (shift_start, time_adjustment)
                            else:
                                time_adjustments[shift_worker] = (time_adjustment, shift_end)
                            shift_workers[idx] = parenthesis_pattern.sub('', shift_worker)
                    #st.write(shift_workers)

                # Try to implement time change in shifts (specified afterwards)

                time_change_pattern = r"^\[(\d{1,2}[APM]{2})-(\d{1,2}[APM]{2})\]$"

                match = re.match(time_change_pattern, text)
                if match and all_shifts:
                    start_time, end_time = match.groups()
                    for i in range(len(shift_workers)):
                        #st.write(f'matched... {start_time}  ->  {end_time} : {str(all_shifts[-(i+1)])}' ) 
                        all_shifts[-(i+1)].change_times(start_time, end_time)
                    #shift_workers = []
                    shift_details = ""
                    #st.write(f'matched... {start_time}  ->  {end_time} : {str(all_shifts[-1])}' )
                    continue

                if current_day and date and shift_workers and shift_detail and shift_start and shift_end and shift_location:
                    if shift_detail not in TYPES:
                        continue
                    for shift_worker in shift_workers:
                        if shift_worker in time_adjustments:
                            all_shifts.append(Shift(current_day, date, shift_worker, time_adjustments[shift_worker][0], time_adjustments[shift_worker][1], shift_location, shift_detail))
                        else:
                            all_shifts.append(Shift(current_day, date, shift_worker, shift_start, shift_end, shift_location, shift_detail))
                    #print(f"[Shift: {current_day} - {date} : {shift_workers} > ({shift_start} - {shift_end}) > {shift_location} & {shift_detail}]")
                    #shift_workers = []
                    shift_detail = ""
                
        #st.write(rows_to_cols)
        #for shift in all_shifts:
        #    st.write(shift)
        show_df = st.toggle('Show DataFrame')
        show_shifts = st.toggle('Show All Shifts In String Format')

        if show_shifts:
            for shift in all_shifts:
                st.write(shift)
        if show_df:
            st.dataframe(df)

        worker_input = st.text_input(
                "Please Enter Worker String (e.g. S12)",
            )
        shifts_available = False
        for shift in all_shifts:
            if shift.is_worker(worker_input):
                shifts_available = True
                break
        if worker_input and shifts_available:
            # Generate .ics file
            user_shifts = []
            for shift in all_shifts:
                if shift.is_worker(worker_input):
                    user_shifts.append(shift)
            st.divider()
            st.write(f"Worker String Occurences in CSV: {df.to_string().count(worker_input)}")
            st.write(f"Amount of Shifts Found and Processed: {len(user_shifts)}")
            st.write("Please make sure the two values match. (If not, it could indicate a disconnect)")
            st.divider()
            st.write("Found Shifts (if Empty, invalid Worker String or no Shifts):")
            for shift in user_shifts:
                st.write(shift)
            st.divider()
            options = st.multiselect(
                "Shifts to Exclude In Import to Google Calendar or .ics File:",
                user_shifts,
                [])

            st.write("Shifts To Exclude Selected:")
            for shift in options:
                st.write(shift)
            st.write("Remaining Shifts (To be added):")
            for shift in user_shifts:
                if str(shift) not in options:
                    st.write(shift)
            st.divider()
            cal = Calendar()
            for shift in user_shifts:
                if str(shift) in options:
                    continue
                event = Event()
                event.add('summary', shift.get_title())
                event.add('description', str(shift))
                event.add('dtstart', shift.get_start_datetime())
                event.add('dtend', shift.get_end_datetime())
                event.add('dtstamp', datetime.now())
                event['location'] = vText(shift.location)
                cal.add_component(event)

            st.download_button(
            label="Download as .ics file",
            data=cal.to_ical(),
            file_name='RSP_SHIFT_DATA.ics',
            mime='text/ics',
            )

            success_count = 0
            self_shift_count = 0
            upload_shifts_to_gcal = st.button("Upload to Google Calendar")
            if upload_shifts_to_gcal:
                progress_text = "Uploading Shifts to Google Calendar..."
                progress_bar = st.progress(0, text=progress_text)

                calendar_id = None
                for num, shift in enumerate(all_shifts):
                    if shift.is_worker(worker_input):
                        if str(shift) in options:
                            continue
                        time.sleep(2)
                        self_shift_count += 1
                        progress_bar.progress(int(((100/len(all_shifts)) * num) + 1), text=progress_text)
                        if not calendar_id:
                            calendar_id = get_calendar_id()
                        success = create_event_on_google_cal(shift, calendar_id)
                        if success:
                            success_count += 1
                time.sleep(1)
                progress_bar.empty()
                #st.write(f"count: {self_shift_count} - success: {success_count}")
                if self_shift_count == success_count:
                    st.balloons()
                    st.success('All Shifts Uploaded Successfully!', icon="✅")
                else:
                    st.error('Some shifts failed to upload...', icon="🚨")



"""
FIX: Dispatch: S15 (9PM) -> ASK JIN WHAT THE TIME IS...
ASK: JIN what the different types are.
FIX THE ONES WITH DIFFETNT TIMES [X - Y] CORRECTION <- Isn't being uploaded. (FIXED)
ADD: FLAG TO CHANGE TITLE TO NOTIFY USER TO CHECK SHIFT...
"""