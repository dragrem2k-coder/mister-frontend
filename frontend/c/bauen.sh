#!/bin/bash
# libdragend fuer den MiSTer (armv7l) uebersetzen.
#
# Braucht auf einem Debian/Ubuntu-PC:
#     sudo apt install gcc-arm-linux-gnueabihf libc6-dev-armhf-cross
#
# Ergebnis: libdragend.so - gehoert nach /media/fat/frontend/
set -e
cd "$(dirname "$0")"
arm-linux-gnueabihf-gcc -shared -fPIC -O2 -Wall -Wextra \
    -o libdragend.so dragend.c
echo "gebaut: $(ls -l libdragend.so | awk '{print $5}') Byte"
file libdragend.so
