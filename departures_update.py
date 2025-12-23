import sqlite3
import time
from united import get_boarding_times_from_data

DB_PATH = "arr_dep.db"

def query_and_print_ua_departures():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # get all UA flights from departures table
    cursor.execute("SELECT flightnumber FROM departures WHERE IATA = ?", ("UA",))
    rows = cursor.fetchall()
    
    if not rows:
        print("No UA departures found.")
    else:
        for (flightnumber,) in rows:
            try:
                resp = get_boarding_times_from_data(flightnumber, "IAD")
                print(f"Flight UA{flightnumber}: {resp}")
            except Exception as e:
                print(f"Error fetching boarding times for UA{flightnumber}: {e}")
    
    conn.close()

def main():
    while True:
        query_and_print_ua_departures()
        time.sleep(60)  # wait one minute

if __name__ == "__main__":
    main()

