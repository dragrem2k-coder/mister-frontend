#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Der Reise-Effekt der Zeitmaschine (Build 352).

NUTZERWUNSCH: beim Start einer Zeitreise ein Effekt "wie bei einer
Zeitreise im Rollenspiel" - Blitz, Wirbel, Blitz, dazu ein eigener
Sound (frontend/sfx/zeitreise.mp3, Quelle siehe frontend/sfx/QUELLEN.txt).
Abschaltbar, mit jeder Taste zu ueberspringen.

ZWEI BILDER, EIN ABLAUF:
  - Mit libdragend ab Fassung 9 zeichnet C den Wirbel (c/dragend.c,
    wirbel_zeichnen) - weich und drehend.
  - Ohne (alte .so, Entwicklungsrechner ohne C) zeichnet Python einen
    Ringtunnel aus gefuellten Rechtecken: ein paar Dutzend fb.rect()
    je Bild, das schafft auch der MiSTer.
Ablauf, Zeiten und die Jahreszahl sind fuer beide gleich und stehen
hier, getrennt vom Zeichnen - so lassen sie sich ohne Bildschirm
pruefen.

DIE ZEIT, NICHT DIE BILDNUMMER, BESTIMMT DAS BILD. Ein langsames Geraet
zeigt weniger Bilder, aber denselben Effekt zur selben Zeit; der Sound
laeuft ja auch nach der Uhr.

KOSTEN: keine, solange niemand reist. Das Modul haelt keinen Zustand
ausser dem Schalter.
"""
import math
import os

ORDNER = "/media/fat/frontend"
AUS_FLAG = os.path.join(ORDNER, "zeitreise_effekt_aus")

# Der Ablauf in Sekunden. Abgestimmt auf den Sound: der ist zwischen
# 0,5 und 1,5 s am lautesten und wird ab 2,6 s ausgeblendet.
BLITZ_EIN = 0.18        # Weiss -> Wirbel
RATTERN = 2.20          # die Jahreszahl laeuft zum Ziel
HALTEN = 0.30           # das Ziel steht, der Wirbel dreht weiter
BLITZ_AUS = 0.22        # Wirbel -> Weiss
WEISS = 0.10            # ganz weiss, dann die Liste
GESAMT = BLITZ_EIN + RATTERN + HALTEN + BLITZ_AUS + WEISS

# Sicherheitsgrenze: so viele Bilder hoechstens, egal was die Uhr sagt.
# Steht die Uhr (Pruefstand) oder springt sie zurueck, endet der Effekt
# trotzdem.
MAX_BILDER = 240

SOUND = "zeitreise"


# ======================================================================
# SCHALTER (Vorgabe AN)
# ======================================================================
_aus = [None]


def an():
    if _aus[0] is None:
        _aus[0] = os.path.exists(AUS_FLAG)
    return not _aus[0]


def toggle_an():
    try:
        if an():
            os.makedirs(os.path.dirname(AUS_FLAG), exist_ok=True)
            open(AUS_FLAG, "w").close()
        elif os.path.exists(AUS_FLAG):
            os.remove(AUS_FLAG)
    except OSError:
        pass
    _aus[0] = None
    return an()


# ======================================================================
# DER ABLAUF
# ======================================================================
def phase(t):
    """Was zur Zeit t (Sekunden seit Beginn) zu sehen ist:
    (blitz 0..256, rattern 0..1, fertig). blitz 256 = ganz weiss,
    rattern = wie weit die Jahreszahl ist."""
    if t < 0:
        t = 0.0
    if t >= GESAMT:
        return 256, 1.0, True
    if t < BLITZ_EIN:
        return int(256 * (1.0 - t / BLITZ_EIN)), 0.0, False
    t -= BLITZ_EIN
    if t < RATTERN:
        return 0, t / RATTERN, False
    t -= RATTERN
    if t < HALTEN:
        return 0, 1.0, False
    t -= HALTEN
    if t < BLITZ_AUS:
        return int(256 * t / BLITZ_AUS), 1.0, False
    return 256, 1.0, False


def jahr_bei(von, nach, anteil):
    """Die Jahreszahl beim Rattern: schnell los, langsam ins Ziel."""
    anteil = max(0.0, min(1.0, anteil))
    e = 1.0 - (1.0 - anteil) ** 3
    return int(round(von + (nach - von) * e))


# ======================================================================
# DER RINGTUNNEL (ohne C)
# ======================================================================
FARBEN = ((40, 60, 200), (110, 50, 210), (190, 60, 220), (60, 190, 230),
          (120, 140, 255))
DUNKEL = (24, 20, 70)
HELL = (235, 240, 255)
RINGE = 18
SCHRITT = 0.80          # jeder Ring 0,8 mal so gross wie der davor
TEMPO = 8.75            # Ringe je Sekunde, die auf einen zukommen


def _mischen(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def ringe(breite, hoehe, t):
    """Die Rechtecke des Tunnels zur Zeit t: [(x, y, w, h, rgb)], vom
    groessten zum kleinsten - in dieser Reihenfolge gezeichnet, liegt
    jeder Ring auf dem davor. Alles ganze Zahlen, alles im Bild."""
    raus = []
    fort = t * TEMPO
    phase_ = fort % 1.0
    k0 = int(fort)
    cx = breite / 2.0 + math.sin(t * 6.0) * breite * 0.035
    cy = hoehe / 2.0 + math.cos(t * 5.0) * hoehe * 0.035
    for i in range(RINGE):
        p = i - phase_
        g = 1.15 * (SCHRITT ** p)
        hw, hh = breite * 0.5 * g, hoehe * 0.5 * g
        if hw < 2 or hh < 2:
            break
        fern = min(1.0, max(0.0, p / RINGE))
        k = i + k0
        grund = FARBEN[(k // 2 + int(t * 6)) % len(FARBEN)] \
            if k % 2 == 0 else DUNKEL
        farbe = _mischen(grund, HELL, fern ** 1.6 * 0.85)
        x0 = max(0, int(cx - hw))
        y0 = max(0, int(cy - hh))
        x1 = min(breite, int(cx + hw))
        y1 = min(hoehe, int(cy + hh))
        if x1 > x0 and y1 > y0:
            raus.append((x0, y0, x1 - x0, y1 - y0, farbe))
    # Licht am Ende des Tunnels
    for r, farbe in ((0.03, (200, 210, 255)), (0.015, (255, 255, 255))):
        w = max(2, int(breite * r * 2))
        h = max(2, int(w * 0.9))
        x0 = max(0, int(cx - w / 2))
        y0 = max(0, int(cy - h / 2))
        raus.append((x0, y0, min(w, breite - x0), min(h, hoehe - y0), farbe))
    return raus


def aufhellen(rgb, blitz):
    """Eine Farbe um blitz/256 Richtung Weiss ziehen."""
    b = max(0, min(256, blitz))
    return tuple(int(c + (255 - c) * b / 256.0) for c in rgb)
