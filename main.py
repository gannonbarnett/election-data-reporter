import requests 
import json 
import pickle 
import datetime 
import os
import sched
import time
from twilio.rest import Client

CONFIG_FILE_PATH = "config.json"
config = json.load(open(CONFIG_FILE_PATH))
ADMIN_PHONES_KEY = "ADMIN_PHONES"
TWILIO_ACCOUNT_SID_KEY = "TWILIO_ACCOUNT_SID"
TWILIO_AUTH_TOKEN_KEY = "TWILIO_AUTH_TOKEN"

"""

Handling records and alert system.

The record file holds the data for which the last alert 
was sent

"""
account_sid = config[TWILIO_ACCOUNT_SID_KEY]
auth_token = config[TWILIO_AUTH_TOKEN_KEY]
client = Client(account_sid, auth_token)

RECORDS_FILE_PATH = "records.json"

# send a message to each of the phone numbers specified
def send_message(phones, message):
    for p in phones: 
        message = client.messages.create(
                            body=message,
                            from_='+18575765754',
                            to=p)

# update record and send alert as needed
def add_record_and_alert(new_record):
    alert_message = "PREDICTIT ALERT\n"
    should_alert = False

    last_record = json.load(open(RECORDS_FILE_PATH))

    # check MOV 
    if last_record["mov"] != new_record["mov"]: 
        should_alert = True
        alert_message += "MOV changed from " + str(last_record["mov"]) + " to " + str(new_record["mov"]) + ".\n"

    # check turnout 
    last_turnout_m = last_record["votes"]["proj"] / 1000000
    new_turnout_m = new_record["votes"]["proj"] / 1000000
    if abs(last_turnout_m - new_turnout_m) > 1: 
        should_alert = True 
        alert_message += "Projected turnout changed from " + str(int(last_turnout_m * 100)/ 100.0) + "m to "
        alert_message += str(int(new_turnout_m * 100)/ 100.0) + "m.\n"

    # send alert if should send
    if should_alert: 
        print("Sending alert...")
        send_message(config[ADMIN_PHONES_KEY], alert_message)
        current_records = json.load(open(RECORDS_FILE_PATH))
        current_records = new_record
        json.dump(current_records, open(RECORDS_FILE_PATH, "w"))


"""

Processing data pipeline below

"""

METADATA_ENDPOINT = "https://interactives.ap.org/elections/live-data/production/2020-11-03/president/metadata.json"
STATEPRES_ENDPOINT_WO_JSON = "https://interactives.ap.org/elections/live-data/production/2020-11-03/president/"

STATE_INITIALS = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA", 
                    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
                    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
                    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
                    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

METADATA_PKL_FILE = "metadata.pkl"
ALLSTATEELECTION_PKL_FILE = "state_elect.pkl"

PROJ_TOTAL_VOTES_KEY = "projected_total_votes"
REAL_TOTAL_VOTES_KEY = "real_total_votes"
DELTA_KEY = "delta"

PROJ_PCT_KEY = "projected_percent"
REAL_PCT_KEY = "real_percent"

CANDIDATES_KEY = "candidates"
STATES_KEY = "states"

### Downloading data pipeline below 

# download metadata
def download_metadata():
    f = open(METADATA_PKL_FILE, "wb")

    json_result = requests.get(METADATA_ENDPOINT).text
    python_result = json.loads(json_result)
    pickle.dump(python_result, f)
    f.close()
    return python_result

# download a single state's data
def download_state_election_data(stateInitials):
    endpoint = STATEPRES_ENDPOINT_WO_JSON + stateInitials + ".json"
    json_result = requests.get(endpoint).text
    python_result = json.loads(json_result)
    return python_result
    
# download all state election data
def download_all_state_election_data(metadata):
    result = {STATES_KEY: {}}
    for i, state in enumerate(STATE_INITIALS):
        downloaded_state_data = download_state_election_data(state)
        result[STATES_KEY][state] = parse_state_election_data(metadata, downloaded_state_data)

    # json.dump(result, open("parsed_results.json", "w"))

    result["timestamp"] = datetime.datetime.utcnow()
    f = open(ALLSTATEELECTION_PKL_FILE, "wb")
    pickle.dump(result, f)
    f.close()

# download metadata and all states data
def download_all_data():
    metadata = download_metadata()
    download_all_state_election_data(metadata)
    
#### Metadata and election data retrieval from pickled files 

def get_metadata():
    f = open(METADATA_PKL_FILE, "rb")
    result = pickle.load(f)
    f.close()
    return result

def get_all_state_election_data():
    f = open(ALLSTATEELECTION_PKL_FILE, "rb")
    result = pickle.load(f)
    f.close()
    return result

def get_candidate_name(metadata, id):
    return metadata["candidates"][id]["fullName"]

### Generating reports 

# aggregate state election statistics
def parse_state_election_data(metadata, data):
    parsed_data = {CANDIDATES_KEY:{}}

    precinct_results = data["results"][0]["results"]
    summary = data["results"][0]["summary"]
    eevp = summary["eevp"] / 100.0

    state_real_total_votes = 0
    state_proj_total_votes = 0

    for precinct, precinct_data in precinct_results.items():
        for entry in precinct_data["results"]:
            name = get_candidate_name(metadata, entry["candidateID"])
            cand_real_total_votes = entry["voteCount"]
            cand_proj_total_votes = cand_real_total_votes / eevp 

            if name not in parsed_data[CANDIDATES_KEY]:
                parsed_data[CANDIDATES_KEY][name] = {REAL_TOTAL_VOTES_KEY: 0, PROJ_TOTAL_VOTES_KEY: 0}
            
            parsed_data[CANDIDATES_KEY][name][REAL_TOTAL_VOTES_KEY] += int(cand_real_total_votes)
            parsed_data[CANDIDATES_KEY][name][PROJ_TOTAL_VOTES_KEY] += int(cand_proj_total_votes)

            state_real_total_votes += cand_real_total_votes
            state_proj_total_votes += cand_proj_total_votes
    parsed_data[REAL_TOTAL_VOTES_KEY] = state_real_total_votes
    parsed_data[PROJ_TOTAL_VOTES_KEY] = state_proj_total_votes
    parsed_data[DELTA_KEY] = state_proj_total_votes - state_real_total_votes

    return parsed_data

# generate a new report and record 
def generate_report(should_print=False):
    new_record = {} 

    metadata = get_metadata()
    all_states_data = get_all_state_election_data()
    
    new_record["timestamp"] = str(all_states_data["timestamp"])

    net_election_results = {}
    net_votes_real = 0
    net_votes_proj = 0
    net_votes_delta = 0

    for state, state_data in all_states_data[STATES_KEY].items(): 
        net_votes_real += state_data[REAL_TOTAL_VOTES_KEY]
        net_votes_proj += state_data[PROJ_TOTAL_VOTES_KEY]
        net_votes_delta += state_data[DELTA_KEY]

        for candidate_name, candidate_data in state_data[CANDIDATES_KEY].items(): 
            if candidate_name not in net_election_results:
                net_election_results[candidate_name] = {REAL_TOTAL_VOTES_KEY:0, PROJ_TOTAL_VOTES_KEY: 0}
            net_election_results[candidate_name][REAL_TOTAL_VOTES_KEY] += candidate_data[REAL_TOTAL_VOTES_KEY]
            net_election_results[candidate_name][PROJ_TOTAL_VOTES_KEY] += candidate_data[PROJ_TOTAL_VOTES_KEY]

    new_record["votes"] = {"real" : net_votes_real, "proj": net_votes_proj, "delta": net_votes_delta}


    if (should_print):
        print("-----------report start")
        print("Data refreshed at " + str(all_states_data["timestamp"]))
        print()
        print("Net votes\treal: " + str(net_votes_real) + "\tproj:" + str(net_votes_proj) + "\tdelta:" + str(net_votes_delta))
        print()

    for candidate_name in ["Joe Biden", "Donald Trump"]:
        data = net_election_results[candidate_name]
        
        data[REAL_PCT_KEY] = int((data[REAL_TOTAL_VOTES_KEY] / net_votes_real) * 10000) / 100.0
        data[PROJ_PCT_KEY] = int((data[PROJ_TOTAL_VOTES_KEY] / net_votes_proj) * 10000) / 100.0
        if (should_print): 
            print(candidate_name + "\treal:" + str(data[REAL_TOTAL_VOTES_KEY]) + ", " + str(data[REAL_PCT_KEY]) + "%\tproj:" + str(data[PROJ_TOTAL_VOTES_KEY]) + ", " + str(data[PROJ_PCT_KEY]) + "%")

    biden = net_election_results["Joe Biden"]
    trump = net_election_results["Donald Trump"]

    
    mov = int((biden[PROJ_PCT_KEY] - trump[PROJ_PCT_KEY]) * 10) / 10
    new_record["mov"] = mov
    if (should_print):
        print()
        print("Estimated MOV: " + str(mov))
        print("-----------report end")

    add_record_and_alert(new_record)


"""

Cron job scheduler

"""
s = sched.scheduler(time.time, time.sleep)

def check_for_alerts(sc): 
    print("checking for alerts...")
    download_all_data()
    generate_report() 
    print("check complete")

    s.enter(config["CRON_FREQ"], 1, check_for_alerts, (sc,))
    
s.enter(0, 1, check_for_alerts, (s,))
s.run()
