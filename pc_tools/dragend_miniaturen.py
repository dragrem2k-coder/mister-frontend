#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dragend - Miniaturen am PC rechnen.

Holt den Auftrag vom MiSTer, rechnet die Cover-Miniaturen auf diesem
Rechner und legt sie im Zwischenspeicher des MiSTer ab.

ABLAUF
------
1. Auf dem MiSTer: System -> Verhalten -> "Miniaturen-Auftrag für PC
   schreiben". Das Frontend legt dabei
   /media/fat/frontend/miniatur_auftrag.json an.
2. Dieses Programm starten, IP des MiSTer eintragen, Start druecken.
3. Fertig. Beim naechsten Frontend-Start liegen die Miniaturen da.

WARUM DER UMWEG UEBER DIE AUFTRAGSDATEI
---------------------------------------
Der Schluessel, unter dem eine Miniatur abgelegt wird, ist

    sha1(Pfad | Kastenbreite | Kastenhoehe | Dateigroesse |
         Aenderungszeit | Verfahrensnummer)

Zwei der sechs Bestandteile sind ueber eine Netzfreigabe nicht
zuverlaessig zu bekommen: der Pfad (Windows schreibt ihn anders,
Umlaute koennen anders kodiert sein) und die Aenderungszeit (FAT32
kennt nur Zwei-Sekunden-Schritte, dazu kommen Zeitzonen-Versaetze).
Waere davon etwas auch nur um eine Sekunde daneben, waere der
Schluessel falsch, der MiSTer faende die Miniaturen nie - und man
saehe es erst, wenn nach Stunden nichts schneller geworden ist.

Deshalb rechnet der MiSTer die Schluessel selbst und schickt sie
fertig mit. Dieses Programm trifft keine einzige Annahme darueber.

Die dritte Gefahr waeren die Kastengroessen: sie haengen am Layout
(Liste/Raster/Galerie, CRT gegen HDMI, Bildrand, Kastenstufen). Auch
die kommen aus dem Auftrag, aus genau dem Code, der sie im Betrieb
benutzt.

BAUEN
-----
    pip install paramiko pillow pyinstaller
    pyinstaller --onefile --windowed --name Dragend-Miniaturen ^
        dragend_miniaturen.py

Oder einfach bauen.bat doppelklicken.
"""
import os
import sys
import json
import queue
import threading
import posixpath
import traceback

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import dragend_kern as KERN                                  # noqa: E402

AUFTRAG_PFAD = "/media/fat/frontend/miniatur_auftrag.json"
VORGABE_HOST = "MiSTer"
VORGABE_USER = "root"
VORGABE_PASS = "1234"
EINSTELLUNGEN = os.path.join(
    os.path.expanduser("~"), ".dragend_miniaturen.json")


# ==========================================================================
# Arbeitsteil - ohne Oberflaeche, damit er auch auf der Kommandozeile laeuft
# ==========================================================================
class Abbruch(Exception):
    pass


def rechnen(args):
    """Ein Cover mit allen seinen Kaesten - laeuft in einem eigenen
    PROZESS, nicht in einem Thread.

    Das Verkleinern ist reines Python (siehe dragend_kern.py) und damit
    an den Interpreter-Sperrriegel gebunden: mit Threads wuerde immer
    nur einer rechnen, egal wie viele man startet. Gemessen an einem
    900x1200-Cover kostet ein HDMI-Kasten 145 ms, der Rasterkasten
    67 ms - bei ein paar tausend Covern ist das der ganze Unterschied
    zwischen drei Minuten und einer halben Stunde.

    Die Threads bleiben trotzdem: sie halten die SFTP-Verbindungen und
    warten auf die Prozesse, und waehrend sie warten, laeuft das Netz
    weiter. Genau diese Ueberlappung ist gewollt - Herunterladen,
    Rechnen und Hochladen passieren gleichzeitig."""
    daten, kaesten = args
    w, h, pix = KERN.bild_lesen(daten)
    fertig = []
    for k in kaesten:
        fertig.append((k["k"],
                       KERN.miniatur_bauen(w, h, pix, k["b"], k["h"])))
    return fertig


class Lauf(object):
    """Ein kompletter Durchgang: verbinden, rechnen, ablegen."""

    def __init__(self, host, user, passwort, melden, fortschritt,
                 threads=0):
        self.host = host
        self.user = user
        self.passwort = passwort
        self.melden = melden              # melden(text)
        self.fortschritt = fortschritt    # fortschritt(fertig, gesamt)
        # Ein Thread je Rechenprozess plus einer, damit immer jemand
        # am Netz haengt, waehrend die anderen rechnen lassen.
        self.kerne = max(1, min(8, os.cpu_count() or 2))
        self.threads = max(2, min(9, threads or self.kerne + 1))
        self.pool = None
        self.stopp = threading.Event()
        self.fehler = []
        self._gezaehlt = 0
        self._zaehler_sperre = threading.Lock()

    # ----------------------------------------------------------------
    def _verbinden(self):
        import paramiko
        klient = paramiko.SSHClient()
        klient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        klient.connect(self.host, username=self.user,
                       password=self.passwort, timeout=15,
                       allow_agent=False, look_for_keys=False)
        return klient

    def _auftrag_lesen(self, sftp):
        try:
            with sftp.open(AUFTRAG_PFAD, "rb") as f:
                daten = json.loads(f.read().decode("utf-8"))
        except IOError:
            raise Abbruch(
                "Keine Auftragsdatei auf dem MiSTer gefunden.\n\n"
                "Bitte dort erst System -> Verhalten -> "
                "\"Miniaturen-Auftrag für PC schreiben\" ausführen.")
        if daten.get("algo") != KERN.THUMB_ALGO_VERSION:
            raise Abbruch(
                "Das Frontend benutzt Verfahren %s, dieses Programm "
                "kennt %s.\n\nBitte die zusammengehörenden Fassungen "
                "verwenden - sonst entstehen Miniaturen, die der "
                "MiSTer nie findet."
                % (daten.get("algo"), KERN.THUMB_ALGO_VERSION))
        return daten

    # ----------------------------------------------------------------
    def _ordner_anlegen(self, sftp, pfad, bekannt):
        """mkdir -p ueber SFTP, mit Gedaechtnis (spart Rundreisen)."""
        if pfad in bekannt:
            return
        teile = pfad.strip("/").split("/")
        aktuell = ""
        for teil in teile:
            aktuell += "/" + teil
            if aktuell in bekannt:
                continue
            try:
                sftp.stat(aktuell)
            except IOError:
                try:
                    sftp.mkdir(aktuell)
                except IOError:
                    pass
            bekannt.add(aktuell)

    def _ablegen(self, sftp, zielpfad, inhalt, bekannt):
        """Atomar schreiben: erst .tmp, dann umbenennen. Ein Abbruch
        mitten im Uebertragen darf keine halbe Datei hinterlassen - der
        MiSTer wuerde sie fuer eine gueltige Miniatur halten."""
        self._ordner_anlegen(sftp, posixpath.dirname(zielpfad), bekannt)
        tmp = zielpfad + ".tmp"
        with sftp.open(tmp, "wb") as f:
            f.set_pipelined(True)
            f.write(inhalt)
        try:
            sftp.remove(zielpfad)
        except IOError:
            pass
        sftp.rename(tmp, zielpfad)

    # ----------------------------------------------------------------
    def _arbeiter(self, klient, auftraege, cache, hd, gesamt):
        sftp = klient.open_sftp()
        bekannt = set()
        try:
            while not self.stopp.is_set():
                try:
                    eintrag = auftraege.get_nowait()
                except queue.Empty:
                    return
                pfad = eintrag["p"]
                kaesten = eintrag["k"]
                try:
                    with sftp.open(pfad, "rb") as f:
                        f.prefetch()
                        daten = f.read()
                    if self.pool is not None:
                        fertig = self.pool.submit(
                            rechnen, (daten, kaesten)).result()
                    else:
                        fertig = rechnen((daten, kaesten))
                except Exception as e:                   # noqa: BLE001
                    self.fehler.append("%s: %s"
                                       % (posixpath.basename(pfad), e))
                    self._weiter(len(kaesten), gesamt)
                    continue
                for (schluessel, inhalt) in fertig:
                    if self.stopp.is_set():
                        return
                    try:
                        if inhalt is None:
                            raise ValueError("Zielgröße nicht berechenbar")
                        self._ablegen(
                            sftp, KERN.cache_pfad(cache, hd, schluessel),
                            inhalt, bekannt)
                    except Exception as e:               # noqa: BLE001
                        self.fehler.append(
                            "%s: %s" % (posixpath.basename(pfad), e))
                    self._weiter(1, gesamt)
        finally:
            try:
                sftp.close()
            except Exception:                            # noqa: BLE001
                pass

    def _weiter(self, n, gesamt):
        with self._zaehler_sperre:
            self._gezaehlt += n
            fertig = self._gezaehlt
        self.fortschritt(fertig, gesamt)

    # ----------------------------------------------------------------
    def starten(self):
        self.melden("Verbinde mit %s ..." % self.host)
        klient = self._verbinden()
        try:
            sftp = klient.open_sftp()
            daten = self._auftrag_lesen(sftp)
            sftp.close()

            cover = daten.get("cover") or []
            cache = daten.get("cache") or "/media/fat/frontend/thumb_cache"
            hd = bool(daten.get("hd"))
            gesamt = sum(len(e.get("k") or []) for e in cover)
            if not gesamt:
                self.melden("Im Auftrag steht nichts zu tun - es liegt "
                            "bereits alles im Zwischenspeicher.")
                return 0, 0
            self.melden("Auftrag: %d Miniaturen aus %d Covern (%s)."
                        % (gesamt, len(cover), "HDMI" if hd else "CRT"))

            auftraege = queue.Queue()
            for e in cover:
                auftraege.put(e)

            try:
                from concurrent.futures import ProcessPoolExecutor
                self.pool = ProcessPoolExecutor(max_workers=self.kerne)
                self.melden("Rechne auf %d Kernen, %d Verbindungen."
                            % (self.kerne, self.threads))
            except Exception:                            # noqa: BLE001
                # Kein Grund aufzugeben - es dauert dann nur laenger.
                self.pool = None
                self.melden("Arbeitsprozesse nicht verfügbar - "
                            "es läuft einkernig weiter.")

            faeden = []
            for _ in range(self.threads):
                th = threading.Thread(
                    target=self._arbeiter,
                    args=(klient, auftraege, cache, hd, gesamt),
                    daemon=True)
                th.start()
                faeden.append(th)
            for th in faeden:
                th.join()
            return self._gezaehlt, gesamt
        finally:
            if self.pool is not None:
                try:
                    self.pool.shutdown(wait=False, cancel_futures=True)
                except TypeError:                        # Python < 3.9
                    self.pool.shutdown(wait=False)
                except Exception:                        # noqa: BLE001
                    pass
            try:
                klient.close()
            except Exception:                            # noqa: BLE001
                pass


# ==========================================================================
# Oberflaeche
# ==========================================================================
def _einstellungen_laden():
    try:
        with open(EINSTELLUNGEN, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _einstellungen_speichern(host, user):
    # BEWUSST OHNE PASSWORT: ein Klartext-Passwort in einer Datei im
    # Benutzerordner waere fuer die eingesparten drei Tastendruecke ein
    # schlechter Tausch.
    try:
        with open(EINSTELLUNGEN, "w", encoding="utf-8") as f:
            json.dump({"host": host, "user": user}, f)
    except OSError:
        pass


def gui():
    import tkinter as tk
    from tkinter import ttk, messagebox

    gespeichert = _einstellungen_laden()

    wurzel = tk.Tk()
    wurzel.title("Dragend - Miniaturen")
    wurzel.resizable(False, False)
    try:
        wurzel.call("tk", "scaling", 1.3)
    except tk.TclError:
        pass

    rahmen = ttk.Frame(wurzel, padding=14)
    rahmen.grid(sticky="nsew")

    ttk.Label(rahmen, text="MiSTer (Name oder IP)").grid(
        row=0, column=0, sticky="w", pady=2)
    e_host = ttk.Entry(rahmen, width=26)
    e_host.insert(0, gespeichert.get("host", VORGABE_HOST))
    e_host.grid(row=0, column=1, sticky="w", pady=2)

    ttk.Label(rahmen, text="Benutzer").grid(
        row=1, column=0, sticky="w", pady=2)
    e_user = ttk.Entry(rahmen, width=26)
    e_user.insert(0, gespeichert.get("user", VORGABE_USER))
    e_user.grid(row=1, column=1, sticky="w", pady=2)

    ttk.Label(rahmen, text="Passwort").grid(
        row=2, column=0, sticky="w", pady=2)
    e_pass = ttk.Entry(rahmen, width=26, show="*")
    e_pass.insert(0, VORGABE_PASS)
    e_pass.grid(row=2, column=1, sticky="w", pady=2)

    balken = ttk.Progressbar(rahmen, length=340, mode="determinate")
    balken.grid(row=3, column=0, columnspan=2, pady=(12, 4), sticky="we")

    protokoll = tk.Text(rahmen, width=52, height=12, wrap="word",
                        state="disabled")
    protokoll.grid(row=4, column=0, columnspan=2, pady=4)

    knopf = ttk.Button(rahmen, text="Start")
    knopf.grid(row=5, column=0, columnspan=2, pady=(6, 0))

    zustand = {"lauf": None}

    def schreiben(text):
        def tun():
            protokoll.configure(state="normal")
            protokoll.insert("end", text + "\n")
            protokoll.see("end")
            protokoll.configure(state="disabled")
        wurzel.after(0, tun)

    letzter = {"wert": -1}

    def setze_fortschritt(fertig, gesamt):
        prozent = int(fertig * 100 / max(1, gesamt))
        if prozent == letzter["wert"]:
            return
        letzter["wert"] = prozent

        def tun():
            balken["maximum"] = gesamt
            balken["value"] = fertig
            wurzel.title("Dragend - Miniaturen (%d%%)" % prozent)
        wurzel.after(0, tun)

    def fertig(nachricht, fehler_liste):
        def tun():
            knopf.configure(text="Start", state="normal")
            zustand["lauf"] = None
            wurzel.title("Dragend - Miniaturen")
            if fehler_liste:
                messagebox.showwarning(
                    "Fertig, mit Ausnahmen",
                    nachricht + "\n\nNicht verarbeitet: %d\n%s"
                    % (len(fehler_liste), "\n".join(fehler_liste[:8])))
            else:
                messagebox.showinfo("Fertig", nachricht)
        wurzel.after(0, tun)

    def arbeiten(host, user, passwort):
        lauf = zustand["lauf"]
        try:
            gezaehlt, gesamt = lauf.starten()
            if lauf.stopp.is_set():
                schreiben("Abgebrochen.")
                fertig("Abgebrochen bei %d von %d." % (gezaehlt, gesamt), [])
                return
            schreiben("Fertig: %d von %d." % (gezaehlt, gesamt))
            fertig("%d Miniaturen liegen jetzt auf dem MiSTer."
                   % (gezaehlt - len(lauf.fehler)), lauf.fehler)
        except Abbruch as e:
            schreiben(str(e))
            fertig(str(e), [])
        except Exception as e:                           # noqa: BLE001
            schreiben("FEHLER: %s" % e)
            schreiben(traceback.format_exc())
            fertig("Abgebrochen: %s" % e, [])

    def gedrueckt():
        if zustand["lauf"] is not None:
            zustand["lauf"].stopp.set()
            knopf.configure(text="Bricht ab ...", state="disabled")
            return
        host = e_host.get().strip()
        user = e_user.get().strip()
        passwort = e_pass.get()
        if not host:
            messagebox.showerror("Fehlt", "Bitte den MiSTer eintragen.")
            return
        _einstellungen_speichern(host, user)
        protokoll.configure(state="normal")
        protokoll.delete("1.0", "end")
        protokoll.configure(state="disabled")
        letzter["wert"] = -1
        zustand["lauf"] = Lauf(host, user, passwort,
                               schreiben, setze_fortschritt)
        knopf.configure(text="Abbrechen")
        threading.Thread(target=arbeiten, args=(host, user, passwort),
                         daemon=True).start()

    knopf.configure(command=gedrueckt)
    e_host.focus_set()
    wurzel.mainloop()


def kommandozeile():
    import argparse
    p = argparse.ArgumentParser(description="Dragend - Miniaturen am PC")
    p.add_argument("--host", default=VORGABE_HOST)
    p.add_argument("--user", default=VORGABE_USER)
    p.add_argument("--passwort", default=VORGABE_PASS)
    p.add_argument("--threads", type=int, default=4)
    a = p.parse_args([x for x in sys.argv[1:] if x != "--cli"])

    letzter = [-1]

    def fortschritt(fertig, gesamt):
        prozent = int(fertig * 100 / max(1, gesamt))
        if prozent != letzter[0]:
            letzter[0] = prozent
            sys.stdout.write("\r%3d%%  (%d/%d)" % (prozent, fertig, gesamt))
            sys.stdout.flush()

    lauf = Lauf(a.host, a.user, a.passwort, print, fortschritt, a.threads)
    try:
        gezaehlt, gesamt = lauf.starten()
    except Abbruch as e:
        print(e)
        return 2
    print("\nFertig: %d von %d." % (gezaehlt, gesamt))
    if lauf.fehler:
        print("Nicht verarbeitet: %d" % len(lauf.fehler))
        for z in lauf.fehler[:20]:
            print("  " + z)
    return 0


if __name__ == "__main__":
    # PFLICHT unter Windows, sobald das Programm als eine Datei
    # gepackt ist: ohne diesen Aufruf startet jeder Arbeitsprozess das
    # ganze Programm noch einmal von vorn - samt Fenster. Man bekommt
    # dann acht Fenster statt acht Arbeitsprozessen.
    import multiprocessing
    multiprocessing.freeze_support()

    if "--cli" in sys.argv:
        sys.exit(kommandozeile())
    try:
        gui()
    except Exception:                                    # noqa: BLE001
        # Ohne Fenstersystem (oder ohne tkinter) auf die Kommandozeile
        # zurueckfallen, statt wortlos zu verschwinden.
        sys.exit(kommandozeile())
