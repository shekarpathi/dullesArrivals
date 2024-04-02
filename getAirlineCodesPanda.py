import pandas as pd
from pandas import isnull, DataFrame
import os


def read_airline_codes_wikipedia() -> DataFrame:
    df = pd.read_html('https://en.wikipedia.org/wiki/List_of_airline_codes')
    return df[0]

def readAirportCodesCsv() -> dict:
    preclearairports = ['AUH', 'DUB', 'SNN', 'AUA', 'BDA', 'NAS', 'YYC', 'YYZ', 'YEG', 'YHZ', 'YUL', 'YOW', 'YVR',
                        'YYJ', 'YWG', 'SJU', 'STT']

    df = read_airline_codes_wikipedia()
    x = range(len(df))
    wwwPath = '/var/www/html'
    if os.getenv("GITHUB_ACTIONS") == "true":
        airlinesCsvFileHandle = open('airline_iata_icao.csv', "w")
    elif (os.path.exists(wwwPath)):
        airlinesCsvFileHandle = open(wwwPath + '/airline_iata_icao.csv', "w")
    else:
        airlinesCsvFileHandle = open('mac_airline_iata_icao.csv', "w")
    airportdict: dict = {}
    for n in x:
        iata = df.values[n][0]
        icao = df.values[n][1]
        # comments = df.values[n][5]
        # if isnull(comments):
        #     comments = ''
        if isnull(iata) or isnull(icao):
            continue
        airportdict[df.values[n][0]] = [df.values[n][1], df.values[n][2], df.values[n][3], df.values[n][4]]
        s = ('%s,%s,%s,%s,%s' % (
            df.values[n][0], df.values[n][1], df.values[n][2], df.values[n][3], df.values[n][4]))
        airlinesCsvFileHandle.write('%s\n' % s)
        print(s)

    s = ('%s,%s,%s,%s,%s' % (
        'N3', 'VOS', 'Volaris El Salvador', 'VOLARIS', 'El Salvador'))
    airlinesCsvFileHandle.write('%s\n' % s)
    airlinesCsvFileHandle.close()

    airportdict['N3'] = ['VOS', 'Volaris El Salvador', 'VOLARIS', 'El Salvador']
    return airportdict


if __name__ == "__main__":
    readAirportCodesCsv()
    q = 0
