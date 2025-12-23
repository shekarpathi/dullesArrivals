import requests
import json
import re
import os
import sqlite3
from pathlib import Path as _Path
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
DB_PATH = str(_Path(__file__).resolve().parent / 'arr_dep.db')




# ---------------------- DB helpers for UA departures ----------------------
def _normalize_flightnumber(fn):
    """Prefer numeric portion if present (e.g., 'UA918' -> '918'); otherwise return as string."""
    s = str(fn).strip()
    digits = re.sub(r"\D", "", s)
    return digits if digits else s

def get_ua_departure_flightnumbers_from_db(db_path: str = DB_PATH):
    """Return distinct flightnumbers from departures where IATA='UA' (no date filter)."""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        from datetime import date
        today = date.today().strftime("%Y-%m-%d")
        cur.execute(
            "SELECT DISTINCT flightnumber FROM departures WHERE IATA = 'UA' AND departure_date = ?",
            (today,))
        rows = cur.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        print(f"[DB] Error reading UA departures: {e}")
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass

UA_COLS = [
    "ua_Status",
    "ua_Departure_Time",
    "ua_scheduled_departure_time",
    "ua_estimated_departure_time",
    "ua_estimated_departure_delay",
    "ua_estimated_arrival_time",
    "ua_scheduled_arrival_time",
    "ua_estimated_arrival_delay",
    "ua_Departure_Info",
]

def update_departure_with_united_fields(flightnumber, resp: dict, db_path: str = DB_PATH, use_today: bool = True):
    """
    Update departures table for IATA='UA' + flightnumber with values from United response.
    If use_today=True, scopes update to rows where departure_date is today's local date.
    """
    if not isinstance(resp, dict):
        print(f"[DB] Skipping update for UA{flightnumber}: response is not a dict")
        return 0

    # Map response keys to UA_* columns
    mapping = {
        "ua_Status": resp.get("Status"),
        "ua_Departure_Time": resp.get("Departure_Time") or resp.get("Departure Time"),
        "ua_scheduled_departure_time": resp.get("scheduled_departure_time"),
        "ua_estimated_departure_time": resp.get("estimated_departure_time"),
        "ua_estimated_departure_delay": resp.get("estimated_departure_delay"),
        "ua_estimated_arrival_time": resp.get("estimated_arrival_time"),
        "ua_scheduled_arrival_time": resp.get("scheduled_arrival_time"),
        "ua_estimated_arrival_delay": resp.get("estimated_arrival_delay"),
        "ua_Departure_Info": resp.get("Departure_Info"),
    }

    sets = []
    values = []
    for col, val in mapping.items():
        sets.append(f'"{col}" = ?')
        values.append(None if val is None else str(val))

    where = "IATA = 'UA' AND flightnumber = ?"
    values.append(str(flightnumber))

    if use_today:
        # keep aligned with how arrivals/departures insert today's date: localtime
        where += " AND departure_date = date('now','localtime')"

    sql = f"UPDATE departures SET {', '.join(sets)} WHERE {where}"

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(sql, values)
        conn.commit()
        return cur.rowcount
    except Exception as e:
        print("[DB] Update failed for UA{flightnumber}: {e}")
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass
# -------------------- end DB helpers for UA departures --------------------


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
    return date_str
    try:
        return datetime.fromisoformat(date_str)
    except (TypeError, ValueError):
        return None

def format_time(dt):
    return dt
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
    filename = "united_"+flight_number+".json"
    with open(filename, 'w') as f:
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
                print('---------------')
                print('---------------')
                print('---------------')
                print(foo2)
                print('---------------')
                print('---------------')
    return {
        "Status": safe_get_tuple(foo, 0),
        "leg_status_description": foo[1],
        "Departure_Time": formatted_departure_time if formatted_departure_time is not None else "",
        "scheduled_departure_time": scheduled_departure_time,
        "estimated_departure_time": estimated_departure_time,
        "estimated_departure_delay" : estimated_departure_delay,
        "estimated_arrival_time": estimated_arrival_time,
        "scheduled_arrival_time": scheduled_arrival_time,
        "estimated_arrival_delay": estimated_arrival_delay,
        "Departure_Info": (
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
    arrival_status=""

    for status in statuses:
        if status.get("StatusType") == "DepartureStatus":
            on_time_status = status.get("Description") or ""
        if status.get("StatusType") == "ArrivalStatus":
            arrival_status = status.get("Description") or ""
        if status.get("StatusType") == "LegStatus":
            where_is_plane = status.get("Description") or ""
        if status.get("StatusType") == "FlightStatus":
            flight_status = status.get("Description") or ""
    return on_time_status, arrival_status, where_is_plane, flight_status


def process_reasons(reason_statuses):
    reason_for_delay = ""
    for reason in reason_statuses:
        descriptions = reason.get("ReasonDescriptions", [])
        if not descriptions:
            continue

        for item in descriptions:
            if item.get("Key") == "CustPubDesc":
                reason_for_delay = item.get("Description")
                # if reason_for_delay:
                #     print("Reason:", reason_for_delay)
                # else:
                #     print("Description is missing for CustPubDesc.")
    return reason_for_delay

def deleteUnitedJson():
    pattern = re.compile(r"^united_\d{1,5}\.json$")

    for filename in os.listdir("."):
        if pattern.match(filename) and os.path.isfile(filename):
            os.remove(filename)
            print(f"Deleted: {filename}")

def main():
    deleteUnitedJson()
    # 1) Query arr_dep.db for UA departures
    flightnumbers = get_ua_departure_flightnumbers_from_db()
    if not flightnumbers:
        print("No UA departures found in DB.")
        return

    # flightnumbers=['2748', '2319']

    # 2) Loop through each flight, call United API helper, print + update DB
    for flight_number in flightnumbers:
        try:
            norm_fn = _normalize_flightnumber(flight_number)
            iata_departure_airport_code = "IAD"
            resp = get_boarding_times_from_data(norm_fn, iata_departure_airport_code)
            print(resp)
            updated = update_departure_with_united_fields(flight_number, resp, DB_PATH, use_today=True)
            print(f"[DB] Updated {updated} row(s) for UA{flight_number}")
        except Exception as e:
            print(f"Error processing flight {flight_number}: {e}")
            print("-" * 40)

if __name__ == "__main__":
    main()
