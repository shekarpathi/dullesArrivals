import pandas as pd
from pandas import isnull
import os


def read_airline_codes_wikipedia():
    df = pd.read_html('https://en.wikipedia.org/wiki/List_of_airline_codes')
    return df[0]


df = read_airline_codes_wikipedia()
# print(df)
x = range(len(df))
# for n in x:
# 	iata = df['IATA'][n]
# 	icao = df['ICAO'][n]
# 	if isnull(iata) or isnull(icao):
# 		continue
# 	print('%s %s %s' % (df['IATA'][n], df['ICAO'][n], df['Airline'][n]))

wwwPath = '/var/www/html'
if os.getenv("GITHUB_ACTIONS") == "true":
    airlinesCsvFileHandle = open('airline_iata_icao.csv', "w")
elif (os.path.exists(wwwPath)):
    airlinesCsvFileHandle = open(wwwPath + '/airline_iata_icao.csv', "w")
else:
    airlinesCsvFileHandle = open('mac_airline_iata_icao.csv', "w")

for n in x:
    iata = df.values[n][0]
    icao = df.values[n][1]
    comments = df.values[n][5]
    if isnull(comments):
        comments = ''
    if isnull(iata) or isnull(icao):
        continue
    s = ('%s,%s,%s,%s,%s,%s' % (
    df.values[n][0], df.values[n][1], df.values[n][2], df.values[n][3], df.values[n][4], comments))
    airlinesCsvFileHandle.write('%s\n' % s)
    print(s)
airlinesCsvFileHandle.close()