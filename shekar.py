import requests
import json
import csv
import io
from datetime import datetime
import time
import urllib3
import os
from urllib.parse import quote

# import globals
airline_name_dict = {
    "EVA Air": "EVA Air",
    "Air Premia Inc.": "Air Premia",
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

# IATA aircraft type designators returned by the Dulles flight feed.
# Unknown codes are intentionally preserved so new equipment is still visible.
aircraft_type_dict = {
    "221": "Airbus A220-100",
    "223": "Airbus A220-300",
    "318": "Airbus A318",
    "319": "Airbus A319",
    "320": "Airbus A320",
    "321": "Airbus A321",
    "A318": "Airbus A318",
    "A319": "Airbus A319",
    "A320": "Airbus A320",
    "A321": "Airbus A321",
    "A20N": "Airbus A320neo",
    "A21N": "Airbus A321neo",
    "32A": "Airbus A320",
    "32B": "Airbus A321",
    "32N": "Airbus A320neo",
    "32Q": "Airbus A321neo",
    "332": "Airbus A330-200",
    "333": "Airbus A330-300",
    "338": "Airbus A330-800neo",
    "339": "Airbus A330-900neo",
    "343": "Airbus A340-300",
    "346": "Airbus A340-600",
    "359": "Airbus A350-900",
    "35K": "Airbus A350-1000",
    "388": "Airbus A380-800",
    "73G": "Boeing 737-700",
    "73H": "Boeing 737-800",
    "73J": "Boeing 737-900",
    "738": "Boeing 737-800",
    "739": "Boeing 737-900",
    "B737": "Boeing 737-700",
    "B738": "Boeing 737-800",
    "B739": "Boeing 737-900",
    "B37M": "Boeing 737 MAX 7",
    "B38M": "Boeing 737 MAX 8",
    "B39M": "Boeing 737 MAX 9",
    "B3XM": "Boeing 737 MAX 10",
    "752": "Boeing 757-200",
    "753": "Boeing 757-300",
    "762": "Boeing 767-200",
    "763": "Boeing 767-300",
    "764": "Boeing 767-400",
    "772": "Boeing 777-200",
    "773": "Boeing 777-300",
    "77L": "Boeing 777-200LR",
    "77W": "Boeing 777-300ER",
    "788": "Boeing 787-8 Dreamliner",
    "789": "Boeing 787-9 Dreamliner",
    "78X": "Boeing 787-10 Dreamliner",
    "AT7": "ATR 72",
    "BCS1": "Airbus A220-100",
    "BCS3": "Airbus A220-300",
    "CR2": "Bombardier CRJ200",
    "CR5": "Bombardier CRJ550",
    "CR7": "Bombardier CRJ700",
    "CR9": "Bombardier CRJ900",
    "E135": "Embraer ERJ-135",
    "E145": "Embraer ERJ-145",
    "ERJ": "Embraer ERJ family",
    "E170": "Embraer E170",
    "E175": "Embraer E175",
    "E75L": "Embraer E175 (long-wing variant)",
    "E75S": "Embraer E175 (short-wing variant)",
    "E190": "Embraer E190",
    "E195": "Embraer E195",
    "E290": "Embraer E190-E2",
    "E295": "Embraer E195-E2",
    "CRJ2": "Bombardier CRJ200",
    "DH8D": "De Havilland Canada Dash 8-400",
    "C208": "Cessna 208 Caravan",
}

AIRCRAFT_CACHE_FILE = "aircraft_type_cache.json"
AIRCRAFT_DATA_URL = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/planes.dat"


def load_aircraft_type_cache():
    if not os.path.exists(AIRCRAFT_CACHE_FILE):
        return {}
    try:
        with open(AIRCRAFT_CACHE_FILE, "r") as cache_file:
            cached_types = json.load(cache_file)
            return cached_types if isinstance(cached_types, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


aircraft_type_cache = load_aircraft_type_cache()
remote_aircraft_types = None


def save_aircraft_type_cache():
    try:
        temporary_file = f"{AIRCRAFT_CACHE_FILE}.tmp"
        with open(temporary_file, "w") as cache_file:
            json.dump(aircraft_type_cache, cache_file, indent=2, sort_keys=True)
        os.replace(temporary_file, AIRCRAFT_CACHE_FILE)
    except OSError as error:
        print(f"Unable to save aircraft type cache: {error}")


def fetch_remote_aircraft_types():
    """Download OpenFlights' IATA/ICAO aircraft list at most once per run."""
    global remote_aircraft_types
    if remote_aircraft_types is not None:
        return remote_aircraft_types

    remote_aircraft_types = {}
    try:
        response = requests.get(AIRCRAFT_DATA_URL, timeout=(5, 10))
        response.raise_for_status()
        for name, iata_code, icao_code in csv.reader(io.StringIO(response.text)):
            for code in (iata_code, icao_code):
                normalized_code = code.strip().upper()
                if normalized_code and normalized_code != r"\N":
                    remote_aircraft_types[normalized_code] = name.strip()
    except (requests.RequestException, ValueError, csv.Error) as error:
        print(f"Unable to refresh aircraft type data: {error}")

    return remote_aircraft_types


def decode_aircraft_type(aircraft_code):
    """Resolve built-in, cached, then remote aircraft names; preserve unknown codes."""
    if not aircraft_code:
        return None
    normalized_code = str(aircraft_code).strip().upper()
    if normalized_code in aircraft_type_dict:
        return compact_aircraft_name(aircraft_type_dict[normalized_code])
    if normalized_code in aircraft_type_cache:
        return compact_aircraft_name(aircraft_type_cache[normalized_code])

    aircraft_name = fetch_remote_aircraft_types().get(normalized_code)
    if aircraft_name:
        aircraft_type_cache[normalized_code] = aircraft_name
        save_aircraft_type_cache()
        return compact_aircraft_name(aircraft_name)

    return normalized_code


def compact_aircraft_name(aircraft_name):
    """Remove space-consuming manufacturer prefixes from Airbus and Boeing names."""
    for prefix in ("Airbus ", "Boeing "):
        if aircraft_name.startswith(prefix):
            return aircraft_name[len(prefix):]
    return aircraft_name


# Optional: Suppress warnings if using verify=False (not recommended for production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CACHE_FILE = "fleet_cache.json"
ICAO_CACHE_FILE = "icao_hex_cache.json"
ICAO_STATE_FILE = "icao_lookup_state.json"
ICAO_MAX_REQUESTS_PER_RUN = 1
ICAO_NOT_FOUND_RETRY_SECONDS = 6 * 60 * 60
ICAO_RATE_LIMIT_RETRY_SECONDS = 60 * 60

# Load cache from file
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        try:
            fleet_ident_cache = json.load(f)
        except json.JSONDecodeError:
            fleet_ident_cache = {}
else:
    fleet_ident_cache = {}

if os.path.exists(ICAO_CACHE_FILE):
    with open(ICAO_CACHE_FILE, "r") as f:
        try:
            icao_hex_cache = json.load(f)
        except json.JSONDecodeError:
            icao_hex_cache = {}
else:
    icao_hex_cache = {}

if os.path.exists(ICAO_STATE_FILE):
    with open(ICAO_STATE_FILE, "r") as f:
        try:
            icao_lookup_state = json.load(f)
        except json.JSONDecodeError:
            icao_lookup_state = {}
else:
    icao_lookup_state = {}

icao_requests_this_run = 0

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(fleet_ident_cache, f)


def save_icao_hex_cache():
    temporary_file = f"{ICAO_CACHE_FILE}.tmp"
    try:
        with open(temporary_file, "w") as f:
            json.dump(icao_hex_cache, f, indent=2, sort_keys=True)
        os.replace(temporary_file, ICAO_CACHE_FILE)
    except OSError as error:
        print(f"Unable to save ICAO hex cache: {error}")


def save_icao_lookup_state():
    temporary_file = f"{ICAO_STATE_FILE}.tmp"
    try:
        with open(temporary_file, "w") as f:
            json.dump(icao_lookup_state, f, indent=2, sort_keys=True)
        os.replace(temporary_file, ICAO_STATE_FILE)
    except OSError as error:
        print(f"Unable to save ICAO lookup state: {error}")


def fetch_icao_hex(registration):
    """Resolve an aircraft registration to its ICAO hex through ADSB.lol."""
    global icao_requests_this_run
    normalized_registration = str(registration).strip().upper()
    if not normalized_registration:
        return None
    if normalized_registration in icao_hex_cache:
        return icao_hex_cache[normalized_registration]

    now = int(time.time())
    if now < int(icao_lookup_state.get("rate_limit_until", 0)):
        return None
    retry_after = icao_lookup_state.get("registrations", {}).get(normalized_registration, 0)
    if now < int(retry_after):
        return None
    if icao_requests_this_run >= ICAO_MAX_REQUESTS_PER_RUN:
        return None

    url = f"https://api.adsb.lol/v2/reg/{quote(normalized_registration, safe='-')}"
    try:
        icao_requests_this_run += 1
        response = requests.get(url, timeout=(5, 10))
        if response.status_code == 429:
            retry_seconds = response.headers.get("Retry-After", "")
            retry_seconds = int(retry_seconds) if retry_seconds.isdigit() else ICAO_RATE_LIMIT_RETRY_SECONDS
            icao_lookup_state["rate_limit_until"] = now + max(retry_seconds, 60)
            save_icao_lookup_state()
            print(f"ADSB.lol rate limit reached; pausing ICAO lookups for {max(retry_seconds, 60)} seconds.")
            return None
        response.raise_for_status()
        aircraft = response.json().get("ac", [])
        matching_aircraft = next(
            (item for item in aircraft if str(item.get("r", "")).upper() == normalized_registration),
            aircraft[0] if aircraft else None,
        )
        icao_hex = str(matching_aircraft.get("hex", "")).lower() if matching_aircraft else ""
        if len(icao_hex) == 6 and all(character in "0123456789abcdef" for character in icao_hex):
            icao_hex_cache[normalized_registration] = icao_hex
            save_icao_hex_cache()
            return icao_hex
        registrations = icao_lookup_state.setdefault("registrations", {})
        registrations[normalized_registration] = now + ICAO_NOT_FOUND_RETRY_SECONDS
        save_icao_lookup_state()
    except (requests.RequestException, json.JSONDecodeError, AttributeError) as error:
        print(f"Unable to resolve ICAO hex for {normalized_registration}: {error}")

    return None

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
            response = requests.get(url, timeout=(5, 10), cookies={"flight-info": "1"})
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
    aircraft_info_value = entry.get("aircraftInfo")
    if isinstance(aircraft_info_value, list) and aircraft_info_value:
        aircraft_info = aircraft_info_value[0]
    elif isinstance(aircraft_info_value, dict):
        aircraft_info = aircraft_info_value
    else:
        aircraft_info = {}

    try:
        flight_number = str(entry.get("flightnumber") or "").strip()
        airline_code = str(entry.get("IATA") or "").strip().upper()
        flightaware_ident = fetch_fleet_ident(airline_code) or airline_code
        entry["flight_url"] = (
            f"https://www.flightaware.com/live/flight/{flightaware_ident}{flight_number}"
            if flightaware_ident and flight_number else None
        )

        tail_number = aircraft_info.get("tail_number")
        if tail_number:
            registration = str(tail_number).strip().lower()
            entry["tail_number"] = registration.upper()
            icao_hex = fetch_icao_hex(registration)
            entry["icao_hex"] = icao_hex
            entry["tail_url"] = f"https://adsb.lol/?icao={icao_hex}" if icao_hex else None
        else:
            entry["tail_number"] = None
            entry["icao_hex"] = None
            entry["tail_url"] = None

        aircraft_code = aircraft_info.get("aircraft_code")
        entry["aircraft_code"] = decode_aircraft_type(aircraft_code)
        entry.pop("aircraftInfo", None)
    except Exception:
        entry["flight_url"] = None
        entry["tail_number"] = None
        entry["icao_hex"] = None
        entry["tail_url"] = None
        entry["aircraft_code"] = None
        entry.pop("aircraftInfo", None)
        print("Error processing tail number for flight:", entry.get("flightnumber"))

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
            entry["ll_door"] = "10↑11"
        elif gate.startswith("A") and international == 0:
            entry["ll_door"] = "10↑11"
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
                            'YYJ', 'YWG', 'YTZ', 'SJU', 'STT']
        starAllianceMembersArray = ['OS', 'DL', 'UA', 'SAB', 'CA', 'NH', 'LX', 'SN', 'LH']

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

def normalize_flight_entries(entries):
    """Normalize array and numerically keyed object flight collections."""
    if isinstance(entries, list):
        candidates = entries
    elif isinstance(entries, dict):
        candidates = entries.values()
    else:
        return []

    return [entry for entry in candidates if isinstance(entry, dict)]

def filter_process_and_sort(entries, cleaner, sort_field):
    entries = normalize_flight_entries(entries)
    cleaned = [cleaner(entry) for entry in entries if is_published_today(entry)]
    return sort_by_datetime_field(cleaned, sort_field)

def write_to_file(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

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
