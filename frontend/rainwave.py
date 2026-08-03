"""
rainwave.py - Rainwave-Internetradio fuer das MiSTer Custom Frontend
(Prototyp/Vorschlag fuer Dragrems Musik-System).

Reines stdlib (urllib/json), passend zur "keine externen Abhaengigkeiten"-
Linie des Frontends. Spielt einen Rainwave-Stationsstream ueber mpg123
(das Frontend nutzt mpg123 ohnehin - und es hat HTTP eingebaut, geprueft)
und holt den aktuell laufenden Titel ANONYM ueber die oeffentliche
api4/info-Schnittstelle (kein Login/Key noetig).

Rainwave (https://rainwave.cc) ist ein kostenloser Dienst; wir sind hier
nur passiver Hoerer: moderates Poll-Intervall, eigener User-Agent, und
eine "via Rainwave"-Nennung im UI wird empfohlen.
"""
import json
import time
import urllib.request

RAINWAVE_API = "https://rainwave.cc/api4/info"

# Rainwave liefert pro Station einen MP3-Icecast-Mount. Struktur <host>/<mount>
# ist stabil; den aktuellen oeffentlichen HOST bitte einmal an der Tune-in-Seite
# von rainwave.cc bestaetigen (sie koennen umziehen/load-balancen).
RAINWAVE_STREAM_HOST = "http://relay.rainwave.cc"   # http! mpg123 hat kein https

# sid -> (Anzeigename, Icecast-Mount)
RAINWAVE_STATIONS = {
    1: ("Game",     "game.mp3"),
    2: ("OCReMix",  "ocremix.mp3"),
    3: ("Covers",   "covers.mp3"),
    4: ("Chiptune", "chiptune.mp3"),
    5: ("All",      "all.mp3"),
}

USER_AGENT = "MiSTer-Custom-Frontend-Radio/1.0 (+https://rainwave.cc)"
POLL_INTERVAL = 15   # Sekunden; moderat, um den Dienst nicht zu belasten
MPG123_BIN = "/usr/bin/mpg123"   # nur fuer den Direkt-Test unten; im Frontend kommt der Pfad von dort


def station_name(sid):
    st = RAINWAVE_STATIONS.get(sid)
    return st[0] if st else None


def stream_url(sid):
    """Anonyme Stream-URL fuer mpg123, oder None bei unbekannter sid."""
    st = RAINWAVE_STATIONS.get(sid)
    if not st:
        return None
    return "%s/%s" % (RAINWAVE_STREAM_HOST.rstrip("/"), st[1])


def parse_now_playing(info):
    """Aus einer api4/info-Antwort 'Interpret - Titel' bauen. Defensiv:
    fehlende Felder -> so viel wie moeglich, sonst None.
    Struktur: info.sched_current.songs[0] mit title/artists[].name/albums[].name."""
    try:
        song = info["sched_current"]["songs"][0]
    except (KeyError, IndexError, TypeError):
        return None
    title = (song.get("title") or "").strip()
    artists = ", ".join(a.get("name", "") for a in song.get("artists", []) if a.get("name"))
    albums = song.get("albums") or []
    album = (albums[0].get("name") or "").strip() if albums else ""
    if title and artists:
        return "%s - %s" % (artists, title)
    return title or album or None


def _fetch_info(sid, timeout=6):
    url = "%s?sid=%d" % (RAINWAVE_API, sid)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


class RainwaveRadio:
    """Haelt den aktuell laufenden Titel einer Station aktuell. tick()
    regelmaessig aus der Hauptschleife aufrufen - es pollt nur im
    Intervall, blockiert also nicht jeden Frame."""

    def __init__(self, sid=1, log=None):
        self.sid = sid
        self._log = log or (lambda *a: None)
        self._now = None
        self._last_poll = 0.0
        self._fail = 0

    def set_station(self, sid):
        if sid != self.sid and sid in RAINWAVE_STATIONS:
            self.sid = sid
            self._now = None
            self._last_poll = 0.0   # sofort neu holen

    def stream_url(self):
        return stream_url(self.sid)

    def now_playing(self):
        """Aktueller Titel oder None (dann zeigt das UI den Stationsnamen)."""
        return self._now

    def tick(self):
        now = time.monotonic()
        if now - self._last_poll < POLL_INTERVAL:
            return
        self._last_poll = now
        try:
            self._now = parse_now_playing(_fetch_info(self.sid))
            self._fail = 0
        except Exception as e:
            self._fail += 1
            if self._fail <= 2:
                self._log("Rainwave: info-Abruf fehlgeschlagen: %s" % e)
            # letzten bekannten Titel behalten, nicht leeren


# ─── Direkt-Test (nur wenn man die Datei direkt startet, nicht beim Import) ───
if __name__ == "__main__":
    import sys
    import subprocess

    if len(sys.argv) == 1:
        # Test A: Now-Playing aller Stationen -> prueft Netz + api4/info + Parser
        print("Now-Playing pro Station (api4/info):\n")
        for _sid in sorted(RAINWAVE_STATIONS):
            try:
                _np = parse_now_playing(_fetch_info(_sid))
            except Exception as _e:
                _np = "FEHLER: %s" % _e
            print("  [%d] %-9s -> %s" % (_sid, station_name(_sid), _np))
        print("\nStream testen:  python3 rainwave.py play <sid>   (z.B. 1 = Game)")
    elif sys.argv[1] == "play":
        # Test B: Stream via mpg123 abspielen -> prueft Streaming + Host/Mount
        _sid = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        _url = stream_url(_sid)   # http:// (mpg123 kann kein https)
        print("Spiele %s (http, direkt): %s\n(Strg+C zum Beenden)" % (station_name(_sid), _url))
        _rc = 0
        try:
            _rc = subprocess.call([MPG123_BIN, "-q", _url])
        except KeyboardInterrupt:
            _rc = 0   # vom Nutzer beendet -> lief
        if _rc not in (0,):
            # Manche Relays erzwingen https -> curl (kann https) in mpg123s stdin pipen.
            _https = _url.replace("http://", "https://", 1)
            print("\n-> Direkt-http scheiterte (rc=%s). Fallback ueber curl (https):" % _rc)
            print("   curl -sL %s | %s -q -" % (_https, MPG123_BIN))
            try:
                subprocess.call("curl -sL '%s' | '%s' -q -" % (_https, MPG123_BIN), shell=True)
            except KeyboardInterrupt:
                pass
    else:
        print("Nutzung: python3 rainwave.py            (Now-Playing-Test)")
        print("         python3 rainwave.py play <sid> (Stream-Test)")
