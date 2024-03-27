import time
from datetime import datetime, timedelta
from pytz import timezone
import os
import requests, json
from createAirportCode import readAirportCodesCsv, readAirlineCodesCsv

url = "https://www.flydulles.com/arrivals-and-departures/json"
wwwPath = '/var/www/html'
fisTableHTML: str = ''
iabTableHTML: str = ''
fisArray = []
iabArray = []
response_code = 401
retryCount = 0
success = False
airportdict: dict = readAirportCodesCsv()
airlinedict: dict = readAirlineCodesCsv()

def isArrivingToday(publishedTime: str) -> bool:
    if (publishedTime.split(" ")[0] <= datetime.today().date().strftime('%Y-%m-%d')):
        print('%s %s' % (publishedTime.split(" ")[0], datetime.today().date().strftime('%Y-%m-%d')))
        return True
    else:
        return False



def getCustomsString(mod_status, customsAt) -> str:
    if mod_status != '':
        # return (mod_status + ' since ' + customsAt)
        return (customsAt)
    else:
        return ''

def getFisTimeString(status, actualtime, mod_status, customsAt) -> str:
    if mod_status != '' and customsAt != '':
        s1 = customsAt.split(" ")[1]
        s2 = s1.split(":")[0] + ":" + s1.split(":")[1]
        # print('\n\n\tCustoms at %s\n\n\n\t' % customsAt)
        print('C%s' % s2)
        # return (mod_status + ' since ' + customsAt)
        return ('C%s' % s2)
    else:
        s1 = actualtime.split(" ")[1]
        s2 = s1.split(":")[0] + ":" + s1.split(":")[1]
        if status == 'InGate':
            return ('G%s' % (s2))
        if status == 'Landed':
            return ('L%s' % (s2))
        if status == 'Delayed':
            return status
            # return ('Dela: %s' % (actualtime.split(" ")[1]))
        if status == 'InAir':
            return status
        if status == 'OutGate':
            return status
            # return ('InAir: %s' % (actualtime.split(" ")[1]))


def isStarAllianceAtFIS(airline) -> bool:
    starAllianceMembersArray = ['AUA', 'DLH', 'UAL', 'SAB', 'CCA', 'ANA', 'SAS']
    if airline in starAllianceMembersArray:
        return True
    else:
        return False


def getCarousel(c, c1, c2, c3):
    if c == '' and c1 == '':
        return (c2 + ',' + c3).rstrip(',')
    else:
        return c


def getCurrentTime() -> str:
    now = datetime.now(tz=timezone('America/New_York'))
    return now.strftime("%b %d, %Y %I:%M %p")


def isTimeBetween1and7(timeString) -> bool:
    if timeString is not None:

        # print(timeString)
        time_split = timeString.split(" ")
        # print(time_split[1])
        hrs = time_split[1].replace(':', '')
        # print(hrs)
        if (int(hrs) > 130000 and int(hrs) < 190000):
            return True
    else:
        return False


def formatTimeFor2To6(timeString) -> str:
    if timeString is not None:
        datetime_object = datetime.strptime(timeString, '%Y-%m-%d %H:%M:%S')
        str_date = datetime_object.strftime("%I:%M %p")
        # print(str_date)
        return str_date


def formatTime(timeString) -> str:
    if timeString is not None:

        element = datetime.strptime(timeString, "%Y-%m-%d %H:%M:%S")

        tuple = element.timetuple()
        passedTimestamp = time.mktime(tuple)

        dtpassed = datetime.fromtimestamp(passedTimestamp)
        # print('Datetime Passed: %s' % (dtpassed))

        now = time.time()
        dtnow = datetime.fromtimestamp(now)
        # print('Datetime Now: %s' % (dtnow))

        deltaTimeStamp = passedTimestamp - now
        delta = dtpassed - dtnow
        if deltaTimeStamp >= 0:
            minutes, seconds = divmod(delta.seconds, 60)
            hours, minutes = divmod(minutes, 60)
            addendum = "<span style=\"background-color: #99ffbb\">In %d:%02d</span>" % (hours, minutes)
        else:
            delta = dtnow - dtpassed
            minutes, seconds = divmod(delta.seconds, 60)
            hours, minutes = divmod(minutes, 60)
            addendum = "<span style=\"background-color: #ffd699\">%d:%02d ago</span>" % (hours, minutes)
        # print(addendum)
        # print('----\n')

        datetime_obj = datetime.strptime(timeString, "%Y-%m-%d %H:%M:%S")
        # print(datetime_obj.strftime("%m/%d %H:%M"))
        return "%s %s" % (datetime_obj.strftime("%m/%d %H:%M"), addendum)
    else:
        return ''


def formatGate(gate, domesticOrInternational):
    rgate = ''
    if domesticOrInternational == "Int":
        if gate != None:
            suffix = "%s - Cafè Americana" % gate
        else:
            suffix = "Cafè Americana"
    else:
        if gate is not None:
            rgate = gate
            if gate[0] == "A":
                suffix = "🚆6-7 &nbsp;&nbsp"
            elif gate[0] == "C":
                suffix = "🚆6-7 &nbsp;&nbsp"
            elif gate[0] == "B":
                suffix = "🚆10-11 &nbsp;&nbsp"
            elif gate[0] == "Z":
                suffix = "🚶8 &nbsp;&nbsp"
            elif gate[0] == "D":
                suffix = "🚌 8 &nbsp;&nbsp"
            else:
                suffix = ''
        else:
            suffix = ''
            rgate = ''
    return '%s %s' % (suffix, rgate)


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

# readAirlineCodesCsv()
# readAirportCodesCsv()


if os.getenv("GITHUB_ACTIONS") == "true":
    arrivalsFileHandle = open('arrivals.html', "w")
    fisFileHandle = open('fis.html', "w")
    iabFileHandle = open('iab.html', "w")
    depFileHandle = open('departures.html', "w")
    starAllianceDepHandle = open('starAllianceDepartures.html', "w")
    arrJsonHandle = open('arr.json', "w")
elif (os.path.exists(wwwPath)):
    arrivalsFileHandle = open(wwwPath + '/index.html', "w")
    fisFileHandle = open(wwwPath + '/fis.html', "w")
    iabFileHandle = open(wwwPath + '/iab.html', "w")
    depFileHandle = open(wwwPath + '/departures.html', "w")
    starAllianceDepHandle = open(wwwPath + '/starAllianceDepartures.html', "w")
    arrJsonHandle = open(wwwPath + '/arr.json', "w")
else:
    arrivalsFileHandle = open('arrivals_mac.html', "w")
    fisFileHandle = open('fis_mac.html', "w")
    iabFileHandle = open('iab_mac.html', "w")
    depFileHandle = open('departures_mac.html', "w")
    starAllianceDepHandle = open('starAllianceDepartures_mac.html', "w")
    arrJsonHandle = open('arr_mac.json', "w")

departuressHeadFileHandle = open('departures.head.html', "r")
depFileHandle.write(departuressHeadFileHandle.read())

arrivalsHeadFileHandle = open("arrivals.head.html", "r")
arrivalsFileHandle.write(arrivalsHeadFileHandle.read())
t = 1

# #########################
arrJsonHandle.write(json.dumps(json_data['arrivals'], indent=2))
arrJsonHandle.close()

for arrivalRecord in json_data['arrivals']:
    status = arrivalRecord['status']
    t = t + 1
    if status != 'Scheduled' and isArrivingToday(arrivalRecord['publishedTime']):
        # actualtime = i['actualtime']
        actualtime = formatTime(arrivalRecord['actualtime'])
        customsAt = formatTime(arrivalRecord['customsAt'])
        # print(isTimeBetween2and6(i['actualtime']))
        try:
            flight = '<a href="https://www.flightaware.com/live/flight/%s%s" target="_blank" rel="noopener noreferrer">%s %s</a>' % (airlinedict[arrivalRecord['IATA']][0], arrivalRecord['flightnumber'], arrivalRecord['IATA'], arrivalRecord['flightnumber'])
        except:
            print(arrivalRecord)
        mod_status = arrivalRecord['mod_status'] if arrivalRecord['mod_status'] is not None else ''
        try:
            gate = formatGate(arrivalRecord['gate'], airportdict[arrivalRecord['dep_airport_code']][0])
        except Exception as err:
            print("Error")


        baggage = arrivalRecord['baggage'] if arrivalRecord['baggage'] is not None else ''
        claim = arrivalRecord['claim'] if arrivalRecord['claim'] is not None else ''
        claim1 = arrivalRecord['claim1'] if arrivalRecord['claim1'] is not None else ''
        claim2 = arrivalRecord['claim2'] if arrivalRecord['claim2'] is not None else ''
        claim3 = arrivalRecord['claim3'] if arrivalRecord['claim3'] is not None else ''
        arrivalsFileHandle.write(
            '<tr>\n\t'
            '<td>%s</td>\n' #Flight
            '<td class="%s">%s %s</td>\n' # Origin
            '<td>%s</td>\n'
            '<td>%s</td>\n'
            '<td>%s</td>\n'
            '<td>%s</td>\n'
            '<td>%s</td>\n'
            '<td>%s</td>\n' % (
                flight,
                arrivalRecord['status'],  arrivalRecord['dep_airport_code'], airportdict[arrivalRecord['dep_airport_code']][3],
                getCarousel(baggage, claim, claim1, claim2),
                airportdict[arrivalRecord['dep_airport_code']][0], gate, status,
                actualtime,
                getCustomsString(mod_status, customsAt),
                # getFisTimeString(status, actualtime, mod_status, customsAt),
                # baggage, claim, claim1, claim2
                ))
        arrivalsFileHandle.write('</tr>\n')

        if airportdict[arrivalRecord['dep_airport_code']][0] == 'Int' and isTimeBetween1and7(arrivalRecord['actualtime']):
            s = ('https://www.flightaware.com/live/flight/%s%s' % (airlinedict[arrivalRecord['IATA']][0], arrivalRecord['flightnumber']))

            iabArray.append([s, formatTimeFor2To6(arrivalRecord['actualtime']), '%s %s' % (arrivalRecord['IATA'], arrivalRecord['flightnumber']), arrivalRecord['city'], getFisTimeString(status, actualtime, mod_status, arrivalRecord['customsAt'])])

            if isStarAllianceAtFIS(airlinedict[arrivalRecord['IATA']][0]):
                fisArray.append([s, formatTimeFor2To6(arrivalRecord['actualtime']), '%s %s' % (arrivalRecord['IATA'], arrivalRecord['flightnumber']), arrivalRecord['city'], getFisTimeString(status, actualtime, mod_status, arrivalRecord['customsAt'])])

# arrivalsFileHandle.close()

fisTableHTML += "<th style=\"background-color:#a3c2c2\" colspan=4>FIS Arrivals from 1-7pm</th>"
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
    fisTableHTML += '<tr %s>\n\t\t<td style="min-width: 100px">%s</td><td style="min-width: 100px">%s</td><td style="min-width: 100px"><a href="%s" target="_blank" rel="noopener noreferrer">%s</a></td>\n\t\t<td>%s</td>\n\t</tr>\n' % (
        color, fis[1], fis[3], fis[0], fis[2], fis[4])
fisTableHTML += '<tr>\n\t\t<td style="background-color:#DFF429" colspan=4>Updated %s</td>\n\t</tr>' % getCurrentTime()

fisFileHandle.write("""<!DOCTYPE html>
<head>
<style>
    table, th, td {
      border: 1px solid black;
      border-collapse: collapse;
      font-family: Consolas, monaco, monospace;
      font-size: 44px;
      font-style: normal;
      font-variant: normal; 
      font-weight: 700;
      padding: 10px;
    }
</style>
    <title>FIS 1-7 Arrivals</title>
    <meta http-equiv="refresh" content="120">
    <meta http-equiv="Cache-control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="expires" content="0">
</head>
<body>
  <table>%s</table>\n</body>\n</html>""" % (fisTableHTML))
fisFileHandle.close()

# #################
iabTableHTML += "<th style=\"background-color:#c2c2a3\" colspan=4>IAB Arrivals from 1-7pm</th>"
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
iabTableHTML += '<tr>\n\t\t<td style="background-color:#DFF429" colspan=4>Updated %s</td>\n\t</tr>' % getCurrentTime()

iabFileHandle.write("""<!DOCTYPE html>
<head>
<style>
    table, th, td {
      border: 1px solid black;
      border-collapse: collapse;
      font-family: Consolas, monaco, monospace;
      font-size: 44px;
      font-style: normal;
      font-variant: normal; 
      font-weight: 700;
      padding: 10px;
    }
</style>
    <title>IAB 1-7 Arrivals</title>
        <meta http-equiv="refresh" content="120">
        <meta http-equiv="Cache-control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="expires" content="0">
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
starAllianceDepArray = []
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
        color = 'style="background-color:#E6FFC8"'
    else:
        color = ''
    try:
        url = 'https://www.flightaware.com/live/flight/%s%s' % (airlinedict[dep[0]][0], dep[1])
    except:
        url = 'https://www.flightaware.com/live'
    depTableHTML += ("""
        <tr %s>
            <td style="max-width: 10px"><a href=\"%s\" target=\"_blank\" rel=\"noopener noreferrer\">%s %s</a></td>
            <td style="max-width: 20px">%s</td>
            <td style="max-width: 20px">%s - %s</td>
            <td style="max-width: 10px" class=\"iatafont\">%s</td>
            <td style="max-width: 15px">%s</td>
            <td style="max-width: 15px">%s</td>
        </tr>\n""" % (color, url, dep[0], dep[1], dep[2], dep[4], dep[3], dep[6], formatTime(dep[5]), dep[7]))

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

# https://github.com/davidmegginson/ourairports-data/blob/main/airports.csv
# https://github.com/davidmegginson/ourairports-data
# https://raw.githubusercontent.com/elmoallistair/datasets/main/airlines.csv
# https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat
# https://raw.githubusercontent.com/jpatokal/openflights/master/data/airlines.dat
