"""Zugriffsprüfung für die Web-Schnittstelle.

Dass die Oberfläche nur die eigenen Sammlungen anzeigt, ist keine
Absicherung — wer die Kennung errät, käme sonst an fremde Daten. Solange
nur die Familie im Heimnetz zugriff, war das verschmerzbar. Sobald
Eingeladene von außen hereinkommen, ist es das nicht mehr.

Darum eine Wache als Mittelschicht, nicht als Prüfung in jeder einzelnen
Route: so gilt sie auch für Routen, die später dazukommen und bei denen
jemand die Prüfung vergisst. Was nicht ausdrücklich erlaubt ist, wird
abgewiesen.

**Im Heimnetz greift sie nicht.** Dort gibt es keine geprüfte Identität,
dort wählt man sein Profil aus einer Liste — das ist gewollt und ändert
sich nicht. Die Wache wirkt nur, wenn Cloudflare Access eine Mailadresse
mitgeschickt hat.

**Der Haken daran, teuer gelernt (14.11.2026):** »keine Mailadresse«
hieß »also Heimnetz, also vertrauenswürdig«. Das stimmt nur, solange vor
JEDEM Weg von außen ein Access steht. Vor der MCP-Adresse stand keines —
dort kann keines stehen, der Konnektor bringt dessen Kopfzeilen nicht
durch. Dieselbe Anlage lieferte unter diesem Namen aber auch die ganze
Oberfläche aus. Anfragen aus dem Internet kamen also ohne Mailadresse an,
galten als Heimnetz, und die Wache sah gar nicht erst hin: Lesen und
Schreiben auf alle Profile und Sammlungen, ohne jedes Merkmal.

Darum wird jetzt umgekehrt geschlossen: Wer über Cloudflare kommt
(erkennbar an `cf-ray`, das die Kante selbst setzt und niemand von außen
entfernen kann) und KEINE geprüfte Identität mitbringt, wird abgewiesen.
Der Weg über den Tunnel ist dann nur noch so weit offen, wie Access ihn
öffnet — unabhängig davon, was in einer Routingtabelle steht.
"""

from __future__ import annotations

import re

from starlette.responses import JSONResponse

import datenbank as dbm
import identitaet
import zugang

# Pfadmuster -> was geprüft wird.
MUSTER = [
    (re.compile(r"^/api/sammlungen/(\d+)"), "sammlung"),
    (re.compile(r"^/api/lexeme/(\d+)"), "lexem"),
    (re.compile(r"^/api/formen/(\d+)"), "form"),
    (re.compile(r"^/api/bedeutungen/(\d+)"), "bedeutung"),
    (re.compile(r"^/api/uebersetzungen/(\d+)"), "uebersetzung"),
    (re.compile(r"^/api/lernziele/(\d+)"), "lernziel"),
    (re.compile(r"^/api/benutzer/(\d+)"), "benutzer"),
    (re.compile(r"^/api/mcp-token/(\d+)"), "mcp_token"),
    # Kamen später dazu und fehlten hier — die Liste wächst nicht von
    # selbst mit. `\d+` trifft dabei nicht /api/uebungen/lernen/…, das
    # sind die Lernwege und die prüfen über sammlung_id.
    (re.compile(r"^/api/uebungen/(\d+)"), "uebung"),
    (re.compile(r"^/api/textaufgaben/(\d+)"), "textaufgabe"),
]

# Diese Pfade sind für alle offen: Stammdaten ohne persönlichen Bezug.
OFFEN = re.compile(r"^/api/(sprachen|merkmale|aufgabentypen|zustand|ich)(/|$)")

SCHREIBEND = {"POST", "PUT", "PATCH", "DELETE"}
LESEND = {"GET", "HEAD", "OPTIONS"}


def _abweisen(grund: str) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": grund})


def _pruefen(db, person: dict, pfad: str, methode: str):
    """Gibt None zurück, wenn es in Ordnung ist, sonst eine Absage."""
    schreibend = methode in SCHREIBEND
    ich = person["id"]

    for muster, art in MUSTER:
        treffer = muster.match(pfad)
        if not treffer:
            continue
        kennung = int(treffer.group(1))
        try:
            if art == "sammlung":
                zugang.sammlung_pruefen(db, ich, kennung, schreibend)
            elif art == "lexem":
                zugang.lexem_pruefen(db, ich, kennung, schreibend)
            elif art == "form":
                zugang.form_pruefen(db, ich, kennung, schreibend)
            elif art == "bedeutung":
                lexem_id = dbm.wert(db, "SELECT lexem_id FROM bedeutung WHERE id = ?",
                                    (kennung,))
                if lexem_id is None:
                    return None            # gibt es nicht — die Route sagt 404
                zugang.lexem_pruefen(db, ich, lexem_id, schreibend)
            elif art == "uebersetzung":
                lexem_id = dbm.wert(db, """SELECT b.lexem_id FROM uebersetzung u
                                            JOIN bedeutung b ON b.id = u.bedeutung_id
                                           WHERE u.id = ?""", (kennung,))
                if lexem_id is None:
                    return None
                zugang.lexem_pruefen(db, ich, lexem_id, schreibend)
            elif art == "lernziel":
                besitzer = dbm.wert(db, "SELECT benutzer_id FROM lernziel WHERE id = ?",
                                    (kennung,))
                if besitzer is not None and besitzer != ich:
                    return _abweisen("Dieses Lernziel gehört dir nicht.")
            elif art == "benutzer":
                if kennung != ich:
                    return _abweisen("Das ist ein fremdes Profil.")
            elif art == "uebung":
                # Eine Übung ist eine Zeile in `text`.
                s = dbm.wert(db, "SELECT sammlung_id FROM text WHERE id = ?",
                             (kennung,))
                if s is None:
                    return None            # gibt es nicht — die Route sagt 404
                zugang.sammlung_pruefen(db, ich, s, schreibend)
            elif art == "textaufgabe":
                s = dbm.wert(db, """SELECT t.sammlung_id FROM textaufgabe ta
                                      JOIN text t ON t.id = ta.text_id
                                     WHERE ta.id = ?""", (kennung,))
                if s is None:
                    return None
                zugang.sammlung_pruefen(db, ich, s, schreibend)
            elif art == "mcp_token":
                besitzer = dbm.wert(db, "SELECT benutzer_id FROM mcp_token WHERE id = ?",
                                    (kennung,))
                if besitzer is not None and besitzer != ich:
                    return _abweisen("Dieses Zugangsmerkmal gehört dir nicht.")
        except zugang.NichtErlaubt as fehler:
            return _abweisen(str(fehler))
        break

    return None


# Setzt die Cloudflare-Kante selbst, bei jeder Anfrage, die sie
# durchreicht. Von außen lässt sie sich nicht entfernen — und gefälscht
# im Heimnetz schadet sie nicht: sie schränkt nur weiter ein.
CLOUDFLARE_KOPFZEILE = "cf-ray"


def _ueber_cloudflare(kopfzeilen) -> bool:
    return bool((kopfzeilen.get(CLOUDFLARE_KOPFZEILE) or "").strip())


def _zahl_aus_anfrage(request, name: str) -> int | None:
    wert = request.query_params.get(name)
    if wert is None:
        return None
    try:
        return int(wert)
    except ValueError:
        return None


async def wache(request, weiter):
    """Mittelschicht. Läuft vor jeder Anfrage."""
    pfad = request.url.path
    if not pfad.startswith("/api/"):
        return await weiter(request)
    methode = request.method
    # OFFEN gilt nur fürs LESEN, und erst NACH der Identitätsprüfung.
    # Vorher stand es ganz vorn und galt für jede Methode — unter
    # /api/sprachen liegen aber zwei schreibende Routen, und deren
    # Verwalterprüfung winkt ohne Identität wortlos durch. Damit war
    # genau der Weg offen, den die Prüfung darunter schließen soll.
    offen = bool(OFFEN.match(pfad)) and methode in LESEND

    db = dbm.verbindung()
    try:
        mail = identitaet.mail_aus_anfrage(request.headers)
        if not mail:
            if _ueber_cloudflare(request.headers):
                if offen:
                    # Stammdaten zum Lesen: die Anmeldeseite muss bis
                    # hierher kommen, sonst kann sie nicht einmal fragen,
                    # wer da ist.
                    return await weiter(request)
                # Sonst: von außen, aber ohne geprüfte Identität. Das ist
                # kein Heimnetz, sondern ein Weg, vor dem kein Access steht.
                return _abweisen(
                    "Von außen geht es nur über die Anmeldung. Diese Adresse "
                    "liefert die Oberfläche nicht aus.")
            # Heimnetz: keine geprüfte Identität, keine Wache.
            return await weiter(request)
        if offen:
            return await weiter(request)
        person = identitaet.profil_fuer_mail(db, mail)
        if person is None:
            return _abweisen("Zu dieser Mailadresse gibt es kein Profil.")

        # Wer von außen kommt, handelt immer als er selbst — ein fremdes
        # benutzer_id in der Abfrage wäre ein Versuch, sich auszugeben.
        verlangt = _zahl_aus_anfrage(request, "benutzer_id")
        if verlangt is not None and verlangt != person["id"]:
            return _abweisen("Du kannst nur im eigenen Namen handeln.")

        # sammlung_id steht bei den Lernwegen im Abfrageteil, nicht im
        # Pfad — dort greift kein MUSTER. Ungeprüft war das der bequemste
        # Weg zu fremden Vokabeln: /api/lernen/naechste?sammlung_id=…
        # gab sie seitenweise heraus, mit Hilfstext.
        gewuenschte = _zahl_aus_anfrage(request, "sammlung_id")
        if gewuenschte is not None:
            try:
                zugang.sammlung_pruefen(db, person["id"], gewuenschte,
                                        methode in SCHREIBEND)
            except zugang.NichtErlaubt as fehler:
                return _abweisen(str(fehler))

        absage = _pruefen(db, dict(person), pfad, methode)
        if absage is not None:
            return absage
    finally:
        db.close()
    return await weiter(request)
