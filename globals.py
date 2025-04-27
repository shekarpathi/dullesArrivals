import requests

def init():
    global bearer_token
    token_url = "https://www.united.com/api/auth/anonymous-token"
    headers_token = {
        "User-Agent": "Mozilla/5.0 Gecko/20100101 Firefox/133.0",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=0"
    }
    response = requests.get(token_url, headers=headers_token, timeout=(5,10)) # 5 seconds connect timeout, 10 seconds read timeout
    response.raise_for_status()
    bearer_token = response.json().get("data", {}).get("token", {}).get("hash")

# Initialize once when this module is first imported
init()