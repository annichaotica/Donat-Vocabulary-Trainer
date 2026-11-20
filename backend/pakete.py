# Vokabeltrainer — Copyright (C) 2026 Annuschka Brenner
#
# Freie Software unter der GNU Affero General Public License, Fassung 3
# oder später. Herausgegeben in der Hoffnung, dass sie nützt, aber OHNE
# JEDE GEWÄHRLEISTUNG. Siehe die Datei LICENSE.
"""Kurspakete einspielen — ganz oder gar nicht.

Ein Paket ist ein ZIP mit einer Beschreibung und je einer Datei für
die Dinge, die der Trainer kennt:

    paket.json      Beschreibung, Herkunft, Prüfvermerk
    vokabeln.json   wie /import/vokabeln
    uebungen.json   wie /import/uebungen
    texte.json      je Eintrag ein Text
    regeln.json     je Eintrag eine Grammatikregel
    lehrgang.json   Formgruppe -> ab welcher Lektion

Nichts davon ist ein neues Format. Es sind genau die Gestalten, die
die vorhandenen Einlese-Wege schon annehmen — zusammengepackt, damit
das Einspielen EINE Handlung ist statt fünf.

GANZ ODER GAR NICHT ist der Grund, warum es diesen Weg überhaupt gibt.
Fünf Aufrufe nacheinander können nach dem dritten abbrechen, und dann
steht im Bestand ein halbes Paket: Vokabeln ohne die Regeln, die sie
erklären, Texte ohne die Wörter, die sie decken. Hier liegt eine
Klammer um alles (`dbm.Klammer`); schlägt ein Teil fehl, war nichts.

DER PRÜFVERMERK ENTSCHEIDET ÜBER DIE FREIGABE. Der Trainer fragt
nichts ab, was ein Mensch nicht bestätigt hat — dieselbe Regel wie bei
Einträgen über die KI-Schnittstelle. Ein Paket darf diese Zusage
mitbringen, aber nur ausdrücklich: in `geprueft` muss ein Eintrag
stehen, der sagt WER WANN WAS geprüft hat und dass es in Ordnung war.
Fehlt er, landen die Formen ungeprüft im Bestand und warten in der
Freigabe. Ein leeres `geprueft` ist damit kein »im Zweifel in
Ordnung«, sondern sichtbar ungeprüft.

WAS VON AUSSEN KOMMT, WIRD NICHT AUSGEPACKT. Gelesen werden nur die
sechs Dateien oben, einzeln und namentlich; nichts wird auf die Platte
geschrieben. Pfadangaben im ZIP spielen damit keine Rolle, und
Verzeichniswechsel (`../`) gehen ins Leere. Dazu zwei stumpfe
Grenzen gegen Packbomben: höchstens 200 Einträge und 20 MB
ausgepackt.
"""

from __future__ import annotations

import io
import json
import sqlite3
import zipfile

import aufgaben
import datenbank as dbm
import lehrgang as lehrgangmodul
import lesetexte
import regeln as regelmodul
import sammelimport
import uebungen as uebungsmodul

FORMAT = 1

# Grenzen gegen Packbomben. Stumpf und absichtlich großzügig: ein
# Lehrwerkjahrgang mit Texten bleibt weit darunter.
HOECHSTENS_EINTRAEGE = 200
HOECHSTENS_BYTE = 20 * 1024 * 1024

# Die Dateien, die gelesen werden. Alles andere im ZIP wird ignoriert —
# nicht abgelehnt: ein Paket darf eine LIESMICH oder eine Lizenz
# mitbringen, ohne dass der Trainer sich daran stört.
TEILE = ("vokabeln", "uebungen", "texte", "regeln", "lehrgang")

# Was ein Prüfvermerk abdecken muss, damit die Formen abgefragt werden.
DECKT_FORMEN = {"vokabeln", "formen", "alles"}


class PaketFehler(ValueError):
    """Das Paket ist nicht brauchbar. Die Nachricht sagt, woran es liegt."""


def _lesen(zip_datei: zipfile.ZipFile, name: str):
    """Eine JSON-Datei aus dem Paket — oder None, wenn sie fehlt."""
    for kandidat in (name, f"./{name}"):
        try:
            roh = zip_datei.read(kandidat)
        except KeyError:
            continue
        try:
            return json.loads(roh.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as fehler:
            raise PaketFehler(f"{name} ist kein lesbares JSON: {fehler}")
    return None


def beschreibung_pruefen(p: dict) -> list[str]:
    """Was an der Beschreibung fehlt. Leere Liste heißt: in Ordnung."""
    fehlt = []
    if not isinstance(p, dict):
        return ["paket.json ist kein Objekt"]
    if p.get("format") != FORMAT:
        fehlt.append(f"format muss {FORMAT} sein, nicht {p.get('format')!r}")
    for feld in ("kennung", "name", "fassung", "sprache"):
        if not str(p.get(feld) or "").strip():
            fehlt.append(f"{feld} fehlt")
    herkunft = p.get("herkunft")
    if not isinstance(herkunft, dict):
        fehlt.append("herkunft fehlt")
    else:
        if not str(herkunft.get("art") or "").strip():
            fehlt.append("herkunft.art fehlt")
        if not str(herkunft.get("lizenz") or "").strip():
            fehlt.append("herkunft.lizenz fehlt")
    if not isinstance(p.get("geprueft"), list):
        fehlt.append("geprueft fehlt oder ist keine Liste")
    return fehlt


def darf_freigeben(p: dict) -> dict | None:
    """Der Prüfvermerk, der die Formen freigibt — oder None.

    Verlangt wird WER, WANN, WAS und ein Ergebnis »in Ordnung«. Ein
    Vermerk ohne Namen oder ohne Datum ist keiner: er sagt nicht, wen
    man fragen kann, wenn sich später etwas als falsch herausstellt.
    """
    for vermerk in p.get("geprueft") or []:
        if not isinstance(vermerk, dict):
            continue
        if (str(vermerk.get("wer") or "").strip()
                and str(vermerk.get("wann") or "").strip()
                and vermerk.get("was") in DECKT_FORMEN
                and vermerk.get("ergebnis") == "in Ordnung"):
            return vermerk
    return None


def oeffnen(roh: bytes) -> tuple[zipfile.ZipFile, dict]:
    """Das ZIP öffnen und die Beschreibung herausholen."""
    try:
        z = zipfile.ZipFile(io.BytesIO(roh))
    except zipfile.BadZipFile:
        raise PaketFehler("Das ist kein ZIP.")
    eintraege = z.infolist()
    if len(eintraege) > HOECHSTENS_EINTRAEGE:
        raise PaketFehler(f"{len(eintraege)} Einträge im Paket — höchstens "
                          f"{HOECHSTENS_EINTRAEGE} sind vorgesehen.")
    gesamt = sum(e.file_size for e in eintraege)
    if gesamt > HOECHSTENS_BYTE:
        raise PaketFehler(f"Ausgepackt {gesamt // 1024 // 1024} MB — höchstens "
                          f"{HOECHSTENS_BYTE // 1024 // 1024} MB sind vorgesehen.")
    p = _lesen(z, "paket.json")
    if p is None:
        raise PaketFehler("Im Paket fehlt paket.json.")
    fehlt = beschreibung_pruefen(p)
    if fehlt:
        raise PaketFehler("paket.json ist unvollständig: " + ", ".join(fehlt))
    return z, p


def einspielen(db: sqlite3.Connection, sammlung_id: int, roh: bytes,
               nur_pruefen: bool = False) -> dict:
    """Ein Paket in eine Sammlung — in einer Klammer.

    `nur_pruefen` schreibt nichts und meldet trotzdem alles, was
    gemeldet worden wäre: dieselbe Zusage wie beim Sammelimport, und
    aus demselben Grund. Wer tausend Wörter einspielt, will vorher
    wissen, was passiert.
    """
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (sammlung_id,))
    if s is None:
        raise KeyError(f"Sammlung {sammlung_id} gibt es nicht")

    z, p = oeffnen(roh)
    inhalt = {name: _lesen(z, f"{name}.json") for name in TEILE}
    vermerk = darf_freigeben(p)

    bericht = {
        "sammlung_id": sammlung_id,
        "nur_pruefen": nur_pruefen,
        "paket": {"kennung": p["kennung"], "name": p["name"],
                  "fassung": p["fassung"], "sprache": p["sprache"]},
        "herkunft": p.get("herkunft"),
        # Ehrlich benennen, was mit den Formen geschieht. Das ist die
        # Angabe, auf die es ankommt — alles andere sind Zahlen.
        "freigegeben": bool(vermerk),
        "freigabe_durch": vermerk,
        "teile": {},
        "warnungen": [],
    }

    if s["sprache"] != p["sprache"]:
        bericht["warnungen"].append(
            f"Das Paket ist für {p['sprache']!r}, die Sammlung für "
            f"{s['sprache']!r}. Eingespielt wird trotzdem — aber die "
            f"Prüfregeln der Sammlung gelten, nicht die des Pakets.")
    if not vermerk:
        bericht["warnungen"].append(
            "Kein Prüfvermerk für die Vokabeln. Die Formen landen "
            "ungeprüft im Bestand und werden erst nach der Freigabe "
            "abgefragt.")

    with dbm.Klammer(db) as klammer:
        # Welche Formen es VORHER schon gab.
        #
        # Freigegeben werden darf nur, was dieses Paket mitbringt. Über
        # die Spalte `quelle` ginge das nicht: sie kennt »import«, aber
        # nicht »paket« (das Schema schränkt sie ein), und »import«
        # träfe auch Formen aus einer früher eingelesenen Datei. Eine
        # Zusage über fremde Arbeit wäre genau das, was die Freigabe
        # verhindern soll. Innerhalb der Klammer ist der Vorher-Nachher-
        # Vergleich exakt.
        vorher = {z["id"] for z in dbm.zeilen(
            db, """SELECT f.id FROM form f JOIN lexem l ON l.id = f.lexem_id
                    WHERE l.sammlung_id = ?""", (sammlung_id,))}

        if inhalt["vokabeln"]:
            bericht["teile"]["vokabeln"] = sammelimport.importieren(
                db, sammlung_id, inhalt["vokabeln"], quelle="import")
        if inhalt["uebungen"]:
            bericht["teile"]["uebungen"] = uebungsmodul.importieren(
                db, sammlung_id, inhalt["uebungen"])
        if inhalt["texte"]:
            angelegt = []
            for t in inhalt["texte"]:
                if not isinstance(t, dict) or not t.get("inhalt"):
                    raise PaketFehler("Ein Text ohne inhalt im Paket.")
                angelegt.append(lesetexte.anlegen(
                    db, sammlung_id, t.get("titel", ""), t["inhalt"],
                    niveau=t.get("niveau"), notiz=t.get("notiz"),
                    uebersetzung=t.get("uebersetzung"),
                    aufteilung=t.get("aufteilung", "auto"))["id"])
            bericht["teile"]["texte"] = {"angelegt": len(angelegt)}
        if inhalt["regeln"]:
            for r in inhalt["regeln"]:
                if not isinstance(r, dict) or not r.get("titel"):
                    raise PaketFehler("Eine Regel ohne titel im Paket.")
                regelmodul.anlegen(
                    db, sammlung_id, r["titel"], r.get("text", ""),
                    s["sprache"], r.get("muster"), r.get("beispiele"),
                    kennung=r.get("kennung"), quelle="import",
                    geprueft=bool(vermerk))
            bericht["teile"]["regeln"] = {"angelegt": len(inhalt["regeln"])}
        if inhalt["lehrgang"]:
            lehrgangmodul.zuordnung_setzen(db, sammlung_id, inhalt["lehrgang"])
            bericht["teile"]["lehrgang"] = {"gruppen": len(inhalt["lehrgang"])}

        if vermerk:
            neu_ids = [z["id"] for z in dbm.zeilen(
                db, """SELECT f.id FROM form f JOIN lexem l ON l.id = f.lexem_id
                        WHERE l.sammlung_id = ? AND f.geprueft = 0""",
                (sammlung_id,)) if z["id"] not in vorher]
            if neu_ids:
                db.execute(
                    "UPDATE form SET geprueft = 1 WHERE id IN ("
                    + ",".join("?" * len(neu_ids)) + ")", tuple(neu_ids))
            bericht["formen_freigegeben"] = len(neu_ids)
        aufgaben.erzeugen_fuer_sammlung(db, sammlung_id)
        bericht["aufgaben"] = dbm.wert(db, """SELECT COUNT(*) FROM aufgabe a
                                                JOIN lexem l ON l.id = a.lexem_id
                                               WHERE l.sammlung_id = ?
                                                 AND a.aktiv = 1""",
                                       (sammlung_id,)) or 0
        if nur_pruefen:
            klammer.zuruecknehmen()

    return bericht
