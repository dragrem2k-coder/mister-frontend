#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audio: Lautstaerke-Verwaltung, Navigations-Soundeffekte (selbst
erzeugte WAVs), MusicPlayer (MP3 + Rainwave-Internetradio). Ausgelagert
aus frontend.py (Modularisierung, Git-Branch 'modular-refactor').

Zwei ehemals WEIT AUSEINANDERLIEGENDE Bloecke aus dem Original hier
zusammengefuehrt (Lautstaerke-Grundlagen lagen frueher im Code, SFX/
MusicPlayer deutlich spaeter) - gehoeren inhaltlich klar zusammen,
kein Grund, sie getrennt zu halten.

VOLUME (siehe cycle_volume() in MusicPlayer) wird von frontend.py aus
an EINER Stelle direkt gelesen (system_items(), fuer die Menue-
Beschriftung) - dieselbe Einfrier-Falle wie bei CURRENT_LANG waere
hier bei einem einfachen Import aufgetreten. Wie bei current_lang()
geloest: get_volume() als Funktion, die IMMER den aktuellen Wert
liefert (hier unproblematisch, da system_items() nur bei Menue-
Aufbau aufgerufen wird, keine heisse Stelle wie Framebuffer.text()).
"""
import os, sys, glob, subprocess, threading, time, wave, struct, math, random
from fe.log import LOG

try:
    import rainwave
except Exception:
    rainwave = None

MPG123_BIN  = "/usr/bin/mpg123"

MUSIC_DIR   = "/media/fat/music"
MUSIC_ENABLED_FILE = "/media/fat/frontend/music_enabled"
MUSIC_SOURCE_FILE  = "/media/fat/frontend/music_source"   # "mp3"/"radio" + Stations-sid
VOLUME_FILE = "/media/fat/frontend/volume"   # Lautstaerke 0-100 (Musik + Menue-Sounds)

# NEUES FEATURE (Nutzerwunsch: Lautstaerke-Regler fuer Musik UND
# Menue-Sounds, uebernommen aus einem separat vorbereiteten, auf
# echter MiSTer-Hardware getesteten Vorschlag - siehe
# CHANGES_VOLUME.md). Zwei unterschiedliche Mechanismen, weil Musik
# und Menue-Sounds technisch verschieden abgespielt werden: Musik
# laeuft ueber mpg123, das einen eingebauten Skalierungsfaktor
# (-f 0..32768) hat. Menue-Sounds sind selbst erzeugte WAVs, abgespielt
# ueber aplay - aplay hat KEINEN Lautstaerke-Schalter, deshalb steckt
# die Lautstaerke dort in der AMPLITUDE der erzeugten WAV-Datei selbst
# (werden bei einer Aenderung neu erzeugt statt nur neu abgespielt).
def _load_volume():
    try:
        return max(0, min(100, int(open(VOLUME_FILE).read().strip())))
    except (OSError, ValueError):
        return 100

def _save_volume(v):
    try:
        os.makedirs(os.path.dirname(VOLUME_FILE), exist_ok=True)
        with open(VOLUME_FILE, "w") as f:
            f.write(str(int(v)))
    except OSError:
        pass

VOLUME = _load_volume()   # 0-100; global, von Musik (mpg123 -f) UND SFX genutzt

def _mpg_scale():
    """mpg123 -f Skalierungsfaktor (0..32768) fuer die aktuelle Lautstaerke."""
    return str(int(32768 * VOLUME / 100))

def _regenerate_sfx():
    """Menue-Sound-WAVs bei geaenderter Lautstaerke neu erzeugen - aplay hat
    keinen Volume-Schalter, also steckt die Lautstaerke in der Amplitude."""
    try:
        for _f in glob.glob(os.path.join(SFX_DIR, "*.wav")):
            os.remove(_f)
    except OSError:
        pass
    _ensure_sfx_files()

_volume_apply_lock = None

def _apply_volume_async(player):
    """SFX-Neuerzeugung + Musik-Neustart im Hintergrund - beides ist auf dem
    MiSTer traege bzw. blockierend (Popen.wait bis 2s), also NICHT im
    Menue-Thread. Ein Lock serialisiert schnelle Mehrfach-Druecke; jeder
    Lauf nutzt das dann aktuelle VOLUME (letzter gewinnt).

    BUGFIX (uebernommen aus separat vorbereitetem Vorschlag, siehe
    CHANGES_v4.2_FIXES.md): rief bisher player._stop_current() und
    player._start_current() als ZWEI getrennte Aufrufe auf - dazwischen
    konnte tick() (aus dem Menue-Thread) ebenfalls einen Start ausloesen,
    zwei mpg123-Prozesse liefen dann gleichzeitig (doppelter/verzerrter
    Radio-Stream). _start_current() beendet jetzt selbst, unter
    _proc_lock, zuerst den alten Prozess, bevor der neue startet - ein
    einziger, atomarer Aufruf reicht."""
    global _volume_apply_lock
    if _volume_apply_lock is None:
        _volume_apply_lock = threading.Lock()
    def _worker():
        with _volume_apply_lock:
            _regenerate_sfx()
            if player.enabled and not player.paused_for_core:
                player._start_current()
    threading.Thread(target=_worker, daemon=True).start()

# ----------------------------------------------------------------------------
# NAVIGATIONS-SOUNDEFFEKTE (selbst erzeugte Sinuston-WAVs, aplay)
#
# Kein Download noetig - die kurzen Toene werden beim ersten Start
# einmalig selbst synthetisiert (reines math/struct) und unter
# SFX_DIR abgelegt. Abgespielt wird "fire and forget" ueber `aplay`
# (Teil von alsa-utils, auf MiSTer bereits vorhanden) - laeuft parallel
# zur Hintergrundmusik; ist die Soundkarte gerade belegt ("device
# busy"), wird der Effekt einfach uebersprungen statt etwas zu stoeren.
# Eine Drossel verhindert, dass beim Halten einer Richtungstaste (mit
# Turbo-Beschleunigung) zu viele Prozesse pro Sekunde losgehen.
SFX_DIR = "/media/fat/frontend/sfx"
SFX_ENABLED_FLAG_FILE = "/media/fat/frontend/sfx_disabled"
SFX_MIN_GAP = 0.07   # Sekunden zwischen zwei Soundeffekten (Drossel)

def sfx_enabled_flag():
    return not os.path.exists(SFX_ENABLED_FLAG_FILE)

def toggle_sfx():
    if os.path.exists(SFX_ENABLED_FLAG_FILE):
        try:
            os.remove(SFX_ENABLED_FLAG_FILE)
        except OSError:
            pass
    else:
        try:
            dirname = os.path.dirname(SFX_ENABLED_FLAG_FILE)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            open(SFX_ENABLED_FLAG_FILE, "w").close()
        except OSError:
            pass

def _synth_tone_samples(freq_start, freq_end, duration_ms, volume, sample_rate):
    """Erzeugt die rohen 16-Bit-Samples fuer EINEN Frequenz-Sweep
    (kumulative Phase statt sin(2*pi*freq*t) mit wechselndem freq -
    sonst wuerden bei einem Sweep hoerbare Spruenge entstehen). Kern
    von _write_wav_tone()/_write_wav_chime()."""
    n = max(1, int(sample_rate * duration_ms / 1000))
    fade = max(1, n // 8)
    samples = bytearray(n * 2)
    phase = 0.0
    for i in range(n):
        freq = freq_start + (freq_end - freq_start) * (i / max(1, n - 1))
        phase += 2 * math.pi * freq / sample_rate
        env = 1.0
        if i < fade:
            env = i / fade
        elif i > n - fade:
            env = (n - i) / fade
        val = int(math.sin(phase) * volume * env * 32767)
        val = max(-32768, min(32767, val))
        struct.pack_into("<h", samples, i * 2, val)
    return samples

def _write_wav(path, data, sample_rate=22050):
    """Schreibt fertige 16-Bit-Mono-Samples als WAV-Datei."""
    byte_rate = sample_rate * 2
    header = (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
             + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate,
                                     byte_rate, 2, 16)
             + b"data" + struct.pack("<I", len(data)))
    with open(path, "wb") as f:
        f.write(header + data)

def _write_wav_tone(path, freq_start, freq_end, duration_ms,
                    volume=0.35, sample_rate=22050):
    """Erzeugt eine kurze Mono-WAV-Datei mit einem einzelnen Sinuston
    (linearer Frequenz-Sweep von freq_start zu freq_end)."""
    samples = _synth_tone_samples(freq_start, freq_end, duration_ms,
                                  volume, sample_rate)
    _write_wav(path, bytes(samples), sample_rate)

def _write_wav_chime(path, segments, volume=0.35, sample_rate=22050):
    """Wie _write_wav_tone(), aber fuer mehrere Toene HINTEREINANDER -
    segments: Liste von (freq_start, freq_end, duration_ms)-Tupeln.
    Fuer den Erfolgs-Sound (kurzer aufsteigender Doppelklang), der mit
    einem einzelnen Sweep nicht "erfolgreich" genug klingt."""
    all_samples = bytearray()
    for freq_start, freq_end, duration_ms in segments:
        all_samples += _synth_tone_samples(freq_start, freq_end, duration_ms,
                                           volume, sample_rate)
    _write_wav(path, bytes(all_samples), sample_rate)

# NEUES FEATURE (Nutzerwunsch: einen echten, selbst aufgenommenen/
# gewaehlten Sound statt des prozedural erzeugten Doppelklangs fuer
# Erfolge UND Popup-Benachrichtigungen verwenden - beide nutzen
# denselben SFX-Schluessel "achievement", siehe SFX_CHIME_DEFS unten
# und die play_sfx()-Aufrufe an mehreren Stellen). Die eigentliche
# Ton-QUELLE liegt als WAV-Datei bei (22050Hz/Mono/16-Bit, damit sie
# zum Rest des SFX-Systems passt - vom urspruenglich hochgeladenen
# FLAC per ffmpeg konvertiert), wird aber bei JEDER Erzeugung/
# Lautstaerke-Aenderung frisch mit der aktuellen VOLUME-Einstellung
# skaliert eingelesen - genau wie bei den prozedural erzeugten Toenen,
# nur dass hier eine echte Aufnahme statt eines Sinuston-Sweeps als
# Ausgangsmaterial dient.
ACHIEVEMENT_SFX_SOURCE = "/media/fat/frontend/sfx_source/achievement.wav"

def _write_wav_from_source(source_path, dest_path, volume=1.0):
    """Liest eine vorhandene WAV-Datei ein, skaliert die Amplitude mit
    volume (0.0-1.0+) und schreibt sie unter dest_path neu heraus -
    gleiches Prinzip wie bei den prozedural erzeugten Toenen
    (_write_wav_tone()/_write_wav_chime()), nur mit echtem
    Audiomaterial als Quelle statt eines berechneten Sinuston-Sweeps.
    Faengt JEDEN Fehler ab und liefert False statt einer Ausnahme -
    Aufrufer soll bei Fehlschlag auf die prozedurale Erzeugung
    zurueckfallen (siehe _ensure_sfx_files())."""
    try:
        with wave.open(source_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            raw = wf.readframes(wf.getnframes())
    except (wave.Error, OSError):
        return False
    if sampwidth != 2:
        return False   # nur 16-Bit-PCM unterstuetzt, Quelle wurde so konvertiert
    n_samples = len(raw) // 2
    scaled = bytearray(len(raw))
    for i in range(n_samples):
        val = struct.unpack_from("<h", raw, i * 2)[0]
        val = int(val * volume)
        val = max(-32768, min(32767, val))
        struct.pack_into("<h", scaled, i * 2, val)
    try:
        with wave.open(dest_path, "wb") as wf_out:
            wf_out.setnchannels(n_channels)
            wf_out.setsampwidth(2)
            wf_out.setframerate(framerate)
            wf_out.writeframes(bytes(scaled))
    except (wave.Error, OSError):
        return False
    return True

SFX_DEFS = {
    "move":    (760, 900, 30),
    "confirm": (600, 1100, 70),
    "back":    (700, 420, 55),
}
SFX_CHIME_DEFS = {
    # Kurzer aufsteigender Doppelklang - deutlich von den einfachen
    # Sweeps oben abgesetzt, fuer den Erfolgs-Sound.
    "achievement": [(600, 900, 60), (950, 1400, 90)],
    # Geheimer Sound (Nutzerwunsch: "Easter Egg System") -
    # verspielter, mehrstufiger Klang, bewusst deutlich anders
    # als die anderen Sounds (auffaelliger "Fund"-Charakter).
    "secret_found": [(300, 600, 50), (600, 450, 40), (450, 900, 70), (900, 700, 90)],
    # Chiptune-Easter-Egg (Nutzerwunsch): kurze, FLACHE Toene (Start-
    # und Zielfrequenz gleich, kein Sweep/Gleiten) statt der weichen
    # Sweeps oben - klingt dadurch "blippiger", naeher an einem
    # klassischen 8-Bit-Arpeggio (A-C#-E-A).
    "chiptune": [(440, 440, 45), (554, 554, 45), (659, 659, 45), (880, 880, 70)],

    # NEU (Nutzerwunsch: eigene MP3-Sounds fuer Geheimes Gold-Theme,
    # Entwicklerraum und den EGG-Bonus-Code, siehe SFX_DIR/*.mp3 bzw.
    # _on_secret_triggered()/draw_dev_room_screen() in frontend.py) -
    # bisher hatten diese drei ueberhaupt keinen Eintrag hier, das
    # Reingehen/Freischalten blieb bis dahin stumm (bzw. nutzte nur den
    # generischen "achievement"-Ton). Synthetische Ersatzklaenge nach
    # demselben Prinzip wie bei den anderen Eintraegen - greifen nur,
    # falls die echte MP3-Datei mal fehlen sollte (siehe play_sfx()/
    # _play_ducked_sfx(): MP3 wird immer bevorzugt).
    "secret_theme_1": [(500, 900, 50), (900, 1300, 60), (1300, 1700, 90)],
    "entwicklerraum": [(200, 500, 60), (500, 350, 40), (350, 650, 70)],
    "dev_room_bonus": [(700, 700, 35), (700, 1000, 35), (1000, 1300, 35), (1300, 1600, 80)],

    # NEU (Nutzerwunsch: eigener Unlock-Sound pro Secret-Theme, siehe
    # SECRET_CODES/THEMES in frontend.py) - alle rein prozedural erzeugt
    # wie die Sounds oben, kein zusaetzliches Audio-Asset noetig.
    "theme_snes": [(300, 300, 40), (500, 500, 40), (750, 750, 40), (1000, 1200, 90)],
    "theme_gb": [(200, 200, 35), (200, 200, 35), (200, 200, 35), (400, 400, 60)],
    "theme_gbc": [(500, 700, 40), (700, 500, 40), (900, 1300, 80)],
    "theme_n64": [(1200, 400, 40), (400, 1400, 70)],
    "theme_ps1": [(150, 150, 60), (150, 600, 90), (600, 600, 50)],
    "theme_megadrive": [(1000, 1400, 35), (1400, 1800, 45)],
    "theme_sms": [(300, 300, 40), (450, 450, 40), (600, 600, 40), (900, 900, 60)],
    "theme_gamegear": [(800, 1100, 30), (1100, 900, 30), (1400, 1400, 50)],
    "theme_saturn": [(200, 200, 70), (200, 700, 90), (700, 300, 60)],
}

def _ensure_sfx_files():
    """Erzeugt die WAV-Dateien einmalig, falls sie noch fehlen (erster
    Start bzw. nach einem Update). Amplitude skaliert mit der
    eingestellten Lautstaerke (VOLUME) - aplay hat selbst keinen
    Lautstaerke-Schalter, siehe _regenerate_sfx()."""
    try:
        os.makedirs(SFX_DIR, exist_ok=True)
    except OSError:
        return
    for name, (f0, f1, dur) in SFX_DEFS.items():
        path = os.path.join(SFX_DIR, name + ".wav")
        if not os.path.exists(path):
            try:
                _write_wav_tone(path, f0, f1, dur, volume=0.35 * VOLUME / 100.0)
            except OSError:
                pass
    for name, segments in SFX_CHIME_DEFS.items():
        path = os.path.join(SFX_DIR, name + ".wav")
        if not os.path.exists(path):
            try:
                _write_wav_chime(path, segments, volume=0.35 * VOLUME / 100.0)
                if name == "achievement" and os.path.exists(ACHIEVEMENT_SFX_SOURCE):
                    # NEUES FEATURE (Nutzerwunsch): echte Audiodatei statt
                    # prozedural erzeugtem Doppelklang - faellt bei jedem
                    # Fehler (Datei fehlt/kaputt/falsches Format) sauber
                    # auf den bisherigen, garantiert funktionierenden
                    # Klang zurueck, statt komplett stumm zu bleiben.
                    ok = _write_wav_from_source(ACHIEVEMENT_SFX_SOURCE, path,
                                                volume=VOLUME / 100.0)
                    if not ok:
                        _write_wav_chime(path, segments, volume=0.35 * VOLUME / 100.0)
                else:
                    _write_wav_chime(path, segments, volume=0.35 * VOLUME / 100.0)
            except OSError:
                pass

_last_sfx_time = 0.0
_sfx_enabled_cache = True
_sfx_enabled_check_next = 0.0
_sfx_proc = None   # laufender aplay-Prozess (oder None) - siehe play_sfx()

def _sfx_enabled_cached():
    """Zwischengespeicherte sfx_enabled_flag()-Abfrage, alle 5 Sekunden
    neu geprueft - selbes Prinzip wie beim Netzwerkstatus/Attract-Modus
    (siehe _network_connected()/_attract_enabled_cached()). Wird von
    play_sfx() genutzt, damit nicht bei jedem einzelnen Aufruf eine
    Datei-Existenzpruefung noetig ist."""
    global _sfx_enabled_cache, _sfx_enabled_check_next
    now = time.monotonic()
    if now >= _sfx_enabled_check_next:
        _sfx_enabled_cache = sfx_enabled_flag()
        _sfx_enabled_check_next = now + 5.0
    return _sfx_enabled_cache

def play_sfx(name, music_playing=False):
    """Spielt einen Soundeffekt ab, falls aktiviert - "fire and forget",
    jeder Fehler (aplay fehlt, Soundkarte belegt, Datei fehlt) wird
    still ignoriert. Nie eine Ausnahme nach aussen. Gedrosselt
    (SFX_MIN_GAP) - sonst wuerden beim Halten einer Richtungstaste mit
    Turbo-Beschleunigung zu viele aplay-Prozesse pro Sekunde entstehen.

    BUGFIX (Nutzer-Rueckmeldung): die reine Zeit-Drossel allein hat
    NICHT verhindert, dass sich bei schneller Navigation mehrere
    aplay-Prozesse ueberlappen - jeder einzelne Aufruf brauchte
    laenger als die Drosselzeit, bis er tatsaechlich fertig war
    (vermutlich, weil aplay auf die Soundkarte warten musste, die
    gleichzeitig von mpg123 fuer die Hintergrundmusik belegt ist).
    Ergebnis: ein wachsender Rueckstau, der noch Toene abspielte, lange
    nachdem der Cursor schon wieder stillstand - UND dabei offenbar
    kurze Aussetzer in der Musik verursachte, weil beide Programme sich
    dieselbe Audioausgabe streitig machten. Zwei Absicherungen dagegen:
    (1) ein neuer Ton wird NICHT gestartet, solange der vorherige
    aplay-Prozess noch laeuft (kein Rueckstau moeglich, hoechstens
    EIN Ton gleichzeitig unterwegs). (2) Solange Musik TATSAECHLICH
    gerade spielt (music_playing=True, vom Aufrufer per
    self.music._proc_alive() ermittelt), wird gar nicht erst
    versucht - vermeidet die Geraete-Ueberschneidung von vornherein,
    statt nur ihre Folgen abzumildern.

    WICHTIG: die guenstige, rein im Speicher liegende Drossel-Pruefung
    muss VOR der (Datei-basierten) Ein/Aus-Pruefung passieren, nicht
    danach - sonst waere bei jedem einzelnen Navigations-Schritt
    waehrend eines Turbo-Sprungs eine Datei-Existenzpruefung noetig
    gewesen. Zusaetzlich per _sfx_enabled_cached() auf 5s
    zwischengespeichert.

    ERWEITERT (Nutzerwunsch: eigener, echter Sound statt des
    synthetischen Klangs fuer den geheimen Ikari-Warriors-Code):
    liegt eine <name>.mp3 in SFX_DIR, wird DIE bevorzugt abgespielt
    (per mpg123, das ohnehin schon fuer die Hintergrundmusik im
    Einsatz ist - aplay selbst kann keine MP3s dekodieren). Die
    <name>.wav bleibt als automatisch erzeugte Rueckfallebene
    bestehen (siehe _ensure_sfx_files()), falls keine eigene MP3
    hinterlegt ist - dadurch bricht nichts, wenn z.B. jemand die
    sfx-mp3-Datei versehentlich loescht."""
    global _last_sfx_time, _sfx_proc
    now = time.monotonic()
    if now - _last_sfx_time < SFX_MIN_GAP:
        return
    if music_playing:
        return
    if _sfx_proc is not None and _sfx_proc.poll() is None:
        return   # voriger Ton laeuft noch - lieber auslassen als stapeln
    if not _sfx_enabled_cached():
        return
    _last_sfx_time = now
    mp3_path = os.path.join(SFX_DIR, name + ".mp3")
    if os.path.exists(mp3_path) and os.path.exists(MPG123_BIN):
        try:
            _sfx_proc = subprocess.Popen(
                [MPG123_BIN, "-q", "-f", _mpg_scale(), mp3_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass
        return
    path = os.path.join(SFX_DIR, name + ".wav")
    try:
        _sfx_proc = subprocess.Popen(["aplay", "-q", path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass

# ----------------------------------------------------------------------------
# BACKGROUND MUSIC (mpg123, extern - no own MP3 decoder needed)
# ----------------------------------------------------------------------------

class MusicPlayer:
    """Plays MP3s from MUSIC_DIR in random order in the background.
    Uses the external mpg123 command-line player (present on MiSTer)
    instead of decoding audio ourselves. Non-blocking: the current
    track runs via subprocess.Popen, the switch to the next track
    happens whenever tick() is called from the main loop."""

    MAX_TRACK_SECONDS = 20 * 60   # Sicherheitsnetz, siehe tick()

    def __init__(self):
        self.enabled = self._load_enabled()
        self.source, _radio_sid = self._load_source()   # "mp3" oder "radio" + sid
        self.radio = rainwave.RainwaveRadio(sid=_radio_sid, log=LOG) \
            if rainwave is not None else None
        self.playlist = []
        self.pos = 0
        self.proc = None
        self._track_started_at = None
        # RLock (nicht Lock): tick() unten haelt die Sperre waehrend des
        # gesamten Durchlaufs (siehe dortiger Kommentar) und ruft dabei
        # selbst _start_current()/_stop_current() auf, die die Sperre
        # INTERN ebenfalls holen - mit einem normalen Lock waere das
        # ein Deadlock (derselbe Thread wartet auf sich selbst). RLock
        # erlaubt genau das (derselbe Thread darf mehrfach verschachtelt
        # zugreifen), verhindert aber weiterhin zuverlaessig, dass ZWEI
        # VERSCHIEDENE Threads (z.B. Haupt-Thread/tick() und ein
        # Hintergrund-Thread fuer Musikquellenwechsel/geheimen Sound)
        # gleichzeitig an mpg123 herumschrauben - der urspruengliche
        # Grund fuer dieses Schloss (siehe Kommentar direkt darunter).
        self._proc_lock = threading.RLock()   # BUGFIX (uebernommen aus separat
                                              # vorbereitetem Vorschlag, siehe
                                              # CHANGES_v4.2_FIXES.md): verhindert
                                              # doppelte mpg123-Prozesse - der
                                              # Lautstaerke-Hintergrund-Thread und
                                              # tick() konnten bisher gleichzeitig
                                              # einen Start ausloesen, zwei mpg123
                                              # gleichzeitig fuehrten zu doppeltem/
                                              # verzerrtem Radio-Stream.
        self.paused_for_core = False
        self.paused_for_jingle = False   # NEU (Nutzerwunsch: Erfolgs-Pop-ups sollen
                                          # jetzt GENAUSO einen Jingle bekommen wie
                                          # der geheime Sound - EIN Flag jetzt
                                          # fuer JEDEN gedaempften Soundeffekt
                                          # verwendet, nicht mehr nur fuer den einen
                                          # Spezialfall). Ohne dieses Flag wuerde
                                          # tick() (laeuft staendig im Haupt-Loop)
                                          # die Musik WAEHREND ein solcher Sound noch
                                          # laeuft automatisch neu starten, sobald es
                                          # merkt, dass "nichts mehr laeuft" -
                                          # GENAU dasselbe Prinzip wie paused_for_core,
                                          # nur ein eigenes Flag, um mit einem gerade
                                          # laufenden Core nicht zu kollidieren.
        # BUGFIX (Nutzer-Rueckmeldung: "Sound kommt beim Code, aber MP3/
        # Radio pausiert nicht dabei, es kommt zur Ueberlagerung und
        # faengt das Stottern an"): _play_ducked_sfx() in frontend.py
        # wird bei einer Erst-Freischaltung mehrfach HINTEREINANDER fuer
        # DENSELBEN Moment aufgerufen (allgemeiner "Erfolg"-Ton PLUS der
        # eigene Theme-/Raum-/Chiptune-Ton) - jeder Aufruf startete
        # bisher einen komplett eigenstaendigen Hintergrund-Thread, der
        # unabhaengig von den anderen die Musik anhielt/neu startete UND
        # seine eigene mpg123/aplay-Instanz startete. Zwei solche Threads
        # kurz hintereinander liefen dadurch TEILWEISE GLEICHZEITIG:
        # zwei Sound-Dateien gleichzeitig auf derselben Audioausgabe
        # (das eigentliche "Stottern"), UND der zuerst fertige Thread
        # setzte "paused_for_jingle" schon wieder auf False und startete
        # die Musik neu, WAEHREND der zweite Sound noch lief. Jetzt statt
        # eines einzelnen Bool-Flags ein Zaehler (_jingle_depth, per
        # _jingle_count_lock geschuetzt): nur der ERSTE gleichzeitig
        # aktive Aufruf haelt die Musik an (und merkt sich in
        # _jingle_was_playing, ob sie lief), nur der LETZTE (Zaehler
        # wieder auf 0) startet sie wieder. _jingle_play_lock sorgt
        # zusaetzlich dafuer, dass die eigentlichen Sound-Dateien trotz
        # gleichzeitig eintreffender Aufrufe strikt NACHEINANDER
        # abgespielt werden statt einander zu ueberlagern.
        self._jingle_depth = 0
        self._jingle_was_playing = False
        self._jingle_count_lock = threading.Lock()
        self._jingle_play_lock = threading.Lock()
        self._rescan()

    @staticmethod
    def _load_enabled():
        try:
            return open(MUSIC_ENABLED_FILE).read().strip() != "0"
        except OSError:
            return True    # default: on, until toggled once

    def _save_enabled(self):
        try:
            os.makedirs(os.path.dirname(MUSIC_ENABLED_FILE), exist_ok=True)
            with open(MUSIC_ENABLED_FILE, "w") as f:
                f.write("1" if self.enabled else "0")
        except OSError:
            pass

    @staticmethod
    def _load_source():
        """(quelle, sid) aus MUSIC_SOURCE_FILE - Default ("mp3", 1).
        Faellt zusaetzlich auf "mp3" zurueck, falls das rainwave-Modul
        nicht geladen werden konnte (siehe Import-Absicherung oben) -
        eine gespeicherte "radio"-Quelle darf dann nicht blind
        uebernommen werden, sonst gaebe es keine Musik mehr."""
        if rainwave is None:
            return "mp3", 1
        try:
            parts = open(MUSIC_SOURCE_FILE).read().split()
            src = parts[0] if parts and parts[0] in ("mp3", "radio") else "mp3"
            sid = int(parts[1]) if len(parts) > 1 else 1
            if sid not in rainwave.RAINWAVE_STATIONS:
                sid = 1
            return src, sid
        except (OSError, ValueError):
            return "mp3", 1

    def _save_source(self):
        if self.radio is None:
            return
        try:
            os.makedirs(os.path.dirname(MUSIC_SOURCE_FILE), exist_ok=True)
            with open(MUSIC_SOURCE_FILE, "w") as f:
                f.write("%s %d" % (self.source, self.radio.sid))
        except OSError:
            pass

    def _rescan(self):
        try:
            files = [os.path.join(MUSIC_DIR, f)
                    for f in os.listdir(MUSIC_DIR)
                    if f.lower().endswith(".mp3")]
        except OSError:
            files = []
        random.shuffle(files)
        self.playlist = files
        self.pos = 0

    def available(self):
        if self.source == "radio":
            return self.radio is not None and os.path.exists(MPG123_BIN)
        return bool(self.playlist) and os.path.exists(MPG123_BIN)

    def _proc_alive(self):
        return self.proc is not None and self.proc.poll() is None

    def _start_current(self):
        """Startet die aktuelle Quelle (MP3/Radio). Lock + 'vorher
        alten Prozess beenden' -> nie zwei mpg123 gleichzeitig (siehe
        _proc_lock-Kommentar im __init__)."""
        with self._proc_lock:
            self._kill_proc()
            self._start_current_impl()

    def _start_current_impl(self):
        if self.source == "radio":
            if self.radio is None:
                return
            url = self.radio.stream_url()
            if not url:
                return
            try:
                self.proc = subprocess.Popen(
                    [MPG123_BIN, "-q", "-f", _mpg_scale(), url],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL)
                self._track_started_at = time.monotonic()
                LOG("Radio: %s -> %s" % (rainwave.station_name(self.radio.sid), url))
            except OSError as e:
                LOG("Radio: mpg123-Start fehlgeschlagen: %s" % e)
                self.proc = None
            return
        if not self.playlist:
            return
        path = self.playlist[self.pos]
        try:
            self.proc = subprocess.Popen(
                [MPG123_BIN, "-q", "-f", _mpg_scale(), path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL)
            self._track_started_at = time.monotonic()
            LOG("Music: playing %s" % os.path.basename(path))
        except OSError as e:
            LOG("Music: failed to start mpg123: %s" % e)
            self.proc = None

    def _kill_proc(self):
        """Beendet den laufenden mpg123-Prozess. Aufrufer haelt _proc_lock."""
        if self.proc is not None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

    def _stop_current(self):
        with self._proc_lock:
            self._kill_proc()

    def _advance(self):
        if not self.playlist:
            return
        self.pos += 1
        if self.pos >= len(self.playlist):
            random.shuffle(self.playlist)   # new round, reshuffled
            self.pos = 0

    def current_track_name(self):
        """Anzeigename des aktuell (bzw. zuletzt gestarteten) Songs,
        ohne Pfad und Dateiendung - oder None, wenn gerade nichts
        gespielt wird/werden soll."""
        if not self.enabled or self.paused_for_core:
            return None
        if self.source == "radio":
            if self.radio is None:
                return None
            return self.radio.now_playing() or \
                ("Radio: %s" % rainwave.station_name(self.radio.sid))
        if not self.playlist:
            return None
        path = self.playlist[self.pos]
        return os.path.splitext(os.path.basename(path))[0]

    def tick(self):
        """Call regularly from the main loop. Starts playback if
        needed, automatically advances to the next track once the
        current one has ended.

        Sicherheitsnetz: manche MP3-Dateien (beschaedigte/unuebliche
        Tags) koennen mpg123 nach dem eigentlichen Ende haengen lassen,
        statt sauber zu beenden - poll() wuerde dann faelschlich
        weiterhin 'laeuft noch' melden. Nach MAX_TRACK_SECONDS wird
        deshalb trotzdem zum naechsten Song gewechselt.

        BUGFIX (Nutzer-Rueckmeldung: geheimer Sound ueberschnitt sich
        mit der Musik/"nur Gestotter", UND der Musikquellenwechsel
        blockierte trotz des vorherigen Hintergrund-Thread-Fixes immer
        noch kurz die Eingabe): zwei zusammenhaengende Ursachen.
        (1) tick() laeuft SEHR haeufig im Haupt-Loop und wusste bisher
        nichts von einer bewusst pausierten Musik fuer einen gedaempften
        Soundeffekt (geheimer Sound, Erfolgs-Jingle) - startete sie
        mitten drin automatisch neu, sobald es "nichts laeuft" sah
        (paused_for_jingle unten behebt das, gleiches Prinzip wie
        paused_for_core). (2) _start_current()/_stop_current() holen
        sich INTERN dieselbe Sperre wie ein Hintergrund-Thread
        (Musikquellenwechsel/gedaempfter Soundeffekt) - lief gerade so
        ein Hintergrund-Thread, wartete tick() im Haupt-Thread bisher
        BLOCKIEREND auf dieselbe Sperre, was trotz des Hintergrund-
        Threads selbst wieder die gesamte Eingabeverarbeitung anhielt.
        Jetzt versucht tick() die Sperre nur noch NICHT-BLOCKIEREND zu
        holen - ist sie gerade belegt, macht tick() diesmal einfach
        nichts und versucht es beim naechsten Durchlauf (kommt sehr
        bald wieder) erneut, statt zu warten."""
        if not self.enabled or self.paused_for_core or self.paused_for_jingle:
            return
        if not self._proc_lock.acquire(blocking=False):
            return   # gerade anderweitig beschaeftigt - naechstes Mal wieder versuchen
        try:
            if self.source == "radio":
                if self.radio is None:
                    return
                self.radio.tick()                 # Now-Playing aktuell halten (nur alle 15s)
                if not self._proc_alive():
                    # (neu) verbinden - kleiner Backoff gegen Haemmern bei Netzausfall
                    if self._track_started_at is None or \
                       time.monotonic() - self._track_started_at > 3:
                        self._start_current()
                return
            if not self.playlist:
                return
            alive = self._proc_alive()
            had_proc = self.proc is not None  # VOR _stop_current() merken -
                                              # das setzt self.proc selbst auf None
            if alive and self._track_started_at is not None and \
               time.monotonic() - self._track_started_at > self.MAX_TRACK_SECONDS:
                LOG("Music: Sicherheitsnetz ausgeloest (Song laeuft laenger "
                    "als %d Minuten) - erzwinge Wechsel"
                    % (self.MAX_TRACK_SECONDS // 60))
                self._stop_current()
                alive = False
            if not alive:
                if had_proc:
                    LOG("Music: Song beendet, wechsle weiter")
                    self._advance()
                self._start_current()
        finally:
            self._proc_lock.release()

    def next_track(self):
        """Manual track skip (Y button). Nicht-blockierend (gleicher
        Grund wie cycle_source(), siehe dortiger Kommentar) - laeuft
        direkt in der Hauptschleife, das Stoppen/Starten von mpg123
        darf sie deshalb nicht aufhalten."""
        if not self.playlist:
            return
        self._advance()

        def _worker():
            self._stop_current()
            if self.enabled and not self.paused_for_core:
                self._start_current()
        threading.Thread(target=_worker, daemon=True).start()

    def toggle(self):
        """Musik an/aus (gleicher Nicht-blockierend-Grund wie
        cycle_source()/next_track() oben)."""
        self.enabled = not self.enabled
        self._save_enabled()
        if self.enabled:
            if not self.paused_for_core:
                threading.Thread(target=self.tick, daemon=True).start()
        else:
            threading.Thread(target=self._stop_current, daemon=True).start()

    def cycle_source(self):
        """Musik-Quelle umschalten: MP3 -> Radio(Game..All) -> zurueck zu MP3.
        Laesst den An/Aus-Zustand (self.enabled) bewusst unberuehrt.
        Ohne geladenes rainwave-Modul (siehe Import-Absicherung oben)
        bleibt das ein no-op - es gaebe nichts, wohin man umschalten
        koennte.

        BUGFIX (Nutzer-Rueckmeldung: "wenn ich die Musikquelle
        wechsel nimmt das Frontend ein paar Sekunden lang KEINE
        Eingabe an, dann ziehen alle auf einmal nach"): rief bisher
        SYNCHRON in der Hauptschleife self._stop_current() auf, was
        intern terminate()+wait(timeout=2) auf den alten mpg123-
        Prozess macht - bei einem gerade haengenden Netzwerk-Stream
        (Radio reagiert nicht sofort auf SIGTERM) blockierte das
        spuerbar die GESAMTE Eingabeverarbeitung, da beides im selben
        Haupt-Thread lief. Jetzt wie bei cycle_volume()/
        _apply_volume_async() (siehe dortiger Kommentar, gleicher
        Grund) in einem Hintergrund-Thread erledigt: state (Quelle/
        Sender) wird weiterhin SOFORT synchron aktualisiert (billig,
        die Menue-Beschriftung stimmt sofort), nur das eigentliche
        Stoppen+Starten von mpg123 laeuft asynchron - weiterhin ueber
        denselben _proc_lock serialisiert wie tick()/die Lautstaerke-
        Anpassung, also weiterhin GARANTIERT kein doppelter mpg123
        gleichzeitig (der urspruengliche Grund fuer den bisherigen
        synchronen Ablauf bleibt gewahrt, nur eben nicht mehr
        blockierend fuer die Hauptschleife)."""
        if self.radio is None:
            return
        stations = sorted(rainwave.RAINWAVE_STATIONS)
        if self.source == "mp3":
            self.source = "radio"
            self.radio.set_station(stations[0])
        else:
            idx = stations.index(self.radio.sid) if self.radio.sid in stations else -1
            if idx + 1 < len(stations):
                self.radio.set_station(stations[idx + 1])
            else:
                self.source = "mp3"
        self._track_started_at = None
        self._save_source()
        if self.enabled and not self.paused_for_core:
            threading.Thread(target=self._start_current, daemon=True).start()
        else:
            threading.Thread(target=self._stop_current, daemon=True).start()

    def cycle_volume(self):
        """Lautstaerke 0->20->...->100->0 (Musik UND Menue-Sounds)."""
        global VOLUME
        levels = [0, 20, 40, 60, 80, 100]
        idx = levels.index(VOLUME) if VOLUME in levels else len(levels) - 1
        VOLUME = levels[(idx + 1) % len(levels)]
        _save_volume(VOLUME)
        _apply_volume_async(self)   # SFX-Regen + Musik-Neustart im Hintergrund

    def pause_for_core(self):
        """Before starting a core/game: stop music so it doesn't mix
        with the game's own audio."""
        self.paused_for_core = True
        self._stop_current()

    def resume_after_core(self):
        """After returning to the frontend: resume music automatically
        if it's enabled."""
        self.paused_for_core = False
        if self.enabled:
            self.tick()

    def shutdown(self):
        self._stop_current()


def get_volume():
    """Liefert IMMER die aktuelle Lautstaerke - siehe Modul-Kommentar
    oben, warum ein direktes 'from fe.audio import VOLUME' an anderer
    Stelle gefaehrlich waere (eingefrorene Kopie)."""
    return VOLUME
