#!/bin/bash

set -Eeuo pipefail

### CONFIG ###
PROJECT_DIR="/home/shekar/projects/dullesArrivals"
WEB_DIR="/var/www/dulles.xyz"
PYTHON="/usr/bin/python3"
LOG_FILE="/var/log/dullesArrivals.log"
TIMESTAMP_FILE="lastRunTimestamp"

### LOGGING ###
exec >> "$LOG_FILE" 2>&1
echo "----------------------------------------"
echo "Run started at $(date)"

### RUN ###
cd "$PROJECT_DIR"

$PYTHON "$PROJECT_DIR/shekar.py"

### DEPLOY (idempotent: overwrite in place) ###
install -m 644 \
  iab.html \
  index.html \
  arrivals.html \
  departures.html \
  arrivals.json \
  departures.json \
  fleet_cache.json \
  styles.css \
  favicon.ico \
  *.png \
  "$WEB_DIR"

### TIMESTAMP ###
date > "$TIMESTAMP_FILE"
install -m 644 "$TIMESTAMP_FILE" "$WEB_DIR/$TIMESTAMP_FILE"

echo "Run completed successfully at $(date)"
