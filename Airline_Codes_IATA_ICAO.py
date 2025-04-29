import requests
from bs4 import BeautifulSoup
import pandas as pd

# URL of the Wikipedia page containing airline codes
url = "https://en.wikipedia.org/wiki/List_of_airline_codes"

# Fetch the content of the webpage
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

# Find all tables on the page
tables = soup.find_all("table", {"class": "wikitable"})

# Store valid airline code data
airline_codes = []

# Loop through each table and extract valid rows
for table in tables:
    rows = table.find_all("tr")[1:]  # Skip header
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 4:
            iata = cols[0].get_text(strip=True)
            icao = cols[1].get_text(strip=True)
            airline_name = cols[2].get_text(strip=True)

            # Apply filters
            if (
                iata and
                "*" not in iata and
                icao and
                icao.lower() != "n/a"
            ):
                airline_codes.append({
                    "IATA": iata,
                    "ICAO": icao,
                    "Airline Name": airline_name
                })

# Convert to DataFrame
df_airlines = pd.DataFrame(airline_codes)

# Save to CSV
df_airlines.to_csv("airline_codes.csv", index=False)

print("Filtered airline codes saved to 'airline_codes.csv'")
