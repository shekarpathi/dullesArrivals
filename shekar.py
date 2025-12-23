import requests
from datetime import datetime
import time
import urllib3
import os
import sqlite3
import re, json, ssl, sys
from urllib.request import Request, urlopen
HOME = "https://www.flydulles.com/"
JSON_URL = "https://www.flydulles.com/arrivals-and-departures/json"

# import globals
airline_name_dict = {
    "Aer Lingus": "Aer Lingus",
    "Aeromexico": "Aeromexico",
    "Air Canada": "Air Canada",
    "Air France": "Air France",
    "Alaska Airlines": "Alaska",
    "All Nippon Airways": "All Nippon",
    "Allegiant Air LLC": "Allegiant",
    "American Airlines": "American",
    "Austrian Airlines AG dba Austrian": "Austrian",
    "Avelo Airlines": "Avelo",
    "Avianca": "Avianca",
    "Breeze Airways": "Breeze",
    "British Airways": "British",
    "Brussels Airlines": "Brussels",
    "COPA Airlines": "COPA",
    "Contour Airlines": "Contour",
    "Delta Air Lines": "Delta",
    "Deutsche Lufthansa AG": "Lufthansa",
    "Egyptair": "Egyptair",
    "Emirates": "Emirates",
    "Ethiopian Airlines": "Ethiopian",
    "Etihad Airways": "Etihad",
    "Frontier Airlines Inc.": "Frontier",
    "Iberia": "Iberia",
    "Icelandair": "Icelandair",
    "KLM-Royal Dutch Airlines": "KLM",
    "Korean Air": "Korean",
    "Porter Airlines": "Porter",
    "Qatar Airways": "Qatar",
    "SAS Scandinavian Airlines": "SAS",
    "SWISS": "SWISS",
    "Saudi Arabian Airlines": "Saudia",
    "Southern Airways Express": "Southern",
    "Southwest Airlines": "Southwest",
    "Sun Country Airlines": "Sun Country",
    "TAP Air Portugal": "TAP",
    "Turkish Airlines": "Turkish",
    "United Airlines": "United",
    "Virgin Atlantic": "Virgin",
    "Volaris El Salvador": "Volaris"
}

# Optional: Suppress warnings if using verify=False (not recommended for production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CACHE_FILE = "fleet_cache.json"
DB_FILE = "arr_dep.db"

# Load cache from file
fleet_ident_cache = {}
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        try:
            fleet_ident_cache = json.load(f)
        except json.JSONDecodeError:
            fleet_ident_cache = {}

def fetch(url, headers=None, insecure=True):
    ctx = None
    if insecure:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    req = Request(url, headers=headers or {})
    with urlopen(req, context=ctx, timeout=30) as r:
        return r.read()


def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(fleet_ident_cache, f)


def fetch_fleet_ident(search_term):
    # Return from cache if available
    if search_term in fleet_ident_cache:
        return fleet_ident_cache[search_term]

    url = "https://www.flightaware.com/search/homepage-api/"
    headers = {
        "Host": "www.flightaware.com",
        "Content-Type": "application/json",
    }
    payload = {
        "searchTerm": search_term
    }

    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, json.JSONDecodeError):
        print(f"Error fetching data for {search_term}")
        return None

    for entry in data:
        if entry.get("type") == "fleet":
            ident = entry.get("ident")
            # Save to cache and persist to file
            fleet_ident_cache[search_term] = ident
            save_cache()
            return ident

    # If not found, store as None to prevent repeat lookups
    fleet_ident_cache[search_term] = None
    save_cache()
    return None


def fetch_flight_data(url, max_attempts=4, wait_seconds=10):
    attempts = 0
    while attempts < max_attempts:
        try:
            response = requests.get(url, timeout=(5, 10))
            if response.status_code == 200:
                with open('mwaa_arr_dep.json', 'w') as file:
                    json.dump(response.json(), file, indent=4)
                return response.json()
            else:
                print(
                    f"Attempt {attempts + 1} failed with status code {response.status_code}. Retrying in {wait_seconds} seconds...")
        except requests.RequestException as e:
            print(f"Attempt {attempts + 1} encountered an error: {e}. Retrying in {wait_seconds} seconds...")

        attempts += 1
        time.sleep(wait_seconds)

    raise Exception(f"Failed to fetch data from {url} after {max_attempts} attempts.")


def is_published_today(entry):
    try:
        published_str = entry.get("publishedTime")
        if not published_str:
            return False
        published_time = datetime.strptime(published_str, "%Y-%m-%d %H:%M:%S")
        return published_time.date() == datetime.today().date()
    except Exception:
        return False


def flatten_codeshare(entry):
    codeshares = entry.get("codeshare", [])
    flattened = [f"{cs.get('IATA', '')}{cs.get('flightnumber', '')}" for cs in codeshares if
                 cs.get("IATA") and cs.get("flightnumber")]
    entry["codeShares"] = ", ".join(flattened)
    entry.pop("codeshare", None)
    return entry


def flatten_baggageclaim(entry):
    values = [entry.get("baggage"), entry.get("claim"), entry.get("claim1"), entry.get("claim2"), entry.get("claim3")]
    baggage_claim = ','.join(sorted(set(filter(None, values))))
    entry["baggage_claim"] = baggage_claim
    entry.pop("claim", None)
    entry.pop("claim1", None)
    entry.pop("claim2", None)
    entry.pop("claim3", None)
    entry.pop("baggage", None)
    entry.pop("dep_gate", None)
    return entry


def flatten_tail_number(entry):
    aircraft_info = {}
    if entry.get("flightnumber") == '3548':
        rr=0
    entry["tail_number"] = None
    if "aircraftInfo" not in entry:
        return None
    if (isinstance(entry["aircraftInfo"], list) and len(entry["aircraftInfo"]) > 0):
        aircraft_info = entry["aircraftInfo"][0]
    elif isinstance(entry["aircraftInfo"], dict):
        aircraft_info = entry.get("aircraftInfo", {})

    try:
        if (isinstance(aircraft_info, dict)):
            try:
                tail_number = aircraft_info.get("tail_number", None)
                if tail_number:
                    entry["tail_number"] = tail_number.lower()
                else:
                    entry["tail_number"] = None
            except Exception:
                entry["tail_number"] = None
            entry["tail_number"] = "{}{}".format("https://www.flightradar24.com/data/aircraft/", entry["tail_number"])

            # Get today's date
            today = datetime.today()
            year = today.year
            month = today.month
            date = today.day

            # Construct the URL
            ident = fetch_fleet_ident(entry['IATA'])

            entry["tail_number"] = f"https://www.flightaware.com/live/flight/{ident}{entry['flightnumber']}"

            try:
                aircraft_code = aircraft_info.get("aircraft_code", None)
                if aircraft_code:
                    entry["aircraft_code"] = aircraft_code
                else:
                    entry["aircraft_code"] = None
            except Exception:
                entry["aircraft_code"] = None

        entry.pop("aircraftInfo", None)
    except Exception:
        entry["tail_number"] = None
        entry.pop("aircraftInfo", None)
        print("Error processing tail number for flight:", entry.get("flightnumber"))

    return entry


def remove_unwanted_data(entry):
    entry.pop("id", None)
    entry.pop("mwaaTime", None)
    entry.pop("dep_terminal", None)
    entry.pop("arr_terminal", None)
    entry.pop("diversion_status", None)
    entry["gate"] = entry.get("gate") or entry.get("mod_gate")
    entry.pop("mod_gate", None)
    entry["status"] = entry.get("status") or entry.get("mod_status")
    entry.pop("mod_status", None)
    gate = entry.get("gate")
    international = entry.get("international")
    iab = entry.get("iab")

    if gate:
        if gate.startswith("C"):
            entry["ll_door"] = "6→7"
        elif gate.startswith("D"):
            entry["ll_door"] = "8"
        elif gate.startswith("A") and len(gate) == 3:
            entry["ll_door"] = "6→7"
        elif gate.startswith("B"):
            entry["ll_door"] = "9→10"
        elif gate.startswith("A") and international == 0:
            entry["ll_door"] = "9→10"
        elif gate.startswith("Z"):
            entry["ll_door"] = "8"

    if iab is True:
        entry["ll_door"] = "15"

    return entry


def format_time_am_pm(datetime_str):
    try:
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%-I:%M %p")  # Use '%I:%M %p' on Windows
    except ValueError:
        return None


def format_time_diff(time_str):
    try:
        gate_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        now = datetime.now()
        delta = gate_time - now
        seconds = int(delta.total_seconds())
        minutes = abs(seconds) // 60
        hours = minutes // 60
        remaining_minutes = minutes % 60

        if seconds > 0:
            if hours > 0:
                return f"in {hours}:{remaining_minutes:02d}"
            else:
                return f"in {remaining_minutes}m"
        else:
            if hours > 0:
                return f"{hours}:{remaining_minutes:02d} ago"
            else:
                return f"{remaining_minutes}m ago"
    except Exception:
        return None


def clean_arrival(entry):
    entry = get_international_domestic(entry)
    entry = flatten_codeshare(entry)
    entry = flatten_tail_number(entry)
    entry = remove_unwanted_data(entry)
    entry = flatten_baggageclaim(entry)
    entry.pop("arrivalInfo", None)
    entry["GateArrivalTime"] = entry.get("actualtime") or entry.get("publishedTime")

    if entry["GateArrivalTime"]:
        entry["ArrivalInfo"] = format_time_diff(entry["GateArrivalTime"])
        entry["ArrivalTime"] = format_time_am_pm(entry["GateArrivalTime"])

    entry.pop("actualtime", None)
    entry.pop("publishedTime", None)
    if entry["airline"] in airline_name_dict:
        entry["airline"] = airline_name_dict.get(entry["airline"])
    return entry


def get_international_domestic(entry):
    try:
        preclearairports = ['AUH', 'DUB', 'SNN', 'AUA', 'BDA', 'NAS', 'YYC', 'YYZ', 'YEG', 'YHZ', 'YUL', 'YOW', 'YVR',
                            'YYJ', 'YWG', 'SJU', 'STT']
        starAllianceMembersArray = ['OS', 'DL', 'UA', 'SAB', 'CA', 'NH', 'SK', 'LX', 'SN', 'LH']

        entry["iab"] = False
        entry["fis"] = False
        if entry["international"] == 1 and entry["dep_airport_code"] in preclearairports:
            entry["international"] = 0

        if entry["international"] == 1:
            entry["iab"] = True
            if entry["IATA"] in starAllianceMembersArray:
                entry["fis"] = True
    except Exception:
        entry["iab"] = False
        entry["fis"] = False
        print("Error processing international/domestic status for flight:", entry.get("flightnumber"))

    if entry["customsAt"] != None:
        entry["status"] = "Customs " + format_time_am_pm(entry["customsAt"])
    else:
        entry["status"] = entry.get("status") or entry.get("mod_status")
    return entry


def clean_departure(entry):
    entry = flatten_codeshare(entry)
    entry = flatten_tail_number(entry)
    entry = remove_unwanted_data(entry)
    entry.pop("departureInfo", None)

    entry["GateDepartureTime"] = entry.get("actualtime") or entry.get("publishedTime")

    if entry["GateDepartureTime"]:
        entry["DepartureInfo"] = format_time_diff(entry["GateDepartureTime"])
        entry["DepartureTime"] = format_time_am_pm(entry["GateDepartureTime"])

    entry.pop("actualtime", None)
    entry.pop("publishedTime", None)
    entry.pop("arr_gate", None)
    entry.pop("baggage", None)
    if entry["airline"] in airline_name_dict:
        entry["airline"] = airline_name_dict.get(entry["airline"])

    return entry


def sort_by_datetime_field(entries, fieldname):
    def parse_datetime(entry):
        value = entry.get(fieldname)
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S") if value else datetime.max
        except Exception:
            return datetime.max

    entrys = sorted(entries, key=parse_datetime)
    i = 1
    for entry in entrys:
        entry["index"] = i
        i += 1
    return entrys


def filter_process_and_sort(entries, cleaner, sort_field):
    cleaned = [cleaner(entry) for entry in entries if is_published_today(entry)]
    return sort_by_datetime_field(cleaned, sort_field)


def write_to_file(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


# ===================== SQLite Support Functions =====================

def get_existing_columns(cursor, table_name):
    """Get list of existing columns in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def add_column_if_not_exists(cursor, table_name, column_name):
    """Add a column to table if it doesn't exist"""
    existing_columns = get_existing_columns(cursor, table_name)
    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT")


def init_arrivals_table():
    """Initialize the arrivals table in arr_dep.db"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create basic table with primary key and UA columns
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS arrivals
                   (
                       arrival_date
                       TEXT
                       NOT
                       NULL,
                       IATA
                       TEXT
                       NOT
                       NULL,
                       flightnumber
                       TEXT
                       NOT
                       NULL,
                       ua_Status
                       TEXT,
                       ua_Departure_Time
                       TEXT,
                       ua_scheduled_departure_time
                       TEXT,
                       ua_estimated_departure_time
                       TEXT,
                       ua_estimated_departure_delay
                       TEXT,
                       ua_estimated_arrival_time
                       TEXT,
                       ua_scheduled_arrival_time
                       TEXT,
                       ua_estimated_arrival_delay
                       TEXT,
                       ua_Departure_Info
                       TEXT,
                       PRIMARY
                       KEY
                   (
                       arrival_date,
                       IATA,
                       flightnumber
                   )
                       )
                   ''')

    conn.commit()
    conn.close()


def init_departures_table():
    """Initialize the departures table in arr_dep.db"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS departures
                   (
                       departure_date
                       TEXT
                       NOT
                       NULL,
                       IATA
                       TEXT
                       NOT
                       NULL,
                       flightnumber
                       TEXT
                       NOT
                       NULL,
                       ua_Status
                       TEXT,
                       ua_Departure_Time
                       TEXT,
                       ua_scheduled_departure_time
                       TEXT,
                       ua_estimated_departure_time
                       TEXT,
                       ua_estimated_departure_delay
                       TEXT,
                       ua_estimated_arrival_time
                       TEXT,
                       ua_scheduled_arrival_time
                       TEXT,
                       ua_estimated_arrival_delay
                       TEXT,
                       ua_Departure_Info
                       TEXT,
                       ua_Delay_Reason_Description
                       TEXT,
                       ua_Where_Is_Flight
                       TEXT,
                       PRIMARY
                       KEY
                   (
                       departure_date,
                       IATA,
                       flightnumber
                   )
                       )
                   ''')

    conn.commit()
    conn.close()


def save_arrivals_to_db(arrivals_data):
    """Save arrivals data to SQLite database"""
    if not arrivals_data:
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    today_date = datetime.today().strftime("%Y-%m-%d")

    # Collect all unique columns from all arrivals
    all_columns = {'arrival_date', 'IATA', 'flightnumber'}
    for arrival in arrivals_data:
        arrival_copy = arrival.copy()
        arrival_copy.pop("ArrivalInfo", None)
        arrival_copy.pop("index", None)
        all_columns.update(arrival_copy.keys())

    # Ensure all columns exist
    for column in all_columns:
        if column not in ['arrival_date', 'IATA', 'flightnumber']:
            add_column_if_not_exists(cursor, 'arrivals', column)

    conn.commit()

    # Now insert/update data
    for arrival in arrivals_data:
        arrival_copy = arrival.copy()
        arrival_copy.pop("ArrivalInfo", None)
        arrival_copy.pop("index", None)

        # Get current columns in table
        existing_columns = get_existing_columns(cursor, 'arrivals')

        # Prepare data - only include columns that exist in table
        columns = ['arrival_date']
        values = [today_date]

        for key, value in arrival_copy.items():
            if key in existing_columns:
                columns.append(key)
                values.append(value)

        # Create placeholders and update clause
        placeholders = ', '.join(['?' for _ in values])
        column_names = ', '.join(columns)

        # Only update non-PK columns
        update_columns = [col for col in columns if col not in ['arrival_date', 'IATA', 'flightnumber']]
        update_clause = ', '.join([f"{col} = excluded.{col}" for col in update_columns])

        if update_clause:  # Only if there are columns to update
            query = f'''
                INSERT INTO arrivals ({column_names})
                VALUES ({placeholders})
                ON CONFLICT(arrival_date, IATA, flightnumber) 
                DO UPDATE SET {update_clause}
            '''
        else:
            query = f'''
                INSERT OR IGNORE INTO arrivals ({column_names})
                VALUES ({placeholders})
            '''

        cursor.execute(query, values)

    conn.commit()
    conn.close()
    print(f"Saved {len(arrivals_data)} arrivals to database")


def save_departures_to_db(departures_data):
    """Save departures data to SQLite database"""
    if not departures_data:
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    today_date = datetime.today().strftime("%Y-%m-%d")

    # Collect all unique columns from all departures
    all_columns = set(['departure_date', 'IATA', 'flightnumber'])
    for departure in departures_data:
        departure_copy = departure.copy()
        departure_copy.pop("DepartureInfo", None)
        departure_copy.pop("index", None)
        all_columns.update(departure_copy.keys())

    # Ensure all columns exist
    for column in all_columns:
        if column not in ['departure_date', 'IATA', 'flightnumber']:
            add_column_if_not_exists(cursor, 'departures', column)

    conn.commit()

    # Now insert/update data
    for departure in departures_data:
        departure_copy = departure.copy()
        departure_copy.pop("DepartureInfo", None)
        departure_copy.pop("index", None)

        # Get current columns in table
        existing_columns = get_existing_columns(cursor, 'departures')

        # Prepare data - only include columns that exist in table
        columns = ['departure_date']
        values = [today_date]

        for key, value in departure_copy.items():
            if key in existing_columns:
                columns.append(key)
                values.append(value)

        # Create placeholders and update clause
        placeholders = ', '.join(['?' for _ in values])
        column_names = ', '.join(columns)

        # Only update non-PK columns
        update_columns = [col for col in columns if col not in ['departure_date', 'IATA', 'flightnumber']]
        update_clause = ', '.join([f"{col} = excluded.{col}" for col in update_columns])

        if update_clause:  # Only if there are columns to update
            query = f'''
                INSERT INTO departures ({column_names})
                VALUES ({placeholders})
                ON CONFLICT(departure_date, IATA, flightnumber) 
                DO UPDATE SET {update_clause}
            '''
        else:
            query = f'''
                INSERT OR IGNORE INTO departures ({column_names})
                VALUES ({placeholders})
            '''

        cursor.execute(query, values)

    conn.commit()
    conn.close()
    print(f"Saved {len(departures_data)} departures to database")


def update_arrival_ua_fields(arrival_date, iata, flightnumber, **ua_fields):
    """
    Update only UA fields for a specific arrival

    Args:
        arrival_date: Date in YYYY-MM-DD format
        iata: IATA airline code
        flightnumber: Flight number
        **ua_fields: Any of the ua_* fields to update
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    valid_ua_fields = ['ua_Status', 'ua_Departure_Time', 'ua_scheduled_departure_time',
                       'ua_estimated_departure_time', 'ua_estimated_departure_delay',
                       'ua_estimated_arrival_time', 'ua_scheduled_arrival_time',
                       'ua_estimated_arrival_delay', 'ua_Departure_Info']

    # Filter to only valid UA fields
    fields_to_update = {k: v for k, v in ua_fields.items() if k in valid_ua_fields}

    if not fields_to_update:
        print("No valid UA fields provided for update")
        conn.close()
        return

    set_clause = ', '.join([f"{k} = ?" for k in fields_to_update.keys()])
    values = list(fields_to_update.values()) + [arrival_date, iata, flightnumber]

    query = f'''
        UPDATE arrivals 
        SET {set_clause}
        WHERE arrival_date = ? AND IATA = ? AND flightnumber = ?
    '''

    cursor.execute(query, values)
    conn.commit()

    if cursor.rowcount > 0:
        print(f"Updated UA fields for arrival {iata}{flightnumber} on {arrival_date}")
    else:
        print(f"No arrival found for {iata}{flightnumber} on {arrival_date}")

    conn.close()


def update_departure_ua_fields(departure_date, iata, flightnumber, **ua_fields):
    """
    Update only UA fields for a specific departure

    Args:
        departure_date: Date in YYYY-MM-DD format
        iata: IATA airline code
        flightnumber: Flight number
        **ua_fields: Any of the ua_* fields to update
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    valid_ua_fields = ['ua_Status', 'ua_Departure_Time', 'ua_scheduled_departure_time',
                       'ua_estimated_departure_time', 'ua_estimated_departure_delay',
                       'ua_estimated_arrival_time', 'ua_scheduled_arrival_time',
                       'ua_estimated_arrival_delay', 'ua_Departure_Info']

    # Filter to only valid UA fields
    fields_to_update = {k: v for k, v in ua_fields.items() if k in valid_ua_fields}

    if not fields_to_update:
        print("No valid UA fields provided for update")
        conn.close()
        return

    set_clause = ', '.join([f"{k} = ?" for k in fields_to_update.keys()])
    values = list(fields_to_update.values()) + [departure_date, iata, flightnumber]

    query = f'''
        UPDATE departures 
        SET {set_clause}
        WHERE departure_date = ? AND IATA = ? AND flightnumber = ?
    '''

    cursor.execute(query, values)
    conn.commit()

    if cursor.rowcount > 0:
        print(f"Updated UA fields for departure {iata}{flightnumber} on {departure_date}")
    else:
        print(f"No departure found for {iata}{flightnumber} on {departure_date}")

    conn.close()

def test():

    # 1) Get homepage and extract cookie value
    html = fetch(HOME, headers={
        "Host": "www.flydulles.com",
        "User-Agent": "mwaa/library",
    })
    m = re.search(rb"drupal_ac_antibot_cookie_value\s*=\s*'([^']+)'", html)
    if not m:
        print("Error: could not find drupal_ac_antibot_cookie_value", file=sys.stderr)
        sys.exit(1)
    cookie_val = m.group(1).decode()
    print(cookie_val)

    # 2) Call JSON endpoint with required cookies
    body = fetch(JSON_URL, headers={
        "Host": "www.flydulles.com",
        "User-Agent": "mwaa/library",
        "Cookie": f"apbct_antibot_={cookie_val}; flight-info=2",
        "Accept": "application/json",
    })
    return

    # Pretty-print JSON (or pass through if non-JSON)
    try:
        data = json.loads(body.decode("utf-8", errors="ignore"))
        # print(json.dumps(data, indent=2, ensure_ascii=False))
    except json.JSONDecodeError:
        # Fallback: print raw
        sys.stdout.buffer.write(body)

# ===================== Main Function =====================

def main():
    test()
    url = "https://www.flydulles.com/arrivals-and-departures/json"

    try:
        # Initialize database tables
        init_arrivals_table()
        init_departures_table()

        data = fetch_flight_data(url)
        arrivals = filter_process_and_sort(data.get("arrivals", []), clean_arrival, "GateArrivalTime")
        departures = filter_process_and_sort(data.get("departures", []), clean_departure, "GateDepartureTime")

        # format current time as "Month Day, Year HH:MM AM/PM"
        current_time_str = datetime.now().strftime("%B %d, %Y %-I:%M %p")

        # build a top-level object
        arrivals_obj = {
            "currentTime": current_time_str,
            "arrivals": arrivals
        }

        # build a top-level object
        departures_obj = {
            "currentTime": current_time_str,
            "departures": departures
        }

        # build a top-level object
        arr_dep_obj = {
            "currentTime": current_time_str,
            "arrivals": arrivals,
            "departures": departures
        }

        write_to_file(arr_dep_obj, "arr_dep.json")

        if arrivals:
            write_to_file(arrivals_obj, "arrivals.json")
            # Save to database
            save_arrivals_to_db(arrivals)
        else:
            print("No arrivals for today.")

        if departures:
            write_to_file(departures_obj, "departures.json")
            # Save to database
            save_departures_to_db(departures)
        else:
            print("No departures for today.")

    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()