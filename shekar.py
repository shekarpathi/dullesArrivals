import requests
import json
from datetime import datetime
import united
import globals

def fetch_flight_data(url):
    response = requests.get(url, response = requests.get(url))
    response.raise_for_status()
    return response.json()

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
            print(entry["flightnumber"])
            if entry["flightnumber"] == "946":
                print(aircraft_info)

            try:
                tail_number = aircraft_info.get("tail_number", None)
                if tail_number:
                    entry["tail_number"] = tail_number.lower()
                else:
                    entry["tail_number"] = None
            except Exception:
                entry["tail_number"] = None

        entry["tail_number"] = "{}{}".format("https://www.flightradar24.com/data/aircraft/", entry["tail_number"])  # "UA121"
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
    entry.pop("dep_airport_code", None)
    entry.pop("dep_terminal", None)
    entry.pop("arr_terminal", None)
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
    entry.pop("arrivalInfo", None)
    entry["GateArrivalTime"] = entry.get("actualtime") or entry.get("publishedTime")
    
    if entry["GateArrivalTime"]:
        entry["ArrivalInfo"] = format_time_diff(entry["GateArrivalTime"])
        entry["ArrivalTime"] = format_time_am_pm(entry["GateArrivalTime"])

    entry.pop("actualtime", None)
    entry.pop("publishedTime", None)
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
    if entry["IATA"] == "UA":
        print(entry.get("IATACode"))
        flight_number = entry["flightnumber"]
        if flight_number:
            try:
                data = united.fetch_flight_data(flight_number, globals.bearer_token, datetime.today().strftime("%Y-%m-%d"))
                boarding_time = united.print_boarding_times_from_data(data, flight_number)
                entry["boarding_time"] = boarding_time
                # print(f"UA boarding time for flight {entry["boarding_time"]}")
            except Exception as e:
                entry["boarding_time"] = "N/A"
                print(f"Error fetching UA boarding time for flight {flight_number}: {e}")
        else:
            entry["boarding_time"] = "N/A"
    
    return entry

def sort_by_datetime_field(entries, fieldname):
    def parse_datetime(entry):
        value = entry.get(fieldname)
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S") if value else datetime.max
        except Exception:
            return datetime.max
    return sorted(entries, key=parse_datetime)

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

        if arrivals:
            write_to_file(arrivals, "arrivals.json")
            print("Wrote arrivals.json sorted by GateArrivalTime.")
        else:
            print("No arrivals for today.")

        if departures:
            write_to_file(departures, "departures.json")
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
