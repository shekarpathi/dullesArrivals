import requests, json

url = "https://www.flydulles.com/arrivals-and-departures/json"

response = requests.request(
    "GET",
    url
)
print(response.status_code)

if response.status_code != 200:
    exit(0)
json_data = json.loads(response.text)

arrivalsFile = open("arrivals.html", "w")
arrivalsFile.write("""<!DOCTYPE html>
<html>
<head>
\t<meta http-equiv="Content-type" content="text/html; charset=utf-8">
\t<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">\n""")
arrivalsFile.write("""<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.11.3/css/jquery.dataTables.min.css">

<script type="text/javascript" src="https://code.jquery.com/jquery-3.5.1.js"></script>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-EVSTQN3/azprG1Anm3QDgpJLIm9Nao0Yz1ztcQTwFspd3yD65VohhpuuCOmLASjC" crossorigin="anonymous">
<script type="text/javascript" src="https://cdn.datatables.net/1.11.3/js/jquery.dataTables.min.js"></script>
<script type="text/javascript">
    $(document).ready(function() {
        $('#example').DataTable();
    });
</script>
</head>\n""")

arrivalsFile.write('<table data-order=\'[[ 5, "asc" ]]\' data-page-length=\'25\' id="example" class="display" style="width:100%">\n')
arrivalsFile.write("""<thead>
            <tr>
                <th>Airline</th>
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
                <th>Carousel3</th>
            </tr>
        </thead>
        <tbody>\n""")


# print(json.dumps(json_data, sort_keys=True, indent=4, separators=(",", ": ")))
# print(json_data['_links']['next'])
t = 1
for i in json_data['arrivals']:
    status = i['status']
    # actualtime = i['actualtime']
    actualtime = i['actualtime'] if i['actualtime'] is not None else ''
    customsAt = i['customsAt'] if i['customsAt'] is not None else    ''
    gate = i['gate'] if i['gate'] is not None else    ''
    mod_status = i['mod_status'] if i['mod_status'] is not None else    ''

    baggage = i['baggage'] if i['baggage'] is not None else    ''
    claim = i['claim'] if i['claim'] is not None else    ''
    claim1 = i['claim1'] if i['claim1'] is not None else ''
    claim2 = i['claim2'] if i['claim2'] is not None else    ''
    claim3 = i['claim3'] if i['claim3'] is not None else    ''

    print(i['IATA'] + " | " + i['flightnumber'] + " | " + i['dep_airport_code'] + " | " + gate + " | " + status + " | " + mod_status + " | " + actualtime + " | " + customsAt + " | " + baggage + " | " + claim + " | " + claim1 + " | " + claim2 + " | " + claim3)
    t = t + 1
    arrivalsFile.write('<tr>\n')
    arrivalsFile.write('    <td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n' % (i['IATA'], i['flightnumber'], i['dep_airport_code'], gate, status, actualtime, mod_status, customsAt, baggage, claim, claim1, claim2, claim3))
    arrivalsFile.write('</tr>\n')
arrivalsFile.write('</tbody>\n')
arrivalsFile.write('</table>\n')
