# Vokabeltrainer — Copyright (C) 2026 Annuschka Brenner
#
# Freie Software unter der GNU Affero General Public License, Fassung 3
# oder später. Herausgegeben in der Hoffnung, dass sie nützt, aber OHNE
# JEDE GEWÄHRLEISTUNG. Siehe die Datei LICENSE.
"""Vokabeltrainer — HTTP-Schnittstelle und Auslieferung der Oberfläche.

Start zur Entwicklung:
    .venv/bin/uvicorn app:app --reload --app-dir backend --port 8030

Im Betrieb läuft dasselbe im Docker-Container auf dem Familienserver.
"""

from __future__ import annotations

import logging
import os
import pathlib
import secrets
import sqlite3
from contextlib import asynccontextmanager
from typing import Iterator

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               RedirectResponse, Response)
from fastapi.staticfiles import StaticFiles

import abtippen
import aufgaben
import einlesen
import drossel
import freigabe as freigabemodul
import datenbank as dbm
import legasthenie
import lernen as lernmodul
import beispielkurs
import lehrgang
import lesetexte
import lernziele
import identitaet
import mcp_dienst
import merkmale as mk
import oauth
import qualitaet
import regeln as regelmodul
import sammelimport
import statistik
import sprachen
import uebung_lernen
import uebungen
import wache
import zugang
from modelle import (RegelEingabe, RegelAendern,
    BedeutungEingabe, BenutzerAendern, BenutzerAnlegen,
                     BewertenEingabe, EingriffEingabe, FormEingabe,
                     LegasthenieEinstellungen, LektionAnlegen,
                     BeispieleSetzen, BuchstandSetzen, ErklaerungSetzen,
                     FassungSichern, ReferenzSetzen,
                     ImportEingabe, LehrgangSetzen, LernwahlSetzen,
                     LesetextAnlegen, WortMerken,
                     LernzielAendern, LernzielAnlegen,
                     SammelimportEingabe,
                     McpTokenAnlegen, OAuthClientAnlegen,
                     AbtippenEingabe,
                     FormAendern, FreigabeEingabe,
                     LexemAendern, LexemEingabe,
                     PruefenEingabe, SammlungAendern, SammlungAnlegen,
                     SammlungEinstellungen, SpracheAnlegen,
                     SprachprofilSetzen, TextPruefenEingabe, ZugriffSetzen,
                     BesitzUebertragen,
                     UebersetzungEingabe, UebungAendern, UebungAntwort,
                     UebungBewertenEingabe, UebungEingabe,
                     UebungPruefenEingabe, UebungenImportEingabe)

OBERFLAECHE = pathlib.Path(__file__).resolve().parent.parent / "frontend"

protokoll = logging.getLogger("vokabeltrainer")


@asynccontextmanager
async def lebenslauf(app: FastAPI):
    db = dbm.verbindung()
    try:
        dbm.einrichten(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Vokabeltrainer", version="0.2.0", lifespan=lebenslauf)

# Die Wache steht VOR allen Routen. Als Mittelschicht und nicht als Prüfung
# in jeder einzelnen Route — so gilt sie auch für Routen, die später
# dazukommen und bei denen jemand die Prüfung vergisst.
app.middleware("http")(wache.wache)


# Erlaubte Kopfzeilen und Verfahren für Anfragen von fremder Herkunft.
# Nur für /mcp — NICHT für /api: dort gibt es im Heimnetz keine Anmeldung,
# und eine beliebige Webseite könnte sonst den Vokabelbestand auslesen,
# sobald jemand im Heimnetz sie öffnet.
MCP_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, DELETE, OPTIONS",
    "Access-Control-Allow-Headers":
        "Authorization, Content-Type, X-Account-Key, X-Vokabel-Token, "
        "Mcp-Session-Id, Mcp-Protocol-Version, Accept",
    "Access-Control-Expose-Headers": "Mcp-Session-Id",
    "Access-Control-Max-Age": "86400",
}


@app.middleware("http")
async def mcp_fremde_herkunft(request: Request, weiter):
    """CORS für die MCP-Schnittstelle.

    Ein Konnektor läuft im Browser und schickt vor dem eigentlichen Aufruf
    eine Vorabanfrage (OPTIONS). Misslingt die, kommt die Anfrage nie
    zustande — und der Client meldet nur "nicht erreichbar", ohne Grund.

    `Allow-Origin: *` ist hier unbedenklich, weil die Anmeldung über eine
    Kopfzeile läuft und nicht über ein Sitzungsplätzchen: eine fremde Seite
    kennt das Zugangsmerkmal nicht und kann es auch nicht nebenbei
    mitschicken lassen. Für /api gilt das NICHT, darum bleibt es dort aus.
    """
    if not request.url.path.startswith("/mcp"):
        return await weiter(request)
    if request.method == "OPTIONS":
        # Die Vorabanfrage trägt nie Anmeldedaten — sie darf nicht an der
        # Zugangsprüfung scheitern.
        return Response(status_code=204, headers=MCP_CORS)
    antwort = await weiter(request)
    antwort.headers.update(MCP_CORS)
    return antwort


@app.middleware("http")
async def frische_oberflaeche(request: Request, weiter):
    """Oberflächendateien immer gegenprüfen lassen.

    Ohne das hält der Browser die ES-Module fest, und nach jeder
    Aktualisierung sähe man tagelang die alte Fassung — ohne Hinweis, dass
    etwas veraltet ist. Ein Bauschritt mit Versionsnummern im Dateinamen
    wäre die andere Lösung; den will dieses Projekt bewusst nicht.

    `no-cache` heißt NICHT "nicht speichern", sondern "vor der Benutzung
    nachfragen". Mit dem ETag antwortet der Server dann meist mit 304 und
    schickt gar nichts — es kostet eine Rückfrage, keine Übertragung.
    """
    antwort = await weiter(request)
    pfad = request.url.path
    if (pfad.startswith(("/js/", "/css/")) or pfad in ("/", "/index.html")
            or pfad.endswith(".webmanifest")):
        antwort.headers["Cache-Control"] = "no-cache"
    return antwort


def datenbank() -> Iterator[sqlite3.Connection]:
    db = dbm.verbindung()
    try:
        # Profilüberschreibungen bei jeder Anfrage neu einlesen. Ändert ein
        # Agent am MCP ein Sprachprofil, gilt das sofort.
        dbm.sprachprofile_laden(db)
        yield db
    finally:
        db.close()


DB = Depends(datenbank)


def _wache_rumpf(db: sqlite3.Connection, request: Request | None,
                 sammlung_id: int | None = None, benutzer_id: int | None = None,
                 verwalter: bool = False, aufgabe_id: int | None = None,
                 textaufgabe_id: int | None = None,
                 schreiben: bool = True) -> None:
    """Prüfung für Angaben, die im Rumpf stehen — die sieht die Wache nicht.

    Greift wie die Wache nur bei geprüfter Identität von außen. `request` darf
    None sein: dann kommt der Aufruf aus dem MCP-Dienst, der seine eigene,
    strengere Prüfung schon gemacht hat.

    `aufgabe_id` und `textaufgabe_id` werden über ihr Wort beziehungsweise
    ihren Text zur Sammlung aufgelöst. Ohne das war das Hochzählen dieser
    Kennung der bequemste Weg zum gesamten Bestand aller Personen: die
    Lernwege nennen keine Sammlung im Pfad, also griff kein Muster.
    """
    if request is None:
        return
    mail = identitaet.mail_aus_anfrage(request.headers)
    if not mail:
        return
    person = identitaet.profil_fuer_mail(db, mail)
    if person is None:
        raise HTTPException(403, "Zu dieser Mailadresse gibt es kein Profil.")
    if aufgabe_id is not None:
        sammlung_id = dbm.wert(db, """SELECT l.sammlung_id FROM aufgabe a
                                        JOIN lexem l ON l.id = a.lexem_id
                                       WHERE a.id = ?""", (aufgabe_id,))
        if sammlung_id is None:
            raise HTTPException(404, f"Aufgabe {aufgabe_id} gibt es nicht")
    if textaufgabe_id is not None:
        sammlung_id = dbm.wert(db, """SELECT t.sammlung_id FROM textaufgabe ta
                                        JOIN text t ON t.id = ta.text_id
                                       WHERE ta.id = ?""", (textaufgabe_id,))
        if sammlung_id is None:
            raise HTTPException(404, f"Textaufgabe {textaufgabe_id} gibt es nicht")
    try:
        if sammlung_id is not None:
            zugang.sammlung_pruefen(db, person["id"], sammlung_id,
                                    schreiben=schreiben)
        if benutzer_id is not None and benutzer_id != person["id"]:
            raise zugang.NichtErlaubt("Du kannst nur im eigenen Namen handeln.")
        if verwalter:
            zugang.verwalter_pruefen(dict(person))
    except zugang.NichtErlaubt as fehler:
        raise HTTPException(403, str(fehler)) from fehler


def _holen(db: sqlite3.Connection, tabelle: str, id_: int) -> dict:
    z = dbm.zeile(db, f"SELECT * FROM {tabelle} WHERE id = ?", (id_,))
    if z is None:
        raise HTTPException(404, f"{tabelle} {id_} gibt es nicht")
    return z


# ============================================================ Sprachen

@app.get("/api/sprachen")
def sprachen_liste(db: sqlite3.Connection = DB):
    liste = []
    for z in dbm.zeilen(db, """SELECT code, name, schrift, stimme FROM sprache
                                ORDER BY name"""):
        p = sprachen.profil(z["code"])
        liste.append({**z,
                      "hat_formgruppen": bool(p.get("formgruppen")),
                      # Zeichen, die auf einer deutschen Tastatur mühsam sind.
                      # Die Leiste unter dem Antwortfeld erspart meist den
                      # Layoutwechsel.
                      "sonderzeichen": p.get("sonderzeichen", []),
                      # Bei nichtlateinischer Schrift hilft keine Leiste —
                      # dort tippt man ganze Wörter und braucht ein Layout.
                      "tastatur_empfohlen": sprachen.tastatur_empfohlen(z["code"])})
    return liste


@app.post("/api/sprachen", status_code=201)
def sprache_anlegen(eingabe: SpracheAnlegen, request: Request = None,
                    db: sqlite3.Connection = DB):
    """Eine neue Sprache einrichten, samt Profil.

    Für Sprachen, die noch kein Profil im Code haben. Das Profil bestimmt,
    welche Formgruppen es gibt und wie Antworten geprüft werden.
    """
    _wache_rumpf(db, request, verwalter=True)
    if dbm.wert(db, "SELECT 1 FROM sprache WHERE code = ?", (eingabe.code,)):
        raise HTTPException(409, f"Die Sprache {eingabe.code!r} gibt es schon. "
                                 f"Zum Ändern: PUT /api/sprachen/{eingabe.code}/profil")
    try:
        sprachen.pruefen_profil(eingabe.profil)
    except sprachen.ProfilFehler as fehler:
        raise HTTPException(400, str(fehler))
    db.execute("""INSERT INTO sprache (code, name, schrift, stimme, profil)
                  VALUES (?, ?, ?, ?, ?)""",
               (eingabe.code, eingabe.name, eingabe.schrift, eingabe.stimme,
                dbm.j_schreiben(eingabe.profil)))
    dbm.sprachprofile_laden(db)
    return sprachprofil_lesen(eingabe.code, db)


@app.get("/api/sprachen/{code}/profil")
def sprachprofil_lesen(code: str, db: sqlite3.Connection = DB):
    """Das wirksame Profil — Code plus Überschreibungen aus der Datenbank."""
    zeile = dbm.zeile(db, "SELECT * FROM sprache WHERE code = ?", (code,))
    if zeile is None:
        raise HTTPException(404, f"Die Sprache {code!r} ist nicht eingetragen")
    dbm.sprachprofile_laden(db)
    wirksam = sprachen.profil(code)
    return {
        "code": code,
        "name": zeile["name"],
        "schrift": zeile["schrift"],
        "stimme": zeile["stimme"],
        "im_code_hinterlegt": code in sprachen.PROFILE,
        "eigene_ueberschreibungen": dbm.j_lesen(zeile["profil"]),
        "wirksames_profil": wirksam,
        "erlaubte_schluessel": sorted(sprachen.ERLAUBTE_SCHLUESSEL),
    }


@app.put("/api/sprachen/{code}/profil")
def sprachprofil_setzen(code: str, eingabe: SprachprofilSetzen,
                        request: Request = None, db: sqlite3.Connection = DB):
    """Das Profil einer Sprache anpassen.

    Hiermit kann ein Agent am MCP eine Sprache zum Laufen bringen, ohne dass
    jemand Code ändert: Formgruppen hinzufügen, Prüfregeln justieren, Artikel
    eintragen. Was nicht übergeben wird, bleibt wie es war.

    Danach werden die Aufgaben aller betroffenen Sammlungen neu gerechnet —
    sonst zeigte die Oberfläche neue Formgruppen an, zu denen es keine
    Aufgaben gäbe.
    """
    _wache_rumpf(db, request, verwalter=True)
    zeile = dbm.zeile(db, "SELECT * FROM sprache WHERE code = ?", (code,))
    if zeile is None:
        raise HTTPException(404, f"Die Sprache {code!r} ist nicht eingetragen")
    try:
        sprachen.pruefen_profil(eingabe.profil)
    except sprachen.ProfilFehler as fehler:
        raise HTTPException(400, str(fehler))

    alt = dbm.j_lesen(zeile["profil"])
    neu = {**alt, **eingabe.profil}
    try:
        sprachen.pruefen_profil(neu)
    except sprachen.ProfilFehler as fehler:
        raise HTTPException(400, f"Zusammen mit dem Bestehenden nicht gültig: {fehler}")
    db.execute("UPDATE sprache SET profil = ? WHERE code = ?",
               (dbm.j_schreiben(neu), code))
    if "name" in eingabe.profil:
        db.execute("UPDATE sprache SET name = ? WHERE code = ?",
                   (eingabe.profil["name"], code))
    if "stimme" in eingabe.profil:
        db.execute("UPDATE sprache SET stimme = ? WHERE code = ?",
                   (eingabe.profil["stimme"], code))
    dbm.sprachprofile_laden(db)

    bilanz = {"sammlungen": 0, "angelegt": 0, "reaktiviert": 0, "abgeschaltet": 0}
    if eingabe.neu_rechnen:
        for s in dbm.zeilen(db, "SELECT id FROM sammlung WHERE sprache = ?", (code,)):
            teil = aufgaben.erzeugen_fuer_sammlung(db, s["id"])
            bilanz["sammlungen"] += 1
            for k in ("angelegt", "reaktiviert", "abgeschaltet"):
                bilanz[k] += teil[k]
    return {"profil": sprachprofil_lesen(code, db), "aufgaben": bilanz}


@app.get("/api/sprachen/{code}/formgruppen")
def formgruppen_liste(code: str):
    """Alle Formgruppen einer Sprache, nach Wortart — für die Auswahl,
    welche Zeiten eine Sammlung abfragt."""
    p = sprachen.profil(code)
    return {
        "sprache": p["name"],
        "wortarten": {
            # erklaerung und beispiel kommen mit: in der Auswahl, WAS
            # abgefragt werden soll, muss man verstehen können, was man da
            # anhakt. "Υποτακτική" sagt dem Lernenden nichts, "Möglichkeit
            # oder Wunsch — dass ich gehe" schon.
            wortart: [{"kennung": g["kennung"], "name": g["name"],
                       "kurz": g["kurz"], "zellen": len(g["zellen"]),
                       "erklaerung": mk.beschriften(g["merkmale"],
                                                    stil="einfach"),
                       # Nur aus den Merkmalen der GRUPPE, nicht aus ihrer
                       # ersten Zelle: sonst erklärte jede griechische Zeit
                       # mit "ich gehe", weil die 1. Person vorne steht.
                       "beispiel": mk.beispiel(g["merkmale"])}
                      for g in gruppen]
            for wortart, gruppen in p.get("formgruppen", {}).items()
        },
        "standard": sprachen.formgruppen_standard(code),
        "stammformen": p.get("stammformen", []),
        "lexemmerkmale": p.get("lexemmerkmale", {}),
        # Wie die Abfrage danach fragt. Dient zugleich als Beschriftung
        # beim Berichtigen: »Ablautreihe« statt »klasse«.
        "lexemmerkmale_fragen": p.get("lexemmerkmale_fragen", {}),
    }


@app.get("/api/sprachen/{code}/formgruppen/{kennung}/zellen")
def formgruppe_zellen(code: str, kennung: str):
    """Die Zellen einer Formgruppe, jede mit Merkmalsbündel und Beschriftung.

    Daraus baut die Eingabemaske ihre Felder: eine Zeile je Zelle, benannt wie
    im Lehrbuch ("Présent, 1. Person Singular").
    """
    gruppe = sprachen.formgruppe(code, kennung)
    if gruppe is None:
        raise HTTPException(404, f"Formgruppe {kennung!r} gibt es in {code!r} nicht")
    wortart = next(
        (w for w, gruppen in sprachen.profil(code).get("formgruppen", {}).items()
         if any(g["kennung"] == kennung for g in gruppen)), "sonstiges")
    return [{"merkmale": zelle,
             "beschriftung": sprachen.beschriften_form(code, wortart, zelle),
             "kurz": sprachen.beschriften_form(code, wortart, zelle, kurz=True)}
            for zelle in gruppe["zellen"]]


@app.get("/api/merkmale")
def merkmale_inventar():
    return {"inventar": {d: {w: {"lang": t[0], "kurz": t[1]}
                             for w, t in werte.items()}
                         for d, werte in mk.INVENTAR.items()},
            "reihenfolge": list(mk.REIHENFOLGE),
            "wortarten": mk.WORTARTEN}


@app.get("/api/aufgabentypen")
def aufgabentypen():
    return {"typen": aufgaben.TYPEN, "standard": aufgaben.TYPEN_STANDARD}


# ============================================================ Benutzer

@app.get("/api/benutzer")
def benutzer_liste(db: sqlite3.Connection = DB):
    return dbm.zeilen(db, """SELECT id, name, farbe, verwalter, angelegt,
                                    (email IS NOT NULL) AS hat_mail
                               FROM benutzer ORDER BY name""")


@app.get("/api/benutzer/{benutzer_id}")
def benutzer_lesen(benutzer_id: int, db: sqlite3.Connection = DB):
    """Ein einzelnes Profil, mit Mailadresse.

    Die Liste zeigt nur, OB eine Adresse gebunden ist. Hier steht sie —
    und die Wache lässt von außen nur das eigene Profil durch.
    """
    b = _holen(db, "benutzer", benutzer_id)
    return {"id": b["id"], "name": b["name"], "farbe": b["farbe"],
            "verwalter": b["verwalter"], "angelegt": b["angelegt"],
            "email": b["email"]}


@app.post("/api/benutzer", status_code=201)
def benutzer_anlegen(eingabe: BenutzerAnlegen, request: Request,
                     db: sqlite3.Connection = DB):
    # Von außen entstehen Profile ausschließlich über Access: wer in
    # der Zugriffsregel steht, bekommt beim ersten Anmelden eines
    # (identitaet.profil_fuer_mail). Von Hand angelegte Profile hätten
    # dort niemanden hinter sich — sie würden nur die Auswahlliste im
    # Heimnetz zumüllen.
    if identitaet.mail_aus_anfrage(request.headers):
        raise HTTPException(403, "Profile legt das Heimnetz an. Von außen "
                                 "entsteht eines beim ersten Anmelden.")
    erster = not dbm.wert(db, "SELECT 1 FROM benutzer LIMIT 1")
    try:
        cur = db.execute("""INSERT INTO benutzer (name, farbe, verwalter)
                            VALUES (?, ?, ?)""",
                         (eingabe.name, eingabe.farbe, int(erster)))
    except sqlite3.IntegrityError:
        raise HTTPException(409, f"Es gibt schon ein Profil namens {eingabe.name!r}")
    return _holen(db, "benutzer", cur.lastrowid)


def _mail_binden(db: sqlite3.Connection, benutzer_id: int, mail: str) -> None:
    """Bindet eine Mailadresse an ein Profil — der Zugang von außen.

    Ohne diese Bindung legt die erste Anmeldung über Access ein NEUES
    Profil an (so steht es in identitaet.py, und das ist dort richtig:
    wer durch Access kommt, ist eingeladen). Wer schon ein Profil mit
    Lernstand hat, bekommt dadurch aber ein zweites, leeres — genau das
    ist hier passiert. Die Adresse vorher einzutragen verhindert es.

    Hält ein anderes Profil diese Adresse schon, gibt es zwei Fälle. Ist
    es leer, war es so ein versehentlich angelegtes: es wird abgeräumt
    und die Adresse wandert herüber. Hat es Lernstand, wird abgelehnt —
    zwei Bestände zusammenzuführen ist nichts, was nebenbei und ohne
    Rückfrage geschehen darf.
    """
    mail = mail.strip().lower()
    if not mail:
        db.execute("UPDATE benutzer SET email = NULL WHERE id = ?",
                   (benutzer_id,))
        return
    if not identitaet._MAIL.match(mail):
        raise HTTPException(400, f"{mail!r} sieht nicht wie eine Mailadresse aus")
    anderer = dbm.zeile(db, "SELECT * FROM benutzer WHERE email = ? AND id != ?",
                        (mail, benutzer_id))
    if anderer is not None:
        spuren = {
            "Lernstand": "SELECT COUNT(*) FROM lernzustand WHERE benutzer_id = ?",
            "Übungsstand": "SELECT COUNT(*) FROM textlernzustand WHERE benutzer_id = ?",
            "Sammlungen": "SELECT COUNT(*) FROM sammlung WHERE besitzer_id = ?",
            "Lernziele": "SELECT COUNT(*) FROM lernziel WHERE benutzer_id = ?",
            "Zugänge": "SELECT COUNT(*) FROM mcp_token WHERE benutzer_id = ?",
        }
        hat = {name: (dbm.wert(db, sql, (anderer["id"],)) or 0)
               for name, sql in spuren.items()}
        if any(hat.values()):
            was = ", ".join(f"{n}: {z}" for n, z in hat.items() if z)
            raise HTTPException(409,
                f"Das Profil {anderer['name']!r} hat diese Adresse und ist "
                f"nicht leer ({was}). Zusammenführen geht nicht nebenbei — "
                f"erst dort aufräumen oder die Adresse dort entfernen.")
        db.execute("DELETE FROM benutzer WHERE id = ?", (anderer["id"],))
    db.execute("UPDATE benutzer SET email = ? WHERE id = ?", (mail, benutzer_id))


@app.patch("/api/benutzer/{benutzer_id}")
def benutzer_aendern(benutzer_id: int, eingabe: BenutzerAendern,
                     db: sqlite3.Connection = DB):
    b = _holen(db, "benutzer", benutzer_id)
    if eingabe.name is not None:
        db.execute("UPDATE benutzer SET name = ? WHERE id = ?", (eingabe.name, benutzer_id))
    if eingabe.farbe is not None:
        db.execute("UPDATE benutzer SET farbe = ? WHERE id = ?", (eingabe.farbe, benutzer_id))
    if eingabe.email is not None:
        _mail_binden(db, benutzer_id, eingabe.email)
    e = dbm.j_lesen(b["einstellungen"])
    if eingabe.wunschretention is not None:
        e["wunschretention"] = eingabe.wunschretention
    if eingabe.neu_je_sitzung is not None:
        e["neu_je_sitzung"] = eingabe.neu_je_sitzung
    if eingabe.fragen_je_tag is not None:
        e["fragen_je_tag"] = eingabe.fragen_je_tag
    if eingabe.neues_einstreuen is not None:
        e["neues_einstreuen"] = eingabe.neues_einstreuen
    if eingabe.beschriftung is not None:
        e["beschriftung"] = eingabe.beschriftung
    if eingabe.tastatur_umschrift is not None:
        e["tastatur_umschrift"] = eingabe.tastatur_umschrift
    db.execute("UPDATE benutzer SET einstellungen = ? WHERE id = ?",
               (dbm.j_schreiben(e), benutzer_id))
    return _holen(db, "benutzer", benutzer_id)


@app.get("/api/benutzer/{benutzer_id}/legasthenie")
def legasthenie_lesen(benutzer_id: int, db: sqlite3.Connection = DB):
    _holen(db, "benutzer", benutzer_id)
    return lernmodul.benutzer_einstellungen(db, benutzer_id)["legasthenie"]


@app.put("/api/benutzer/{benutzer_id}/legasthenie")
def legasthenie_setzen(benutzer_id: int, eingabe: LegasthenieEinstellungen,
                       db: sqlite3.Connection = DB):
    """Legastheniemodus einstellen.

    Zur Lesbarkeit: der vergrößerte Zeichenabstand ist die am besten belegte
    Maßnahme und darum voreingestellt. Die eigens entworfenen Schriftarten
    sind nur ein Angebot — kontrollierte Vergleiche finden gegenüber einer
    schlichten Grotesk meist keinen Vorteil.
    """
    b = _holen(db, "benutzer", benutzer_id)
    e = dbm.j_lesen(b["einstellungen"])
    lg = {**legasthenie.VOREINSTELLUNG, **(e.get("legasthenie") or {})}
    for feld, wert in eingabe.model_dump(exclude_none=True).items():
        lg[feld] = wert
    e["legasthenie"] = lg
    db.execute("UPDATE benutzer SET einstellungen = ? WHERE id = ?",
               (dbm.j_schreiben(e), benutzer_id))
    return lg


@app.get("/api/benutzer/{benutzer_id}/einstellungen")
def benutzer_einstellungen(benutzer_id: int, db: sqlite3.Connection = DB):
    _holen(db, "benutzer", benutzer_id)
    return lernmodul.benutzer_einstellungen(db, benutzer_id)


# ============================================================ Sammlungen

# Die Farben, die eine Sammlung ohne eigene Wahl bekommt.
#
# Sie sind Information, keine Verzierung: dieselbe Farbe steht an der
# Kartenkante, in den Einstellungen und überall, wo die Sammlung
# vorkommt. Wer drei Sprachen lernt, erkennt am Rand, worin er steckt.
#
# Gewählt nach zwei Bedingungen: untereinander gut zu unterscheiden,
# und auf hellem wie dunklem Grund lesbar. Darum mittlere Sättigung —
# ein reines Rot wäre im Dunkelmodus eine Lampe.
PALETTE = ["#35558a", "#2a6a4a", "#8a4a2a", "#5a3a7a",
           "#1f6f78", "#8a3a5a", "#6a5a1f", "#3a5a8a"]


def _farbe(sammlung: dict) -> str:
    """Die wirksame Farbe: die gewählte, sonst eine aus der Kennung.

    Abgeleitet statt beim Anlegen gewürfelt: so hat auch jede
    bestehende Sammlung sofort eine, ohne Wanderung, und dieselbe
    Sammlung bekommt überall dieselbe.
    """
    return sammlung.get("farbe") or PALETTE[(sammlung["id"] or 0) % len(PALETTE)]


@app.get("/api/sammlungen")
def sammlungen_liste(request: Request = None, benutzer_id: int | None = None,
                     db: sqlite3.Connection = DB):
    if benutzer_id is None:
        # Im Heimnetz die ganze Liste — dort wählt man sein Profil erst
        # danach. Von außen steht die Person schon fest, und dann ist
        # "alle Sammlungen" die Kennungsliste fremder Bestände.
        mail = (identitaet.mail_aus_anfrage(request.headers)
                if request is not None else None)
        if mail:
            person = identitaet.profil_fuer_mail(db, mail)
            if person is None:
                raise HTTPException(403, "Zu dieser Mailadresse gibt es "
                                         "kein Profil.")
            benutzer_id = person["id"]
        else:
            return dbm.zeilen(db, "SELECT * FROM sammlung ORDER BY name")
    reihen = dbm.zeilen(db, """
        SELECT s.*, (s.besitzer_id = ?) AS eigen,
               -- Sichtbar heißt nicht gelernt: eine Freigabe zum
               -- Mitpflegen soll die fremden Wörter nicht in die
               -- allgemeine Abfrage mischen. Vorgabe ist der Besitz,
               -- `lernwahl` trägt nur die Abweichungen.
               COALESCE((SELECT w.lernen FROM lernwahl w
                          WHERE w.sammlung_id = s.id AND w.benutzer_id = ?),
                        s.besitzer_id = ?) AS lerne_ich,
               -- Hier mit, nicht in einem eigenen Aufruf je Karte: die
               -- Übersicht soll nicht nach Sammlungszahl langsamer
               -- werden. Dieselbe Entscheidung wie bei den offenen
               -- Formen eine Zeile weiter unten.
               (SELECT b.bis_lektion FROM buchstand b
                 WHERE b.sammlung_id = s.id AND b.benutzer_id = ?)
                 AS bis_lektion,
               -- Wann zuletzt etwas aus dieser Sammlung beantwortet
               -- wurde. Nur zum Sortieren der Übersicht; eine Zahl,
               -- die sonst nirgends vorkommt, kann auch nirgends
               -- widersprechen.
               (SELECT MAX(w.zeitpunkt) FROM wiederholung w
                  JOIN aufgabe a ON a.id = w.aufgabe_id
                  JOIN lexem l2 ON l2.id = a.lexem_id
                 WHERE l2.sammlung_id = s.id AND w.benutzer_id = ?)
                 AS zuletzt_gelernt,
               (SELECT COUNT(*) FROM lektion k WHERE k.sammlung_id = s.id)
                 AS lektionen,
               (SELECT COUNT(*) FROM lexem l WHERE l.sammlung_id = s.id) AS lexeme,
               -- Hier mit, nicht in einem eigenen Aufruf: die Übersicht
               -- soll nicht je Sammlung einen Rundlauf brauchen, nur um
               -- den Freigabeknopf zeigen zu können.
               (SELECT COUNT(*) FROM form f JOIN lexem l ON l.id = f.lexem_id
                 WHERE l.sammlung_id = s.id AND f.geprueft = 0) AS offene_formen,
               -- Übungen und Regeln zählen hier mit, sonst bleibt der
               -- Freigabeknopf unsichtbar, solange nur sie warten. Genau
               -- das ist beim ersten Eintragen einer Regel passiert: sie
               -- lag in der Freigabe, aber kein Weg führte hin.
               (SELECT COUNT(*) FROM text t
                 WHERE t.sammlung_id = s.id AND t.geprueft = 0) AS offene_uebungen,
               (SELECT COUNT(*) FROM regel r
                 WHERE r.sammlung_id = s.id AND r.geprueft = 0) AS offene_regeln
          FROM sammlung s
         WHERE s.besitzer_id = ?
            OR s.id IN (SELECT sammlung_id FROM freigabe WHERE benutzer_id = ?)
         ORDER BY s.name""", (benutzer_id, benutzer_id, benutzer_id,
                               benutzer_id, benutzer_id, benutzer_id,
                               benutzer_id))
    for z in reihen:
        z["farbe_wirksam"] = _farbe(z)
    return reihen


@app.post("/api/sammlungen", status_code=201)
def sammlung_anlegen(eingabe: SammlungAnlegen, request: Request = None,
                     db: sqlite3.Connection = DB):
    _wache_rumpf(db, request, benutzer_id=eingabe.besitzer_id)
    _holen(db, "benutzer", eingabe.besitzer_id)
    if not dbm.wert(db, "SELECT 1 FROM sprache WHERE code = ?", (eingabe.sprache,)):
        raise HTTPException(400, f"Sprache {eingabe.sprache!r} ist nicht eingetragen")
    cur = db.execute("""INSERT INTO sammlung
                          (besitzer_id, name, sprache, grundsprache, beschreibung)
                        VALUES (?, ?, ?, ?, ?)""",
                     (eingabe.besitzer_id, eingabe.name, eingabe.sprache,
                      eingabe.grundsprache, eingabe.beschreibung))
    return _holen(db, "sammlung", cur.lastrowid)


@app.patch("/api/sammlungen/{sammlung_id}")
def sammlung_aendern(sammlung_id: int, eingabe: SammlungAendern,
                     db: sqlite3.Connection = DB):
    _holen(db, "sammlung", sammlung_id)
    if eingabe.name is not None:
        db.execute("UPDATE sammlung SET name = ? WHERE id = ?", (eingabe.name, sammlung_id))
    if eingabe.beschreibung is not None:
        db.execute("UPDATE sammlung SET beschreibung = ? WHERE id = ?",
                   (eingabe.beschreibung, sammlung_id))
    return _holen(db, "sammlung", sammlung_id)


@app.delete("/api/sammlungen/{sammlung_id}", status_code=204)
def sammlung_loeschen(sammlung_id: int, db: sqlite3.Connection = DB):
    _holen(db, "sammlung", sammlung_id)
    db.execute("DELETE FROM sammlung WHERE id = ?", (sammlung_id,))


# ------------------------------------------------- Wer darf mitlernen
#
# Nicht zu verwechseln mit der Freigabe von FORMEN. Hier geht es um
# Menschen: wer eine Sammlung benutzen darf und wer sie pflegen darf.
#
# Der Lernstand hängt an der Person, nicht an der Sammlung. Wer eine
# Sammlung mitbenutzt, fängt mit seinem eigenen Fortschritt an — das ist
# der Sinn der Sache: die Mutter pflegt die Vokabeln, das Kind lernt sie.

@app.get("/api/sammlungen/{sammlung_id}/zugriff")
def zugriff_lesen(sammlung_id: int, db: sqlite3.Connection = DB):
    """Wem gehört die Sammlung, und wer darf mit?"""
    s = _holen(db, "sammlung", sammlung_id)
    return {
        "sammlung_id": sammlung_id,
        "besitzer": dbm.zeile(db, "SELECT id, name, farbe FROM benutzer WHERE id = ?",
                              (s["besitzer_id"],)),
        "mitlernende": dbm.zeilen(db, """
            SELECT b.id, b.name, b.farbe, f.recht
              FROM freigabe f JOIN benutzer b ON b.id = f.benutzer_id
             WHERE f.sammlung_id = ?
             ORDER BY b.name""", (sammlung_id,)),
    }


@app.put("/api/sammlungen/{sammlung_id}/zugriff")
def zugriff_setzen(sammlung_id: int, eingabe: ZugriffSetzen,
                   request: Request = None, db: sqlite3.Connection = DB):
    """Gibt einer Person Zugriff oder nimmt ihn zurück.

    `recht`: "lesen" (hineinsehen), "schreiben" (auch pflegen) oder null
    (Zugriff entziehen).

    Zugriff heißt NICHT, dass die Sammlung mitgelernt wird — das sagt
    die Lernwahl (`PUT …/lernwahl`), und die steht voreingestellt auf
    »nein« für fremde Sammlungen. Hier stand einmal »lesen
    (mitlernen)«, und genau daran lag es, dass ein fremdes
    Französisch zwischen den griechischen Wörtern auftauchte.
    """
    _wache_rumpf(db, request, sammlung_id=sammlung_id)
    s = _holen(db, "sammlung", sammlung_id)
    _holen(db, "benutzer", eingabe.benutzer_id)
    if eingabe.benutzer_id == s["besitzer_id"]:
        raise HTTPException(
            400, "Der Besitzerin muss man nichts freigeben — sie darf ohnehin "
                 "alles. Zum Weitergeben den Besitz übertragen.")
    if eingabe.recht is None:
        db.execute("DELETE FROM freigabe WHERE sammlung_id = ? AND benutzer_id = ?",
                   (sammlung_id, eingabe.benutzer_id))
    else:
        db.execute("""INSERT INTO freigabe (sammlung_id, benutzer_id, recht)
                      VALUES (?, ?, ?)
                      ON CONFLICT(sammlung_id, benutzer_id)
                      DO UPDATE SET recht = excluded.recht""",
                   (sammlung_id, eingabe.benutzer_id, eingabe.recht))
    return zugriff_lesen(sammlung_id, db)


@app.put("/api/sammlungen/{sammlung_id}/lernwahl")
def lernwahl_setzen(sammlung_id: int, eingabe: LernwahlSetzen,
                    request: Request = None, db: sqlite3.Connection = DB):
    """Lerne ich diese Sammlung aktiv, oder sehe ich sie nur?

    Betrifft nur die Abfrage OHNE gewählte Sammlung und ohne Lernziel —
    wer eine Sammlung ausdrücklich aufruft, bekommt sie weiterhin. Der
    Lernstand bleibt unangetastet: wer wieder einschaltet, macht da
    weiter, wo er aufgehört hat.
    """
    _wache_rumpf(db, request, benutzer_id=eingabe.benutzer_id,
                 sammlung_id=sammlung_id)
    _holen(db, "sammlung", sammlung_id)
    _holen(db, "benutzer", eingabe.benutzer_id)
    sichtbar = lernmodul.sichtbare_sammlungen(db, eingabe.benutzer_id)
    if sammlung_id not in sichtbar:
        raise HTTPException(403, "Diese Sammlung ist für dich nicht sichtbar.")
    lernmodul.lernwahl_setzen(db, eingabe.benutzer_id, sammlung_id,
                              eingabe.lernen)
    return {"sammlung_id": sammlung_id, "lernen": bool(eingabe.lernen)}


@app.post("/api/sammlungen/{sammlung_id}/besitz")
def besitz_uebertragen(sammlung_id: int, eingabe: BesitzUebertragen,
                       request: Request = None, db: sqlite3.Connection = DB):
    """Überträgt die Sammlung an eine andere Person.

    Die bisherige Besitzerin behält auf Wunsch Schreibzugriff — sonst
    könnte sie die Vokabeln, die sie pflegt, hinterher nicht mehr ändern.
    Der Lernstand bleibt bei allen, wie er ist: er hängt an der Person.
    """
    _wache_rumpf(db, request, sammlung_id=sammlung_id)
    s = _holen(db, "sammlung", sammlung_id)
    neu = _holen(db, "benutzer", eingabe.benutzer_id)
    if neu["id"] == s["besitzer_id"]:
        raise HTTPException(400, f"{neu['name']} ist schon Besitzerin.")
    bisher = s["besitzer_id"]
    db.execute("UPDATE sammlung SET besitzer_id = ? WHERE id = ?",
               (neu["id"], sammlung_id))
    # Die neue Besitzerin braucht keine Freigabe mehr.
    db.execute("DELETE FROM freigabe WHERE sammlung_id = ? AND benutzer_id = ?",
               (sammlung_id, neu["id"]))
    if eingabe.bisherige_behaelt_zugriff:
        db.execute("""INSERT INTO freigabe (sammlung_id, benutzer_id, recht)
                      VALUES (?, ?, 'schreiben')
                      ON CONFLICT(sammlung_id, benutzer_id)
                      DO UPDATE SET recht = 'schreiben'""",
                   (sammlung_id, bisher))
    return zugriff_lesen(sammlung_id, db)


@app.get("/api/sammlungen/{sammlung_id}/einstellungen")
def sammlung_einstellungen_lesen(sammlung_id: int, db: sqlite3.Connection = DB):
    _holen(db, "sammlung", sammlung_id)
    e = aufgaben.sammlung_einstellungen(db, sammlung_id)
    e.pop("sammlung", None)
    return e


@app.put("/api/sammlungen/{sammlung_id}/einstellungen")
def sammlung_einstellungen_setzen(sammlung_id: int, eingabe: SammlungEinstellungen,
                                  db: sqlite3.Connection = DB):
    """Einstellungen ändern und die Aufgaben der Sammlung neu durchrechnen.

    Abgewählte Formgruppen werden abgeschaltet, nicht gelöscht — wer das
    Plus-que-parfait später wieder zuschaltet, findet seinen Lernstand vor.
    """
    s = _holen(db, "sammlung", sammlung_id)
    alt = dbm.j_lesen(s["einstellungen"])
    neu = dict(alt)
    for feld in ("formgruppen", "typen", "ungeprueft_abfragen"):
        wert = getattr(eingabe, feld)
        if wert is not None:
            neu[feld] = wert
    unbekannt = set(neu.get("typen") or []) - set(aufgaben.TYPEN)
    if unbekannt:
        raise HTTPException(400, f"Unbekannte Aufgabentypen: {sorted(unbekannt)}")
    db.execute("UPDATE sammlung SET einstellungen = ? WHERE id = ?",
               (dbm.j_schreiben(neu), sammlung_id))
    bilanz = aufgaben.erzeugen_fuer_sammlung(db, sammlung_id)
    return {"einstellungen": sammlung_einstellungen_lesen(sammlung_id, db),
            "aufgaben": bilanz}


@app.post("/api/beispielkurs", status_code=201)
def beispielkurs_anlegen(benutzer_id: int, request: Request = None,
                         db: sqlite3.Connection = DB):
    """Ein kleiner englischer Übungskurs zum Ausprobieren.

    Einmal je Person; beim zweiten Aufruf wird der bestehende
    zurückgegeben statt eines zweiten angelegt.
    """
    _wache_rumpf(db, request, benutzer_id=benutzer_id)
    try:
        return beispielkurs.anlegen(db, benutzer_id)
    except KeyError as f:
        raise HTTPException(404, str(f))


@app.get("/api/sammlungen/{sammlung_id}/wortarten")
def sammlung_wortarten(sammlung_id: int, benutzer_id: int | None = None,
                       request: Request = None,
                       db: sqlite3.Connection = DB):
    """Welche Wortarten kommen in dieser Sammlung vor, mit Zahlen.

    Aus dem Bestand, nicht aus dem Sprachprofil: das Profil kennt nur
    die Wortarten mit Formentabellen, also keine Adverbien und keine
    Konjunktionen. Zum gezielten Üben braucht man aber genau die Liste,
    die wirklich dasteht — und die Zahlen daneben, damit man sieht, ob
    sich ein Ausschnitt lohnt.
    """
    _wache_rumpf(db, request, sammlung_id=sammlung_id)
    _holen(db, "sammlung", sammlung_id)
    return dbm.zeilen(db, """
        SELECT l.wortart,
               COUNT(DISTINCT l.id) AS woerter,
               COUNT(a.id) AS aufgaben
          FROM lexem l
          LEFT JOIN aufgabe a ON a.lexem_id = l.id AND a.aktiv = 1
         WHERE l.sammlung_id = ?
         GROUP BY l.wortart
        HAVING aufgaben > 0
         ORDER BY aufgaben DESC""", (sammlung_id,))


@app.get("/api/sammlungen/{sammlung_id}/lehrgang")
def lehrgang_lesen(sammlung_id: int, benutzer_id: int | None = None,
                   request: Request = None, db: sqlite3.Connection = DB):
    """Ab welcher Lektion gilt welche Formgruppe — und wo stehe ich?"""
    _wache_rumpf(db, request, sammlung_id=sammlung_id,
                 benutzer_id=benutzer_id)
    _holen(db, "sammlung", sammlung_id)
    try:
        return {
            "zuordnung": lehrgang.zuordnung(db, sammlung_id),
            "vorschlag": lehrgang.vorschlag(db, sammlung_id),
            "buchstand": (lehrgang.buchstand(db, benutzer_id, sammlung_id)
                          .get(sammlung_id) if benutzer_id else None),
            "ausgeblendet": (lehrgang.ausgeblendet(db, benutzer_id, sammlung_id)
                             if benutzer_id else []),
        }
    except KeyError as f:
        raise HTTPException(404, str(f))


@app.put("/api/sammlungen/{sammlung_id}/lehrgang")
def lehrgang_setzen(sammlung_id: int, eingabe: LehrgangSetzen,
                    request: Request = None, db: sqlite3.Connection = DB):
    """Die Zuordnung als Ganzes ersetzen."""
    _wache_rumpf(db, request, sammlung_id=sammlung_id)
    try:
        return {"zuordnung": lehrgang.zuordnung_setzen(db, sammlung_id,
                                                       eingabe.zuordnung)}
    except KeyError as f:
        raise HTTPException(404, str(f))


@app.put("/api/sammlungen/{sammlung_id}/buchstand")
def buchstand_setzen(sammlung_id: int, eingabe: BuchstandSetzen,
                     request: Request = None, db: sqlite3.Connection = DB):
    """»Ich bin bei Lektion N.« — null hebt die Schranke auf."""
    _wache_rumpf(db, request, sammlung_id=sammlung_id,
                 benutzer_id=eingabe.benutzer_id)
    _holen(db, "sammlung", sammlung_id)
    _holen(db, "benutzer", eingabe.benutzer_id)
    lehrgang.buchstand_setzen(db, eingabe.benutzer_id, sammlung_id,
                              eingabe.bis_lektion)
    return {"sammlung_id": sammlung_id, "bis_lektion": eingabe.bis_lektion,
            "ausgeblendet": lehrgang.ausgeblendet(db, eingabe.benutzer_id,
                                                  sammlung_id)}


@app.get("/api/sammlungen/{sammlung_id}/lektionen")
def lektionen_liste(sammlung_id: int, db: sqlite3.Connection = DB):
    _holen(db, "sammlung", sammlung_id)
    return sammelimport.lektionen(db, sammlung_id)


@app.post("/api/sammlungen/{sammlung_id}/lektionen", status_code=201)
def lektion_anlegen(sammlung_id: int, eingabe: LektionAnlegen,
                    db: sqlite3.Connection = DB):
    """Legt eine Lektion an — oder zieht die vorhandene mit dieser Nummer nach."""
    _holen(db, "sammlung", sammlung_id)
    if eingabe.nr is not None:
        kennung = sammelimport.lektion_sichern(db, sammlung_id, eingabe.nr,
                                               eingabe.name, eingabe.beschreibung)
        return _holen(db, "lektion", kennung)
    cur = db.execute("""INSERT INTO lektion
                          (sammlung_id, name, beschreibung, reihenfolge)
                        VALUES (?, ?, ?, ?)""",
                     (sammlung_id, eingabe.name, eingabe.beschreibung,
                      eingabe.reihenfolge))
    return _holen(db, "lektion", cur.lastrowid)


@app.post("/api/sammlungen/{sammlung_id}/import/vokabeln")
def vokabeln_importieren(sammlung_id: int, eingabe: SammelimportEingabe,
                         request: Request = None,
                         db: sqlite3.Connection = DB):
    """Viele Wörter in einem Aufruf — mit Probelauf und wiederholbar.

    Berichtet wird knapp: je Eintrag nur, wenn es etwas zu sagen gibt.
    Bei sechzehnhundert Wörtern will niemand sechzehnhundert Zeilen lesen.
    """
    _wache_rumpf(db, request, sammlung_id=sammlung_id)
    _holen(db, "sammlung", sammlung_id)
    try:
        return sammelimport.importieren(db, sammlung_id, eingabe.eintraege,
                                        eingabe.nur_pruefen, eingabe.quelle)
    except (sammelimport.ImportFehler, mk.MerkmalFehler) as fehler:
        raise HTTPException(400, str(fehler))


# ============================================================ Freigabe

@app.get("/api/sammlungen/{sammlung_id}/freigabe/lektionen")
def freigabe_lektionen(sammlung_id: int, db: sqlite3.Connection = DB):
    """Wo ist noch etwas freizugeben? Der Einstieg in die Prüfansicht."""
    _holen(db, "sammlung", sammlung_id)
    return freigabemodul.offene_lektionen(db, sammlung_id)


@app.get("/api/sammlungen/{sammlung_id}/freigabe")
def freigabe_ansicht(sammlung_id: int, lektion_nr: int | None = None,
                     wortart: str | None = None, nur_offene: bool = True,
                     ab: int = 0, anzahl: int = Query(default=25, le=100),
                     db: sqlite3.Connection = DB):
    """Die Prüfansicht: je Wort die Formen als Paradigmentabelle.

    Eine Liste von Formen in Eingabereihenfolge lässt sich nicht prüfen.
    Eine Tabelle mit einer leeren oder doppelt besetzten Zelle sieht man
    auf einen Blick.
    """
    _holen(db, "sammlung", sammlung_id)
    return freigabemodul.uebersicht(db, sammlung_id, lektion_nr, wortart,
                                    nur_offene, ab, anzahl)


@app.post("/api/sammlungen/{sammlung_id}/freigabe")
def freigabe_setzen(sammlung_id: int, eingabe: FreigabeEingabe,
                    request: Request = None, db: sqlite3.Connection = DB):
    """Gibt Formen frei — je Wort oder je Lektion, Zellen abwählbar.

    Bewusst nur über die Oberfläche: es gibt dafür kein MCP-Werkzeug. Ein
    Agent, der seine eigenen Einträge im Stapel freigibt, hätte die
    Prüfung abgeschafft, nicht erledigt.

    Das gilt für den STAPEL. Einzeln kann ein Agent sehr wohl gleich
    freigeben — `als_geprueft` an vokabel_anlegen und formen_ergaenzen.
    Das ist so entschieden; hier steht es, damit niemand aus diesem
    Docstring schließt, die Prüfung sei erzwungen.
    """
    _wache_rumpf(db, request, sammlung_id=sammlung_id)
    _holen(db, "sammlung", sammlung_id)
    try:
        return freigabemodul.setzen(
            db, sammlung_id, eingabe.form_ids, eingabe.lexem_ids,
            eingabe.lektion_nr, eingabe.ausser, eingabe.geprueft,
            eingabe.uebung_ids, eingabe.ausser_uebungen)
    except freigabemodul.FreigabeFehler as fehler:
        raise HTTPException(400, str(fehler))


# ============================================================ Übungen

def _uebung(db: sqlite3.Connection, uebung_id: int) -> dict:
    try:
        return uebungen.lesen(db, uebung_id)
    except uebungen.UebungFehler as fehler:
        raise HTTPException(404, str(fehler))


@app.get("/api/sammlungen/{sammlung_id}/uebungen")
def uebungen_auflisten(sammlung_id: int, lektion_nr: int | None = None,
                       bis_lektion: int | None = None,
                       typ: str | None = None, nur_ungepruefte: bool = False,
                       ab: int = 0, anzahl: int = Query(default=50, le=500),
                       db: sqlite3.Connection = DB):
    _holen(db, "sammlung", sammlung_id)
    return uebungen.auflisten(db, sammlung_id, lektion_nr, typ, bis_lektion,
                              nur_ungepruefte, ab, anzahl)


@app.post("/api/sammlungen/{sammlung_id}/uebungen", status_code=201)
def uebung_anlegen(sammlung_id: int, eingabe: UebungEingabe,
                   request: Request = None, db: sqlite3.Connection = DB):
    _wache_rumpf(db, request, sammlung_id=sammlung_id)
    _holen(db, "sammlung", sammlung_id)
    try:
        return uebungen.anlegen(db, sammlung_id,
                                eingabe.model_dump(exclude_none=True))
    except uebungen.UebungFehler as fehler:
        raise HTTPException(400, str(fehler))


@app.post("/api/sammlungen/{sammlung_id}/import/uebungen")
def uebungen_importieren(sammlung_id: int, eingabe: UebungenImportEingabe,
                         request: Request = None,
                         db: sqlite3.Connection = DB):
    """Viele Übungen in einem Aufruf — mit Probelauf und wiederholbar."""
    _wache_rumpf(db, request, sammlung_id=sammlung_id)
    _holen(db, "sammlung", sammlung_id)
    try:
        return uebungen.importieren(db, sammlung_id, eingabe.eintraege,
                                    eingabe.nur_pruefen)
    except uebungen.UebungFehler as fehler:
        raise HTTPException(400, str(fehler))


@app.post("/api/sammlungen/{sammlung_id}/text/pruefen")
def text_deckung(sammlung_id: int, eingabe: TextPruefenEingabe,
                 db: sqlite3.Connection = DB):
    """Welche Wörter eines Textes stehen bis zu dieser Lektion noch nicht da?

    Damit lässt sich ein Text VORHER auf die Stufe zuschneiden, statt ihn
    hinterher zu verwerfen.
    """
    _holen(db, "sammlung", sammlung_id)
    try:
        return uebungen.text_pruefen(db, sammlung_id, eingabe.text,
                                     eingabe.bis_lektion)
    except uebungen.UebungFehler as fehler:
        raise HTTPException(404, str(fehler))


@app.get("/api/uebungen/{uebung_id}")
def uebung_lesen(uebung_id: int, db: sqlite3.Connection = DB):
    return _uebung(db, uebung_id)


@app.patch("/api/uebungen/{uebung_id}")
def uebung_aendern(uebung_id: int, eingabe: UebungAendern,
                   request: Request = None, db: sqlite3.Connection = DB):
    _uebung(db, uebung_id)
    _wache_rumpf(db, request)
    try:
        return uebungen.aendern(db, uebung_id,
                                eingabe.model_dump(exclude_unset=True))
    except uebungen.UebungFehler as fehler:
        raise HTTPException(400, str(fehler))


@app.post("/api/uebungen/{uebung_id}/freigabe")
def uebung_freigeben(uebung_id: int, geprueft: bool = True,
                     request: Request = None, db: sqlite3.Connection = DB):
    """Die Freigabe bleibt beim Menschen — darum ein eigener Aufruf."""
    _uebung(db, uebung_id)
    _wache_rumpf(db, request)
    return uebungen.freigeben(db, uebung_id, geprueft)


@app.delete("/api/uebungen/{uebung_id}", status_code=204)
def uebung_loeschen(uebung_id: int, request: Request = None,
                    db: sqlite3.Connection = DB):
    _uebung(db, uebung_id)
    _wache_rumpf(db, request)
    uebungen.loeschen(db, uebung_id)
    return Response(status_code=204)


# ------------------------------------------------------- Lesen und Übersetzen

@app.get("/api/sammlungen/{sammlung_id}/texte")
def texte_auflisten(sammlung_id: int, request: Request = None,
                    db: sqlite3.Connection = DB):
    _wache_rumpf(db, request, sammlung_id=sammlung_id)
    _holen(db, "sammlung", sammlung_id)
    return lesetexte.auflisten(db, sammlung_id)


@app.post("/api/sammlungen/{sammlung_id}/texte", status_code=201)
def text_anlegen(sammlung_id: int, eingabe: LesetextAnlegen,
                 request: Request = None, db: sqlite3.Connection = DB):
    """Text einwerfen — eingefügt oder hochgeladen, hier ist beides dasselbe."""
    _wache_rumpf(db, request, sammlung_id=sammlung_id)
    try:
        return lesetexte.anlegen(db, sammlung_id, eingabe.titel,
                                 eingabe.inhalt, niveau=eingabe.niveau,
                                 notiz=eingabe.notiz,
                                 uebersetzung=eingabe.uebersetzung)
    except ValueError as f:
        raise HTTPException(400, str(f))
    except KeyError as f:
        raise HTTPException(404, str(f))


@app.get("/api/texte/{text_id}")
def text_lesen(text_id: int, benutzer_id: int | None = None,
               request: Request = None, db: sqlite3.Connection = DB):
    _wache_rumpf(db, request, benutzer_id=benutzer_id)
    try:
        return lesetexte.lesen(db, text_id, benutzer_id)
    except KeyError as f:
        raise HTTPException(404, str(f))


@app.delete("/api/texte/{text_id}", status_code=204)
def text_loeschen(text_id: int, request: Request = None,
                  db: sqlite3.Connection = DB):
    try:
        lesetexte.loeschen(db, text_id)
    except KeyError as f:
        raise HTTPException(404, str(f))
    return Response(status_code=204)


@app.get("/api/texte/{text_id}/deckung")
def text_deckung(text_id: int, benutzer_id: int, request: Request = None,
                 db: sqlite3.Connection = DB):
    """Könnte ich das schon übersetzen?"""
    _wache_rumpf(db, request, benutzer_id=benutzer_id)
    _holen(db, "benutzer", benutzer_id)
    try:
        return lesetexte.deckung(db, text_id, benutzer_id)
    except KeyError as f:
        raise HTTPException(404, str(f))


@app.get("/api/texte/{text_id}/nachschlagen")
def text_nachschlagen(text_id: int, wort: str, request: Request = None,
                      db: sqlite3.Connection = DB):
    try:
        return lesetexte.nachschlagen(db, text_id, wort)
    except KeyError as f:
        raise HTTPException(404, str(f))


@app.put("/api/abschnitte/{abschnitt_id}/fassung")
def fassung_sichern(abschnitt_id: int, eingabe: FassungSichern,
                    request: Request = None, db: sqlite3.Connection = DB):
    """Meine Übersetzung eines Abschnitts — beim Tippen gesichert."""
    _wache_rumpf(db, request, benutzer_id=eingabe.benutzer_id)
    _holen(db, "benutzer", eingabe.benutzer_id)
    try:
        return lesetexte.fassung_sichern(db, abschnitt_id,
                                         eingabe.benutzer_id, eingabe.fassung)
    except KeyError as f:
        raise HTTPException(404, str(f))


@app.put("/api/texte/{text_id}/referenz")
def text_referenz_setzen(text_id: int, eingabe: ReferenzSetzen,
                         request: Request = None,
                         db: sqlite3.Connection = DB):
    """Die Referenzübersetzung je Abschnitt — meist von der KI."""
    try:
        return lesetexte.referenz_setzen(db, text_id, eingabe.fassungen)
    except KeyError as f:
        raise HTTPException(404, str(f))
    except ValueError as f:
        raise HTTPException(400, str(f))


@app.post("/api/texte/{text_id}/wortwunsch", status_code=201)
def wort_merken(text_id: int, eingabe: WortMerken, request: Request = None,
                db: sqlite3.Connection = DB):
    """»Das Wort kenne ich nicht« — auf die Liste für die KI."""
    _wache_rumpf(db, request, benutzer_id=eingabe.benutzer_id)
    _holen(db, "benutzer", eingabe.benutzer_id)
    try:
        return lesetexte.wort_merken(db, eingabe.benutzer_id, text_id,
                                     eingabe.wort, eingabe.zusammenhang)
    except KeyError as f:
        raise HTTPException(404, str(f))
    except ValueError as f:
        raise HTTPException(400, str(f))


@app.post("/api/texte/{text_id}/wortwuensche/alle", status_code=201)
def alle_unbekannten_merken(text_id: int, benutzer_id: int,
                            request: Request = None,
                            db: sqlite3.Connection = DB):
    """Alle unbekannten Wörter dieses Textes auf einmal anfordern."""
    _wache_rumpf(db, request, benutzer_id=benutzer_id)
    _holen(db, "benutzer", benutzer_id)
    try:
        return lesetexte.alle_unbekannten_merken(db, benutzer_id, text_id)
    except KeyError as f:
        raise HTTPException(404, str(f))


@app.delete("/api/texte/{text_id}/wortwuensche/alle")
def alle_zuruecknehmen(text_id: int, benutzer_id: int,
                       request: Request = None,
                       db: sqlite3.Connection = DB):
    """Was aus diesem Text angefordert wurde, wieder von der Liste."""
    _wache_rumpf(db, request, benutzer_id=benutzer_id)
    try:
        return lesetexte.alle_zuruecknehmen(db, benutzer_id, text_id)
    except KeyError as f:
        raise HTTPException(404, str(f))


@app.delete("/api/texte/{text_id}/wortwunsch", status_code=204)
def wort_vergessen(text_id: int, benutzer_id: int, wort: str,
                   request: Request = None, db: sqlite3.Connection = DB):
    _wache_rumpf(db, request, benutzer_id=benutzer_id)
    try:
        lesetexte.wort_vergessen(db, benutzer_id, text_id, wort)
    except KeyError as f:
        raise HTTPException(404, str(f))
    return Response(status_code=204)


@app.get("/api/wortwuensche")
def wortwuensche_lesen(benutzer_id: int, sammlung_id: int | None = None,
                       offen: bool = True, request: Request = None,
                       db: sqlite3.Connection = DB):
    """Die Liste, die auch die angebundene KI über den MCP sieht."""
    _wache_rumpf(db, request, benutzer_id=benutzer_id)
    _holen(db, "benutzer", benutzer_id)
    return lesetexte.wortwuensche(db, benutzer_id, sammlung_id, offen)


@app.delete("/api/wortwuensche/{wunsch_id}", status_code=204)
def wortwunsch_loeschen(wunsch_id: int, request: Request = None,
                        db: sqlite3.Connection = DB):
    db.execute("DELETE FROM wortwunsch WHERE id = ?", (wunsch_id,))
    return Response(status_code=204)


@app.post("/api/textaufgaben/{textaufgabe_id}/pruefen")
def textaufgabe_pruefen(textaufgabe_id: int, eingabe: UebungAntwort,
                        db: sqlite3.Connection = DB):
    """Bewertet eine freie Übersetzung Wort für Wort.

    Bei längeren Blöcken ist `zaehlt` falsch: dort bleibt die Einschätzung
    beim Menschen, der Vergleich ist nur Hilfestellung.
    """
    try:
        return uebungen.bewerten(db, textaufgabe_id, eingabe.antwort)
    except uebungen.UebungFehler as fehler:
        raise HTTPException(404, str(fehler))


# ================================================== Übungen abfragen

def _uebung_fehler(aufruf, *args, **kw):
    try:
        return aufruf(*args, **kw)
    except uebung_lernen.UebungFehler as fehler:
        raise HTTPException(400, str(fehler))


@app.get("/api/uebungen/lernen/stand")
def uebungen_stand(benutzer_id: int, sammlung_id: int | None = None,
                   db: sqlite3.Connection = DB):
    _holen(db, "benutzer", benutzer_id)
    return uebung_lernen.stand(db, benutzer_id, sammlung_id)


@app.get("/api/uebungen/lernen/naechste")
def uebungen_naechste(benutzer_id: int, sammlung_id: int | None = None,
                      lektion_nr: int | None = None,
                      bis_lektion: int | None = None,
                      typ: str | None = None, richtung: str | None = None,
                      nur: str | None = None,
                      anzahl: int = Query(default=1, le=20),
                      db: sqlite3.Connection = DB):
    """Die nächsten Übungsaufgaben — nur aus freigegebenen Übungen."""
    _holen(db, "benutzer", benutzer_id)
    return _uebung_fehler(uebung_lernen.naechste, db, benutzer_id, sammlung_id,
                          lektion_nr, bis_lektion, typ, richtung, nur, anzahl)


@app.post("/api/uebungen/lernen/pruefen")
def uebungen_pruefen(eingabe: UebungPruefenEingabe, request: Request,
                     db: sqlite3.Connection = DB):
    """Vergleicht Wort für Wort. Schreibt noch nichts fort."""
    _holen(db, "benutzer", eingabe.benutzer_id)
    _wache_rumpf(db, request, benutzer_id=eingabe.benutzer_id,
                 textaufgabe_id=eingabe.textaufgabe_id, schreiben=False)
    return _uebung_fehler(uebung_lernen.pruefen, db, eingabe.benutzer_id,
                          eingabe.textaufgabe_id, eingabe.antwort)


@app.post("/api/uebungen/lernen/aufdecken")
def uebungen_aufdecken(eingabe: UebungPruefenEingabe, request: Request,
                       db: sqlite3.Connection = DB):
    _holen(db, "benutzer", eingabe.benutzer_id)
    _wache_rumpf(db, request, benutzer_id=eingabe.benutzer_id,
                 textaufgabe_id=eingabe.textaufgabe_id, schreiben=False)
    return _uebung_fehler(uebung_lernen.aufdecken, db, eingabe.benutzer_id,
                          eingabe.textaufgabe_id)


@app.post("/api/uebungen/lernen/bewerten")
def uebungen_bewerten(eingabe: UebungBewertenEingabe, request: Request,
                      db: sqlite3.Connection = DB):
    _holen(db, "benutzer", eingabe.benutzer_id)
    _wache_rumpf(db, request, benutzer_id=eingabe.benutzer_id,
                 textaufgabe_id=eingabe.textaufgabe_id)
    return _uebung_fehler(
        uebung_lernen.bewerten, db, eingabe.benutzer_id,
        eingabe.textaufgabe_id, eingabe.urteil, eingabe.bewertung,
        eingabe.antwort, eingabe.dauer_ms, eingabe.aufgedeckt,
        eingabe.versuche, eingabe.rueckmeldung)


# ======================================================= Grammatikregeln

@app.get("/api/sammlungen/{sammlung_id}/regeln")
def regeln_auflisten(sammlung_id: int, nur_ungepruefte: bool = False,
                     db: sqlite3.Connection = DB):
    """Alle Regeln dieser Sammlung — auch die noch ungeprüften."""
    _holen(db, "sammlung", sammlung_id)
    return regelmodul.auflisten(db, sammlung_id, nur_ungepruefte)


@app.post("/api/sammlungen/{sammlung_id}/regeln", status_code=201)
def regel_anlegen(sammlung_id: int, eingabe: RegelEingabe, request: Request,
                  db: sqlite3.Connection = DB):
    """Legt eine Regel an oder berichtigt die mit derselben Kennung.

    Sie bleibt ungeprüft — wie eine eingetragene Vokabel.
    """
    sammlung = _holen(db, "sammlung", sammlung_id)
    _wache_rumpf(db, request, sammlung_id=sammlung_id)
    try:
        return regelmodul.anlegen(
            db, sammlung_id, eingabe.titel, eingabe.text, sammlung["sprache"],
            eingabe.muster, eingabe.beispiele, eingabe.kennung,
            eingabe.quelle, eingabe.reihenfolge)
    except ValueError as fehler:
        raise HTTPException(400, str(fehler))


@app.get("/api/regeln/{regel_id}")
def regel_lesen(regel_id: int, db: sqlite3.Connection = DB):
    z = regelmodul.lesen(db, regel_id)
    if z is None:
        raise HTTPException(404, f"Regel {regel_id} gibt es nicht")
    return z


@app.patch("/api/regeln/{regel_id}")
def regel_aendern(regel_id: int, eingabe: RegelAendern,
                  db: sqlite3.Connection = DB):
    r = _holen(db, "regel", regel_id)
    sammlung = _holen(db, "sammlung", r["sammlung_id"])
    try:
        return regelmodul.aendern(db, regel_id, sammlung["sprache"],
                                  **eingabe.model_dump(exclude_unset=True))
    except (ValueError, KeyError) as fehler:
        raise HTTPException(400, str(fehler))


@app.post("/api/regeln/{regel_id}/freigabe")
def regel_freigeben(regel_id: int, geprueft: bool = True,
                    db: sqlite3.Connection = DB):
    """Die Freigabe bleibt beim Menschen — es gibt dafür bewusst kein
    MCP-Werkzeug."""
    _holen(db, "regel", regel_id)
    return regelmodul.freigeben(db, regel_id, geprueft)


@app.delete("/api/regeln/{regel_id}", status_code=204)
def regel_loeschen(regel_id: int, db: sqlite3.Connection = DB):
    _holen(db, "regel", regel_id)
    regelmodul.loeschen(db, regel_id)
    return Response(status_code=204)


# ============================================================ Wortschatz

def _lexem_ausbauen(db: sqlite3.Connection, lexem: dict,
                    mit_aufgaben: bool = False) -> dict:
    s = _holen(db, "sammlung", lexem["sammlung_id"])
    code, grund = s["sprache"], s["grundsprache"]
    formen = dbm.zeilen(db, "SELECT * FROM form WHERE lexem_id = ?", (lexem["id"],))
    for f in formen:
        f["merkmale"] = dbm.j_lesen(f["merkmale"])
        f["beschriftung"] = sprachen.beschriften_form(code, lexem["wortart"],
                                                      f["merkmale"])
        f["gruppe"] = (aufgaben._gruppe_der_form(code, lexem["wortart"],
                                                 f["merkmale"]) or {}).get("kennung")
    formen.sort(key=lambda f: mk.sortierbar(f["merkmale"]))
    bedeutungen = dbm.zeilen(db, """SELECT * FROM bedeutung WHERE lexem_id = ?
                                     ORDER BY reihenfolge, id""", (lexem["id"],))
    for b in bedeutungen:
        b["uebersetzungen"] = dbm.zeilen(db, """
            SELECT * FROM uebersetzung WHERE bedeutung_id = ?
             ORDER BY ist_haupt DESC, id""", (b["id"],))
    ergebnis = {
        **lexem,
        "merkmale": dbm.j_lesen(lexem["merkmale"]),
        "sprache": code,
        "grundsprache": grund,
        "wortart_name": mk.WORTARTEN.get(lexem["wortart"], lexem["wortart"]),
        "formen": formen,
        "bedeutungen": bedeutungen,
        "beispiele": dbm.zeilen(db, "SELECT * FROM beispiel WHERE lexem_id = ?",
                                (lexem["id"],)),
    }
    if mit_aufgaben:
        ergebnis["aufgaben"] = dbm.zeilen(db, """
            SELECT id, typ, ziel_art, ziel_id, aktiv FROM aufgabe
             WHERE lexem_id = ? ORDER BY typ""", (lexem["id"],))
    return ergebnis


@app.get("/api/sammlungen/{sammlung_id}/lexeme")
def lexeme_liste(sammlung_id: int, suche: str | None = None,
                 lektion_id: int | None = None,
                 lektion_nr: int | None = None,
                 wortart: str | None = None,
                 nur_ungepruefte: bool = False,
                 ab: int = 0, anzahl: int = Query(default=50, le=500),
                 db: sqlite3.Connection = DB):
    _holen(db, "sammlung", sammlung_id)
    bedingungen, werte = ["l.sammlung_id = ?"], [sammlung_id]
    if suche:
        bedingungen.append("""(l.lemma LIKE ? OR EXISTS (
            SELECT 1 FROM bedeutung b JOIN uebersetzung u ON u.bedeutung_id = b.id
             WHERE b.lexem_id = l.id AND u.text LIKE ?))""")
        werte += [f"%{suche}%", f"%{suche}%"]
    if lektion_id is not None:
        bedingungen.append("l.lektion_id = ?")
        werte.append(lektion_id)
    if lektion_nr is not None:
        # Über die Nummer, nicht die Kennung: so denkt ein Lehrwerk, und
        # nur so lässt sich eine Lektion von außen benennen.
        bedingungen.append("""l.lektion_id IN (SELECT id FROM lektion
                                WHERE sammlung_id = ? AND nr = ?)""")
        werte += [sammlung_id, lektion_nr]
    if wortart:
        bedingungen.append("l.wortart = ?")
        werte.append(wortart)
    if nur_ungepruefte:
        bedingungen.append("""EXISTS (SELECT 1 FROM form f
                               WHERE f.lexem_id = l.id AND f.geprueft = 0)""")
    wo = " AND ".join(bedingungen)
    gesamt = dbm.wert(db, f"SELECT COUNT(*) FROM lexem l WHERE {wo}", werte)
    zeilen = dbm.zeilen(db, f"""
        SELECT l.*,
               (SELECT COUNT(*) FROM form f WHERE f.lexem_id = l.id) AS formen_anzahl,
               (SELECT COUNT(*) FROM form f WHERE f.lexem_id = l.id AND f.geprueft = 0)
                   AS ungeprueft_anzahl,
               (SELECT COUNT(*) FROM aufgabe a WHERE a.lexem_id = l.id AND a.aktiv = 1)
                   AS aufgaben_anzahl,
               (SELECT u.text FROM bedeutung b
                  JOIN uebersetzung u ON u.bedeutung_id = b.id
                 WHERE b.lexem_id = l.id
                 ORDER BY b.reihenfolge, u.ist_haupt DESC LIMIT 1) AS erste_bedeutung
          FROM lexem l WHERE {wo}
         ORDER BY l.lemma LIMIT ? OFFSET ?""", (*werte, anzahl, ab))
    for z in zeilen:
        z["merkmale"] = dbm.j_lesen(z["merkmale"])
    return {"gesamt": gesamt, "ab": ab, "anzahl": len(zeilen), "lexeme": zeilen}


@app.post("/api/lexeme", status_code=201)
def lexem_anlegen(eingabe: LexemEingabe, request: Request = None,
                  db: sqlite3.Connection = DB):
    """Ein vollständiges Wort in einem Aufruf: Lemma, Formen, Bedeutungen.

    Die Aufgaben werden anschließend selbsttätig erzeugt.
    """
    # Die Sammlungskennung steht im Rumpf, die Wache sieht sie darum nicht.
    _wache_rumpf(db, request, sammlung_id=eingabe.sammlung_id)
    s = _holen(db, "sammlung", eingabe.sammlung_id)
    try:
        lex_merkmale = sprachen.pruefen_lexemmerkmale(
            s["sprache"], eingabe.wortart, eingabe.merkmale)
    except mk.MerkmalFehler as fehler:
        raise HTTPException(400, str(fehler))
    if eingabe.lektion_id is not None:
        k = _holen(db, "lektion", eingabe.lektion_id)
        if k["sammlung_id"] != eingabe.sammlung_id:
            raise HTTPException(400, "Die Lektion gehört zu einer anderen Sammlung")

    db.execute("BEGIN")
    try:
        lektion_id = eingabe.lektion_id
        if lektion_id is None and eingabe.lektion_nr is not None:
            lektion_id = sammelimport.lektion_sichern(db, eingabe.sammlung_id,
                                                      eingabe.lektion_nr)
        cur = db.execute("""INSERT INTO lexem
                              (sammlung_id, lektion_id, lemma, wortart, merkmale,
                               notiz, reihenfolge, kennung, luecken, staemme)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                         (eingabe.sammlung_id, lektion_id, eingabe.lemma,
                          eingabe.wortart, dbm.j_schreiben(lex_merkmale),
                          eingabe.notiz, eingabe.reihenfolge,
                          (eingabe.kennung or "").strip() or None,
                          dbm.j_schreiben(eingabe.luecken),
                          dbm.j_schreiben(eingabe.staemme)))
        lexem_id = cur.lastrowid
        for f in eingabe.formen:
            _form_einfuegen(db, lexem_id, f)
        for b in eingabe.bedeutungen:
            _bedeutung_einfuegen(db, lexem_id, b, s["grundsprache"])
        for bs in eingabe.beispiele:
            db.execute("""INSERT INTO beispiel (lexem_id, satz, uebersetzung, quelle)
                          VALUES (?, ?, ?, ?)""",
                       (lexem_id, bs.satz, bs.uebersetzung, bs.quelle))
        bilanz = aufgaben.erzeugen(db, lexem_id)
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise
    ergebnis = _lexem_ausbauen(db, _holen(db, "lexem", lexem_id), mit_aufgaben=True)
    ergebnis["aufgaben_bilanz"] = bilanz
    return ergebnis


def _form_einfuegen(db: sqlite3.Connection, lexem_id: int, f: FormEingabe) -> int:
    cur = db.execute("""INSERT INTO form
                          (lexem_id, text, merkmale, ist_grundform, ist_variante,
                           aussprache, quelle, geprueft, notiz)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                     (lexem_id, f.text, dbm.j_schreiben(f.merkmale),
                      int(f.ist_grundform), int(f.ist_variante), f.aussprache,
                      f.quelle, int(f.geprueft), f.notiz))
    haupt = cur.lastrowid
    # Nebenformen derselben Zelle daneben eintragen, nicht statt dessen.
    for text in f.varianten:
        if not (text or "").strip():
            continue
        db.execute("""INSERT INTO form (lexem_id, text, merkmale, ist_grundform,
                                        ist_variante, quelle, geprueft)
                      VALUES (?, ?, ?, 0, 1, ?, ?)""",
                   (lexem_id, text.strip(), dbm.j_schreiben(f.merkmale),
                    f.quelle, int(f.geprueft)))
    return haupt


def _bedeutung_einfuegen(db: sqlite3.Connection, lexem_id: int,
                         b: BedeutungEingabe, grundsprache: str) -> int:
    cur = db.execute("""INSERT INTO bedeutung (lexem_id, reihenfolge, kontext, notiz)
                        VALUES (?, ?, ?, ?)""",
                     (lexem_id, b.reihenfolge, b.kontext, b.notiz))
    bedeutung_id = cur.lastrowid
    for i, u in enumerate(b.uebersetzungen):
        db.execute("""INSERT INTO uebersetzung
                        (bedeutung_id, sprache, text, ist_haupt, quelle, geprueft)
                      VALUES (?, ?, ?, ?, ?, ?)""",
                   (bedeutung_id, u.sprache or grundsprache, u.text,
                    int(u.ist_haupt or i == 0), u.quelle, int(u.geprueft)))
    return bedeutung_id


@app.get("/api/lexeme/{lexem_id}")
def lexem_lesen(lexem_id: int, db: sqlite3.Connection = DB):
    return _lexem_ausbauen(db, _holen(db, "lexem", lexem_id), mit_aufgaben=True)


@app.patch("/api/lexeme/{lexem_id}")
def lexem_aendern(lexem_id: int, eingabe: LexemAendern, db: sqlite3.Connection = DB):
    _holen(db, "lexem", lexem_id)
    felder, werte = [], []
    if eingabe.lemma is not None:
        felder.append("lemma = ?"); werte.append(eingabe.lemma)
    if eingabe.wortart is not None:
        if eingabe.wortart not in mk.WORTARTEN:
            raise HTTPException(400, f"Unbekannte Wortart {eingabe.wortart!r}")
        felder.append("wortart = ?"); werte.append(eingabe.wortart)
    if eingabe.merkmale is not None:
        lexem = _holen(db, "lexem", lexem_id)
        s = _holen(db, "sammlung", lexem["sammlung_id"])
        try:
            felder.append("merkmale = ?")
            werte.append(dbm.j_schreiben(sprachen.pruefen_lexemmerkmale(
                s["sprache"], eingabe.wortart or lexem["wortart"],
                eingabe.merkmale)))
        except mk.MerkmalFehler as fehler:
            raise HTTPException(400, str(fehler))
    if eingabe.lektion_id is not None:
        felder.append("lektion_id = ?"); werte.append(eingabe.lektion_id)
    if eingabe.notiz is not None:
        felder.append("notiz = ?"); werte.append(eingabe.notiz)
    if eingabe.reihenfolge is not None:
        felder.append("reihenfolge = ?"); werte.append(eingabe.reihenfolge)
    if eingabe.kennung is not None:
        felder.append("kennung = ?"); werte.append(eingabe.kennung)
    if eingabe.bedeutungen is not None:
        if not eingabe.bedeutungen:
            raise HTTPException(
                400, "Ohne Bedeutung entsteht keine Bedeutungsaufgabe. "
                     "Um alle zu entfernen, das Wort löschen.")
        lexem = _holen(db, "lexem", lexem_id)
        s_ = _holen(db, "sammlung", lexem["sammlung_id"])
        # Ersetzen, nicht ergänzen: welche einzelne Übersetzung gemeint
        # wäre, ließe sich nicht ausdrücken.
        db.execute("DELETE FROM bedeutung WHERE lexem_id = ?", (lexem_id,))
        for b in eingabe.bedeutungen:
            _bedeutung_einfuegen(db, lexem_id, b, s_["grundsprache"])
        felder = felder or []
    if felder or eingabe.bedeutungen is not None:
        felder.append("geaendert = datetime('now')")
        db.execute(f"UPDATE lexem SET {', '.join(felder)} WHERE id = ?",
                   (*werte, lexem_id))
        aufgaben.erzeugen(db, lexem_id)
    return _lexem_ausbauen(db, _holen(db, "lexem", lexem_id), mit_aufgaben=True)


@app.put("/api/lexeme/{lexem_id}/beispiele")
def beispiele_setzen(lexem_id: int, eingabe: BeispieleSetzen,
                     request: Request = None, db: sqlite3.Connection = DB):
    """Beispielsätze zu einem Wort — wie im Wörterbuch.

    Als GANZES ersetzt, nicht einzeln angehängt. Ein Werkzeug, das nur
    anfügt, sammelt bei jedem Lauf der KI dieselben Sätze noch einmal;
    wer ersetzt, muss vorher lesen und sieht dabei, was schon da ist.

    Die Sätze sind Lesestoff, keine Aufgaben: sie erzeugen nichts und
    werden nicht abgefragt. Darum brauchen sie auch keine Freigabe —
    ein falscher Beispielsatz steht daneben und wird nicht gepaukt.
    """
    _wache_rumpf(db, request, lexem_id=lexem_id)
    _holen(db, "lexem", lexem_id)
    eigene = {z["id"] for z in dbm.zeilen(db, """
        SELECT id FROM bedeutung WHERE lexem_id = ?""", (lexem_id,))}
    db.execute("DELETE FROM beispiel WHERE lexem_id = ?", (lexem_id,))
    for b in eingabe.beispiele:
        if b.bedeutung_id is not None and b.bedeutung_id not in eigene:
            raise HTTPException(
                400, f"Bedeutung {b.bedeutung_id} gehört nicht zu diesem Wort.")
        db.execute("""INSERT INTO beispiel (lexem_id, bedeutung_id, satz,
                                            uebersetzung, quelle)
                      VALUES (?, ?, ?, ?, ?)""",
                   (lexem_id, b.bedeutung_id, b.satz, b.uebersetzung,
                    b.quelle))
    return {"lexem_id": lexem_id, "beispiele": len(eingabe.beispiele)}


@app.put("/api/bedeutungen/{bedeutung_id}/erklaerung")
def erklaerung_setzen(bedeutung_id: int, eingabe: ErklaerungSetzen,
                      request: Request = None, db: sqlite3.Connection = DB):
    """Der Erklärsatz zu einer Bedeutung — die Duden-Zeile.

    Nicht zu verwechseln mit `kontext`: der unterscheidet zwei
    Bedeutungen voneinander (»mit Fahrzeug«), die Erklärung sagt, was
    die Bedeutung ist. Beides nebeneinander, weil beides gebraucht
    wird.
    """
    _wache_rumpf(db, request, bedeutung_id=bedeutung_id)
    if dbm.zeile(db, "SELECT 1 FROM bedeutung WHERE id = ?",
                 (bedeutung_id,)) is None:
        raise HTTPException(404, f"Bedeutung {bedeutung_id} gibt es nicht")
    db.execute("UPDATE bedeutung SET notiz = ? WHERE id = ?",
               (eingabe.erklaerung or None, bedeutung_id))
    return {"bedeutung_id": bedeutung_id, "erklaerung": eingabe.erklaerung}


@app.delete("/api/lexeme/{lexem_id}", status_code=204)
def lexem_loeschen(lexem_id: int, db: sqlite3.Connection = DB):
    _holen(db, "lexem", lexem_id)
    db.execute("DELETE FROM lexem WHERE id = ?", (lexem_id,))


@app.post("/api/lexeme/{lexem_id}/formen", status_code=201)
def form_anlegen(lexem_id: int, eingabe: FormEingabe, db: sqlite3.Connection = DB):
    _holen(db, "lexem", lexem_id)
    form_id = _form_einfuegen(db, lexem_id, eingabe)
    aufgaben.erzeugen(db, lexem_id)
    return _holen(db, "form", form_id)


@app.patch("/api/formen/{form_id}")
def form_aendern(form_id: int, eingabe: FormEingabe, db: sqlite3.Connection = DB):
    f = _holen(db, "form", form_id)
    db.execute("""UPDATE form SET text = ?, merkmale = ?, ist_grundform = ?,
                       aussprache = ?, quelle = ?, geprueft = ?, notiz = ?
                   WHERE id = ?""",
               (eingabe.text, dbm.j_schreiben(eingabe.merkmale),
                int(eingabe.ist_grundform), eingabe.aussprache, eingabe.quelle,
                int(eingabe.geprueft), eingabe.notiz, form_id))
    aufgaben.erzeugen(db, f["lexem_id"])
    return _holen(db, "form", form_id)


@app.patch("/api/formen/{form_id}/teil")
def form_teil_aendern(form_id: int, eingabe: FormAendern,
                      db: sqlite3.Connection = DB):
    """Teiländerung. Was nicht genannt ist, bleibt stehen.

    Ändert sich Text oder Merkmalsbündel, fällt die Form auf **ungeprüft**
    zurück — sofern nicht ausdrücklich etwas anderes verlangt wird. Was
    geändert wurde, ist nicht mehr das, was jemand freigegeben hat.
    """
    f = _holen(db, "form", form_id)
    gesetzt = eingabe.model_dump(exclude_unset=True)
    if not gesetzt:
        raise HTTPException(400, "Nichts zu ändern angegeben")
    felder, werte = [], []
    inhaltlich = False
    if eingabe.text is not None:
        inhaltlich = inhaltlich or eingabe.text != f["text"]
        felder.append("text = ?"); werte.append(eingabe.text)
    if eingabe.merkmale is not None:
        try:
            geprueftes = mk.pruefen(eingabe.merkmale)
        except mk.MerkmalFehler as fehler:
            raise HTTPException(400, str(fehler))
        inhaltlich = inhaltlich or geprueftes != dbm.j_lesen(f["merkmale"])
        felder.append("merkmale = ?"); werte.append(dbm.j_schreiben(geprueftes))
    for name, wert in (("ist_grundform", eingabe.ist_grundform),
                       ("ist_variante", eingabe.ist_variante)):
        if wert is not None:
            felder.append(f"{name} = ?"); werte.append(int(wert))
    for name, wert in (("aussprache", eingabe.aussprache),
                       ("notiz", eingabe.notiz)):
        if wert is not None:
            felder.append(f"{name} = ?"); werte.append(wert)
    if eingabe.geprueft is not None:
        felder.append("geprueft = ?"); werte.append(int(eingabe.geprueft))
    elif inhaltlich and f["geprueft"]:
        felder.append("geprueft = 0")
    db.execute(f"UPDATE form SET {', '.join(felder)} WHERE id = ?",
               (*werte, form_id))
    aufgaben.erzeugen(db, f["lexem_id"])
    return _holen(db, "form", form_id)


@app.post("/api/formen/{form_id}/bestaetigen")
def form_bestaetigen(form_id: int, db: sqlite3.Connection = DB):
    """Eine generierte oder von der KI ergänzte Form als geprüft markieren.
    Erst danach wird sie abgefragt."""
    f = _holen(db, "form", form_id)
    db.execute("UPDATE form SET geprueft = 1 WHERE id = ?", (form_id,))
    aufgaben.erzeugen(db, f["lexem_id"])
    return _holen(db, "form", form_id)


@app.delete("/api/formen/{form_id}", status_code=204)
def form_loeschen(form_id: int, db: sqlite3.Connection = DB):
    f = _holen(db, "form", form_id)
    db.execute("DELETE FROM form WHERE id = ?", (form_id,))
    aufgaben.erzeugen(db, f["lexem_id"])


@app.post("/api/lexeme/{lexem_id}/bedeutungen", status_code=201)
def bedeutung_anlegen(lexem_id: int, eingabe: BedeutungEingabe,
                      db: sqlite3.Connection = DB):
    lexem = _holen(db, "lexem", lexem_id)
    s = _holen(db, "sammlung", lexem["sammlung_id"])
    bedeutung_id = _bedeutung_einfuegen(db, lexem_id, eingabe, s["grundsprache"])
    aufgaben.erzeugen(db, lexem_id)
    return _holen(db, "bedeutung", bedeutung_id)


@app.delete("/api/bedeutungen/{bedeutung_id}", status_code=204)
def bedeutung_loeschen(bedeutung_id: int, db: sqlite3.Connection = DB):
    b = _holen(db, "bedeutung", bedeutung_id)
    db.execute("DELETE FROM bedeutung WHERE id = ?", (bedeutung_id,))
    aufgaben.erzeugen(db, b["lexem_id"])


@app.post("/api/bedeutungen/{bedeutung_id}/uebersetzungen", status_code=201)
def uebersetzung_anlegen(bedeutung_id: int, eingabe: UebersetzungEingabe,
                         db: sqlite3.Connection = DB):
    b = _holen(db, "bedeutung", bedeutung_id)
    lexem = _holen(db, "lexem", b["lexem_id"])
    s = _holen(db, "sammlung", lexem["sammlung_id"])
    cur = db.execute("""INSERT INTO uebersetzung
                          (bedeutung_id, sprache, text, ist_haupt, quelle, geprueft)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                     (bedeutung_id, eingabe.sprache or s["grundsprache"],
                      eingabe.text, int(eingabe.ist_haupt), eingabe.quelle,
                      int(eingabe.geprueft)))
    aufgaben.erzeugen(db, b["lexem_id"])
    return _holen(db, "uebersetzung", cur.lastrowid)


@app.delete("/api/uebersetzungen/{uebersetzung_id}", status_code=204)
def uebersetzung_loeschen(uebersetzung_id: int, db: sqlite3.Connection = DB):
    u = _holen(db, "uebersetzung", uebersetzung_id)
    b = _holen(db, "bedeutung", u["bedeutung_id"])
    db.execute("DELETE FROM uebersetzung WHERE id = ?", (uebersetzung_id,))
    aufgaben.erzeugen(db, b["lexem_id"])


# ============================================================ Import

@app.post("/api/sammlungen/{sammlung_id}/import/vorschau")
def import_vorschau(sammlung_id: int, eingabe: ImportEingabe,
                    db: sqlite3.Connection = DB):
    """Liest die Datei und zeigt, was dabei herauskäme — ohne etwas zu ändern.

    Erkennt Trennzeichen, Kopfzeile und Spaltenrollen selbst; die Zuordnung
    lässt sich in der Antwort ablesen und beim Übernehmen berichtigen.
    """
    _holen(db, "sammlung", sammlung_id)
    try:
        return einlesen.vorschau(db, sammlung_id, eingabe.text, eingabe.trenner,
                                 eingabe.zuordnung, eingabe.hat_kopfzeile)
    except KeyError as fehler:
        raise HTTPException(404, str(fehler))


@app.post("/api/sammlungen/{sammlung_id}/import")
def import_uebernehmen(sammlung_id: int, eingabe: ImportEingabe,
                       db: sqlite3.Connection = DB):
    """Übernimmt die Datei in den Bestand."""
    _holen(db, "sammlung", sammlung_id)
    try:
        return einlesen.uebernehmen(db, sammlung_id, eingabe.text,
                                    eingabe.trenner, eingabe.zuordnung,
                                    eingabe.hat_kopfzeile, eingabe.doppelte)
    except mk.MerkmalFehler as fehler:
        raise HTTPException(400, str(fehler))
    except KeyError as fehler:
        raise HTTPException(404, str(fehler))


# ============================================================ Lernziele

@app.get("/api/lernziele")
def lernziele_liste(benutzer_id: int, nur_aktive: bool = True,
                    mit_fortschritt: bool = True, db: sqlite3.Connection = DB):
    _holen(db, "benutzer", benutzer_id)
    liste = lernziele.auflisten(db, benutzer_id, nur_aktive)
    if mit_fortschritt:
        for z in liste:
            z["fortschritt"] = lernziele.fortschritt(db, benutzer_id, z["id"])
    return liste


@app.post("/api/lernziele", status_code=201)
def lernziel_anlegen(eingabe: LernzielAnlegen, request: Request,
                     db: sqlite3.Connection = DB):
    _holen(db, "benutzer", eingabe.benutzer_id)
    _wache_rumpf(db, request, benutzer_id=eingabe.benutzer_id)
    try:
        return lernziele.anlegen(db, eingabe.benutzer_id, eingabe.name,
                                 eingabe.umfang, eingabe.termin, eingabe.ziel,
                                 eingabe.notiz)
    except ValueError as fehler:
        raise HTTPException(400, str(fehler))


@app.get("/api/lernziele/{lernziel_id}")
def lernziel_lesen(lernziel_id: int, db: sqlite3.Connection = DB):
    try:
        ziel = lernziele.lesen(db, lernziel_id)
    except KeyError as fehler:
        raise HTTPException(404, str(fehler))
    ziel["umfang_text"] = lernziele.umfang_beschreiben(db, ziel["umfang"])
    return ziel


@app.patch("/api/lernziele/{lernziel_id}")
def lernziel_aendern(lernziel_id: int, eingabe: LernzielAendern,
                     db: sqlite3.Connection = DB):
    _holen(db, "lernziel", lernziel_id)
    felder, werte = [], []
    # `None` heißt hier »nicht genannt, also unverändert« — sonst würde
    # eine Teiländerung alles andere löschen. Für das Leeren eines
    # Feldes gibt es darum den leeren String: ohne ihn ließe sich ein
    # einmal gesetzter Termin nie wieder entfernen, und das Ziel bliebe
    # für immer unter Zeitdruck.
    gesetzt = eingabe.model_dump(exclude_unset=True)
    for feld in ("name", "termin", "ziel", "notiz"):
        if feld not in gesetzt:
            continue
        wert = gesetzt[feld]
        if wert == "":
            wert = None               # ausdrücklich leeren
        elif wert is None:
            continue                  # nicht genannt
        felder.append(f"{feld} = ?")
        werte.append(wert)
    if eingabe.umfang is not None:
        felder.append("umfang = ?")
        werte.append(dbm.j_schreiben(eingabe.umfang))
    if eingabe.aktiv is not None:
        felder.append("aktiv = ?")
        werte.append(int(eingabe.aktiv))
    if felder:
        db.execute(f"UPDATE lernziel SET {', '.join(felder)} WHERE id = ?",
                   (*werte, lernziel_id))
    return lernziel_lesen(lernziel_id, db)


@app.delete("/api/lernziele/{lernziel_id}", status_code=204)
def lernziel_loeschen(lernziel_id: int, db: sqlite3.Connection = DB):
    _holen(db, "lernziel", lernziel_id)
    db.execute("DELETE FROM lernziel WHERE id = ?", (lernziel_id,))


@app.get("/api/lernziele/{lernziel_id}/fortschritt")
def lernziel_fortschritt(lernziel_id: int, benutzer_id: int,
                         db: sqlite3.Connection = DB):
    """Wie weit ist das Ziel — und was heißt das für heute?"""
    _holen(db, "benutzer", benutzer_id)
    try:
        return lernziele.fortschritt(db, benutzer_id, lernziel_id)
    except KeyError as fehler:
        raise HTTPException(404, str(fehler))


@app.post("/api/lernziele/{lernziel_id}/wuerfeln")
def lernziel_wuerfeln(lernziel_id: int, benutzer_id: int,
                      anzahl: int = Query(default=20, ge=1, le=100),
                      request: Request = None,
                      db: sqlite3.Connection = DB):
    """Noch einmal zusammenstellen — andere Wörter, gleicher Zuschnitt.

    Der Wurf wird AM ZIEL vermerkt, nicht nur in der Ansicht. Vorschau
    und Abfrage rechnen durch dieselbe Funktion; bliebe der Wurf in der
    Ansicht, zeigte »Was käme dran?« etwas anderes, als »Los« danach
    liefert.
    """
    _wache_rumpf(db, request, benutzer_id=benutzer_id)
    _holen(db, "benutzer", benutzer_id)
    z = _holen(db, "lernziel", lernziel_id)
    if z["benutzer_id"] != benutzer_id:
        raise HTTPException(403, "Dieses Lernziel gehört dir nicht.")
    db.execute("UPDATE lernziel SET wurf = wurf + 1 WHERE id = ?",
               (lernziel_id,))
    return lernziele.block(db, benutzer_id, lernziel_id, anzahl)


@app.get("/api/lernziele/{lernziel_id}/block")
def lernziel_block(lernziel_id: int, benutzer_id: int,
                   anzahl: int = Query(default=20, ge=1, le=100),
                   db: sqlite3.Connection = DB):
    """Der nächste Lernblock: Fälliges, Wackliges und so viel Neues, wie der
    Termin verlangt — verschränkt gemischt, mit Begründung des Zuschnitts."""
    _holen(db, "benutzer", benutzer_id)
    try:
        return lernziele.block(db, benutzer_id, lernziel_id, anzahl)
    except KeyError as fehler:
        raise HTTPException(404, str(fehler))


# ====================================================== Qualität der Daten

@app.get("/api/lexeme/{lexem_id}/pruefung")
def lexem_pruefen(lexem_id: int, db: sqlite3.Connection = DB):
    """Taugt dieser Eintrag für das, was der Trainer kann?

    Prüft auf Dinge, die formal zulässig, aber inhaltlich nutzlos sind:
    fehlende Übersetzung, lückiges Paradigma, nicht ableitbarer Stamm,
    Formen außerhalb jeder Formgruppe. Gedacht vor allem für den Agenten am
    MCP, der nach dem Eintragen nicht selbst nachsieht.
    """
    try:
        return qualitaet.pruefen(db, lexem_id)
    except KeyError as fehler:
        raise HTTPException(404, str(fehler))


@app.get("/api/sammlungen/{sammlung_id}/pruefung")
def sammlung_pruefen(sammlung_id: int, nur_mangelhafte: bool = True,
                     db: sqlite3.Connection = DB):
    """Alle Einträge einer Sammlung auf einmal prüfen."""
    _holen(db, "sammlung", sammlung_id)
    return qualitaet.pruefen_sammlung(db, sammlung_id, nur_mangelhafte)


# ========================================================== Wörterbuch

@app.get("/api/sammlungen/{sammlung_id}/woerterbuch")
def woerterbuch(sammlung_id: int, suche: str = Query(min_length=1),
                anzahl: int = Query(default=30, le=200),
                db: sqlite3.Connection = DB):
    """Nachschlagen — über Lemma, ALLE Formen und alle Übersetzungen.

    Der eigentliche Gewinn gegenüber einer Wortliste: wer in einem Text
    »έγραψαν« liest, findet damit den Eintrag γράφω und bekommt gesagt, welche
    Form das ist. Dafür braucht es die Formentabelle, und die ist da.
    """
    _holen(db, "sammlung", sammlung_id)
    muster = f"%{suche.strip()}%"
    treffer = dbm.zeilen(db, """
        SELECT DISTINCT l.id
          FROM lexem l
          LEFT JOIN form f ON f.lexem_id = l.id
          LEFT JOIN bedeutung b ON b.lexem_id = l.id
          LEFT JOIN uebersetzung u ON u.bedeutung_id = b.id
         WHERE l.sammlung_id = ?
           AND (l.lemma LIKE ? OR f.text LIKE ? OR u.text LIKE ?)
         ORDER BY
           CASE WHEN l.lemma = ? THEN 0
                WHEN l.lemma LIKE ? THEN 1
                ELSE 2 END,
           l.lemma
         LIMIT ?""",
        (sammlung_id, muster, muster, muster, suche.strip(),
         f"{suche.strip()}%", anzahl))

    s = _holen(db, "sammlung", sammlung_id)
    begriff = suche.strip().casefold()
    eintraege = []
    for t in treffer:
        lexem = _lexem_ausbauen(db, _holen(db, "lexem", t["id"]))
        # Sagen, WARUM der Eintrag gefunden wurde — bei einer Formsuche ist
        # genau das die Auskunft, die man wollte.
        fundstellen = []
        if begriff in lexem["lemma"].casefold():
            fundstellen.append({"wo": "lemma", "text": lexem["lemma"]})
        for f in lexem["formen"]:
            if begriff in f["text"].casefold():
                fundstellen.append({"wo": "form", "text": f["text"],
                                    "beschriftung": f["beschriftung"]})
        for b in lexem["bedeutungen"]:
            for u in b["uebersetzungen"]:
                if begriff in u["text"].casefold():
                    fundstellen.append({"wo": "uebersetzung", "text": u["text"]})
        lexem["fundstellen"] = fundstellen
        eintraege.append(lexem)
    return {"suche": suche, "gefunden": len(eintraege), "eintraege": eintraege,
            "sprache": s["sprache"]}


# ============================================================ Lernen

@app.get("/api/sammlungen/{sammlung_id}/lernstand")
def lernstand_lesen(sammlung_id: int, benutzer_id: int,
                    anzahl: int = Query(default=40, le=200),
                    db: sqlite3.Connection = DB):
    """Was sitzt, und woran hakt es? Je Wort, nicht je Aufgabe."""
    _holen(db, "sammlung", sammlung_id)
    _holen(db, "benutzer", benutzer_id)
    return lernmodul.lernstand(db, benutzer_id, sammlung_id, anzahl)


@app.get("/api/statistik")
def statistik_lesen(benutzer_id: int, sammlung_id: int | None = None,
                    request: Request = None, db: sqlite3.Connection = DB):
    """Der eigene Lernfortschritt — alles für die Seite in einem Aufruf."""
    _wache_rumpf(db, request, benutzer_id=benutzer_id,
                 sammlung_id=sammlung_id)
    _holen(db, "benutzer", benutzer_id)
    return statistik.alles(db, benutzer_id, sammlung_id)


@app.get("/api/lernen/stand")
def lern_stand(benutzer_id: int, sammlung_id: int | None = None,
               db: sqlite3.Connection = DB):
    _holen(db, "benutzer", benutzer_id)
    return lernmodul.stand(db, benutzer_id, sammlung_id)


@app.get("/api/lernen/naechste")
def lern_naechste(benutzer_id: int, sammlung_id: int | None = None,
                  lektion_id: int | None = None,
                  bis_lektion: int | None = Query(
                      default=None,
                      description="nur Wörter aus Lektionen bis zu dieser "
                                  "Nummer — der übliche Schnitt beim "
                                  "Mitlernen mit einem Lehrwerk"),
                  typ: list[str] | None = Query(default=None),
                  wortart: list[str] | None = Query(
                      default=None,
                      description="Lernmodus: nur diese Wortarten, z.B. "
                                  "verb oder adjektiv"),
                  formgruppe: list[str] | None = Query(
                      default=None,
                      description="Lernmodus: nur diese Formgruppen, z.B. "
                                  "eine einzelne Zeitform"),
                  nur: str | None = None,
                  anzahl: int = Query(default=1, ge=1, le=50),
                  lernziel_id: int | None = None,
                  ohne_grenze: bool = Query(
                      default=False,
                      description="über die Tagesdosis hinaus weitermachen"),
                  db: sqlite3.Connection = DB):
    """Die nächsten Aufgaben, mit Begründung und Terminvorschau.

    nur=neu | faellig | fehler | frei — "frei" übt ohne Terminlogik.
    """
    _holen(db, "benutzer", benutzer_id)
    if nur not in (None, "neu", "faellig", "fehler", "frei"):
        raise HTTPException(400, "nur muss neu, faellig, fehler oder frei sein")
    # Mit Namen, nicht nach Stellung: die Reihenfolge der Parameter hat
    # sich schon einmal geändert, und ein positionaler Aufruf rutschte
    # dabei stillschweigend um eine Stelle.
    return lernmodul.naechste(db, benutzer_id, sammlung_id=sammlung_id,
                              lektion_id=lektion_id, typen=typ,
                              wortarten=wortart, formgruppen=formgruppe,
                              nur=nur, anzahl=anzahl,
                              lernziel_id=lernziel_id,
                              bis_lektion=bis_lektion,
                              ohne_grenze=ohne_grenze)


@app.post("/api/lernen/pruefen")
def lern_pruefen(eingabe: PruefenEingabe, request: Request,
                 db: sqlite3.Connection = DB):
    """Prüft die Antwort, ohne den Lernstand zu verändern."""
    _holen(db, "benutzer", eingabe.benutzer_id)
    _wache_rumpf(db, request, benutzer_id=eingabe.benutzer_id,
                 aufgabe_id=eingabe.aufgabe_id, schreiben=False)
    try:
        return lernmodul.pruefen(db, eingabe.benutzer_id, eingabe.aufgabe_id,
                                 eingabe.antwort, eingabe.denkzeit_ms,
                                 eingabe.versuche, eingabe.aufgedeckt,
                                 eingabe.tipps)
    except KeyError as fehler:
        raise HTTPException(404, str(fehler))


@app.post("/api/lernen/aufdecken")
def lern_aufdecken(eingabe: EingriffEingabe, request: Request,
                   db: sqlite3.Connection = DB):
    """Lösung zeigen, ohne zu bewerten — für "ich weiß es nicht" und für das
    Einprägen vor dem Schreiben im Legastheniemodus."""
    _holen(db, "benutzer", eingabe.benutzer_id)
    _holen(db, "aufgabe", eingabe.aufgabe_id)
    _wache_rumpf(db, request, benutzer_id=eingabe.benutzer_id,
                 aufgabe_id=eingabe.aufgabe_id, schreiben=False)
    return lernmodul.aufdecken(db, eingabe.benutzer_id, eingabe.aufgabe_id)


@app.get("/api/lernen/tipp")
def lern_tipp(benutzer_id: int, aufgabe_id: int, stufe: int = 1,
              request: Request = None, db: sqlite3.Connection = DB):
    """Ein Tipp statt der Lösung — die Abfrage läuft weiter.

    Die erwartete Antwort steht bewusst NICHT in der Rückgabe: was der
    Browser nicht bekommt, kann er auch nicht verraten.
    """
    _holen(db, "benutzer", benutzer_id)
    _holen(db, "aufgabe", aufgabe_id)
    _wache_rumpf(db, request, benutzer_id=benutzer_id,
                 aufgabe_id=aufgabe_id, schreiben=False)
    try:
        return lernmodul.tipp(db, benutzer_id, aufgabe_id, stufe)
    except KeyError as fehler:
        raise HTTPException(404, str(fehler))


@app.post("/api/lernen/bewerten")
def lern_bewerten(eingabe: BewertenEingabe, request: Request,
                  db: sqlite3.Connection = DB):
    _holen(db, "benutzer", eingabe.benutzer_id)
    _holen(db, "aufgabe", eingabe.aufgabe_id)
    _wache_rumpf(db, request, benutzer_id=eingabe.benutzer_id,
                 aufgabe_id=eingabe.aufgabe_id)
    try:
        return lernmodul.bewerten(
            db, eingabe.benutzer_id, eingabe.aufgabe_id, eingabe.bewertung,
            eingabe.antwort, eingabe.urteil, eingabe.dauer_ms,
            eingabe.denkzeit_ms, eingabe.versuche, eingabe.aufgedeckt,
            eingabe.fehlerart, eingabe.tipps)
    except ValueError as fehler:
        raise HTTPException(400, str(fehler))


@app.post("/api/lernen/aussetzen")
def lern_aussetzen(eingabe: EingriffEingabe, request: Request,
                   db: sqlite3.Connection = DB):
    _wache_rumpf(db, request, benutzer_id=eingabe.benutzer_id,
                 aufgabe_id=eingabe.aufgabe_id)
    lernmodul.aussetzen(db, eingabe.benutzer_id, eingabe.aufgabe_id, True)
    return {"zustand": "ausgesetzt"}


@app.post("/api/lernen/fortsetzen")
def lern_fortsetzen(eingabe: EingriffEingabe, request: Request,
                    db: sqlite3.Connection = DB):
    _wache_rumpf(db, request, benutzer_id=eingabe.benutzer_id,
                 aufgabe_id=eingabe.aufgabe_id)
    lernmodul.aussetzen(db, eingabe.benutzer_id, eingabe.aufgabe_id, False)
    return {"zustand": "wieder dabei"}


@app.post("/api/lernen/zuruecksetzen")
def lern_zuruecksetzen(eingabe: EingriffEingabe, request: Request,
                       db: sqlite3.Connection = DB):
    _wache_rumpf(db, request, benutzer_id=eingabe.benutzer_id,
                 aufgabe_id=eingabe.aufgabe_id)
    lernmodul.zuruecksetzen(db, eingabe.benutzer_id, eingabe.aufgabe_id)
    return {"zustand": "neu"}


@app.post("/api/lernen/termin")
def lern_termin(eingabe: EingriffEingabe, request: Request,
                db: sqlite3.Connection = DB):
    _wache_rumpf(db, request, benutzer_id=eingabe.benutzer_id,
                 aufgabe_id=eingabe.aufgabe_id)
    if not eingabe.datum:
        raise HTTPException(400, "datum fehlt (Format JJJJ-MM-TT)")
    try:
        lernmodul.termin_setzen(db, eingabe.benutzer_id, eingabe.aufgabe_id,
                                eingabe.datum)
    except ValueError:
        raise HTTPException(400, "datum muss JJJJ-MM-TT sein")
    return {"faellig": eingabe.datum}


@app.get("/api/lernen/verlauf")
def lern_verlauf(benutzer_id: int, aufgabe_id: int | None = None,
                 anzahl: int = Query(default=100, le=1000),
                 db: sqlite3.Connection = DB):
    """Das Wiederholungsprotokoll — Grundlage für Statistik und für die
    spätere Optimierung der FSRS-Parameter."""
    if aufgabe_id is not None:
        return dbm.zeilen(db, """SELECT * FROM wiederholung
                                  WHERE benutzer_id = ? AND aufgabe_id = ?
                                  ORDER BY zeitpunkt DESC LIMIT ?""",
                          (benutzer_id, aufgabe_id, anzahl))
    return dbm.zeilen(db, """SELECT * FROM wiederholung WHERE benutzer_id = ?
                              ORDER BY zeitpunkt DESC LIMIT ?""",
                      (benutzer_id, anzahl))


# ================================================================== MCP

# Jede Anfrage gehört zu einer Person: das Token ist an ein Profil gebunden,
# und alles, was darüber geschieht, geschieht in deren Namen und nur auf
# deren Bestand. Ein gemeinsames Geheimnis wäre hier falsch — man könnte
# weder zuordnen noch einzeln entziehen.
#
# Die Schnittstelle schaltet sich selbst frei, sobald es ein Token gibt.
# Ohne Token kommt niemand hinein, auch nicht versehentlich.
#
# Das Merkmal darf in drei Kopfzeilen stehen. Der Grund für die dritte ist
# ärgerlich, aber bindend: der Konnektor in claude.ai lässt nur eine feste
# Liste von Headernamen zu. Weder "Authorization" noch ein eigener Name
# stehen darauf — "x-account-key" schon.
MCP_KOPFZEILEN = ("authorization", "x-vokabel-token", "x-account-key")

# Die öffentliche Adresse der Schnittstelle — nur für die Anleitung, damit
# dort die Adresse zum Abschreiben steht und kein Platzhalter. Sie kommt
# aus der Umgebung, weil sie zur Anlage gehört und nicht in den Quelltext.
MCP_URL = os.environ.get("VOKABEL_MCP_URL", "").strip()

# Die Adresse der Oberfläche von außen — die mit Cloudflare Access davor.
# Sie wird für OAuth gebraucht und NUR dafür: der Schritt, in dem ein
# Mensch einwilligt, muss hinter der Anmeldung liegen. Ohne sie bietet
# der Trainer kein OAuth an, statt einen Endpunkt zu nennen, der
# ungeschützt wäre.
WEB_URL = os.environ.get("VOKABEL_WEB_URL", "").strip().rstrip("/")


def _mcp_geheimnis(request: Request) -> str:
    kopf = request.headers.get("authorization", "")
    if kopf[:7].lower() == "bearer ":
        return kopf[7:].strip()
    for name in MCP_KOPFZEILEN[1:]:
        wert = request.headers.get(name, "").strip()
        if wert:
            # Auch hier ein vorangestelltes "Bearer " vertragen, falls es
            # jemand aus Gewohnheit mitschreibt.
            return wert[7:].strip() if wert[:7].lower() == "bearer " else wert
    return ""


def _mcp_hinweis() -> dict:
    """Die Kopfzeile, mit der ein 401 sagt, WO die Anmeldeangaben stehen.

    RFC 9728 sieht sie vor, und die MCP-Spezifikation verlangt sie vom
    Ressourcenserver. Sie ist hier aber nicht bloß Formsache, sondern
    der einzige Weg: die vorgeschriebenen Stellen unter /.well-known
    sind auf diesem Namen von Cloudflare gesperrt — nur /mcp kommt
    durch. Über diese Kopfzeile nennt der Server die Adresse, die
    tatsächlich erreichbar ist, statt darauf zu hoffen, dass der Client
    rät.
    """
    if not MCP_URL:
        return {}
    return {"WWW-Authenticate":
            f'Bearer resource_metadata='
            f'"{MCP_URL}/.well-known/oauth-protected-resource"'}


def _mcp_person(request: Request, db: sqlite3.Connection) -> dict:
    # Ohne Access davor trägt das Merkmal die Last allein. Darum eine Sperre
    # gegen Durchprobieren — erraten lässt sich ein 256-Bit-Merkmal zwar
    # nicht, aber eine Liste geleakter Merkmale ließe sich durchgehen.
    wer = drossel.kennung_aus_anfrage(request)
    rest = drossel.gesperrt(wer)
    if rest > 0:
        raise HTTPException(429, f"Zu viele Fehlversuche. Wieder möglich in "
                                 f"{int(rest // 60) + 1} Minuten.",
                            headers={"Retry-After": str(int(rest) + 1)})

    geheimnis = _mcp_geheimnis(request)
    treffer = zugang.person_zu_token(db, geheimnis)
    if treffer is None:
        sperre = drossel.fehlversuch(wer)
        # Welche Kopfzeilen kamen an? NUR die Namen — Werte nie, die wären
        # Geheimnisse. Ohne das lässt sich ein fehlgeleiteter Konnektor
        # nicht einkreisen: man sieht bloß 401 und weiß nicht, ob die
        # Kopfzeile fehlte oder der Wert nicht stimmte.
        protokoll.warning(
            "MCP abgewiesen von %s · Kopfzeilen: %s · Merkmal mitgeschickt: %s",
            wer, ", ".join(sorted(request.headers.keys())),
            "ja, %d Zeichen" % len(geheimnis) if geheimnis else "NEIN")
        if not zugang.mcp_eingeschaltet(db):
            raise HTTPException(503, "Die MCP-Schnittstelle ist noch nicht "
                                     "eingerichtet. In den Einstellungen des "
                                     "Trainers ein Zugangsmerkmal anlegen.")
        hinweis = (" Weitere Versuche sind für eine Weile gesperrt."
                   if sperre > 0 else "")
        raise HTTPException(401, "Kein gültiges Zugangsmerkmal. Erwartet wird "
                                 "es in der Kopfzeile Authorization (Bearer) "
                                 "oder x-account-key." + hinweis,
                            headers=_mcp_hinweis())
    drossel.geschafft(wer)
    return dict(treffer["benutzer"])


@app.post("/mcp")
async def mcp_endpunkt(request: Request, db: sqlite3.Connection = DB):
    """MCP über HTTP (Streamable HTTP, zustandslos).

    Zustandslos heißt: keine Sitzungskennung, jede Anfrage steht für sich.
    Für einen Werkzeugserver ohne von sich aus gesendete Nachrichten ist das
    zulässig und spart die ganze Sitzungsverwaltung.
    """
    person = _mcp_person(request, db)
    try:
        inhalt = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={
            "jsonrpc": "2.0", "id": None,
            "error": {"code": -32700, "message": "Kein gültiges JSON"}})

    stapel = inhalt if isinstance(inhalt, list) else [inhalt]
    antworten = []
    for nachricht in stapel:
        if not isinstance(nachricht, dict):
            continue
        antwort = mcp_dienst.behandeln(nachricht, db, person)
        if antwort is not None:
            antworten.append(antwort)

    if not antworten:
        return Response(status_code=202)
    return JSONResponse(content=antworten if isinstance(inhalt, list)
                        else antworten[0])


@app.get("/mcp")
async def mcp_strom(request: Request, db: sqlite3.Connection = DB):
    """Dieser Server sendet nichts von sich aus, also kein Ereignisstrom."""
    _mcp_person(request, db)
    return Response(status_code=405, headers={"Allow": "POST"})


@app.delete("/mcp")
async def mcp_beenden(request: Request, db: sqlite3.Connection = DB):
    """Zustandslos — es gibt keine Sitzung zu beenden."""
    _mcp_person(request, db)
    return Response(status_code=204)


# ------------------------------------------------- Zugangsmerkmale

@app.get("/api/benutzer/{benutzer_id}/mcp-token")
def mcp_token_liste(benutzer_id: int, db: sqlite3.Connection = DB):
    """Die Zugangsmerkmale einer Person. Das Geheimnis selbst steht nirgends
    gespeichert — nur sein Streuwert und die ersten Zeichen."""
    _holen(db, "benutzer", benutzer_id)
    return zugang.token_auflisten(db, benutzer_id)


@app.post("/api/benutzer/{benutzer_id}/mcp-token", status_code=201)
def mcp_token_anlegen(benutzer_id: int, eingabe: McpTokenAnlegen,
                      db: sqlite3.Connection = DB):
    """Legt ein Zugangsmerkmal an. Das Geheimnis wird NUR HIER einmal
    zurückgegeben und ist danach nicht mehr abrufbar."""
    _holen(db, "benutzer", benutzer_id)
    return zugang.token_anlegen(db, benutzer_id, eingabe.name)


@app.delete("/api/mcp-token/{token_id}", status_code=204)
def mcp_token_zuruecknehmen(token_id: int, db: sqlite3.Connection = DB):
    _holen(db, "mcp_token", token_id)
    zugang.token_zuruecknehmen(db, token_id)


# ============================================================ Identität

@app.get("/api/ich")
def wer_bin_ich(request: Request, db: sqlite3.Connection = DB):
    """Wer fragt hier an?

    Von außen steht Cloudflare Access davor und hat die Mailadresse schon
    geprüft; dann steht die Identität fest und der Profilwähler entfällt.
    Im Heimnetz gibt es keine solche Angabe — dort wählt man sein Profil wie
    bisher aus der Liste.
    """
    return identitaet.wer_bin_ich(db, request.headers)


# ============================================================== Abtippen

@app.get("/api/sammlungen/{sammlung_id}/abtippen")
def abtippen_reihe(sammlung_id: int, lektion_id: int | None = None,
                   db: sqlite3.Connection = DB):
    """Die Wörter zum Abtippen, in der Reihenfolge des Lehrwerks."""
    _holen(db, "sammlung", sammlung_id)
    return abtippen.reihe(db, sammlung_id, lektion_id)


@app.post("/api/abtippen/pruefen")
def abtippen_pruefen(eingabe: AbtippenEingabe, db: sqlite3.Connection = DB):
    """Stimmt das Abgetippte? Schreibt bewusst KEINEN Lernstand fort."""
    try:
        return abtippen.pruefen(db, eingabe.lexem_id, eingabe.eingabe)
    except KeyError as fehler:
        raise HTTPException(404, str(fehler))


# ================================================================ OAuth
#
# Nur für Konnektoren ohne eigene Kopfzeile — siehe oauth.py. Die
# Anmeldung des Menschen macht Cloudflare Access; hier wird sie nur
# verlangt.

async def _formular(request: Request) -> dict[str, str]:
    """Den Rumpf lesen, ohne `request.form()`.

    Starlette verlangt dafür `python-multipart`, und dieses Projekt
    nimmt keine neue Abhängigkeit auf. Gebraucht wird ohnehin nur
    `application/x-www-form-urlencoded` — das schreibt der
    OAuth-Standard für den Tokenendpunkt vor, und ein HTML-Formular
    schickt es von sich aus. JSON wird mitgenommen, weil manche
    Konnektoren es trotzdem senden.
    """
    from urllib.parse import parse_qsl
    rumpf = (await request.body()).decode("utf-8", "replace")
    art = request.headers.get("content-type", "")
    if art.startswith("application/json"):
        try:
            daten = dbm.j_lesen(rumpf) or {}
            return {k: str(v) for k, v in daten.items() if v is not None}
        except Exception:
            return {}
    return dict(parse_qsl(rumpf, keep_blank_values=True))


def _oauth_bereit() -> None:
    if not (WEB_URL and MCP_URL):
        raise HTTPException(
            503, "OAuth ist nicht eingerichtet. Dafür müssen "
                 "VOKABEL_WEB_URL und VOKABEL_MCP_URL gesetzt sein.")


def _mcp_wurzel() -> str:
    """Der Ursprung der MCP-Adresse, ohne Pfad."""
    ohne = MCP_URL.split("//", 1)
    if len(ohne) != 2:
        return MCP_URL.rstrip("/")
    schema, rest = ohne
    return f"{schema}//{rest.split('/', 1)[0]}"


# Beide Endpunkte hängen zusätzlich unter /mcp. Der Grund steht nicht im
# Standard, sondern im Tunnel: auf dem Namen der Schnittstelle ist nur
# der Pfad /mcp freigegeben, alles daneben beantwortet Cloudflare selbst
# mit einem leeren 404 — die Anwendung sieht es nie. Gemessen:
#
#   /mcp/irgendwas   404 {"detail":"Not Found"}   ← die Anwendung
#   /.well-known/…   404 (leerer Rumpf)           ← Cloudflare
#
# Die vorgeschriebene Stelle bleibt bestehen, damit es richtig wird,
# sobald der Pfad bei Cloudflare freigegeben ist. Angekündigt wird aber
# die Adresse, die HEUTE durchkommt.
# WO dieses Blatt liegen DARF, bestimmt der Herausgeber: RFC 8414 §3.3
# verlangt, dass der darin genannte `issuer` genau zu der Adresse
# passt, unter der es abgerufen wurde. Ein Blatt an der falschen
# Stelle ist darum schlimmer als keines — ein prüfender Client
# verwirft es und sucht weiter. Genau daran ist ChatGPT gescheitert:
# es holte das Blatt (200) und ging danach trotzdem weiter auf die
# Suche, weil der Herausgeber »…/mcp« hieß und die Adresse auf den
# bloßen Namen zeigte.
#
# Darum ist der Herausgeber jetzt der Name ohne Pfad, und das Blatt
# liegt an der dazu passenden Stelle. Die Fassung unter /mcp bleibt
# als Notnagel für den Fall, dass die Tunnelroute für /.well-known
# einmal fehlt — dann ist sie das einzig Erreichbare.
@app.get("/.well-known/oauth-authorization-server")
@app.get("/mcp/.well-known/oauth-authorization-server")
def oauth_kennblatt():
    """Was ein Konnektor über diesen Autorisierungsdienst wissen muss.

    Die beiden Endpunkte liegen mit Absicht auf VERSCHIEDENEN Namen:
    der Autorisierungsschritt dort, wo Access davorsteht und einen
    Menschen anmeldet, der Tokentausch dort, wo kein Mensch mehr
    beteiligt ist und ein Anmeldefenster nur im Weg wäre.
    """
    _oauth_bereit()
    return {
        "issuer": _mcp_wurzel(),
        # Auf DEMSELBEN Namen wie der Herausgeber. Dass hier vorher der
        # andere Name stand, war die zweite Auffälligkeit: erlaubt,
        # aber ungewöhnlich, und manche Clients nehmen es nicht an.
        # Die Weiterleitung dorthin macht jetzt der Server selbst —
        # siehe oauth_weiterleiten. Am Ablauf ändert das nichts: der
        # Mensch landet weiterhin hinter der Access-Anmeldung.
        "authorization_endpoint": f"{_mcp_wurzel()}/mcp/oauth/authorize",
        # Unter /mcp, weil nur dieser Pfad durch den Tunnel kommt.
        "token_endpoint": f"{_mcp_wurzel()}/mcp/oauth/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
        "scopes_supported": ["vokabeln"],
    }


# Die Ressource HAT einen Pfad (/mcp), hier gehört er also hinter den
# .well-known-Teil. Die Fassung unter /mcp daneben ist die, auf die
# die WWW-Authenticate-Kopfzeile zeigt; RFC 9728 lässt dort jede
# Adresse zu, und sie kommt auch ohne Tunnelroute durch.
@app.get("/.well-known/oauth-protected-resource/mcp")
@app.get("/mcp/.well-known/oauth-protected-resource")
def oauth_ressource():
    _oauth_bereit()
    return {"resource": MCP_URL,
            "authorization_servers": [_mcp_wurzel()],
            "scopes_supported": ["vokabeln"]}


def _einwilligungsseite(vorgang: dict, handgriff: str, person: dict,
                        client: dict) -> HTMLResponse:
    from html import escape as _e
    return HTMLResponse(f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zugriff erlauben?</title>
<style>
  body {{ font: 16px/1.6 system-ui, sans-serif; margin: 0; padding: 2rem 1rem;
         background: #f7f6f3; color: #222; display: flex;
         justify-content: center; }}
  main {{ max-width: 32rem; background: #fff; border-radius: .6rem;
          padding: 1.5rem 1.8rem; box-shadow: 0 1px 4px rgba(0,0,0,.12); }}
  h1 {{ font-size: 1.3rem; margin: 0 0 1rem; }}
  dl {{ display: grid; grid-template-columns: auto 1fr; gap: .3rem .9rem;
        margin: 1rem 0; }}
  dt {{ color: #667; }}
  dd {{ margin: 0; font-weight: 600; }}
  .knoepfe {{ display: flex; gap: .6rem; margin-top: 1.4rem; }}
  button {{ font: inherit; padding: .5rem 1.1rem; border-radius: .4rem;
            border: 1px solid #ccc; background: #fff; cursor: pointer; }}
  button.ja {{ background: #1d4ed8; border-color: #1d4ed8; color: #fff; }}
  .leise {{ color: #667; font-size: .92rem; }}
</style></head><body><main>
<h1>Zugriff auf deine Vokabeln erlauben?</h1>
<p><b>{_e(client["name"])}</b> möchte in deinem Namen auf den
   Vokabeltrainer zugreifen: Wörter lesen, anlegen und ändern.</p>
<dl>
  <dt>Dein Profil</dt><dd>{_e(person["name"])}</dd>
  <dt>Angemeldet als</dt><dd>{_e(vorgang["mail"])}</dd>
  <dt>Zurück an</dt><dd class="leise">{_e(vorgang["rueckadresse"])}</dd>
</dl>
<p class="leise">Erlaubst du es, bekommt {_e(client["name"])} ein eigenes
   Zugangsmerkmal. Du kannst es jederzeit in den Einstellungen unter
   deinen Zugängen wieder zurücknehmen — dann ist die Verbindung sofort
   tot.</p>
<form method="post" action="/oauth/authorize" class="knoepfe">
  <input type="hidden" name="vorgang" value="{_e(handgriff)}">
  <button class="ja" name="antwort" value="ja">Erlauben</button>
  <button name="antwort" value="nein">Abbrechen</button>
</form>
</main></body></html>""")


def _zurueck(rueckadresse: str, **felder) -> RedirectResponse:
    from urllib.parse import urlencode
    teile = {k: v for k, v in felder.items() if v is not None}
    trenner = "&" if "?" in rueckadresse else "?"
    return RedirectResponse(f"{rueckadresse}{trenner}{urlencode(teile)}",
                            status_code=303)


@app.get("/mcp/oauth/authorize")
def oauth_weiterleiten(request: Request):
    """Schickt den Browser zu der Adresse, hinter der die Anmeldung steht.

    Der Umweg hat einen einzigen Zweck: im Kennblatt soll der
    Autorisierungsendpunkt auf demselben Namen stehen wie der
    Herausgeber. Die Anmeldung selbst kann hier nicht stattfinden —
    vor diesem Namen steht kein Access, und ohne geprüfte Mailadresse
    verweigert die Einwilligungsseite ohnehin.
    """
    _oauth_bereit()
    frage = request.url.query
    return RedirectResponse(f"{WEB_URL}/oauth/authorize"
                            + (f"?{frage}" if frage else ""), status_code=302)


@app.get("/oauth/authorize")
def oauth_autorisieren(request: Request,
                       client_id: str = "",
                       redirect_uri: str = "",
                       response_type: str = "code",
                       code_challenge: str = "",
                       code_challenge_method: str = "",
                       state: str | None = None,
                       scope: str | None = None,
                       db: sqlite3.Connection = DB):
    """Die Einwilligungsseite.

    HIER liegt die eigentliche Absicherung, und sie ist eine einzige
    Bedingung: ohne eine von Cloudflare Access geprüfte Mailadresse
    passiert nichts. Dieser Endpunkt gehört deshalb auf den Namen, hinter
    dem Access steht. Wird er anders erreicht — im Heimnetz oder über
    den Namen ohne Access —, gibt es keine Einwilligung, sondern eine
    Erklärung.
    """
    _oauth_bereit()
    if response_type != "code":
        raise HTTPException(400, "Nur response_type=code wird unterstützt.")

    mail = identitaet.mail_aus_anfrage(request.headers)
    if not mail:
        raise HTTPException(
            403, "Diese Seite muss über die von außen erreichbare Adresse "
                 "aufgerufen werden, bei der die Anmeldung davorsteht. Nur "
                 "dort steht fest, wer einwilligt.")
    person = identitaet.profil_fuer_mail(db, mail, anlegen=False)
    if person is None:
        raise HTTPException(
            403, f"Zu {mail} gibt es kein Profil im Trainer. Erst anlegen "
                 f"und die Adresse dort hinterlegen.")
    try:
        handgriff = oauth.vorgang_anlegen(
            db, client_id, person["id"], mail, redirect_uri,
            code_challenge, code_challenge_method, state)
        vorgang = oauth.vorgang_lesen(db, handgriff, mail)
    except oauth.OAuthFehler as fehler:
        # Fehler VOR der Prüfung der Rückadresse werden angezeigt und
        # nicht weitergeleitet: an eine unbestätigte Adresse darf nichts
        # geschickt werden, auch keine Fehlermeldung.
        raise HTTPException(400, f"{fehler.code}: {fehler.beschreibung}")
    return _einwilligungsseite(vorgang, handgriff,
                               oauth.client_lesen(db, client_id) or {},
                               person)


@app.post("/oauth/authorize")
async def oauth_einwilligen(request: Request, db: sqlite3.Connection = DB):
    _oauth_bereit()
    mail = identitaet.mail_aus_anfrage(request.headers)
    if not mail:
        raise HTTPException(403, "Keine geprüfte Anmeldung.")
    formular = await _formular(request)
    handgriff = formular.get("vorgang", "")
    try:
        if formular.get("antwort") == "ja":
            e = oauth.einwilligen(db, handgriff, mail)
            db.commit()
            return _zurueck(e["rueckadresse"], code=e["code"],
                            state=e["zustand"])
        e = oauth.abbrechen(db, handgriff, mail)
        db.commit()
        return _zurueck(e["rueckadresse"], error="access_denied",
                        state=e["zustand"])
    except oauth.OAuthFehler as fehler:
        raise HTTPException(400, f"{fehler.code}: {fehler.beschreibung}")


@app.post("/oauth/token")
@app.post("/mcp/oauth/token")
async def oauth_token(request: Request, db: sqlite3.Connection = DB):
    """Code gegen Zugangsmerkmal. Kein Mensch mehr beteiligt.

    Mit derselben Sperre gegen Durchprobieren wie die Schnittstelle
    selbst: ein Code ist zwar kurzlebig, aber der Endpunkt steht offen
    im Netz.
    """
    _oauth_bereit()
    wer = drossel.kennung_aus_anfrage(request)
    rest = drossel.gesperrt(wer)
    if rest > 0:
        raise HTTPException(429, "Zu viele Fehlversuche.",
                            headers={"Retry-After": str(int(rest) + 1)})
    formular = await _formular(request)
    if formular.get("grant_type") != "authorization_code":
        return JSONResponse({"error": "unsupported_grant_type"}, 400)
    try:
        antwort = oauth.code_einloesen(
            db, formular.get("code", ""), formular.get("client_id", ""),
            formular.get("redirect_uri", ""),
            formular.get("code_verifier", ""),
            formular.get("client_secret") or None)
    except oauth.OAuthFehler as fehler:
        db.commit()        # auch die Rücknahme bei zweiter Einlösung
        drossel.fehlversuch(wer)
        return JSONResponse({"error": fehler.code,
                             "error_description": fehler.beschreibung}, 400)
    drossel.geschafft(wer)
    oauth.aufraeumen(db)
    return antwort


@app.get("/api/oauth/clients")
def oauth_clients_lesen(db: sqlite3.Connection = DB):
    return {"eingerichtet": bool(WEB_URL and MCP_URL),
            "clients": oauth.client_auflisten(db)}


@app.post("/api/oauth/clients", status_code=201)
def oauth_client_anlegen(eingabe: OAuthClientAnlegen,
                         db: sqlite3.Connection = DB):
    """Legt einen Konnektor an. Der Schlüssel kommt nur dieses eine Mal."""
    _oauth_bereit()
    try:
        return oauth.client_anlegen(db, eingabe.name, eingabe.rueckadresse)
    except oauth.OAuthFehler as fehler:
        raise HTTPException(400, fehler.beschreibung)


@app.delete("/api/oauth/clients/{client_id}", status_code=204)
def oauth_client_zuruecknehmen(client_id: str, db: sqlite3.Connection = DB):
    oauth.client_zuruecknehmen(db, client_id)


# ============================================================ Oberfläche

QUELLTEXT = "https://github.com/annichaotica/vokabeltrainer"


@app.get("/api/zustand")
def zustand():
    return {
        "name": "Vokabeltrainer",
        "version": app.version,
        "datenbank": str(dbm.PFAD),
        # AGPL §13: eine über das Netz erreichbare Fassung muss ihren
        # Nutzern den Quelltext anbieten. Darum steht er hier und in der
        # Fußzeile der Oberfläche, nicht nur in einer Datei im Repo.
        "lizenz": "AGPL-3.0-or-later",
        "quelltext": QUELLTEXT,
        # Leer, solange niemand von außen zugreift — die Anleitung sagt
        # dann, dass es nur im Heimnetz geht, statt eine Adresse zu
        # nennen, die nicht stimmt.
        "mcp_url": MCP_URL,
        "mcp_kopfzeile": "x-account-key",
    }


if OBERFLAECHE.is_dir():
    app.mount("/", StaticFiles(directory=OBERFLAECHE, html=True), name="oberflaeche")
