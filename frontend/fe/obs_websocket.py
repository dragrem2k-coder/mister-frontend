#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimaler OBS-WebSocket-v5-Client (reine Python-Standardbibliothek,
kein "websockets"-Paket verfuegbar auf dem MiSTer) - fuer genau EINEN
Zweck gebaut: eine Szene per SetCurrentProgramScene umschalten.

NEUES FEATURE (Nutzerwunsch: "diese Umstellung muesste das Frontend
registrieren und dann quasi umschalten, wenn ich dann wieder rausgehe
sollte man auch wieder das Frontend-Menue sehen" - CRT/HDMI koennen
nicht gleichzeitig in nativer Aufloesung laufen, siehe fruehere
Recherche, ABER: fuer ein LAUFENDES SPIEL bekommt HDMI unabhaengig
vom CRT-Signal bereits das Live-Bild direkt vom FPGA-Core, wenn eine
Capture-Karte am HDMI-Port haengt - das Frontend muss dafuer selbst
nichts umschalten. Was das Frontend stattdessen sinnvoll beitragen
kann: OBS per WebSocket mitteilen, WANN es zwischen der Capture-
Karten-Szene (waehrend des Spiels) und der Frontend-Spiegel-Szene
(waehrend des Browsens) wechseln soll - das weiss nur das Frontend
selbst zuverlaessig.

Protokoll-Ablauf (offizielle obs-websocket-v5-Spezifikation,
https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md):
  1. WebSocket-Verbindung aufbauen (HTTP-Upgrade-Handshake)
  2. Server schickt "Hello" (op=0), enthaelt bei aktivierter
     Authentifizierung challenge+salt
  3. Client berechnet die Antwort:
     base64_secret = base64(sha256(passwort + salt))
     antwort       = base64(sha256(base64_secret + challenge))
  4. Client schickt "Identify" (op=1) mit der Antwort
  5. Server schickt "Identified" (op=2) - Verbindung einsatzbereit
  6. Client schickt "Request" (op=6), z.B. SetCurrentProgramScene
  7. Server schickt "RequestResponse" (op=7) mit Erfolg/Misserfolg

Bewusst OHNE dauerhafte Verbindung - Szenenwechsel passieren selten
(nur bei Spielstart/-ende), jedes Mal frisch verbinden ist einfacher
und robuster als eine Verbindung ueber die ganze Frontend-Laufzeit
am Leben zu halten (kein Keepalive/Reconnect-Handling noetig).

Bewusst KOMPLETT FEHLERTOLERANT (jede Funktion faengt alle Fehler ab
und gibt bei Misserfolg einfach False zurueck) - ein nicht
erreichbarer/falsch konfigurierter OBS-Rechner darf niemals den
Spielstart oder die Rueckkehr zum Menue verzoegern oder verhindern.
"""
import base64, hashlib, json, os, socket, struct

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"  # RFC 6455, fest vorgegeben


def _ws_handshake(sock, host, port, path="/"):
    """HTTP-Upgrade-Handshake fuer eine WebSocket-Verbindung - wirft bei
    jedem Problem eine Exception (vom Aufrufer abgefangen)."""
    key = base64.b64encode(os.urandom(16)).decode()
    req = ("GET %s HTTP/1.1\r\n"
           "Host: %s:%d\r\n"
           "Upgrade: websocket\r\n"
           "Connection: Upgrade\r\n"
           "Sec-WebSocket-Key: %s\r\n"
           "Sec-WebSocket-Version: 13\r\n"
           "Sec-WebSocket-Protocol: obswebsocket.json\r\n"
           "\r\n" % (path, host, port, key))
    sock.sendall(req.encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("Verbindung waehrend Handshake geschlossen")
        resp += chunk
    header_part, _, rest = resp.partition(b"\r\n\r\n")
    status_line = header_part.split(b"\r\n", 1)[0]
    if b" 101 " not in (b" " + status_line):
        raise ConnectionError("Kein WebSocket-Upgrade: %r" % status_line[:80])
    expected_accept = base64.b64encode(
        hashlib.sha1((key + _WS_GUID).encode()).digest())
    if expected_accept not in header_part:
        raise ConnectionError("Sec-WebSocket-Accept stimmt nicht ueberein")
    return rest   # bereits mitgelesene Bytes NACH dem HTTP-Header


class _WSClient:
    """Sehr schlanker WebSocket-Rahmen (RFC 6455) - nur Text-Frames,
    nur das, was fuer den OBS-Handshake und einzelne Requests noetig
    ist. Kein Ping/Pong, keine Fragmentierung, kein Kompressions-
    Handling - fuer diesen einen, kurzlebigen Zweck nicht noetig."""

    def __init__(self, sock, prefetched=b""):
        self.sock = sock
        self._buf = prefetched

    def _recv_exact(self, n):
        while len(self._buf) < n:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Verbindung geschlossen")
            self._buf += chunk
        data, self._buf = self._buf[:n], self._buf[n:]
        return data

    def send_text(self, text):
        payload = text.encode("utf-8")
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        ln = len(payload)
        if ln <= 125:
            header = bytes([0x81, 0x80 | ln])
        elif ln <= 0xFFFF:
            header = bytes([0x81, 0x80 | 126]) + struct.pack(">H", ln)
        else:
            header = bytes([0x81, 0x80 | 127]) + struct.pack(">Q", ln)
        self.sock.sendall(header + mask + masked)

    def recv_text(self):
        b0 = self._recv_exact(1)[0]
        opcode = b0 & 0x0F
        b1 = self._recv_exact(1)[0]
        is_masked = bool(b1 & 0x80)
        ln = b1 & 0x7F
        if ln == 126:
            ln = struct.unpack(">H", self._recv_exact(2))[0]
        elif ln == 127:
            ln = struct.unpack(">Q", self._recv_exact(8))[0]
        mask_key = self._recv_exact(4) if is_masked else None
        payload = self._recv_exact(ln)
        if mask_key:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        if opcode == 0x8:
            raise ConnectionError("Server hat die Verbindung geschlossen (Close-Frame)")
        return payload.decode("utf-8")


def _compute_auth(password, salt, challenge):
    """SHA256-Challenge-Response exakt nach obs-websocket-Spezifikation."""
    base64_secret = base64.b64encode(
        hashlib.sha256((password + salt).encode()).digest()).decode()
    return base64.b64encode(
        hashlib.sha256((base64_secret + challenge).encode()).digest()).decode()


def switch_scene(host, port, password, scene_name, timeout=3.0):
    """Verbindet sich zu OBS, wechselt zur angegebenen Szene, trennt
    sich wieder. True bei bestaetigtem Erfolg, False bei JEDEM Fehler
    (nicht erreichbar, falsches Passwort, Szene existiert nicht, ...) -
    siehe Modul-Kommentar oben zur Begruendung der Fehlertoleranz."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        prefetched = _ws_handshake(sock, host, port)
        ws = _WSClient(sock, prefetched)

        hello = json.loads(ws.recv_text())
        if hello.get("op") != 0:
            return False
        d = hello.get("d", {})

        identify = {"rpcVersion": d.get("rpcVersion", 1),
                    "eventSubscriptions": 0}
        auth_info = d.get("authentication")
        if auth_info:
            identify["authentication"] = _compute_auth(
                password or "", auth_info["salt"], auth_info["challenge"])
        ws.send_text(json.dumps({"op": 1, "d": identify}))

        identified = json.loads(ws.recv_text())
        if identified.get("op") != 2:
            return False

        req_id = base64.b16encode(os.urandom(4)).decode()
        ws.send_text(json.dumps({
            "op": 6,
            "d": {"requestType": "SetCurrentProgramScene",
                 "requestId": req_id,
                 "requestData": {"sceneName": scene_name}},
        }))

        resp = json.loads(ws.recv_text())
        if resp.get("op") != 7:
            return False
        status = resp.get("d", {}).get("requestStatus", {})
        return bool(status.get("result"))
    except Exception:
        return False
    finally:
        try:
            sock.close()
        except Exception:
            pass
