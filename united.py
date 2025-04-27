import requests
from datetime import datetime

user_agent="Mozilla/5.0 Gecko/20100101 Firefox/133.0"
accept_language="en-US,en;q=0.5"
accept_encoding="gzip, deflate, br"

def get_bearer_token():
    token_url = "https://www.united.com/api/auth/anonymous-token"
    headers_token = { 
        "Host": "www.united.com",
        "User-Agent": "Mozilla/5.0 Gecko/20100101 Firefox/133.0",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=0"
    }
    response = requests.get(token_url, headers=headers_token, timeout=(5,10)) # 5 seconds connect timeout, 10 seconds read timeout
    response.raise_for_status()
    return response.json().get("data", {}).get("token", {}).get("hash")

def fetch_flight_data(flight_number, token, date_str):
    url = f"https://www.united.com/api/flight/status/{flight_number}/{date_str}"
    headers = {
        "Host": "www.united.com",
        "User-Agent": "Mozilla/5.0 Gecko/20100101 Firefox/133.0",
        "Accept": "application/json",
        "X-Authorization-Api": f"bearer {token}",
        "Sec-Fetch-Site": "same-origin",
        "Priority": "u=0"
    }
    response = requests.get(url, headers=headers, timeout=(2,4)) # 5 seconds connect timeout, 10 seconds read timeout
    response.raise_for_status()
    return response.json()

def parse_date(date_str):
    try:
        return datetime.fromisoformat(date_str)
    except (TypeError, ValueError):
        return None

def format_time(dt):
    return dt.strftime("%I:%M %p") if dt else "N/A"

def print_boarding_times_from_data(data, flight_number):
    flight_legs = data.get("data", {}).get("flightLegs", [])
    boarding_times = None

    for leg in flight_legs:
        segments = leg.get("OperationalFlightSegments", [])
        for segment in segments:
            if segment.get("DepartureAirport", {}).get("IATACode") == "IAD":
                char_map = {char["Code"]: char["Value"] for char in segment.get("Characteristic", [])}

                estimated_start = parse_date(char_map.get("LocalEstimatedBoardStartDateTime"))
                scheduled_start = parse_date(char_map.get("LocalScheduledBoardStartDateTime"))
                estimated_end = parse_date(char_map.get("LocalEstimatedBoardEndDateTime"))
                scheduled_end = parse_date(char_map.get("LocalScheduledBoardEndDateTime"))

                board_start = max(filter(None, [estimated_start, scheduled_start]))
                board_end = max(filter(None, [estimated_end, scheduled_end]))

                print(f"Flight: {flight_number}")
                print("  Boarding Start Time:", format_time(board_start))
                print("  Boarding End Time:  ", format_time(board_end))
                print("-" * 40)
                boarding_times = (format_time(board_start), format_time(board_end))
                result = f"BS: {board_start}\nBE: {board_end}"
    return result

def main():
    flight_numbers = [5028, 545, 2029, 1491, 1670, 408, 1234, 1235, 1236, 1237, 1238, 1239]
    date_str = datetime.today().strftime("%Y-%m-%d")
    token = get_bearer_token()

    for flight_number in flight_numbers:
        try:
            data = fetch_flight_data(flight_number, token, date_str)
            print_boarding_times_from_data(data, flight_number)
        except Exception as e:
            print(f"Error processing flight {flight_number}: {e}")
            print("-" * 40)

if __name__ == "__main__":
    main()
