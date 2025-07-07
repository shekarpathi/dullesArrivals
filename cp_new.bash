#!/bin/bash
cd /home/ec2-user/dullesArrivals
git fetch
git pull
/usr/bin/python3 shekar.py
sudo rm -f /var/www/html/fis.html /var/www/html/iab.html /var/www/html/index.html /var/www/html/arrivals.html /var/www/html/arrivals.json /var/www/html/departures.html /var/www/html/departures.json
sudo cp iab.html /var/www/html
sudo cp index.html /var/www/html
sudo cp arrivals.html /var/www/html
sudo cp departures.html /var/www/html
sudo cp arrivals.json /var/www/html
sudo cp departures.json /var/www/html
sudo cp fleet_cache.json /var/www/html
sudo cp styles.css /var/www/html
sudo cp *.png /var/www/html
sudo cp favicon.ico /var/www/html
sudo chown ec2-user /var/www/html/*
sudo chgrp ec2-user /var/www/html/*
date >> /tmp/lastRunTimestamp
date >> lastRunTimestamp
sudo cp lastRunTimestamp /var/www/html
