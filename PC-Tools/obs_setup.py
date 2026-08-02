#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
obs_setup.py - Stream-Overlay fuer OBS auf dem PC einrichten

Legt eine fertige Overlay-Datei auf dem PC ab, in der die IP des
MiSTers bereits eingetragen ist. In OBS wird dann diese lokale Datei
als Browser-Quelle geladen; die Daten (Auswahl, Cover) holt sie sich
weiterhin live vom MiSTer.

Hinweis: Das ist der KOMFORT-Weg. Es geht auch voellig ohne diese
Datei - dann in OBS einfach http://<MiSTer-IP>:8080/ als Browser-
Quelle eintragen. Die lokale Variante lohnt sich, wenn du das
Aussehen selbst per CSS anpassen willst oder die Quelle unabhaengig
vom MiSTer laden moechtest.

Aufruf (fragt alles ab):
    python obs_setup.py

Ohne Rueckfragen:
    python obs_setup.py --ip 192.168.1.50 --out "C:\\OBS\\MiSTer"

Braucht nur Python 3 - keine Zusatzpakete.
"""

import argparse
import os
import re
import sys
import urllib.request

DEFAULT_PORT = 8080
HERE = os.path.dirname(os.path.abspath(__file__))

# Die Vorlage liegt im Paket neben den Frontend-Dateien.
TEMPLATE_CANDIDATES = [
    os.path.join(HERE, "..", "frontend", "stream_overlay.html"),
    os.path.join(HERE, "stream_overlay.html"),
]

ANLEITUNG = """OBS einrichten - Kurzfassung
============================

MiSTer-IP:  {ip}
Overlay:    {html}

1. Am MiSTer muss das Stream-Overlay eingeschaltet sein:
   OSD -> Scripts -> stream_toggle   (danach Frontend neu starten)

2. In OBS: Quelle hinzufuegen -> "Browser"

3. Haken bei "Lokale Datei" setzen und diese Datei waehlen:
   {html}

4. Breite / Hoehe auf deine Canvas-Groesse setzen, z.B. 1920 x 1080

5. Die Quelle in der Szene nach oben ziehen, damit sie ueber dem
   Spielbild liegt. Der Hintergrund ist transparent.

Aussehen aendern (Farben, Ecke, Groesse, was angezeigt wird):
   http://{ip}:{port}/admin   im Browser oeffnen

Wenn nichts erscheint:
- Laeuft das Frontend gerade? Der Server laeuft nur mit ihm.
- Wurde das Frontend nach dem Einschalten neu gestartet?
- Stimmt die IP? Test im Browser: http://{ip}:{port}/
- Sind MiSTer und PC im selben Netzwerk?
"""


def find_template():
    for p in TEMPLATE_CANDIDATES:
        p = os.path.normpath(p)
        if os.path.isfile(p):
            return p
    return None


def valid_host(s):
    """IP oder Hostname grob pruefen."""
    s = s.strip()
    if not s:
        return False
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", s):
        return all(0 <= int(p) <= 255 for p in s.split("."))
    return bool(re.match(r"^[A-Za-z0-9._-]+$", s))


def check_connection(ip, port, timeout=4):
    """Versuchen, den MiSTer zu erreichen. (True, info) / (False, Grund)"""
    url = "http://%s:%d/state" % (ip, port)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            r.read(200)
        return True, "erreichbar"
    except Exception as e:
        return False, str(e)


def build_overlay(template_path, ip, port):
    """Overlay-HTML mit fest eingetragener MiSTer-Adresse erzeugen."""
    with open(template_path, encoding="utf-8") as f:
        html = f.read()

    base = "http://%s:%d" % (ip, port)

    # Relative Pfade auf die MiSTer-Adresse umbiegen.
    replacements = [
        ("new EventSource('/events')", "new EventSource(BASE + '/events')"),
        ("'/art?sys=' + encodeURIComponent", "BASE + '/art?sys=' + encodeURIComponent"),
    ]
    for old, new in replacements:
        if old not in html:
            raise RuntimeError(
                "Vorlage passt nicht (nicht gefunden: %r).\n"
                "Wurde stream_overlay.html geaendert? Dann diese Datei "
                "anpassen oder in OBS direkt http://%s/ verwenden."
                % (old, base))
        html = html.replace(old, new)

    # BASE-Konstante einsetzen
    anchor = "<script>\nconst $ = id => document.getElementById(id);"
    if anchor not in html:
        raise RuntimeError("Vorlage passt nicht (Script-Anfang nicht gefunden).")
    html = html.replace(
        anchor,
        "<script>\n// Adresse des MiSTers - von obs_setup.py eingetragen\n"
        "const BASE = \"%s\";\nconst $ = id => document.getElementById(id);"
        % base)

    return html


def ask(prompt, default=None):
    suffix = " [%s]" % default if default else ""
    try:
        val = input(prompt + suffix + ": ").strip()
    except EOFError:
        val = ""
    return val or (default or "")


def main():
    ap = argparse.ArgumentParser(
        description="Stream-Overlay fuer OBS auf dem PC einrichten")
    ap.add_argument("--ip", help="IP oder Hostname des MiSTers")
    ap.add_argument("--out", help="Zielordner auf dem PC")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT,
                    help="Port (Standard: %d)" % DEFAULT_PORT)
    ap.add_argument("--no-check", action="store_true",
                    help="Verbindungstest ueberspringen")
    args = ap.parse_args()

    print("=" * 46)
    print(" Stream-Overlay fuer OBS einrichten")
    print("=" * 46)

    template = find_template()
    if not template:
        print("\nFEHLER: stream_overlay.html nicht gefunden.")
        print("Dieses Skript im entpackten Paket lassen (Ordner PC-Tools),")
        print("damit es die Vorlage in ../frontend/ findet.")
        return 1

    # --- IP ---
    ip = args.ip
    while not ip or not valid_host(ip):
        if ip:
            print("  Das sieht nicht nach einer gueltigen Adresse aus.")
        ip = ask("\nIP-Adresse des MiSTers (z.B. 192.168.1.50)")
        if not ip:
            print("Ohne Adresse geht es nicht - abgebrochen.")
            return 1
    ip = ip.strip()

    # --- Verbindungstest ---
    if not args.no_check:
        print("\nTeste Verbindung zu %s:%d ..." % (ip, args.port))
        ok, info = check_connection(ip, args.port)
        if ok:
            print("  OK - der MiSTer antwortet.")
        else:
            print("  Keine Antwort (%s)." % info.split("\n")[0])
            print("  Das ist nicht zwingend ein Fehler: der Server laeuft nur,")
            print("  wenn das Frontend gerade laeuft und das Overlay am MiSTer")
            print("  eingeschaltet ist (OSD -> Scripts -> stream_toggle).")
            weiter = ask("  Trotzdem fortfahren? (j/n)", "j")
            if not weiter.lower().startswith("j"):
                return 1

    # --- Zielordner ---
    out = args.out
    default_out = os.path.join(os.path.expanduser("~"), "MiSTer-Overlay")
    while not out:
        out = ask("\nZielordner auf dem PC", default_out)
    out = os.path.expanduser(out.strip().strip('"'))

    try:
        os.makedirs(out, exist_ok=True)
    except OSError as e:
        print("\nFEHLER: Ordner konnte nicht angelegt werden: %s" % e)
        return 1

    # --- Dateien schreiben ---
    try:
        html = build_overlay(template, ip, args.port)
    except RuntimeError as e:
        print("\nFEHLER: %s" % e)
        return 1

    html_path = os.path.join(out, "mister_overlay.html")
    txt_path = os.path.join(out, "OBS_ANLEITUNG.txt")
    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(ANLEITUNG.format(ip=ip, port=args.port, html=html_path))
    except OSError as e:
        print("\nFEHLER beim Schreiben: %s" % e)
        return 1

    print("\n" + "=" * 46)
    print(" Fertig.")
    print("=" * 46)
    print("Overlay-Datei:  %s" % html_path)
    print("Kurzanleitung:  %s" % txt_path)
    print("\nIn OBS:")
    print("  Quelle hinzufuegen -> Browser")
    print("  Haken bei 'Lokale Datei' -> die Datei oben waehlen")
    print("  Breite/Hoehe = Canvas, z.B. 1920 x 1080")
    print("\nAussehen einstellen:  http://%s:%d/admin" % (ip, args.port))
    return 0


if __name__ == "__main__":
    sys.exit(main())
