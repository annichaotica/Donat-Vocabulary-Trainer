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
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

import aufgaben
import einlesen
import drossel
import datenbank as dbm
import legasthenie
import lernen as lernmodul
import lernziele
import identitaet
import mcp_dienst
import merkmale as mk
import qualitaet
import sammelimport
import sprachen
import wache
import zugang
from modelle import (BedeutungEingabe, BenutzerAendern, BenutzerAnlegen,
                     BewertenEingabe, EingriffEingabe, FormEingabe,
                     LegasthenieEinstellungen, LektionAnlegen,
                     ImportEingabe, LernzielAendern, LernzielAnlegen,
                     SammelimportEingabe,
                     McpTokenAnlegen,
                     LexemAendern, LexemEingabe,
                     PruefenEingabe, SammlungAendern, SammlungAnlegen,
                     SammlungEinstellungen, SpracheAnlegen,
                     SprachprofilSetzen, UebersetzungEingabe)

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
                 verwalter: bool = False) -> None:
    """Prüfung für Angaben, die im Rumpf stehen — die sieht die Wache nicht.

    Greift wie die Wache nur bei geprüfter Identität von außen. `request` darf
    None sein: dann kommt der Aufruf aus dem MCP-Dienst, der seine eigene,
    strengere Prüfung schon gemacht hat.
    """
    if request is None:
        return
    mail = identitaet.mail_aus_anfrage(request.headers)
    if not mail:
        return
    person = identitaet.profil_fuer_mail(db, mail)
    if person is None:
        raise HTTPException(403, "Zu dieser Mailadresse gibt es kein Profil.")
    try:
        if sammlung_id is not None:
            zugang.sammlung_pruefen(db, person["id"], sammlung_id, schreiben=True)
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
            wortart: [{"kennung": g["kennung"], "name": g["name"],
                       "kurz": g["kurz"], "zellen": len(g["zellen"])}
                      for g in gruppen]
            for wortart, gruppen in p.get("formgruppen", {}).items()
        },
        "standard": sprachen.formgruppen_standard(code),
        "stammformen": p.get("stammformen", []),
        "lexemmerkmale": p.get("lexemmerkmale", {}),
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


@app.post("/api/benutzer", status_code=201)
def benutzer_anlegen(eingabe: BenutzerAnlegen, db: sqlite3.Connection = DB):
    erster = not dbm.wert(db, "SELECT 1 FROM benutzer LIMIT 1")
    try:
        cur = db.execute("""INSERT INTO benutzer (name, farbe, verwalter)
                            VALUES (?, ?, ?)""",
                         (eingabe.name, eingabe.farbe, int(erster)))
    except sqlite3.IntegrityError:
        raise HTTPException(409, f"Es gibt schon ein Profil namens {eingabe.name!r}")
    return _holen(db, "benutzer", cur.lastrowid)


@app.patch("/api/benutzer/{benutzer_id}")
def benutzer_aendern(benutzer_id: int, eingabe: BenutzerAendern,
                     db: sqlite3.Connection = DB):
    b = _holen(db, "benutzer", benutzer_id)
    if eingabe.name is not None:
        db.execute("UPDATE benutzer SET name = ? WHERE id = ?", (eingabe.name, benutzer_id))
    if eingabe.farbe is not None:
        db.execute("UPDATE benutzer SET farbe = ? WHERE id = ?", (eingabe.farbe, benutzer_id))
    e = dbm.j_lesen(b["einstellungen"])
    if eingabe.wunschretention is not None:
        e["wunschretention"] = eingabe.wunschretention
    if eingabe.neu_je_sitzung is not None:
        e["neu_je_sitzung"] = eingabe.neu_je_sitzung
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

@app.get("/api/sammlungen")
def sammlungen_liste(benutzer_id: int | None = None, db: sqlite3.Connection = DB):
    if benutzer_id is None:
        return dbm.zeilen(db, "SELECT * FROM sammlung ORDER BY name")
    return dbm.zeilen(db, """
        SELECT s.*, (s.besitzer_id = ?) AS eigen,
               (SELECT COUNT(*) FROM lexem l WHERE l.sammlung_id = s.id) AS lexeme
          FROM sammlung s
         WHERE s.besitzer_id = ?
            OR s.id IN (SELECT sammlung_id FROM freigabe WHERE benutzer_id = ?)
         ORDER BY s.name""", (benutzer_id, benutzer_id, benutzer_id))


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
                 wortart: str | None = None,
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
    if wortart:
        bedingungen.append("l.wortart = ?")
        werte.append(wortart)
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
    if felder:
        felder.append("geaendert = datetime('now')")
        db.execute(f"UPDATE lexem SET {', '.join(felder)} WHERE id = ?",
                   (*werte, lexem_id))
        aufgaben.erzeugen(db, lexem_id)
    return _lexem_ausbauen(db, _holen(db, "lexem", lexem_id), mit_aufgaben=True)


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
def lernziel_anlegen(eingabe: LernzielAnlegen, db: sqlite3.Connection = DB):
    _holen(db, "benutzer", eingabe.benutzer_id)
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
    for feld in ("name", "termin", "ziel", "notiz"):
        wert = getattr(eingabe, feld)
        if wert is not None:
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
                  nur: str | None = None,
                  anzahl: int = Query(default=1, ge=1, le=50),
                  lernziel_id: int | None = None,
                  db: sqlite3.Connection = DB):
    """Die nächsten Aufgaben, mit Begründung und Terminvorschau.

    nur=neu | faellig | fehler | frei — "frei" übt ohne Terminlogik.
    """
    _holen(db, "benutzer", benutzer_id)
    if nur not in (None, "neu", "faellig", "fehler", "frei"):
        raise HTTPException(400, "nur muss neu, faellig, fehler oder frei sein")
    return lernmodul.naechste(db, benutzer_id, sammlung_id, lektion_id,
                              typ, nur, anzahl, lernziel_id, bis_lektion)


@app.post("/api/lernen/pruefen")
def lern_pruefen(eingabe: PruefenEingabe, db: sqlite3.Connection = DB):
    """Prüft die Antwort, ohne den Lernstand zu verändern."""
    _holen(db, "benutzer", eingabe.benutzer_id)
    try:
        return lernmodul.pruefen(db, eingabe.benutzer_id, eingabe.aufgabe_id,
                                 eingabe.antwort, eingabe.denkzeit_ms,
                                 eingabe.versuche, eingabe.aufgedeckt)
    except KeyError as fehler:
        raise HTTPException(404, str(fehler))


@app.post("/api/lernen/aufdecken")
def lern_aufdecken(eingabe: EingriffEingabe, db: sqlite3.Connection = DB):
    """Lösung zeigen, ohne zu bewerten — für "ich weiß es nicht" und für das
    Einprägen vor dem Schreiben im Legastheniemodus."""
    _holen(db, "benutzer", eingabe.benutzer_id)
    _holen(db, "aufgabe", eingabe.aufgabe_id)
    return lernmodul.aufdecken(db, eingabe.benutzer_id, eingabe.aufgabe_id)


@app.post("/api/lernen/bewerten")
def lern_bewerten(eingabe: BewertenEingabe, db: sqlite3.Connection = DB):
    _holen(db, "benutzer", eingabe.benutzer_id)
    _holen(db, "aufgabe", eingabe.aufgabe_id)
    try:
        return lernmodul.bewerten(
            db, eingabe.benutzer_id, eingabe.aufgabe_id, eingabe.bewertung,
            eingabe.antwort, eingabe.urteil, eingabe.dauer_ms,
            eingabe.denkzeit_ms, eingabe.versuche, eingabe.aufgedeckt,
            eingabe.fehlerart)
    except ValueError as fehler:
        raise HTTPException(400, str(fehler))


@app.post("/api/lernen/aussetzen")
def lern_aussetzen(eingabe: EingriffEingabe, db: sqlite3.Connection = DB):
    lernmodul.aussetzen(db, eingabe.benutzer_id, eingabe.aufgabe_id, True)
    return {"zustand": "ausgesetzt"}


@app.post("/api/lernen/fortsetzen")
def lern_fortsetzen(eingabe: EingriffEingabe, db: sqlite3.Connection = DB):
    lernmodul.aussetzen(db, eingabe.benutzer_id, eingabe.aufgabe_id, False)
    return {"zustand": "wieder dabei"}


@app.post("/api/lernen/zuruecksetzen")
def lern_zuruecksetzen(eingabe: EingriffEingabe, db: sqlite3.Connection = DB):
    lernmodul.zuruecksetzen(db, eingabe.benutzer_id, eingabe.aufgabe_id)
    return {"zustand": "neu"}


@app.post("/api/lernen/termin")
def lern_termin(eingabe: EingriffEingabe, db: sqlite3.Connection = DB):
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
                                 "oder x-account-key." + hinweis)
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
    }


if OBERFLAECHE.is_dir():
    app.mount("/", StaticFiles(directory=OBERFLAECHE, html=True), name="oberflaeche")
