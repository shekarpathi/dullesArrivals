import requests
import json
import re
from datetime import datetime, timezone
token = ""
expiresAt = ""
headers = {
    "Host": "www.united.com",
    "User-Agent": "NSCP/55.0 Geckoo/90100901 Duncan/433.0",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.5",
    "Sec-Fetch-Site": "same-origin",
    "Priority": "u=0"
}

def is_current_time_before_or_equal(extracted_timestamp, current_timestamp):
    """
    Compares two timestamps in 'YYYY-MM-DDTHH:MM:SS' format.
    Returns True if current time <= extracted time, else False.
    """
    fmt = "%Y-%m-%dT%H:%M:%S"
    extracted_dt = datetime.strptime(extracted_timestamp, fmt)
    current_dt = datetime.strptime(current_timestamp, fmt)
    return current_dt <= extracted_dt

def get_current_utc_iso():
    """
    Returns current UTC time in 'YYYY-MM-DDTHH:MM:SS' format.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

def extract_iso_datetime(timestamp):
    """
    Extracts 'YYYY-MM-DDTHH:MM:SS' from full ISO timestamp string.
    """
    match = re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", timestamp)
    if match:
        return match.group(0)
    else:
        return None

def get_bearer_token():
    global token
    global expiresAt

    if expiresAt != "":
        extracted = extract_iso_datetime(expiresAt)
        current = get_current_utc_iso()
        result = is_current_time_before_or_equal(extracted, current)
        if result:
            return

    token_url = "https://www.united.com/api/auth/anonymous-token"
    response = requests.get(token_url, headers=headers, timeout=(5,10)) # 5 seconds connect timeout, 10 seconds read timeout
    response.raise_for_status()
    token = response.json().get("data", {}).get("token", {}).get("hash")
    expiresAt = response.json().get("data", {}).get("token", {}).get("expiresAt")

def fetch_flight_data(flight_number, date_str):
    get_bearer_token()
    url = f"https://www.united.com/api/flight/status/{flight_number}/{date_str}"
    global headers
    headers["X-Authorization-Api"] = f"Bearer {token}"
    try:
        response = requests.get(url, headers=headers, timeout=(2,4)) # 5 seconds connect timeout, 10 seconds read timeout
        if response.status_code == 401:
            headers["X-Authorization-Api"] = f"Bearer {token}"
            response = requests.get(url, headers=headers,
                                    timeout=(2, 4))  # 5 seconds connect timeout, 10 seconds read timeout
            return response.json()
        elif response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {}
        elif response.status_code == 400:
            return {}
        else:
            response.raise_for_status()
    except Exception as e:
        print(e)
        return '{}'

def parse_date(date_str):
    try:
        return datetime.fromisoformat(date_str)
    except (TypeError, ValueError):
        return None

def format_time(dt):
    return dt.strftime("%I:%M %p") if dt else "N/A"


def emit_json(flight_number):
    date_str = datetime.today().strftime("%Y-%m-%d")
    data = fetch_flight_data(flight_number, date_str)
    return data


def get_boarding_times_from_data(flight_number, iata_departure_airport_code):
    foo = ()
    formatted_departure_time = ""

    date_str = datetime.today().strftime("%Y-%m-%d")
    data = fetch_flight_data(flight_number, date_str)
    # print(data)
    result = ""
    with open("foo.json", 'w') as f:
        json.dump(data, f, indent=4)
    pretty_json_string = json.dumps(data, indent=4)
    # print(pretty_json_string)

    segments_from_IAD = []
    segments_to_IAD = []

    # flight_legs = data.get("data", {}).get("flightLegs", [])
    vdata = data.get("data")
    if not vdata:
        return {
            "Status": '',
            "Departure Time": '',
            "Departure Info": ''
        }
    flegs = vdata.get("flightLegs", [])
    if not flegs:
        return {
            "Status": '',
            "Departure Time": '',
            "Departure Info": ''
        }

    boarding_times = None
    estimated_arrival_time = None
    estimated_departure_time = None
    scheduled_departure_time = None
    scheduled_arrival_time = None
    estimated_departure_delay = None
    estimated_arrival_delay = None

    for leg in flegs:
        boarding_times=""
        segments = leg.get("OperationalFlightSegments", [])
        for segment in segments:

            departure_airport = segment.get("DepartureAirport", {})

            estimated_departure_delay = segment.get("EstimatedDepartureDelayMinutes", {})
            estimated_arrival_delay = segment.get("EstimatedArrivalDelayMinutes", {})
            estimated_arrival_time = format_time(parse_date(segment.get("EstimatedArrivalTime")))
            estimated_departure_time = format_time(parse_date(segment.get("EstimatedDepartureTime")))
            scheduled_departure_time = format_time(parse_date(segment.get("DepartureDateTime")))
            scheduled_arrival_time = format_time(parse_date(segment.get("ArrivalDateTime")))

            if departure_airport.get("IATACode") == iata_departure_airport_code:
                segments_from_IAD.append(segment)
                # Save to Python variable as JSON string
                iad_segments_json = json.dumps(segments_from_IAD, indent=2)
                # Write matching segments to output file
                with open("segments_from_IAD.json", "w") as out_file:
                    json.dump(segments_from_IAD, out_file, indent=2)

            if departure_airport.get("IATACode") == iata_departure_airport_code:
                # 1
                # print(segment.get("EstimatedDepartureDelayMinutes"))
                estimated_dep_time = parse_date(segment.get("EstimatedDepartureTime"))
                formatted_departure_time = format_time(estimated_dep_time) + " (E)"
                actual_dep_time = parse_date(segment.get("ActualDepartureTime"))
                if actual_dep_time is not None:
                    # print('Act Dep Time:', format_time(actual_dep_time))
                    formatted_departure_time = format_time(actual_dep_time)
                # print(formatted_departure_time)

                characteristic = segment.get("Characteristic", [])
                if characteristic:
                    char_map = {char["Code"]: char["Value"] for char in segment.get("Characteristic", [])}

                    estimated_start = parse_date(char_map.get("LocalEstimatedBoardStartDateTime"))
                    scheduled_start = parse_date(char_map.get("LocalScheduledBoardStartDateTime"))
                    estimated_end = parse_date(char_map.get("LocalEstimatedBoardEndDateTime"))
                    scheduled_end = parse_date(char_map.get("LocalScheduledBoardEndDateTime"))

                    board_start = max(
                        filter(None, [estimated_start, scheduled_start]),
                        default=""
                    )
                    # board_start = max(filter(None, [estimated_start, scheduled_start]))
                    board_end = max(
                        filter(None, [estimated_end, scheduled_end]),
                        default=None
                    )
                    # board_end = max(filter(None, [estimated_end, scheduled_end]))


                    boarding_times = f"BS: {format_time(board_start)}\nBE: {format_time(board_end)}"


                # 1.1
                statuses = segment.get("FlightStatuses", [])
                if not statuses:
                    continue
                foo = process_statuses(statuses)
                # print(foo)

                reason_statuses = segment.get("ReasonStatuses", [])
                if not reason_statuses:
                    continue
                foo2 = process_reasons(reason_statuses)
                # print(foo2)
    return {
        "ua_Status": safe_get_tuple(foo, 0),
        "ua_Departure_Time": formatted_departure_time if formatted_departure_time is not None else "",
        "ua_scheduled_departure_time": scheduled_departure_time,
        "ua_estimated_departure_time": estimated_departure_time,
        "ua_estimated_departure_delay" : estimated_departure_delay,
        "ua_estimated_arrival_time": estimated_arrival_time,
        "ua_scheduled_arrival_time": scheduled_arrival_time,
        "ua_estimated_arrival_delay": estimated_arrival_delay,
        "ua_Departure_Info": (
            (boarding_times if boarding_times is not None else "")
            + ("\n" + safe_get_tuple(foo, 1))
            + ("\n" + safe_get_tuple(foo, 2))
        )
    }


def safe_get_tuple(tup, index):
    if index < len(tup):
        return tup[index] if tup[index] is not None else ""
    else:
        return ""


def process_statuses(statuses):
    on_time_status=""
    where_is_plane=""
    flight_status=""

    for status in statuses:
        if status.get("StatusType") == "DepartureStatus":
            on_time_status = status.get("Description")
            # if on_time_status:
            #     print("Del/Ontime:", on_time_status)
            # else:
            #     print("No description available for DepartureStatus.")

        if status.get("StatusType") == "LegStatus":
            where_is_plane = status.get("Description")
            # if where_is_plane:
            #     print("Dep/At gate:", where_is_plane)
            # else:
            #     print("No description available for LegStatus.")

        if status.get("StatusType") == "FlightStatus":
            flight_status = status.get("Description") or ""
    return on_time_status, where_is_plane, flight_status


def process_reasons(reason_statuses):
    reason_for_delay = ""
    for reason in reason_statuses:
        descriptions = reason.get("ReasonDescriptions", [])
        if not descriptions:
            continue

        for item in descriptions:
            if item.get("Key") == "LongOpsDesc":
                reason_for_delay = item.get("Description")
                # if reason_for_delay:
                #     print("Reason:", reason_for_delay)
                # else:
                #     print("Description is missing for LongOpsDesc.")
    return reason_for_delay


def main():
    flight_numbers = [918,1129]
    for flight_number in flight_numbers:
        try:
            # iata_departure_arrival_code = "IAD"
            iata_departure_airport_code = "IAD"
            depData = get_boarding_times_from_data(flight_number, iata_departure_airport_code)
            print(depData)
            # arrData = get_boarding_times_from_data(flight_number, iata_departure_arrival_code)
            # print(arrData)
        except Exception as e:
            print(f"Error processing flight {flight_number}: {e}")
            print("-" * 40)

if __name__ == "__main__":
    main()