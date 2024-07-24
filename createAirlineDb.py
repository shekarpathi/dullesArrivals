import requests
import sqlite3
import csv
import os

def add_airlines(conn, airlinedict):
    try:
        # sql = ("DELETE FROM ARRIVALS WHERE id='%s'") % arr_rec[0]
        # cur = conn.cursor()
        # cur.execute(sql)
        # conn.commit()

        sql = '''INSERT OR REPLACE INTO AIRLINES (Name, IATA, ICAO, Callsign, Country, Active)
                 VALUES(?,?,?,?,?,?) '''
        cur = conn.cursor()
        cur.execute(sql, airlinedict)
        # print(cur.lastrowid)
        # print(cur.connection.total_changes)
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError as ie:
        print(ie)

connection_obj = sqlite3.connect('arrivals.db')
cursor_obj = connection_obj.cursor()
cursor_obj.execute("DROP TABLE IF EXISTS AIRLINES")
table = """ CREATE TABLE AIRLINES (
            Name VARCHAR(30),
            IATA CHAR(2),
            ICAO CHAR(3),
            Callsign VARCHAR(30),
            Country VARCHAR(20),
            Active CHAR(1)
        ); """
cursor_obj.execute(table)
connection_obj.close()

airlinedict: list = {}

req = requests.get("https://raw.githubusercontent.com/elmoallistair/datasets/main/airlines.csv")
url_content = req.content
csv_file=open('airlines.csv', 'wb')
csv_file.write(url_content)
csv_file.close()

with sqlite3.connect('arrivals.db') as conn:
    with open('airlines.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row[5] != 'N' and row[1] != '' and "Cargo" not in row[0] and row[1] != '\\N' and row[1] != '-'  and row[1] != '&T' and row[1] != '--' and row[2] != '' and row[2] != '\\N' and row[0] != 'Jayrow' and row[0] != 'Avilu' and row[0] != 'U.S. Air' :
                airlinedict = [row[0], row[1], row[2], row[3], row[4], row[5]]
                try:
                    arrival_id = add_airlines(conn, airlinedict)
                except sqlite3.Error as e:
                    print(e)
        # Closing file
        csvfile.close()
        os.remove("airlines.csv")
conn.close()