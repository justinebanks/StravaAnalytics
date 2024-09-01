from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import pandas as pd

import os
import threading
import time


request_received = False
param_dict = {}


# Converts A Dictionary to a Query String
def get_query_string(params: dict):
    final_string = "?"

    for key in params:
        final_string += str(key) + "=" + str(params[key]) + "&"

    return final_string


# Converts A List of Dictionaries Into A Pandas DataFrame
def dict_to_df(data: list[dict], selected_columns=[]):
    if len(selected_columns) == 0:
        data = [ { key: value for key, value in data_item.items() } for data_item in data]
    else:
        data = [ { key: value for key, value in data_item.items() if key in selected_columns } for data_item in data]

    df = pd.DataFrame.from_records(data)
    return df


# Defines HTTP Server To Accept Data From Strava OAuth Redirect
class StravaExchangeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global param_dict
        global request_received

        request_received = True

        try:
            params = self.path.split("?")[1].split("&")

            for param in params:
                parts = param.split("=")
                param_dict.update({ parts[0]: parts[1] })
            
            if "terminate" in param_dict.keys():
                self.server.shutdown()
                return
            
        except IndexError:
            print("Index Error")

        self.send_response(200, "<html><head></head><body><h1>Redirect Success</h1><body></html>")
        self.end_headers()



# Separate Thread To Run Server
def run_server():
    server = HTTPServer(("localhost", 8000), StravaExchangeHandler)
    server.serve_forever()
    server.server_close()



# Opens Chrome To The OAuth Authorization Page
def get_authentication_code(client_id: int, redirect_url: str, streamlit=False):

    #redirect = "http://localhost:8000" if not streamlit else "http://localhost:8501"

    auth_params = {
        "client_id": client_id,
        "redirect_uri": redirect_url,
        "response_type": "code",
        "scope": "read,activity:read_all",
        "state": "authorized"
    }

    url = "https://www.strava.com/oauth/authorize" + get_query_string(auth_params)

    if not streamlit:
        # Start Server
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Open Browser
        os.system(f"start chrome.exe \"{url}\"")

        while not request_received:
            print("Waiting...")
            time.sleep(1)

        print("Auth Data: ", param_dict)

        # Terminate Server
        #requests.get("http://localhost:8000?terminate=true")
        #server_thread.join()

        return param_dict["code"]

    else:
        #os.system(f"start chrome.exe \"{url}\"")
        #webbrowser.open_new_tab(url)
        return url


# Gets The Access Token Using the Code From the "get_authorization_code" Function
def get_access_token(client_id: int, client_secret: str, code: str):
    token_params = {
        "client_secret": client_secret,
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": code
    }

    token_response = requests.post("https://www.strava.com/api/v3/oauth/token", params=token_params)

    if token_response.status_code != 200:
        print("ERROR")
        print(token_response.json())
        return

    access_token = token_response.json()["access_token"]
    print("Access Token: ", access_token)

    return access_token



def get_athlete(access_token: str):
    athlete_response = requests.get("https://www.strava.com/api/v3/athlete", headers={ "Authorization": f"Bearer {access_token}" })
    athlete_data = athlete_response.json()

    return athlete_data



def get_athlete_activities(access_token: str, start_time, end_time, max_count=30):
    date_format = "%m/%d/%y"

    before = end_time #datetime.strptime(end_time, date_format)
    after = start_time #datetime.strptime(start_time, date_format)

    final_data = []
    more_data = True
    page = 1

    while more_data:
        activities_response = requests.get("https://www.strava.com/api/v3/athlete/activities", 
            headers={
                "Authorization": f"Bearer {access_token}" 
            }, 
            params= {
                "before": int(before.timestamp()), 
                "after": int(after.timestamp()),
                "per_page": max_count,
                "page": page
            }
        )

        if activities_response.status_code != 200:
            print("ERROR from getAthleteActivities")
            print(activities_response.json())
            return
        

        if len(activities_response.json()) < max_count:
            more_data = False
            
        for i in activities_response.json():
            final_data.append(i)
        
        print(str(len(activities_response.json())) + " Entries Recieved From Page " + str(page))
        page += 1
    
    return final_data
