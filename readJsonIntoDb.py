import json
import sqlite3


def add_arrivals(conn, arr_rec):
    try:
        # sql = ("DELETE FROM ARRIVALS WHERE id='%s'") % arr_rec[0]
        # cur = conn.cursor()
        # cur.execute(sql)
        # conn.commit()

        sql = '''INSERT OR REPLACE INTO ARRIVALS (id, IATA, flightnumber, airportcode, baggage, status, mod_status, airline, gate, mod_gate, 
        dep_airport_code,publishedTime, mwaaTime, actualtime, city, claim,  claim1,  claim2,  claim3, dep_terminal, arr_terminal,
         dep_gate, incustoms, customsAt, international, codeshare, aircraft_code, tail_number, weight_class)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) '''
        cur = conn.cursor()
        cur.execute(sql, arr_rec)
        # print(cur.lastrowid)
        print(cur.connection.total_changes)
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError as ie:
        print(ie)


table = """ CREATE TABLE ARRIVALS (
            id VARCHAR(33) NOT NULL PRIMARY KEY,
            IATA CHAR(5) NOT NULL,
            flightnumber VARCHAR(5),
            airportcode CHAR(3),
            baggage CHAR(3),
            status VARCHAR(15),
            mod_status VARCHAR(15),
            airline VARCHAR(25),
            gate VARCHAR(5),
            mod_gate VARCHAR(5),
            dep_airport_code CHAR(3),
            publishedTime datetime,
            mwaaTime datetime,
            actualtime datetime,
            city VARCHAR(25),
            claim VARCHAR(4),
            claim1 VARCHAR(4),
            claim2 VARCHAR(4),
            claim3 VARCHAR(4),
            dep_terminal VARCHAR(10),
            arr_terminal VARCHAR(10),
            dep_gate VARCHAR(10),
            incustoms VARCHAR(10),
            customsAt datetime,
            international VARCHAR(2),
            codeshare VARCHAR(300),
            aircraft_code VARCHAR(10),
            tail_number VARCHAR(10),
            weight_class VARCHAR(10)
        ); """
# connection_obj = sqlite3.connect('arrivals.db')
# cursor_obj = connection_obj.cursor()
# cursor_obj.execute("DROP TABLE IF EXISTS ARRIVALS")
# cursor_obj.execute(table)
# connection_obj.close()

arrJsonFileHandle = open('mac_arr.json', "r")
f = open('mac_arr.json')
data = json.load(f)
# Closing file
f.close()

for i in data:
    aircraftInfoRec = i['aircraftInfo']
    codeshareRec = i['codeshare']
    if aircraftInfoRec is None:
        aircraft_code = ''
        tail_number = ''
        weight_class = ''
    else:
        aircraft_code = i['aircraftInfo']['aircraft_code']
        tail_number = i['aircraftInfo']['tail_number']
        weight_class = i['aircraftInfo']['weight_class']

    codeshare = ''
    if codeshareRec is None:
        codeshare = ''
    else:
        for cs in codeshareRec:
            codeshare = "%s%s%s\n" % (codeshare, cs['IATA'], cs['flightnumber'])

    print(codeshare)

    arr_rec = [i['id'],
               i['IATA'],
               i['flightnumber'],
               i['airportcode'],
               i['baggage'],
               i['status'],
               i['mod_status'],
               i['airline'],
               i['gate'],
               i['mod_gate'],
               i['dep_airport_code'],
               i['publishedTime'],
               i['mwaaTime'],
               i['actualtime'],
               i['city'],
               i['claim'],
               i['claim1'],
               i['claim2'],
               i['claim3'],
               i['dep_terminal'],
               i['arr_terminal'],
               i['dep_gate'],
               i['incustoms'],
               i['customsAt'],
               i['international'],
               codeshare.rstrip(),
               aircraft_code,
               tail_number,
               weight_class]
    print(json.dumps(i['codeshare']))
    try:
        with sqlite3.connect('arrivals.db') as conn:
            arrival_id = add_arrivals(conn, arr_rec)
    except sqlite3.Error as e:
        print(e)
