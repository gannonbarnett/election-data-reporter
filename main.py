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
    for i, state in enumerate(STATE_INITIALS):
        result["states"][state] = download_state_election_data(state)
        print("Collected " + state)

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
            total_precincts += 1
            reporting_pct = precinct_data["precinctsReportingPct"] / 100.0
            if reporting_pct == 0:
                # no reported yet
                # print("ERROR: state '" + state + "', precinct '" + precinct + "' reporting pct is 0")
                continue 

            for entry in precinct_data["results"]:
                name = get_candidate_name(metadata, entry["candidateID"])
                real_votes = entry["voteCount"]
                extrapolated_total = real_votes / reporting_pct
                
                if name not in full_data[state]:
                    full_data[state][name] = {"real_votes": 0, "extrapolated_total": 0}
                
                full_data[state][name]["real_votes"] += int(real_votes)
                full_data[state][name]["extrapolated_total"] += int(extrapolated_total)
    
    # print("reviewed " + str(total_precincts) + " precincts")
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
    total_votes = 0
    total_extra = 0
    for state, state_data in results.items(): 
        for candidate_name, candidate_data in state_data.items(): 
            if candidate_name not in candidates:
                candidates[candidate_name] = {"real_votes":0, "extrapolated_total": 0}
            
            candidates[candidate_name]["real_votes"] += candidate_data["real_votes"]
            candidates[candidate_name]["extrapolated_total"] += candidate_data["extrapolated_total"]

            total_votes += candidate_data["extrapolated_total"] 
            total_extra += candidate_data["extrapolated_total"] - candidate_data["real_votes"] 

    print()
    print("Vote breakdown: current total: " + str(total_votes) + ", estimated remaining: " + str(total_extra))
    print()
    max_to_show = 2
    count = 0
    for candidate_name, data in candidates.items():
        if count >= max_to_show:
            break
        
        data["current_pct"] = int((data["real_votes"] / (total_votes - total_extra)) * 10000) / 100.0
        data["est_pct"] = int((data["extrapolated_total"] / total_votes) * 10000) / 100.0
        print(candidate_name + "\treal votes:" + str(data["real_votes"]) + "\tproj votes: " + str(data["extrapolated_total"]) + "\treal pct: " + str(data["current_pct"]) + "\tproj pct: " + str(data["est_pct"]))


        count += 1
    biden = candidates["Joe Biden"]
    trump = candidates["Donald Trump"]

    print()
    # print("Biden pct: current: " + str(biden["current_pct"]) + ", est: " + str(biden["est_pct"]))
    # print("Trump pct: current: " + str(trump["current_pct"]) + ", est: " + str(trump["est_pct"]))
    mov = int((biden["est_pct"] - trump["est_pct"]) * 10) / 10
    print("Estimated MOV: " + str(mov))

# download_all_data()
generate_report()