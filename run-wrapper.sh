#!/bin/sh

sleep 1s && touch main.py &

watchmedo shell-command \
 -R \
 --patterns="*.py" \
 --command='python3 main.py' \
 .
