import requests, time
from .config import HACKMD_API_TOKEN

api_base_url = "https://api.hackmd.io/v1"

def request(path, method="GET"):
    timeout = 60
    
    while True: 
        resp = requests.request(
            method = method,
            url = api_base_url + path, 
            headers = {
                "Authorization": "Bearer " + HACKMD_API_TOKEN
            }
        )

        if resp.status_code == 200:
            return resp.json()

        elif resp.status_code == 429:
            print(resp.status_code, resp.text, f"retrying in {timeout} seconds")
            time.sleep(timeout)
            timeout *= 2
        else:
            print(resp.status_code, resp.text)
            return