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
]

# Diese Pfade sind für alle offen: Stammdaten ohne persönlichen Bezug.
OFFEN = re.compile(r"^/api/(sprachen|merkmale|aufgabentypen|zustand|ich)(/|$)")

SCHREIBEND = {"POST", "PUT", "PATCH", "DELETE"}


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
            elif art == "mcp_token":
                besitzer = dbm.wert(db, "SELECT benutzer_id FROM mcp_token WHERE id = ?",
                                    (kennung,))
                if besitzer is not None and besitzer != ich:
                    return _abweisen("Dieses Zugangsmerkmal gehört dir nicht.")
        except zugang.NichtErlaubt as fehler:
            return _abweisen(str(fehler))
        break

    return None


def _benutzer_id_aus_anfrage(request) -> int | None:
    wert = request.query_params.get("benutzer_id")
    if wert is None:
        return None
    try:
        return int(wert)
    except ValueError:
        return None


async def wache(request, weiter):
    """Mittelschicht. Läuft vor jeder Anfrage."""
    pfad = request.url.path
    if not pfad.startswith("/api/") or OFFEN.match(pfad):
        return await weiter(request)

    db = dbm.verbindung()
    try:
        mail = identitaet.mail_aus_anfrage(request.headers)
        if not mail:
            # Heimnetz: keine geprüfte Identität, keine Wache.
            return await weiter(request)
        person = identitaet.profil_fuer_mail(db, mail)
        if person is None:
            return _abweisen("Zu dieser Mailadresse gibt es kein Profil.")

        # Wer von außen kommt, handelt immer als er selbst — ein fremdes
        # benutzer_id in der Abfrage wäre ein Versuch, sich auszugeben.
        verlangt = _benutzer_id_aus_anfrage(request)
        if verlangt is not None and verlangt != person["id"]:
            return _abweisen("Du kannst nur im eigenen Namen handeln.")

        absage = _pruefen(db, dict(person), pfad, request.method)
        if absage is not None:
            return absage
    finally:
        db.close()
    return await weiter(request)
