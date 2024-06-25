import os
import requests, json
from datetime import datetime
from getAirlineCodesPanda import readAirportCodesCsv

def constructFlightStatsURL(twoLetterAirlineCode, flightnumber, arrivalTime):
    # https://www.flightstats.com/v2/flight-tracker/LX/72?year=2024&month=3&date=30
    yyyymmdd = arrivalTime.split(' ')[0]
    yyyy = yyyymmdd.split('-')[0]
    mm = yyyymmdd.split('-')[1]
    dd = yyyymmdd.split('-')[2]
    s: str = 'https://www.flightstats.com/v2/flight-tracker/%s/%s?year=%s&month=%s&date=%s' % (twoLetterAirlineCode, flightnumber, yyyy, mm, dd)
    return s

def constructFlightAwareURL(threeLetterAirlineCode, flightnumber):
    # https://www.flightaware.com/live/flight/SWR72
    s: str = 'https://www.flightaware.com/live/flight/%s%s' % (threeLetterAirlineCode, flightnumber)
    return s


def getDataAndWriteToJson():
    wwwPath = '/var/www/html'
    if os.getenv("GITHUB_ACTIONS") == "true":
        arrJsonHandle = open('arr.json', "w")
        depJsonHandle = open('dep.json', "w")
    elif (os.path.exists(wwwPath)):
        arrJsonHandle = open(wwwPath + '/arr.json', "w")
        depJsonHandle = open(wwwPath + '/dep.json', "w")
    else:
        arrJsonHandle = open('mac_arr.json', "w")
        depJsonHandle = open('mac_dep.json', "w")

    url = "https://www.flydulles.com/arrivals-and-departures/json"
    headers = dict()
    headers[
        "Cookie"] = "gdprText=1; ct_check_js=1c40e376161c5de64b00f3eb4ca54aed; ct_ps_timestamp=1708001301; ct_fkp_timestamp=0; ct_pointer_data=0; ct_timezone=-5; apbct_antibot=e057b330c453aaf1b084653edef1acc2866210a559d6700bc40c126dd2634986; ct_has_scrolled=false; alertsText=Yes; flight-info=1"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        json_data = json.loads(response.text)
        arrJsonHandle.write(json.dumps(json_data['arrivals'], indent=2))
        arrJsonHandle.close()
        depJsonHandle.write(json.dumps(json_data['departures'], indent=2))
        depJsonHandle.close()


def isArrivingToday(publishedTime: str) -> bool:
    return True
    if (publishedTime.split(" ")[0] == datetime.today().date().strftime('%Y-%m-%d')):
        # print('%s %s' % (publishedTime.split(" ")[0], datetime.today().date().strftime('%Y-%m-%d')))
        return True
    else:
        return False

def makeCodeSharesString(codeshareList: list) -> str:
    s: str = ''
    for codeshare in codeshareList:
        s += ('%s%s ' % (codeshare['IATA'], codeshare['flightnumber']))
    return s.rstrip()

def getCarousel(c, c1, c2, c3):
    if c == '' and c1 == '':
        return (c2 + ',' + c3).rstrip(',')
    else:
        return c

def getArrivalTime(publishedTime, actualtime):
    if actualtime != None:
        retTime = actualtime
    else:
        retTime = publishedTime
    # return retTime.split(" ")[1]
    return retTime

def parseArrivalJson():
    airlineDict = readAirportCodesCsv()
    wwwPath = '/var/www/html'
    if os.getenv("GITHUB_ACTIONS") == "true":
        arrJsonHandle = open('arr.json', "r")
        depJsonHandle = open('dep.json', "r")
    elif (os.path.exists(wwwPath)):
        arrJsonHandle = open(wwwPath + '/arr.json', "r")
        depJsonHandle = open(wwwPath + '/dep.json', "r")
    else:
        arrJsonHandle = open('mac_arr.json', "r")
        depJsonHandle = open('mac_dep.json', "r")
    json_data = json.loads(arrJsonHandle.read())
    for arrivalRecord in json_data:
        if isArrivingToday(arrivalRecord['publishedTime']):
            airlineCode = arrivalRecord['IATA']
            flightnumber = arrivalRecord['flightnumber']
            airline = arrivalRecord['airline']
            departureAirport = arrivalRecord['dep_airport_code']
            departureCity = arrivalRecord['city']
            status = arrivalRecord['status']
            gate = arrivalRecord['gate']
            baggage = arrivalRecord['baggage'] if arrivalRecord['baggage'] is not None else ''
            arrivalTime = getArrivalTime(arrivalRecord['publishedTime'], arrivalRecord['actualtime'])
            baggageClaim = getCarousel(baggage, arrivalRecord['claim'], arrivalRecord['claim1'], arrivalRecord['claim2'])
            # intDomFlag = arrivalRecord['incustoms']
            intDom = 'Int' if arrivalRecord['international'] == 1 else 'Dom'
            # arrivalRecord['arrivalInfo'][0]
            try:
                threeLetterAirlineCode = airlineDict[airlineCode][0]
                trackingURL = constructFlightStatsURL(airlineCode, flightnumber, arrivalTime)
                constructFlightAwareURL(threeLetterAirlineCode, flightnumber)
                s = ('%s%s| %s | %s | %s | %s | %s | %s | %s | %s | B:%s | %s 🚌 👜 🛄' % (
                airlineCode, flightnumber, trackingURL, departureAirport, departureCity, airline, gate, intDom,
                makeCodeSharesString(arrivalRecord['codeshare']), arrivalTime, baggageClaim, status))
                print(s)
            except:
                print(airlineCode)


if __name__ == "__main__":
    getDataAndWriteToJson()
    parseArrivalJson()
