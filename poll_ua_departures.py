import sqlite3
import time
import json
from typing import Any, Dict, Optional

from united import get_boarding_times_from_data

DB_PATH = 'arr_dep.db'

UA_COLUMNS = [
    'ua_Status',
    'ua_Departure_Time',
    'ua_scheduled_departure_time',
    'ua_estimated_departure_time',
    'ua_estimated_departure_delay',
    'ua_estimated_arrival_time',
    'ua_scheduled_arrival_time',
    'ua_estimated_arrival_delay',
    'ua_Departure_Info',
]

def deep_find_first(d: Any, key_candidates) -> Optional[Any]:
    if d is None:
        return None
    if isinstance(key_candidates, str):
        key_candidates = [key_candidates]
    key_candidates_lc = [k.lower() for k in key_candidates]
    if isinstance(d, dict):
        for k, v in d.items():
            if k.lower() in key_candidates_lc:
                return v
        for v in d.values():
            found = deep_find_first(v, key_candidates_lc)
            if found is not None:
                return found
    elif isinstance(d, list):
        for item in d:
            found = deep_find_first(item, key_candidates_lc)
            if found is not None:
                return found
    return None

def extract_ua_updates(united_resp: Dict[str, Any]) -> Dict[str, Optional[str]]:
    status = deep_find_first(united_resp, ['Status', 'FlightStatus', 'statusText', 'status'])
    dep_time = deep_find_first(united_resp, ['DepartureTime', 'ActualDepartureTime', 'ActualGateDepartureTime'])
    sch_dep_time = deep_find_first(united_resp, ['ScheduledDepartureTime', 'ScheduledGateDepartureTime'])
    est_dep_time = deep_find_first(united_resp, ['EstimatedDepartureTime', 'EstimatedGateDepartureTime'])
    est_dep_delay = deep_find_first(united_resp, ['EstimatedDepartureDelayMinutes', 'DepartureDelayMinutes', 'DepDelayMinutes'])
    est_arr_time = deep_find_first(united_resp, ['EstimatedArrivalTime', 'EstimatedGateArrivalTime'])
    sch_arr_time = deep_find_first(united_resp, ['ScheduledArrivalTime', 'ScheduledGateArrivalTime'])
    est_arr_delay = deep_find_first(united_resp, ['EstimatedArrivalDelayMinutes', 'ArrivalDelayMinutes', 'ArrDelayMinutes'])
    try:
        dep_info = json.dumps(united_resp, separators=(',', ':'), ensure_ascii=False)[:50000]
    except Exception:
        dep_info = None
    def to_str(x):
        return None if x is None else str(x)
    return {
        'ua_Status': to_str(status),
        'ua_Departure_Time': to_str(dep_time),
        'ua_scheduled_departure_time': to_str(sch_dep_time),
        'ua_estimated_departure_time': to_str(est_dep_time),
        'ua_estimated_departure_delay': to_str(est_dep_delay),
        'ua_estimated_arrival_time': to_str(est_arr_time),
        'ua_scheduled_arrival_time': to_str(sch_arr_time),
        'ua_estimated_arrival_delay': to_str(est_arr_delay),
        'ua_Departure_Info': to_str(dep_info),
    }

def update_departure_row(conn: sqlite3.Connection, iata: str, flightnumber: str, updates: Dict[str, Optional[str]]) -> int:
    sets = []
    values = []
    for k, v in updates.items():
        if k in UA_COLUMNS:
            sets.append('"{}" = ?'.format(k))
            values.append(v)
    if not sets:
        return 0
    values.extend(['UA', flightnumber])
    sql = 'UPDATE departures SET ' + ', '.join(sets) + ' WHERE departure_date = date(\'now\',\'localtime\') AND IATA = ? AND flightnumber = ?'
    cur = conn.execute(sql, values)
    return cur.rowcount

def get_ua_flights(conn: sqlite3.Connection):
    cur = conn.execute("SELECT DISTINCT flightnumber FROM departures WHERE IATA = 'UA' AND departure_date = date('now','localtime')")
    return [row[0] for row in cur.fetchall()]

def poll_once():
    conn = sqlite3.connect(DB_PATH)
    try:
        flightnumbers = get_ua_flights(conn)
        if not flightnumbers:
            print('[poll] No UA departures for today.')
            return
        for fn in flightnumbers:
            try:
                resp = get_boarding_times_from_data(fn, 'IAD')
                print('[UA {}] API response: {}'.format(fn, resp))
                updates = extract_ua_updates(resp if isinstance(resp, dict) else {})
                updated = update_departure_row(conn, 'UA', fn, updates)
                conn.commit()
                print('[UA {}] UA columns updated: {} row(s).'.format(fn, updated))
            except Exception as e:
                print('[UA {}] Error: {}'.format(fn, e))
    finally:
        conn.close()

def main():
    while True:
        poll_once()
        time.sleep(60)

if __name__ == '__main__':
    main()