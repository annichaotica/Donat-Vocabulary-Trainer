"""Sperre gegen Durchprobieren.

Nötig geworden, weil die MCP-Schnittstelle von außen erreichbar ist und davor
kein Cloudflare Access mehr stehen kann: der Konnektor in claude.ai lässt nur
eine feste Liste von Headernamen zu, und die Access-Kopfzeilen sind nicht
dabei. Damit trägt das Zugangsmerkmal des Trainers die Last allein.

Ein 256-Bit-Merkmal lässt sich nicht erraten. Die Sperre ist trotzdem
sinnvoll: sie macht Versuche teuer, hält das Protokoll lesbar und fängt den
Fall ab, dass jemand eine Liste geleakter Merkmale durchprobiert.

Bewusst einfach gehalten — im Arbeitsspeicher, nicht in der Datenbank. Nach
einem Neustart ist sie leer, und das ist in Ordnung: sie soll Massen
abwehren, nicht buchhalten.
"""

from __future__ import annotations

import threading
import time

# Nach so vielen Fehlversuchen in FENSTER Sekunden wird gesperrt.
GRENZE = 8
FENSTER = 300.0
SPERRE = 900.0
# Obergrenze, damit die Ablage nicht unbegrenzt wächst.
HOECHSTENS = 5000

_schloss = threading.Lock()
_versuche: dict[str, list] = {}       # Kennung -> [Anzahl, erster, gesperrt_bis]


def _jetzt() -> float:
    return time.monotonic()


def _aufraeumen(jetzt: float) -> None:
    """Alte Einträge wegwerfen. Läuft nur, wenn die Ablage zu groß wird."""
    if len(_versuche) <= HOECHSTENS:
        return
    alt = [k for k, (_n, erster, bis) in _versuche.items()
           if jetzt - erster > FENSTER and jetzt > bis]
    for k in alt:
        _versuche.pop(k, None)
    # Falls das nicht reicht: die ältesten zuerst.
    if len(_versuche) > HOECHSTENS:
        for k in sorted(_versuche, key=lambda k: _versuche[k][1])[:len(_versuche) // 2]:
            _versuche.pop(k, None)


def gesperrt(kennung: str) -> float:
    """Wie viele Sekunden bleibt diese Kennung noch gesperrt? 0 = frei."""
    with _schloss:
        eintrag = _versuche.get(kennung)
        if not eintrag:
            return 0.0
        rest = eintrag[2] - _jetzt()
        return max(0.0, rest)


def fehlversuch(kennung: str) -> float:
    """Einen Fehlversuch vermerken. Gibt die Sperrdauer zurück, falls erreicht."""
    jetzt = _jetzt()
    with _schloss:
        _aufraeumen(jetzt)
        anzahl, erster, bis = _versuche.get(kennung, [0, jetzt, 0.0])
        if jetzt - erster > FENSTER and jetzt > bis:
            anzahl, erster = 0, jetzt           # Fenster abgelaufen
        anzahl += 1
        if anzahl >= GRENZE:
            bis = jetzt + SPERRE
            anzahl, erster = 0, jetzt           # nach der Sperre neu zählen
        _versuche[kennung] = [anzahl, erster, bis]
        return max(0.0, bis - jetzt)


def geschafft(kennung: str) -> None:
    """Gelungener Zugang — der Zähler darf zurück."""
    with _schloss:
        _versuche.pop(kennung, None)


def kennung_aus_anfrage(request) -> str:
    """Wer fragt an? Hinter Cloudflare steht die echte Adresse in
    CF-Connecting-IP; request.client wäre dort immer der Tunnel."""
    for kopf in ("cf-connecting-ip", "x-forwarded-for"):
        wert = request.headers.get(kopf, "")
        if wert:
            return wert.split(",")[0].strip()
    return getattr(getattr(request, "client", None), "host", "") or "unbekannt"


def zuruecksetzen() -> None:
    """Nur für Tests."""
    with _schloss:
        _versuche.clear()
