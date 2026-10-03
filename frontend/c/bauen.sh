#!/bin/bash
# libdragend fuer den MiSTer (armv7l) uebersetzen.
#
# Braucht auf einem Debian/Ubuntu-PC:
#     sudo apt install gcc-arm-linux-gnueabihf libc6-dev-armhf-cross
#
# Ergebnis: ZWEI Dateien, beide gehoeren nach /media/fat/frontend/
#
#   libdragend.so        die bisherige Fassung (-O2, ohne NEON)
#   libdragend_neon.so   dieselbe Quelle, vektorisiert
#
# WARUM ZWEI
#
# Der Cortex-A9 im DE10-Nano hat NEON. Gebaut wurde bisher mit blossem
# -O2, also skalar - ein Byte nach dem anderen. Aus dem Bench auf dem
# Geraet: 112 ms fuer 1200x1600 auf 578x770, das sind 58 Nanosekunden
# je Quellpunkt. Fuer C auf 800 MHz ist das viel.
#
# Die Flaechenmittelung ist genau die Sorte Schleife, die ein Vektor-
# befehlssatz mag: je Zielpunkt Summen ueber Quellpunkte, drei Kanaele,
# alles 8 Bit. GCC vektorisiert sie mit den Flags unten auch
# tatsaechlich (nachgeprueft mit -fopt-info-vec-optimized: die
# Schleifen in skalieren_flaechenmittel() und hochskalieren()).
#
# Ob daraus auf dem Geraet wirklich ein Gewinn wird, sagt NICHT der
# Compiler, sondern die Messung - siehe unten.
#
# WAS BEWUSST NICHT DABEI IST
#
# Kein -ffast-math und nichts aus dieser Familie. Die Zielbereiche
# werden ueber DOUBLE gerechnet (siehe dragend.c), und das Ergebnis
# muss bitgleich zur Python-Fassung bleiben - sonst waeren die
# Miniaturen im Cache nicht mehr austauschbar mit frisch gerechneten,
# und der Vergleich in tools/test_c_modul.py faellt auseinander.
#
# Nachgeprueft: -O3 mit Vektorisierung liefert gegenueber -O2 ueber 120
# Vergleiche (Flaechenmittel, Nearest, Hochskalieren, Zufallsgroessen)
# bitgleiche Ergebnisse.
#
# SO WIRD VERGLICHEN
#
# Beide Dateien nach /media/fat/frontend/ kopieren, dann:
#
#     python3 /media/fat/frontend/frontend.py --bench
#     DRAGEND_LIB=/media/fat/frontend/libdragend_neon.so \
#         python3 /media/fat/frontend/frontend.py --bench
#
# Abschnitt C beider Laeufe nebeneinanderlegen. Interessant sind die
# vier Verkleinern-Zeilen. Alles andere sollte sich nicht ruehren.
set -e
cd "$(dirname "$0")"

GEMEINSAM="-shared -fPIC -Wall -Wextra"

arm-linux-gnueabihf-gcc $GEMEINSAM -O2 \
    -o libdragend.so dragend.c
echo "gebaut: libdragend.so       $(ls -l libdragend.so | awk '{print $5}') Byte"

# -mfpu=neon-vfpv3 statt blossem -mfpu=neon: NEON rechnet einfache
# Genauigkeit nicht IEEE-treu (Flush-to-Zero). Unsere Fliesskomma-
# rechnung ist DOUBLE und laeuft damit ohnehin ueber VFP - diese
# Schreibweise macht das ausdruecklich.
arm-linux-gnueabihf-gcc $GEMEINSAM -O3 \
    -mcpu=cortex-a9 -mfpu=neon-vfpv3 -mfloat-abi=hard -ftree-vectorize \
    -o libdragend_neon.so dragend.c
echo "gebaut: libdragend_neon.so  $(ls -l libdragend_neon.so | awk '{print $5}') Byte"

# NEU (Build 219): auch die Fassung fuer den Entwicklungsrechner. Sie
# liegt seit Build 155 im Ordner, wurde aber von Hand gebaut - und genau
# das ist ein Problem: die Tests in tools/ benutzen sie ueber
# DRAGEND_LIB, um "C gegen Python" zu vergleichen. Bleibt sie beim Bauen
# aussen vor, prueft dieser Vergleich irgendwann eine alte Fassung gegen
# neues Python und meldet Gruen fuer etwas, das auf dem Geraet anders
# aussieht.
gcc $GEMEINSAM -O2 \
    -o libdragend_x86.so dragend.c
echo "gebaut: libdragend_x86.so   $(ls -l libdragend_x86.so | awk '{print $5}') Byte"

# NEU (Build 227): und sofort eine Ebene hoeher kopieren. DIESE Kopie
# laedt frontend.py (fe/art.py sucht sie neben frontend.py, nicht in
# c/) - der Schritt war bisher Handarbeit, und genau das ist in Build
# 227 schiefgegangen: die neue Fassung lag in c/, geladen wurde die
# alte, und das Frontend meldete still "Version 7 ohne texte_zeichnen"
# und rechnete weiter in Python. Ein Gewinn, den niemand sieht, ist
# schlimmer als keiner - also tut es jetzt das Skript.
cp -f libdragend.so libdragend_neon.so libdragend_x86.so ..
echo "kopiert nach frontend/: alle drei"

echo
echo "Vektorisierte Schleifen:"
arm-linux-gnueabihf-gcc $GEMEINSAM -O3 \
    -mcpu=cortex-a9 -mfpu=neon-vfpv3 -mfloat-abi=hard -ftree-vectorize \
    -fopt-info-vec-optimized -o /dev/null dragend.c 2>&1 \
    | grep "vectorized" | sed 's/^/  /' || echo "  keine"

echo
file libdragend.so
file libdragend_neon.so
