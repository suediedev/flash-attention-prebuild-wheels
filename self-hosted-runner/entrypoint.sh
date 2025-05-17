#!/bin/bash
id

# Start docker daemon
sudo service docker start

exec "$@"