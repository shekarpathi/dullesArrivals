import time
from datetime import datetime, timedelta
from pytz import timezone
import os
import requests, json
import csv

url = "https://www.flydulles.com/arrivals-and-departures/json"
wwwPath = '/var/www/html'
fisTableHTML: str = ''
iabTableHTML: str = ''
fisArray = []
iabArray = []
response_code = 401
retryCount = 0
success = False
airportdict: dict = {}
airlinedict: dict = {}


def readAirportCodesCsv():
    preclearairports = ['AUH', 'DUB', 'SNN', 'AUA', 'BDA', 'NAS', 'YYC', 'YYZ', 'YEG', 'YHZ', 'YUL', 'YOW', 'YVR',
                        'YYJ', 'YWG', 'SJU', 'STT']
    with open('airport_codes.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row[9] != '' and "_airport" in row[1] != '':
                # print(row[0], row[1], row[5], row[9])
                if row[5] == 'US' or row[9] in preclearairports:
                    # print(row[9], row[5])
                    airportdict[row[9]] = ['Domestic', row[7]]
                else:
                    # print(row[9])
                    airportdict[row[9]] = ['International', row[7]]
        csvfile.close()


def readAirlineCodesCsv():
    with open('airline_codes.csv', 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            airlinedict[row[0]] = row[1]
        csvfile.close()


def getCustomsString(mod_status, customsAt) -> str:
    if mod_status != '':
        # return (mod_status + ' since ' + customsAt)
        return (customsAt)
    else:
        return ''


def getCarousel(c, c1, c2, c3):
    if c == '' and c1 == '':
        return (c2 + ',' + c3).rstrip(',')
    else:
        return c


def getCurrentTime():
    now = datetime.now(tz=timezone('America/New_York'))
    return now.strftime("%b %d, %Y %I:%M %p")


def isTimeBetween2and6(timeString) -> bool:
    if timeString is not None:

        print(timeString)
        time_split = timeString.split(" ")
        print(time_split[1])
        hrs = time_split[1].replace(':', '')
        print(hrs)
        if (int(hrs) > 140000 and int(hrs) < 180000):
            return True
    else:
        return False


def formatTimeFor2To6(timeString) -> str:
    if timeString is not None:
        datetime_object = datetime.strptime(timeString, '%Y-%m-%d %H:%M:%S')
        str_date = datetime_object.strftime("%I:%M %p")
        print(str_date)
        return str_date


def formatTime(timeString) -> str:
    if timeString is not None:
        print(timeString)
        passedTime = datetime.strptime(timeString, "%Y-%m-%d %H:%M:%S")
        now = datetime.today()
        past = now - passedTime
        if past.days < 0:
            past = past * -1
            print('+%s' % past.seconds)
            convert = time.strftime("+F %Hh %Mm", time.gmtime(past.seconds))
            print(convert)
        else:
            print('-%s' % past.seconds)
            convert = time.strftime("-P %Hh %Mm", time.gmtime(past.seconds))
            print(convert)
        print('----\n')

        datetime_obj = datetime.strptime(timeString, "%Y-%m-%d %H:%M:%S")
        # print(datetime_obj.strftime("%m/%d %H:%M"))
        return datetime_obj.strftime("%m/%d %H:%M")
    else:
        return ''


def formatGate(gate, domesticOrInternational):
    rgate = ''
    if domesticOrInternational == "International":
        if gate != None:
            suffix = " %s - Bag 15" % gate
        else:
            suffix = " Bag 15"
    else:
        if gate is not None:
            rgate = gate
            if gate[0] == "A":
                suffix = "&nbsp;&nbsp;&nbsp;&nbsp;🚆6-7"
            elif gate[0] == "C":
                suffix = "&nbsp;&nbsp;&nbsp;&nbsp;🚆6-7"
            elif gate[0] == "B":
                suffix = "&nbsp;&nbsp;&nbsp;&nbsp;🚆10-11"
            elif gate[0] == "Z":
                suffix = "&nbsp;&nbsp;&nbsp;&nbsp;🚶8"
            elif gate[0] == "D":
                suffix = "&nbsp;&nbsp;&nbsp;&nbsp;🚌 8"
            else:
                suffix = ''
        else:
            suffix = ''
            rgate = ''
    return '%s %s' % (rgate, suffix)


while retryCount < 5 and response_code != 200:
    headers = dict()
    headers[
        "Cookie"] = "gdprText=1; ct_check_js=1c40e376161c5de64b00f3eb4ca54aed; ct_ps_timestamp=1708001301; ct_fkp_timestamp=0; ct_pointer_data=0; ct_timezone=-5; apbct_antibot=e057b330c453aaf1b084653edef1acc2866210a559d6700bc40c126dd2634986; ct_has_scrolled=false; alertsText=Yes; flight-info=1"

    response = requests.get(url, headers=headers)
    response_code = response.status_code
    print('Retry count: %s response_code: %s' % (retryCount, response_code))
    if response.status_code == 200:
        json_data = json.loads(response.text)
        success = True
    else:
        retryCount += 1
        print('%s. Sleeping for 15 seconds' % retryCount)
        time.sleep(15)

if not success:
    print('Could not get the response after 5 tries, hence exiting')
    exit(3)

readAirlineCodesCsv()
readAirportCodesCsv()

if os.getenv("GITHUB_ACTIONS") == "true":
    arrivalsFileHandle = open('arrivals.html', "w")
    fisFileHandle = open('fis.html', "w")
    iabFileHandle = open('iab.html', "w")
    depFileHandle = open('departures.html', "w")
elif (os.path.exists(wwwPath)):
    arrivalsFileHandle = open(wwwPath + '/index.html', "w")
    fisFileHandle = open(wwwPath + '/fis.html', "w")
    iabFileHandle = open(wwwPath + '/iab.html', "w")
    depFileHandle = open(wwwPath + '/departures.html', "w")
else:
    arrivalsFileHandle = open('arrivals_mac.html', "w")
    fisFileHandle = open('fis_mac.html', "w")
    iabFileHandle = open('iab_mac.html', "w")
    depFileHandle = open('departures_mac.html', "w")

departuressHeadFileHandle = open('departures.head.html', "r")
depFileHandle.write(departuressHeadFileHandle.read())

arrivalsHeadFileHandle = open("arrivals.head.html", "r")
arrivalsFileHandle.write(arrivalsHeadFileHandle.read())
t = 1

for i in json_data['arrivals']:
    status = i['status']
    t = t + 1
    if status != 'Scheduled_':
        # actualtime = i['actualtime']
        actualtime = formatTime(i['actualtime'])
        customsAt = formatTime(i['customsAt'])
        print(isTimeBetween2and6(i['actualtime']))
        flight = '<a href="https://www.flightaware.com/live/flight/%s%s" target="_blank" rel="noopener noreferrer">%s %s</a>' % (airlinedict[i['IATA']], i['flightnumber'], i['IATA'], i['flightnumber'])
        mod_status = i['mod_status'] if i['mod_status'] is not None else ''
        gate = formatGate(i['gate'], airportdict[i['dep_airport_code']][0])

        baggage = i['baggage'] if i['baggage'] is not None else ''
        claim = i['claim'] if i['claim'] is not None else ''
        claim1 = i['claim1'] if i['claim1'] is not None else ''
        claim2 = i['claim2'] if i['claim2'] is not None else ''
        claim3 = i['claim3'] if i['claim3'] is not None else ''
        arrivalsFileHandle.write(
            '<tr>\n\t<td style="width: 5%%">%s</td>\n<td class="%s">%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n' % (
                flight, i['status'],
                airportdict[i['dep_airport_code']][1],
                i['dep_airport_code'],
                airportdict[i['dep_airport_code']][0], gate, status,
                actualtime, getCustomsString(mod_status, customsAt),
                # baggage, claim, claim1, claim2
                getCarousel(baggage, claim, claim1, claim2)))
        arrivalsFileHandle.write('</tr>\n')

        if airportdict[i['dep_airport_code']][0] == 'International' and isTimeBetween2and6(i['actualtime'] and status != 'Scheduled_'):
            s = ('https://www.flightaware.com/live/flight/%s%s' % (airlinedict[i['IATA']], i['flightnumber']))
            iabArray.append(
                [s, formatTimeFor2To6(i['actualtime']), '%s %s' % (i['IATA'], i['flightnumber']), i['city'], status])
            if (airlinedict[i['IATA']] == 'UAL' or airlinedict[i['IATA']] == 'DLH' or airlinedict[i['IATA']] == 'AUA' or
                    airlinedict[i['IATA']] == 'SAB' or airlinedict[i['IATA']] == 'CCA' or airlinedict[i['IATA']] == 'ANA' or airlinedict[i['IATA']] == 'SAS'):
                fisArray.append(
                    [s, formatTimeFor2To6(i['actualtime']), '%s %s' % (i['IATA'], i['flightnumber']), i['city'],
                     status])
# arrivalsFileHandle.close()

fisArray.sort(key=lambda x: x[1])
for fis in fisArray:
    if fis[4] == 'InAir':
        color = 'style="background-color:#ADDFFF"'
    elif fis[4] == 'Landed':
        color = 'style="background-color:#AF9B60"'
    elif fis[4] == 'InGate':
        color = 'style="background-color:#22CE83"'
    else:
        color = ''
    fisTableHTML += '<tr %s>\n\t\t<td>%s</td><td>%s</td>  <td><a href="%s" target="_blank" rel="noopener noreferrer">%s</a></td>\n\t\t<td>%s</td>\n\t</tr>\n' % (
        color, fis[1], fis[3], fis[0], fis[2], fis[4])

fisFileHandle.write("""<!DOCTYPE html>
<head>
<style>
table, th, td {
  border: 1px solid black;
  border-collapse: collapse;
}
</style>
    <title>FIS 2-6 Arrivals</title>
    <meta http-equiv="refresh" content="120">
</head>
<body>
  <table>%s</table>\n</body>\n</html>""" % fisTableHTML)
fisFileHandle.close()

# #################
iabArray.sort(key=lambda x: x[1])
for iab in iabArray:
    if iab[4] == 'InAir':
        color = 'style="background-color:#ADDFFF"'
    elif iab[4] == 'Landed':
        color = 'style="background-color:#AF9B60"'
    elif iab[4] == 'InGate':
        color = 'style="background-color:#22CE83"'
    else:
        color = ''
    iabTableHTML += '<tr %s>\n\t\t<td>%s</td><td>%s</td>  <td><a href="%s" target="_blank" rel="noopener noreferrer">%s</a></td>\n\t\t<td>%s</td>\n\t</tr>\n' % (
        color, iab[1], iab[3], iab[0], iab[2], iab[4])

iabFileHandle.write("""<!DOCTYPE html>
<head>
<style>
table, th, td {
  border: 1px solid black;
  border-collapse: collapse;
}
</style>
    <title>IAB 2-6 Arrivals</title>
    <meta http-equiv="refresh" content="120">
</head>
<body>
  <table>%s</table>\n</body>\n</html>""" % iabTableHTML)
iabFileHandle.close()
# #################


arrivalsFileHandle.write("""
    </tbody>
    </table>
    <script>
        const rows = document.querySelectorAll('td');
        rows.forEach((row) => {
          if (row.innerHTML === 'InAir') {
            const parent = row.parentNode;
            parent.style.backgroundColor = 'Cornsilk';
          }
          else if (row.innerHTML === 'InGate') {
            const parent = row.parentNode;
            parent.style.backgroundColor = 'HoneyDew';
          }
          else if (row.innerHTML === 'Delayed') {
            const parent = row.parentNode;
            parent.style.backgroundColor = 'SeaShell';
          }
        });
    </script>
    <p id=\"update\" onclick=\"myFunction()\">Information current as of %s</p>
    <p id=\"info\" onclick=\"myFunction()\">Click here to refresh this page</p>
    <script>
        function myFunction() {
          document.getElementById("info").innerHTML = "Page refreshed at ";
          location.reload()
        }
    </script>
""" % getCurrentTime())
arrivalsFileHandle.close()

# https://htmlcolorcodes.com/color-names/
# https://www.bansard.com/sites/default/files/download_documents/Bansard-airlines-codes-IATA-ICAO.xlsx


# #########################
# fhd = open('dep.json', 'w')
# fhd.write(json.dumps(json_data['departures'], indent=2))
# fhd.close()
depArray = []
for i in json_data['departures']:
    date_format = '%Y-%m-%d %H:%M:%S'
    if i['actualtime'] is not None:
        # use this for time computation
        passedDate = datetime.strptime(i['actualtime'], date_format)
        printableDate = i['actualtime']
    else:
        # use i['publishedTime'] for time computation
        passedDate = datetime.strptime(i['publishedTime'], date_format)
        printableDate = i['publishedTime']

    if i['mod_gate'] is None:
        printableGate = i['gate']
    else:
        printableGate = i['mod_gate']

    currentTime = datetime.now()
    currentTimeMinusTwo = currentTime - timedelta(days=0, hours=2)
    currentTimePlusTen = currentTime + timedelta(days=0, hours=10)
    if (currentTimeMinusTwo < passedDate) and (currentTimePlusTen > passedDate) and (printableGate != None):
        depArray.append([i['IATA'], i['flightnumber'], i['airline'], i['city'], i['airportcode'],
                         printableDate, printableGate, i['status']])
depArray.sort(key=lambda x: x[5])
depTableHTML: str = ''
for dep in depArray:
    if dep[7] == 'InAir':
        color = 'style="background-color:#ADDFFF"'
    elif dep[7] == 'Delayed':
        color = 'style="background-color:#FFEBB0"'
    elif dep[7] == 'Scheduled':
        color = 'style="background-color:#72FFD3"'
    else:
        color = ''
    url = 'https://www.flightaware.com/live/flight/%s%s' % (airlinedict[dep[0]], dep[1])
    depTableHTML += ("""
        <tr %s>
            <td><a href=\"%s\" target=\"_blank\" rel=\"noopener noreferrer\">%s %s</a></td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
            <td>%s</td>
        </tr>\n""" % (color, url, dep[0], dep[1], dep[2], dep[3], dep[4], dep[5], dep[6], dep[7]))

depFileHandle.write(depTableHTML)
depFileHandle.write("</table>\n</body>")
depFileHandle.close()

# depFileHandle.write("""<!DOCTYPE html>
# <head>
#     <style>
#         table, th, td {
#             border: 1px solid black;
#             border-collapse: collapse;
#         }
#     </style>
#     <title>IAB 2-6 Arrivals</title>
#     <meta http-equiv="refresh" content="120">
# </head>
# <body>
#     <table>
#         %s
#     </table>
# </body>
# """ % depTableHTML)
# depFileHandle.close()
