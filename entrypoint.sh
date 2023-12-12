#!/bin/bash
set -e

# Infinite loop to keep the container running and restart the Python script in case of failure
while true; do
    # Execute Python script
    python3.10 -u /root/algos/data_trade_scraper.py  # Add any necessary arguments
    echo "Python script exited with status $?. Respawning.." >&2
    sleep 5
done
