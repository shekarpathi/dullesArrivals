import requests

def init():
    global config
    global bearer_token
    print("Initializing global variables...")
    token_url = "https://www.united.com/api/auth/anonymous-token"
    headers_token = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "application/json",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=0"
    }
    response = requests.get(token_url, headers=headers_token)
    response.raise_for_status()
    bearer_token = response.json().get("data", {}).get("token", {}).get("hash")

# Initialize once when this module is first imported
init()