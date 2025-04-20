import requests
import datetime

starAllianceMembersArray = ['AUA', 'DLH', 'UAL', 'SAB', 'CCA', 'ANA', 'SAS', 'SWR', 'BEL']
preclearairports = ['AUH', 'DUB', 'SNN', 'AUA', 'BDA', 'NAS', 'YYC', 'YYZ', 'YEG', 'YHZ', 'YUL', 'YOW', 'YVR', 'YYJ', 'YWG', 'SJU', 'STT']

def fetch_and_process_arrivals():
    # URL to fetch the flight data
    url = "https://www.flydulles.com/arrivals-and-departures/json"

    # Get today's date in YYYY-MM-DD format
    today = datetime.datetime.now().date().isoformat()

    # Function to format time as HH:MM if it's a valid date, else return "N/A"
    def format_time(time_str):
        try:
            # Check if the time_str is a valid date
            dt = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            #dt = datetime.datetime.strptime(time_str, "%I:%M %p")
            formatted_time = dt.strftime("%-I:%M %p")
            #print(dt, formatted_time)
            return formatted_time 
        except (ValueError, TypeError):
            # Return "" if the format is invalid or time_str is not a date
            return ""

    try:
        # Fetch the JSON data from the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()  # Parse the JSON response

        # Extract the arrivals node
        arrivals = data.get("arrivals", [])
        departures = data.get("departures", [])
        arrival_flights = []
        ua_departures = []
        ab_departures = []
        fis_arrivals = []
        iab_arrivals = []

        for arrival in arrivals:
            # Extract the required fields
            IATA = arrival.get("IATA", "")
            flightnumber = arrival.get("flightnumber", "")
            airline = arrival.get("airline", "")
            dep_airport_code = arrival.get("dep_airport_code", "")
            city = arrival.get("city", "")
            baggage = arrival.get("baggage", "")
            international = arrival.get("international", "")
            international = 0 if dep_airport_code in preclearairports else international
            dom_or_int = "Int" if (international == 1) else "Dom"
            status = arrival.get("status", "")
            gate = arrival.get("gate", "")
            mod_gate = arrival.get("mod_gate", "")
            publishedTime = arrival.get("publishedTime", "")
            actualtime = arrival.get("actualtime", "")
            time = actualtime if actualtime else publishedTime
            claim = arrival.get("claim", "")
            claim1 = arrival.get("claim1", "")
            claim2 = arrival.get("claim2", "")
            claim3 = arrival.get("claim3", "")
            customsAt = arrival.get("customsAt", "")
            try:
                aircraft_code = arrival.get("aircraftInfo", {}).get("aircraft_code", "")
            except:
                print("error")
            try:
                arrival_info = arrival.get("arrivalInfo", [])
                remaining_time = arrival_info[0].get("remaining_time", "") if arrival_info else ""
            except:
                print("error")

            # Use actualtime if available, otherwise publishedTime
            flight_time_unformatted = actualtime if actualtime else publishedTime
            flight_time = format_time(actualtime) if actualtime else format_time(publishedTime)
            customs_time = format_time(customsAt)
            values = [baggage, claim, claim1, claim2, claim3]
            unique_baggage = set(value for value in values if value is not None)
            unique_values_string = ",".join(map(str, unique_baggage))
            #print(unique_values_string)

            # Filter for flights where publishedTime is today
            if today in publishedTime:
                arrival_flights.append({
                    "IATA": IATA,
                    "flightnumber": flightnumber,
                    "airline": airline,
                    #"time": time,
                    "dep_airport_code": dep_airport_code,
                    "city": city,
                    "baggage": baggage,
                    "international": international,
                    "dom_or_int": dom_or_int,
                    "status": status,
                    "gate": gate,
                    "mod_gate": mod_gate,
                    "time": flight_time,
                    "arrivalTime": flight_time_unformatted,
                    "claim": claim,
                    "claim1": claim1,
                    "claim2": claim2,
                    "claim3": claim3,
                    "ubaggage": unique_values_string,
                    "customsAt": customs_time,
                    "aircraft_code": aircraft_code,
                    "remaining_time": remaining_time,
                })
            
            # Filter for flights where publishedTime is today
            if today in publishedTime and IATA == "UA":
                ua_departures.append({
                    "IATA": IATA,
                    "flightnumber": flightnumber,
                })

        # Sort the flights by actualtime or publishedTime (time format)
        sorted_flights = sorted(arrival_flights, key=lambda x: x["arrivalTime"])

        # Print the sorted flights
        for flight in sorted_flights:
            print(f"Flight: {flight['IATA']} {flight['flightnumber']}")
            print(f"Airline: {flight['airline']}")
            print(f"https://planefinder.net/flight/{flight['IATA']}{flight['flightnumber']}")
            print(f"Dep Airport: {flight['dep_airport_code']} {flight['city']}")
            #print(f"City: {flight['city']}")
            print(f"Arrival: {flight['time']}")
            #print(f"Baggage: {flight['baggage']}, {flight['claim']}, {flight['claim1']}, {flight['claim2']}")
            print(f"Baggage: {flight['ubaggage']}")
            #print(f"International: {flight['international']}")
            print(f"Dom/Int: {flight['dom_or_int']}")
            print(f"Status: {flight['status']}")
            print(f"Gate: {flight['gate']}")
            #print(f"Modified Gate: {flight['mod_gate']}")
            print(f"Customs At: {flight['customsAt']}")
            print(f"Aircraft Code: {flight['aircraft_code']}")
            print(f"Remaining Time: {flight['remaining_time']}")
            print("-" * 40)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
    except ValueError as e:
        print(f"Error parsing JSON: {e}")

# Run the function
if __name__ == "__main__":
    fetch_and_process_arrivals()
