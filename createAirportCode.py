import csv
import re

# "id","ident","type","name","latitude_deg","longitude_deg","elevation_ft","continent","iso_country","iso_region","municipality","scheduled_service","gps_code","iata_code","local_code","home_link","wikipedia_link","keywords"

def readAirportCodesCsv() -> dict:
    airportdict: dict = {}
    preclearairports = ['AUH', 'DUB', 'SNN', 'AUA', 'BDA', 'NAS', 'YYC', 'YYZ', 'YEG', 'YHZ', 'YUL', 'YOW', 'YVR',
                        'YYJ', 'YWG', 'SJU', 'STT']
    uselessTypes = ['heliport', 'closed', 'seaplane_base', 'baloonport']
    domesticAirportsCountryCodes = ['US', 'AS', 'GU', 'MP', 'PR', 'US']
    with open('airport_codes.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row[13] == '':
                continue
            if row[3] in uselessTypes:
                continue
            if doesHaveNumbers(row[1]):
                continue

            if row[13] in preclearairports or row[8] in domesticAirportsCountryCodes:
                domIntString = 'Dom'
            else:
                domIntString = 'Int'
            # print(row[1])
            if row[1] == 'OMAA':
                    r=0
            airportdict[row[13]] = [domIntString, row[14], row[3], row[10]]
    csvfile.close()
    # print(airportdict)
    return airportdict

def readAirlineCodesCsv() -> dict:
    airlinedict: dict = {}
    with open('airline_codes.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row[5] == 'N':
                continue
            if row[1] == '':
                continue
            if row[2] == '':
                continue
            airlinedict[row[1]] = [row[2], row[0]]
    csvfile.close()
    return airlinedict

def doesHaveNumbers(inputString):
    return bool(re.search(r'\d', inputString))

# readAirportCodesCsv()
# readAirlineCodesCsv()
