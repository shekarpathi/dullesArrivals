SELECT ARRIVALS.actualtime, ARRIVALS.publishedtime,
    case when ARRIVALS.actualtime is null
        THEN
           ARRIVALS.publishedTime
        else
            ARRIVALS.actualtime
        END as arrivaltime,

    case when ARRIVALS.mod_gate is not null
        THEN
           ARRIVALS.mod_gate
        else
            ARRIVALS.gate
        END as actual_gate,

    case when mod_status is not null
    then
        ARRIVALS.mod_status
    else
        ARRIVALS.status
    end as status2,
    AIRLINES.ICAO,
    'https://www.flydulles.com/flight/arrival/'||DATE('now')||'/'||ARRIVALS.IATA||'/'||ARRIVALS.flightnumber AS FlyDullesURL,
    'https://www.flightradar24.com/data/aircraft/'||ARRIVALS.tail_number AS equipment_history,
    case when substr(timediff(actualtime, datetime('now', 'localtime')), 1, 1) == '-'
        Then substr(timediff(actualtime, datetime('now', 'localtime')), 12, 6) || ' Ago'
        Else 'In' || substr(timediff(actualtime, datetime('now', 'localtime')), 12, 6)
        END AS TimeDifference, status,
    *
       from ARRIVALS, AIRLINES where DATE(publishedTime) = DATE('now')  and ARRIVALS.IATA = AIRLINES.IATA order by actualtime asc;