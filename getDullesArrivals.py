import time
from datetime import datetime
from pytz import timezone

import requests, json

url = "https://www.flydulles.com/arrivals-and-departures/json"

response_code = 401
retryCount = 0
success = False


def getCurrentTime():
    now = datetime.now(tz=EST5EDT())
    return now.strftime("%b %d, %Y %I:%M %p")


def formatTime(ss):
    if ss is not None:
        datetime_obj = datetime.strptime(ss, "%Y-%m-%d %H:%M:%S")
        # print(datetime_obj.strftime("%m/%d %H:%M"))
        return datetime_obj.strftime("%m/%d %H:%M")
    else:
        return ''


def formatGate(gate, customs):
    rgate = ''
    if customs == "In Customs":
        suffix = " Cafe Americana"
    else:
        if gate is not None:
            rgate = gate
            if gate[0] == "A":
                suffix = " | 🚆6╩7"
            elif gate[0] == "C":
                suffix = " | 🚆6╩7"
            elif gate[0] == "B":
                suffix = " | 🚆10╩11"
            elif gate[0] == "Z":
                suffix = " | 🚶╚8"
            elif gate[0] == "D":
                suffix = " | 🚌 ╔8"
            else:
                suffix = ''
        else:
            suffix = ''
            rgate = ''
    return '%s %s' % (rgate, suffix)


while retryCount < 5 and response_code != 200:
    response = requests.get(url)
    response_code = response.status_code
    print('Retry count: %s response_code: %s' % (retryCount, response_code))
    if response.status_code == 200:
        json_data = json.loads(response.text)
        success = True
    else:
        retryCount += 1
        print('Sleeping for %s seconds' % (retryCount * 10))
        time.sleep(retryCount * 10)

if not success:
    print('Could not get the response after 5 tries, hence exiting')
    exit(3)

arrivalsFile = open("arrivals.html", "w")
arrivalsFile.write("""<!DOCTYPE html>
<html>
<head>
\t<meta http-equiv="refresh" content="600">
\t<meta http-equiv="Content-type" content="text/html; charset=utf-8">
\t<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">\n""")
arrivalsFile.write("""<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.11.3/css/jquery.dataTables.min.css">

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

</head>\n""")

arrivalsFile.write(
    '<table data-order=\'[[ 5, "asc" ]]\' data-page-length=\'15\' id="example" class="cell-border" style="width:100%">\n')
arrivalsFile.write("""<thead>
            <tr>
                <th>Number</th>
                <th>Origin</th>
                <th>Gate</th>
                <th>Status</th>
                <th>Gate Time</th>
                <th>Customs</th>
                <th>In Customs since</th>
                <th>Baggage Carousel</th>
                <th>Carousel</th>
                <th>Carousel1</th>
                <th>Carousel2</th>
            </tr>
        </thead>
        <tbody>\n""")

# print(json.dumps(json_data, sort_keys=True, indent=4, separators=(",", ": ")))
# print(json_data['_links']['next'])
t = 1

for i in json_data['arrivals']:
    status = i['status']
    # actualtime = i['actualtime']
    actualtime = formatTime(i['actualtime'])
    # actualtime = i['actualtime'] if i['actualtime'] is not None else ''
    customsAt = formatTime(i['customsAt'])
    # customsAt = i['customsAt'] if i['customsAt'] is not None else ''

    mod_status = i['mod_status'] if i['mod_status'] is not None else ''
    gate = formatGate(i['gate'], i['mod_status'])

    baggage = i['baggage'] if i['baggage'] is not None else ''
    claim = i['claim'] if i['claim'] is not None else ''
    claim1 = i['claim1'] if i['claim1'] is not None else ''
    claim2 = i['claim2'] if i['claim2'] is not None else ''
    claim3 = i['claim3'] if i['claim3'] is not None else ''

    # print(i['IATA'] + " | " + i['flightnumber'] + " | " + i[
    #     'dep_airport_code'] + " | " + gate + " | " + status + " | " + mod_status + " | " + actualtime + " | " + customsAt + " | " + baggage + " | " + claim + " | " + claim1 + " | " + claim2 + " | " + claim3)
    t = t + 1
    if status != 'Scheduled':
        arrivalsFile.write('<tr>\n')
        arrivalsFile.write(
            '    <td><a href="https://www.flightstats.com/v2/flight-tracker/%s/%s" target="_blank" rel="noopener noreferrer">%s %s</a></td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n' % (
                i['IATA'], i['flightnumber'], i['IATA'], i['flightnumber'], i['dep_airport_code'], gate, status,
                actualtime, mod_status, customsAt,
                baggage, claim, claim1, claim2))
        arrivalsFile.write('</tr>\n')
arrivalsFile.write('</tbody>\n')
arrivalsFile.write('</table>\n')
arrivalsFile.write("""
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
""")
arrivalsFile.write("Information updated at " + getCurrentTime())
arrivalsFile.write('</html>\n')

# https://htmlcolorcodes.com/color-names/
