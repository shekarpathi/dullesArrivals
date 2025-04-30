import requests
import json
from datetime import datetime
import time
import globals

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
            entry["tail_number"] = f"https://www.flightstats.com/v2/flight-tracker/{entry['IATA']}/{entry['flightnumber']}?year={year}&month={month}&date={date}"
            entry["tail_number"] = f"https://www.flightradar24.com/{entry['IATA']}{entry['flightnumber']}"

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
                return f"in {hours}h {remaining_minutes}m"
            else:
                return f"in {remaining_minutes}m"
        else:
            if hours > 0:
                return f"{hours}h {remaining_minutes}m ago"
            else:
                return f"{remaining_minutes}m ago"
    except Exception:
        return None

def clean_arrival(entry):
    entry = flatten_codeshare(entry)
    entry = flatten_tail_number(entry)
    entry = remove_unwanted_data(entry)
    entry = flatten_baggageclaim(entry)
    entry = get_international_domestic(entry)
    entry.pop("arrivalInfo", None)
    entry["GateArrivalTime"] = entry.get("actualtime") or entry.get("publishedTime")
    
    if entry["GateArrivalTime"]:
        entry["ArrivalInfo"] = format_time_diff(entry["GateArrivalTime"])
        entry["ArrivalTime"] = format_time_am_pm(entry["GateArrivalTime"])

    entry.pop("actualtime", None)
    entry.pop("publishedTime", None)
    return entry

def get_international_domestic(entry):
    try:
        preclearairports = ['AUH', 'DUB', 'SNN', 'AUA', 'BDA', 'NAS', 'YYC', 'YYZ', 'YEG', 'YHZ', 'YUL', 'YOW', 'YVR',
                            'YYJ', 'YWG', 'SJU', 'STT']
        starAllianceMembersArray = ['OS', 'DL', 'UA', 'SAB', 'CA', 'NH', 'SK', 'LX', 'SN']

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
                    return f"in {hours}h {remaining_minutes}m"
                else:
                    return f"in {remaining_minutes}m"
            else:
                if hours > 0:
                    return f"{hours}h {remaining_minutes}m ago"
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
    print(globals.bearer_token)
    main()
