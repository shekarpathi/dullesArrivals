import time
from datetime import datetime
from pytz import timezone
import os
import requests, json
import csv

url = "https://www.flydulles.com/arrivals-and-departures/json"
arrivalsFileName = "arrivals.html"
# wwwPath = '/usr/share/httpd/noindex'
wwwPath = '/var/www/html'
fisTableHTML: str = ''
iabTableHTML: str = ''
fisArray = []
iabArray = []
response_code = 401
retryCount = 0
success = False
airportdict = {}
airlinedict = {}


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
        return (mod_status + ' since ' + customsAt)
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
    arrivalsFileHandle = open(arrivalsFileName, "w")
    fisFileHandle = open('fis.html', "w")
    iabFileHandle = open('iab.html', "w")
elif (os.path.exists(wwwPath)):
    arrivalsFileHandle = open(wwwPath + '/index.html', "w")
    fisFileHandle = open(wwwPath + '/fis.html', "w")
    iabFileHandle = open(wwwPath + '/iab.html', "w")
else:
    arrivalsFileHandle = open('arrivals.html', "w")
    fisFileHandle = open('fis.html', "w")
    iabFileHandle = open('iab.html', "w")

arrivalsFileHandle.write("""
<!DOCTYPE html>
<html>
<head title=Dulles Arrivals>
<meta http-equiv="refresh" content="600">
<meta http-equiv="Content-type" content="text/html; charset=utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.11.3/css/jquery.dataTables.min.css">

<script type="text/javascript" src="https://code.jquery.com/jquery-3.5.1.js"></script>
<script type="text/javascript" src="https://cdn.datatables.net/1.12.1/js/jquery.dataTables.min.js"></script>
<script type="text/javascript" src="https://cdn.datatables.net/fixedheader/3.2.3/js/dataTables.fixedHeader.min.js"></script>
<script type="text/javascript">


$(document).ready(function () {
    // Setup - add a text input to each footer cell
    $('#example thead tr')
        .clone(true)
        .addClass('filters')
        .appendTo('#example thead');

    var table = $('#example').DataTable({
    "autoWidth": false,
        "columnDefs": [
        {"className": "dt-left", "targets": "_all", "width": "5%"},
      {
        targets: 1,
         width: 1
      }
      ],

        orderCellsTop: true,
        fixedHeader: true,
        initComplete: function () {
            var api = this.api();

            // For each column
            api
                .columns()
                .eq(0)
                .each(function (colIdx) {
                    // Set the header cell to contain the input element
                    var cell = $('.filters th').eq(
                        $(api.column(colIdx).header()).index()
                    );
                    var title = $(cell).text();
                    $(cell).html('<input type="text" placeholder="' + title + '" />');

                    // On every keypress in this input
                    $(
                        'input',
                        $('.filters th').eq($(api.column(colIdx).header()).index())
                    )
                        .off('keyup change')
                        .on('change', function (e) {
                            // Get the search value
                            $(this).attr('title', $(this).val());
                            var regexr = '({search})'; //$(this).parents('th').find('select').val();

                            var cursorPosition = this.selectionStart;
                            // Search the column for that value
                            api
                                .column(colIdx)
                                .search(
                                    this.value != ''
                                        ? regexr.replace('{search}', '(((' + this.value + ')))')
                                        : '',
                                    this.value != '',
                                    this.value == ''
                                )
                                .draw();
                        })
                        .on('keyup', function (e) {
                            e.stopPropagation();

                            $(this).trigger('change');
                            $(this)
                                .focus()[0]
                                .setSelectionRange(cursorPosition, cursorPosition);
                        });
                });
        },
    });
});

</script>

<style type="text/css" class="init">
thead input {
        width: 100%;
    }
    .selected{
  background-color:green;
}
.bad{
  background-color:red;
}
</style>
</head>\n
""")

arrivalsFileHandle.write("""
    <table data-order=\'[[ 5, "asc" ]]\' data-page-length=\'300\' id="example" class="cell-border" style="width:100%">
    <thead>
            <tr>
                <th>Number</th>
                <th>Origin</th>
                <th>Dom/Int</th>
                <th>Gate</th>
                <th>Status</th>
                <th>Gate Time</th>
                <th>Customs</th>
                <th>Baggage Carousel</th>
            </tr>
        </thead>
        <tbody>\n
    """)

# print(json.dumps(json_data, sort_keys=True, indent=4, separators=(",", ": ")))
# print(json_data['_links']['next'])
t = 1
for i in json_data['arrivals']:
    status = i['status']
    t = t + 1
    if status != 'Scheduled':
        # actualtime = i['actualtime']
        actualtime = formatTime(i['actualtime'])
        customsAt = formatTime(i['customsAt'])
        print(isTimeBetween2and6(i['actualtime']))

        mod_status = i['mod_status'] if i['mod_status'] is not None else ''
        gate = formatGate(i['gate'], airportdict[i['dep_airport_code']][0])

        baggage = i['baggage'] if i['baggage'] is not None else ''
        claim = i['claim'] if i['claim'] is not None else ''
        claim1 = i['claim1'] if i['claim1'] is not None else ''
        claim2 = i['claim2'] if i['claim2'] is not None else ''
        claim3 = i['claim3'] if i['claim3'] is not None else ''
        arrivalsFileHandle.write(
            '<tr>\n    <td><a href="https://www.flightaware.com/live/flight/%s%s" target="_blank" rel="noopener noreferrer">%s %s</a></td>\n<td>%s&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n' % (
                airlinedict[i['IATA']], i['flightnumber'], i['IATA'], i['flightnumber'], i['dep_airport_code'],
                airportdict[i['dep_airport_code']][1],
                airportdict[i['dep_airport_code']][0], gate, status,
                actualtime, getCustomsString(mod_status, customsAt),
                # baggage, claim, claim1, claim2
                getCarousel(baggage, claim, claim1, claim2)))
        arrivalsFileHandle.write('</tr>\n')

        if airportdict[i['dep_airport_code']][0] == 'International' and isTimeBetween2and6(i['actualtime']):
            s = ('https://www.flightaware.com/live/flight/%s%s' % (airlinedict[i['IATA']], i['flightnumber']))
            iabArray.append([s, formatTimeFor2To6(i['actualtime']), '%s %s' % (i['IATA'], i['flightnumber']), i['city'], status])
            if (airlinedict[i['IATA']] == 'UAL' or airlinedict[i['IATA']] == 'DLH' or airlinedict[i['IATA']] == 'AUA' or airlinedict[i['IATA']] == 'AVA' or airlinedict[i['IATA']] == 'CCA'):
                fisArray.append([s, formatTimeFor2To6(i['actualtime']), '%s %s' % (i['IATA'], i['flightnumber']), i['city'], status])

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
    fisTableHTML += '<tr %s>\n\t\t<td>%s</td><td>%s</td>  <td><a href="%s" target="_blank" rel="noopener noreferrer">%s</a></td>\n\t\t<td>%s</td>\n\t</tr>\n' % (color,fis[1], fis[3], fis[0], fis[2], fis[4])

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
    iabTableHTML += '<tr %s>\n\t\t<td>%s</td><td>%s</td>  <td><a href="%s" target="_blank" rel="noopener noreferrer">%s</a></td>\n\t\t<td>%s</td>\n\t</tr>\n' % (color,iab[1], iab[3], iab[0], iab[2], iab[4])

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
</html>
""" % getCurrentTime())
arrivalsFileHandle.close()

# https://htmlcolorcodes.com/color-names/
# https://www.bansard.com/sites/default/files/download_documents/Bansard-airlines-codes-IATA-ICAO.xlsx
