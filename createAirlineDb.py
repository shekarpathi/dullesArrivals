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

        sql = '''INSERT OR REPLACE INTO AIRLINES (Name, IATA, ICAO, Callsign, Country, Active, starAllianceMember)
                 VALUES(?,?,?,?,?,?,?) '''
        cur = conn.cursor()
        cur.execute(sql, airlinedict)
        # print(cur.lastrowid)
        # print(cur.connection.total_changes)
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError as ie:
        print(ie)

def add_airport(conn, airportlist):
    try:
        sql = '''INSERT OR REPLACE INTO AIRPORTS (id, ident,type,name,continent,iso_country,iso_region,iata_code,local_code,preclearance)
                 VALUES(?,?,?,?,?,?,?,?,?,?) '''
        cur = conn.cursor()
        cur.execute(sql, airportlist)
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
            Active CHAR(1),
            starAllianceMember INTEGER
        ); """
cursor_obj.execute(table)

cursor_obj.execute("DROP TABLE IF EXISTS AIRPORTS")
table = """ CREATE TABLE AIRPORTS (
            id VARCHAR(10),
            ident CHAR(4),
            type CHAR(3),
            name VARCHAR(30),
            continent VARCHAR(20),
            iso_country VARCHAR(20),
            iso_region VARCHAR(20),
            iata_code VARCHAR(20),
            local_code VARCHAR(20),
            preclearance integer
        ); """
cursor_obj.execute(table)
connection_obj.close()

req = requests.get("https://raw.githubusercontent.com/elmoallistair/datasets/main/airlines.csv")
url_content = req.content
csv_file=open('airlines.csv', 'wb')
csv_file.write(url_content)
csv_file.close()

with sqlite3.connect('arrivals.db') as conn:
    with open('airlines.csv', 'r') as csvfile:
        starAllianceMembersArray = ['AUA', 'DLH', 'UAL', 'SAB', 'CCA', 'ANA', 'SAS', 'SWR', 'BEL']
        reader = csv.reader(csvfile)
        for row in reader:
            starAllianceFlag = 0
            if row[2] in starAllianceMembersArray:
                starAllianceFlag = 1

            if row[5] != 'N' and row[1] != '' and "Cargo" not in row[0] and row[1] != '\\N' and row[1] != '-'  and row[1] != '&T' and row[1] != '--' and row[2] != '' and row[2] != '\\N' and row[0] != 'Jayrow' and row[0] != 'Avilu' and row[0] != 'U.S. Air' :
                airlinelist = [row[0], row[1], row[2], row[3], row[4], row[5], starAllianceFlag]
                try:
                    arrival_id = add_airlines(conn, airlinelist)
                except sqlite3.Error as e:
                    print(e)
        # Closing file
        csvfile.close()
        os.remove("airlines.csv")
conn.close()

# req = requests.get("https://davidmegginson.github.io/ourairports-data/airports.csv")
# url_content = req.content
# csv_file=open('airports.csv', 'wb')
# csv_file.write(url_content)
# csv_file.close()
with sqlite3.connect('arrivals.db') as conn:
    with open('airports.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        preclearedAirports = ['SNN', 'DUB', 'AUH', 'NAS', 'AUA', 'BDA', 'YYC', 'YEG', 'YHZ', 'YUL', 'YOW', 'YYZ', 'YVR', 'YYJ', 'YWG']
        for row in reader:
            if row[13] != '' and row[2] != 'heliport' and row[2] != 'seaplane_base':
                preclearanceFlag = 0
                if row[13] in preclearedAirports or row[8] == 'US':
                    preclearanceFlag = 1
                airportlist = [row[0], row[1], row[2], row[3], row[7], row[8], row[9],row[13],row[14], preclearanceFlag]
                try:
                    arrival_id = add_airport(conn, airportlist)
                except sqlite3.Error as e:
                    print(e)
        # Closing file
        csvfile.close()
        # os.remove("airports.csv")
conn.close()

