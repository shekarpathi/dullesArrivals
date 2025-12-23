import requests
import json

# ---------------------- SQLite Arrivals/Departures Sync ----------------------
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Optional, Any
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "arr_dep.db"
ARRIVALS_JSON = BASE_DIR / "arrivals.json"
DEPARTURES_JSON = BASE_DIR / "departures.json"

UA_COLUMNS: Tuple[str, ...] = (
    "ua_Status",
    "ua_Departure_Time",
    "ua_scheduled_departure_time",
    "ua_estimated_departure_time",
    "ua_estimated_departure_delay",
    "ua_estimated_arrival_time",
    "ua_scheduled_arrival_time",
    "ua_estimated_arrival_delay",
    "ua_Departure_Info",
)

ARRIVAL_EXCLUDE_KEYS = {"ArrivalInfo", "index"}
DEPARTURE_EXCLUDE_KEYS = {"DepartureInfo", "index"}

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def _ensure_columns(conn: sqlite3.Connection, table: str, columns: Iterable[str]) -> None:
    cur = conn.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cur.fetchall()}
    for col in columns:
        if col not in existing:
            conn.execute(f'ALTER TABLE {table} ADD COLUMN "{col}" TEXT NULL')

def _create_base_table(conn: sqlite3.Connection, table: str, date_col: str, pk_cols: Tuple[str, str, str]) -> None:
    pk_a, pk_b, pk_c = pk_cols
    ua_cols_sql = ",\n    ".join([f'"{c}" TEXT NULL' for c in UA_COLUMNS])
    sql = f"""
    CREATE TABLE IF NOT EXISTS {table} (
        "{date_col}" TEXT NOT NULL,
        "{pk_b}" TEXT NOT NULL,
        "{pk_c}" TEXT NOT NULL,
        {ua_cols_sql},
        PRIMARY KEY ("{date_col}", "{pk_b}", "{pk_c}")
    );
    """
    conn.execute(sql)

def _rows_from_json(path: Path, array_key: str, exclude_keys: Iterable[str]) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f1:
        payload = json.load(f1)
    items = payload.get(array_key, []) or []
    cleaned = []
    for it in items:
        if isinstance(it, dict):
            cleaned.append({k: v for k, v in it.items() if k not in exclude_keys})
    return cleaned

def _upsert_rows(conn: sqlite3.Connection, table: str, rows: List[Dict[str, Any]], date_col: str, pk_cols: Tuple[str, str, str]) -> int:
    if not rows:
        return 0
    _create_base_table(conn, table, date_col, pk_cols)

    dynamic_cols: set = set()
    for r in rows:
        dynamic_cols.update(r.keys())
    dynamic_cols.discard(date_col)
    dynamic_cols.difference_update(set(pk_cols))
    dynamic_cols.difference_update(UA_COLUMNS)

    _ensure_columns(conn, table, dynamic_cols)

    all_cols = [date_col, pk_cols[1], pk_cols[2]] + sorted(dynamic_cols) + list(UA_COLUMNS)
    placeholders = ", ".join(["?"] * len(all_cols))
    col_list_sql = ", ".join([f'"{c}"' for c in all_cols])
    non_pk_cols = [c for c in all_cols if c not in (date_col, pk_cols[1], pk_cols[2])]
    update_sql = ", ".join([f'"{c}"=excluded."{c}"' for c in non_pk_cols])

    sql = f"""
    INSERT INTO {table} ({col_list_sql})
    VALUES ({placeholders})
    ON CONFLICT("{date_col}","{pk_cols[1]}","{pk_cols[2]}") DO UPDATE SET
        {update_sql};
    """

    data_to_insert = []
    for r in rows:
        row_with_defaults = dict(r)
        row_with_defaults.setdefault(pk_cols[1], r.get("IATA", ""))
        row_with_defaults.setdefault(pk_cols[2], r.get("flightnumber", ""))
        values = []
        for c in all_cols:
            if c == date_col:
                values.append(_today_str())
            else:
                values.append(row_with_defaults.get(c))
        data_to_insert.append(values)

    conn.executemany(sql, data_to_insert)
    conn.commit()
    return len(rows)

def save_arrivals_from_json(json_path: Optional[Path] = None) -> int:
    path = json_path or ARRIVALS_JSON
    rows = _rows_from_json(path, "arrivals", ARRIVAL_EXCLUDE_KEYS)
    if not rows:
        return 0
    with _connect() as conn:
        return _upsert_rows(conn, "arrivals", rows, "arrival_date", ("arrival_date", "IATA", "flightnumber"))

def save_departures_from_json(json_path: Optional[Path] = None) -> int:
    path = json_path or DEPARTURES_JSON
    rows = _rows_from_json(path, "departures", DEPARTURE_EXCLUDE_KEYS)
    if not rows:
        return 0
    with _connect() as conn:
        return _upsert_rows(conn, "departures", rows, "departure_date", ("departure_date", "IATA", "flightnumber"))

def update_arrival_ua_fields(iata: str, flightnumber: str, ua_fields: Dict[str, Optional[str]], arrival_date: Optional[str] = None) -> int:
    arrival_date = arrival_date or _today_str()
    allowed = {k: v for k, v in ua_fields.items() if k in UA_COLUMNS}
    if not allowed:
        return 0
    sets = ", ".join([f'"{k}"=?' for k in allowed.keys()])
    values = list(allowed.values()) + [arrival_date, iata, flightnumber]
    with _connect() as conn:
        cur = conn.execute(
            f'UPDATE arrivals SET {sets} WHERE arrival_date=? AND IATA=? AND flightnumber=?',
            values
        )
        conn.commit()
        return cur.rowcount

def update_departure_ua_fields(iata: str, flightnumber: str, ua_fields: Dict[str, Optional[str]], departure_date: Optional[str] = None) -> int:
    departure_date = departure_date or _today_str()
    allowed = {k: v for k, v in ua_fields.items() if k in UA_COLUMNS}
    if not allowed:
        return 0
    sets = ", ".join([f'"{k}"=?' for k in allowed.keys()])
    values = list(allowed.values()) + [departure_date, iata, flightnumber]
    with _connect() as conn:
        cur = conn.execute(
            f'UPDATE departures SET {sets} WHERE departure_date=? AND IATA=? AND flightnumber=?',
            values
        )
        conn.commit()
        return cur.rowcount

def after_arrivals_json_created(json_path: Optional[Path] = None) -> int:
    return save_arrivals_from_json(json_path)

def after_departures_json_created(json_path: Optional[Path] = None) -> int:
    return save_departures_from_json(json_path)
# -------------------- End SQLite Arrivals/Departures Sync --------------------

import time
import urllib3
import os

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

# Load cache from file
fleet_ident_cache = {}
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        try:
            fleet_ident_cache = json.load(f)
        except json.JSONDecodeError:
            fleet_ident_cache = {}

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
                return response.json()
            else:
                print(f"Attempt {attempts + 1} failed with status code {response.status_code}. Retrying in {wait_seconds} seconds...")
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
    flattened = [f"{cs.get('IATA', '')}{cs.get('flightnumber', '')}" for cs in codeshares if cs.get("IATA") and cs.get("flightnumber")]
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
    aircraft_info={}
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
            entry["tail_number"] = "{}{}".format("https://www.flightradar24.com/data/aircraft/", entry["tail_number"])  # "UA121"

            # Get today's date
            today = datetime.today()
            year = today.year
            month = today.month
            date = today.day

            # Construct the URL
            ident = fetch_fleet_ident(entry['IATA'])
            # if ident:
            #     print(f"Fleet ident: {entry['IATA']}:{ident}")
            # else:
            #     print("No fleet ident found.")

            # entry["tail_number"] = f"https://www.flightstats.com/v2/flight-tracker/{entry['IATA']}/{entry['flightnumber']}?year={year}&month={month}&date={date}"
            # entry["tail_number"] = f"https://www.flightradar24.com/{entry['IATA']}{entry['flightnumber']}"
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
        # print("Aircraft Info:", aircraft_info)
        # print("Entry:", entry)

    return entry


def remove_unwanted_data(entry):
    entry.pop("id", None)
    entry.pop("mwaaTime", None)
    # entry.pop("dep_airport_code", None)
    entry.pop("dep_terminal", None)
    entry.pop("arr_terminal", None)
    # entry.pop("international", None)
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
            entry["ll_door"] = "6↑7"
        elif gate.startswith("D"):
            entry["ll_door"] = "8"
        elif gate.startswith("A") and len(gate) == 3:
            entry["ll_door"] = "6↑7"
        elif gate.startswith("B"):
            entry["ll_door"] = "9↑10"
        elif gate.startswith("A") and international == 0:
            entry["ll_door"] = "9↑10"
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
        # print("Entry:", entry)
        # print("International:", entry["international"])
    
    if entry["customsAt"] != None:
        entry["status"] = "Customs " + format_time_am_pm(entry["customsAt"])
    else:
        entry["status"] = entry.get("status") or entry.get("mod_status")
    return entry

def clean_departure(entry):
    from datetime import datetime

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

    # Add boarding_time for UA flights
    # if entry["IATA"] == "UA":
    #     print(entry.get("IATACode"))
    #     flight_number = entry["flightnumber"]
    #     if flight_number:
    #         try:
    #             data = united.fetch_flight_data(flight_number, globals.bearer_token, datetime.today().strftime("%Y-%m-%d"))
    #             boarding_time = united.print_boarding_times_from_data(data, flight_number)
    #             entry["boarding_time"] = boarding_time
    #             # print(f"UA boarding time for flight {entry["boarding_time"]}")
    #         except Exception as e:
    #             entry["boarding_time"] = "N/A"
    #             print(f"Error fetching UA boarding time for flight {flight_number}: {e}")
    #     else:
    #         entry["boarding_time"] = "N/A"
    
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
    try:
        # Kick DB upsert after file creation
        p = Path(filename)
        if p.name == "arrivals.json":
            inserted = after_arrivals_json_created(p)
            print(f"Arrivals upserted: {inserted}")
        elif p.name == "departures.json":
            inserted = after_departures_json_created(p)
            print(f"Departures upserted: {inserted}")
    except Exception as e:
        print(f"DB upsert failed for {filename}: {e}")

def main():
    url = "https://www.flydulles.com/arrivals-and-departures/json"
    
    try:
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
            print("Wrote arrivals.json sorted by GateArrivalTime.")
        else:
            print("No arrivals for today.")

        if departures:
            write_to_file(departures_obj, "departures.json")
            print("Wrote departures.json sorted by GateDepartureTime.")
        else:
            print("No departures for today.")
    
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # print(globals.bearer_token)
    main()
