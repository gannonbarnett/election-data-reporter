import requests 
import json 
import pickle 
import datetime 

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

PROJ_PCT_KEY = "projected_percent"
REAL_PCT_KEY = "real_percent"

def download_metadata():
    f = open(METADATA_PKL_FILE, "wb")

    json_result = requests.get(METADATA_ENDPOINT).text
    python_result = json.loads(json_result)
    pickle.dump(python_result, f)
    f.close()
    print("Download metadata completed")

def get_metadata():
    f = open(METADATA_PKL_FILE, "rb")
    result = pickle.load(f)
    f.close()
    return result

def download_state_election_data(stateInitials):
    endpoint = STATEPRES_ENDPOINT_WO_JSON + stateInitials + ".json"
    json_result = requests.get(endpoint).text
    python_result = json.loads(json_result)
    return python_result
    
def download_all_state_election_data():
    result = {"states": {}}
    print("Collecting data from 50 states ...")
    for i, state in enumerate(STATE_INITIALS):
        result["states"][state] = download_state_election_data(state)
    result["timestamp"] = datetime.datetime.utcnow()
    f = open(ALLSTATEELECTION_PKL_FILE, "wb")
    pickle.dump(result, f)
    f.close()
    print("Download state election data completed")

def get_all_state_election_data():
    f = open(ALLSTATEELECTION_PKL_FILE, "rb")
    result = pickle.load(f)
    f.close()
    return result

def get_candidate_name(metadata, id):
    return metadata["candidates"][id]["fullName"]

def calculate_candidate_votes(statedata, metadata):
    full_data = {}
    total_precincts = 0
    for state, state_data in statedata["states"].items():
        precinct_results = state_data["results"][0]["results"]
        full_data[state] = {}

        for precinct, precinct_data in precinct_results.items():
            reporting_pct = precinct_data["precinctsReportingPct"] / 100.0
            if reporting_pct == 0:
                continue 

            for entry in precinct_data["results"]:
                name = get_candidate_name(metadata, entry["candidateID"])
                real_total_votes = entry["voteCount"]
                proj_total_votes= real_total_votes / reporting_pct
                
                if name not in full_data[state]:
                    full_data[state][name] = {REAL_TOTAL_VOTES_KEY: 0, PROJ_TOTAL_VOTES_KEY: 0}
                
                full_data[state][name][REAL_TOTAL_VOTES_KEY] += int(real_total_votes)
                full_data[state][name][PROJ_TOTAL_VOTES_KEY] += int(proj_total_votes)
    
    return full_data

def download_all_data():
    download_all_state_election_data()
    download_metadata()

def generate_report(): 
    metadata = get_metadata()
    statedata = get_all_state_election_data()
    print("Data refreshed at " + str(statedata["timestamp"]))

    results = calculate_candidate_votes(statedata, metadata)

    candidates = {}
    net_real_votes = 0
    net_proj_votes = 0
    for state, state_data in results.items(): 
        # print("=======" + state)
        
        for candidate_name, candidate_data in state_data.items(): 
            if candidate_name not in candidates:
                candidates[candidate_name] = {REAL_TOTAL_VOTES_KEY:0, PROJ_TOTAL_VOTES_KEY: 0}
            
            candidates[candidate_name][REAL_TOTAL_VOTES_KEY] += candidate_data[REAL_TOTAL_VOTES_KEY]
            candidates[candidate_name][PROJ_TOTAL_VOTES_KEY] += candidate_data[PROJ_TOTAL_VOTES_KEY]

            net_real_votes += candidate_data[REAL_TOTAL_VOTES_KEY]  
            net_proj_votes += candidate_data[PROJ_TOTAL_VOTES_KEY] - candidate_data[REAL_TOTAL_VOTES_KEY] 

        #     if candidate_name in ["Donald Trump", "Joe Biden"]:
        #         print(candidate_name + ", " + str(candidate_data[REAL_TOTAL_VOTES_KEY]))
        # print()
    proj_total_votes = net_real_votes + net_proj_votes

    print()
    print("Net votes\treal: " + str(net_real_votes) + "\tproj:" + str(net_proj_votes) + "\treal + proj:" + str(proj_total_votes))
    print()
    
    for candidate_name in ["Joe Biden", "Donald Trump"]:
        data = candidates[candidate_name]
        
        data[REAL_PCT_KEY] = int((data[REAL_TOTAL_VOTES_KEY] / net_real_votes) * 10000) / 100.0
        data[PROJ_PCT_KEY] = int((data[PROJ_TOTAL_VOTES_KEY] / proj_total_votes) * 10000) / 100.0
        print(candidate_name + "\treal:" + str(data[REAL_TOTAL_VOTES_KEY]) + ", " + str(data[REAL_PCT_KEY]) + "%\tproj:" + str(data[PROJ_TOTAL_VOTES_KEY]) + ", " + str(data[PROJ_PCT_KEY]) + "%")

    biden = candidates["Joe Biden"]
    trump = candidates["Donald Trump"]

    print()
    mov = int((biden[PROJ_PCT_KEY] - trump[PROJ_PCT_KEY]) * 10) / 10
    print("Estimated MOV: " + str(mov))

download_all_data()
generate_report()