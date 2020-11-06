import requests 
import json 

METADATA_ENDPOINT = "https://interactives.ap.org/elections/live-data/production/2020-11-03/president/metadata.json"
STATEPRES_ENDPOINT_WO_JSON = "https://interactives.ap.org/elections/live-data/production/2020-11-03/president/"

STATE_INITIALS = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA", 
          "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
          "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
          "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
          "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"]

def getMetadata():
    json_result = requests.get(METADATA_ENDPOINT).text
    python_result = json.loads(json_result)
    return python_result


def getStateElectionData(stateInitials):
    endpoint = STATEPRES_ENDPOINT_WO_JSON + stateInitials + ".json"
    json_result = requests.get(endpoint).text
    python_result = json.loads(json_result)
    return python_result

def getAllStateData():
    result = {}
    for state in STATE_INITIALS:
        result[state] = getStateElectionData(state)
        print("Collected " + state)
    return state

metadata = getMetadata()
statedata = getAllStateData()


