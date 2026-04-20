#!/bin/bash
# Install script for Ecobee PG3x node server

MYDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Installing Ecobee Node Server dependencies from $MYDIR"

pip3 install requests --upgrade

echo "Install complete."
exit 0
