"""Übungssätze und Texte.

Ein Übungssatz und ein ganzer Text sind derselbe Gegenstand mit
unterschiedlich vielen Abschnitten. Darum liegen beide in `text` und
`textabschnitt` und nicht in getrennten Tabellen: sonst zerfiele der
Lernstand auf zwei Orte, und die Verknüpfung zu den Vokabeln (`text_lexem`),
die ein Satz genauso braucht, müsste es zweimal geben.

Fünf Dinge leistet dieses Modul:

**Anlegen und Einlesen** — einzeln und in Mengen, mit Probelauf, wiederholbar
über die Kennung, und ohne Geprüftes zu überschreiben. Dieselben drei
Zusagen wie beim Vokabelimport, aus demselben Grund.

**Abschnitte bilden.** Bei `typ: "satz"` ist der ganze Eintrag ein Abschnitt.
Bei längerem wird in Sätze geteilt — aber nur, wenn Zielsprache und
Grundsprache dabei auf dieselbe Zahl kommen. Sonst bliebe die
Satzzuordnung geraten, und eine falsch zugeordnete Referenzübersetzung ist
schlimmer als ein ungeteilter Text.

**Aufgaben erzeugen** aus `richtungen`, genau wie bei den Vokabeln aus den
Merkmalen: nicht kuratiert, sondern abgeleitet, damit eine berichtigte
Übung ihren Lernstand behält.

**Bewerten** über `satzpruefung` — Wort für Wort gegen alle gültigen
Fassungen. Bei längeren Blöcken zusätzlich Selbsteinschätzung, weil dort
ein Vergleich selten passt.

**Deckung prüfen** (`text_pruefen`): welche Wörter eines Textes kommen im
Bestand bis zu einer Lektion noch nicht vor. Damit lassen sich Texte
passgenau zur Stufe schreiben, statt sie hinterher zu verwerfen.
"""

from __future__ import annotations

import re
import sqlite3

import datenbank as dbm
import pruefung
import sammelimport
import satzpruefung
import sprachen

TYPEN = ("satz", "text", "dialog", "brief", "zeitungsstil")

# Nur der Satz wird genau verglichen. Bei allem Längeren ist eine wörtliche
# Übereinstimmung die Ausnahme, nicht die Regel — dort zählt die eigene
# Einschätzung, und der Vergleich ist nur noch Hilfe.
GENAU_BEWERTBAR = ("satz",)

QUELLENARTEN = {"ki": "ki", "eigen": "manuell", "verweis": "manuell",
                "manuell": "manuell", "import": "import"}

RICHTUNGEN = ("hin", "rueck")        # hin: Zielsprache -> Grundsprache

_SATZENDE = re.compile(r"(?<=[.!?;·;])\s+(?=[^\s])")
_WORTTRENNER = re.compile(r"[^\w''’-]+", re.UNICODE)


class UebungFehler(ValueError):
    pass


# ------------------------------------------------------------ Abschnitte

def saetze(text: str) -> list[str]:
    """Teilt an Satzenden. Das griechische Fragezeichen (;) zählt mit."""
    return [t.strip() for t in _SATZENDE.split((text or "").strip()) if t.strip()]


def abschnitte_bilden(eintrag: dict) -> tuple[list[dict], list[str]]:
    """Macht aus einem Eintrag die Abschnitte. Gibt auch Notizen zurück.

    Vorrang hat eine ausdrückliche Liste `abschnitte`. Fehlt sie, wird bei
    `typ: "satz"` nicht geteilt und sonst an Satzenden — letzteres nur, wenn
    beide Sprachen auf gleich viele Sätze kommen. Eine geratene Zuordnung
    wäre schlimmer als ein ungeteilter Text: die Rückmeldung verglich dann
    mit dem falschen Satz.
    """
    hinweise: list[str] = []
    wenn_liste = eintrag.get("abschnitte")
    if wenn_liste:
        gebildet = []
        for i, a in enumerate(wenn_liste):
            ziel = (a.get("zielsprache") or "").strip()
            if not ziel:
                raise UebungFehler(f"Abschnitt {i + 1} hat keine Zielsprache")
            gebildet.append({
                "original": ziel,
                "referenz": (a.get("grundsprache") or "").strip() or None,
                "varianten": list(a.get("alternativen_zielsprache") or []),
                "referenz_varianten": list(a.get("alternativen_grundsprache") or []),
                "notiz": a.get("notiz"),
            })
        return gebildet, hinweise

    ziel = (eintrag.get("zielsprache") or "").strip()
    grund = (eintrag.get("grundsprache") or "").strip()
    typ = eintrag.get("typ") or "satz"
    einer = [{"original": ziel, "referenz": grund or None,
              "varianten": list(eintrag.get("alternativen_zielsprache") or []),
              "referenz_varianten": list(
                  eintrag.get("alternativen_grundsprache") or []),
              "notiz": None}]
    if typ == "satz":
        return einer, hinweise

    z_saetze, g_saetze = saetze(ziel), saetze(grund)
    if len(z_saetze) < 2:
        return einer, hinweise
    if len(z_saetze) != len(g_saetze):
        hinweise.append(
            f"Nicht in Sätze geteilt: {len(z_saetze)} in der Zielsprache, "
            f"{len(g_saetze)} in der Grundsprache. Mit einer ausdrücklichen "
            f"Liste `abschnitte` lässt sich die Zuordnung angeben.")
        return einer, hinweise
    # Varianten gelten für das Ganze und lassen sich nicht aufteilen.
    if (eintrag.get("alternativen_zielsprache")
            or eintrag.get("alternativen_grundsprache")):
        hinweise.append(
            "Die Alternativen gelten für den ganzen Text und wurden darum "
            "nicht auf die Sätze verteilt. Für satzweise Alternativen die "
            "Liste `abschnitte` benutzen.")
    return [{"original": z, "referenz": g, "varianten": [],
             "referenz_varianten": [], "notiz": None}
            for z, g in zip(z_saetze, g_saetze)], hinweise


# -------------------------------------------------------------- Aufgaben

def _schluessel(text_id: int, abschnitt_folge: int, typ: str) -> str:
    """Wie bei den Vokabeln aus dem Inhalt, nicht aus einer Zählung: eine
    berichtigte Übung behält damit ihren Lernstand."""
    return f"text:{text_id}:{abschnitt_folge}:{typ}"


def aufgaben_erzeugen(db: sqlite3.Connection, text_id: int) -> dict:
    """Legt die Textaufgaben aus den Richtungen an.

    Abgeleitet, nicht kuratiert. Was nicht mehr vorgesehen ist, wird
    abgeschaltet und nicht gelöscht — sonst ginge der Lernstand verloren,
    wenn jemand eine Richtung versehentlich abwählt.
    """
    t = dbm.zeile(db, "SELECT * FROM text WHERE id = ?", (text_id,))
    if t is None:
        raise UebungFehler(f"Übung {text_id} gibt es nicht")
    richtungen = dbm.j_lesen(t["richtungen"]) or []
    genau = t["typ"] in GENAU_BEWERTBAR
    abschnitte = dbm.zeilen(db, """SELECT * FROM textabschnitt
                                    WHERE text_id = ? ORDER BY reihenfolge, id""",
                            (text_id,))
    gewollt: dict[str, dict] = {}
    for a in abschnitte:
        for richtung in richtungen:
            typ = ("uebersetzung_hin" if richtung == "hin"
                   else "uebersetzung_rueck")
            # Ohne Referenzübersetzung gibt es nichts zu übersetzen und
            # nichts, womit sich vergleichen ließe.
            if richtung == "hin" and not a["referenz"]:
                continue
            s = _schluessel(text_id, a["reihenfolge"], typ)
            gewollt[s] = {
                "abschnitt_id": a["id"], "typ": typ,
                "bewertung_art": "genau" if genau else "selbst",
                "frage": None,
                "erwartet": dbm.j_schreiben(_erwartet(a, richtung)),
            }

    vorhanden = {z["schluessel"]: z for z in dbm.zeilen(
        db, "SELECT * FROM textaufgabe WHERE text_id = ?", (text_id,))}
    neu = 0
    for s, daten in gewollt.items():
        alt = vorhanden.get(s)
        if alt is None:
            db.execute("""INSERT INTO textaufgabe
                            (text_id, abschnitt_id, typ, bewertung_art, frage,
                             erwartet, schluessel, aktiv)
                          VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                       (text_id, daten["abschnitt_id"], daten["typ"],
                        daten["bewertung_art"], daten["frage"],
                        daten["erwartet"], s))
            neu += 1
        else:
            db.execute("""UPDATE textaufgabe
                             SET abschnitt_id = ?, bewertung_art = ?,
                                 erwartet = ?, aktiv = 1
                           WHERE id = ?""",
                       (daten["abschnitt_id"], daten["bewertung_art"],
                        daten["erwartet"], alt["id"]))
    stillgelegt = 0
    for s, alt in vorhanden.items():
        if s not in gewollt and alt["aktiv"]:
            db.execute("UPDATE textaufgabe SET aktiv = 0 WHERE id = ?", (alt["id"],))
            stillgelegt += 1
    return {"neu": neu, "aktiv": len(gewollt), "stillgelegt": stillgelegt}


def _erwartet(abschnitt: dict, richtung: str) -> list[str]:
    """Alle gültigen Fassungen der gesuchten Seite."""
    if richtung == "hin":
        haupt = abschnitt["referenz"]
        weitere = dbm.j_lesen(abschnitt["referenz_varianten"]) or []
    else:
        haupt = abschnitt["original"]
        weitere = dbm.j_lesen(abschnitt["varianten"]) or []
    return [x for x in [haupt, *weitere] if (x or "").strip()]


# ------------------------------------------------------------- Schreiben

def _pruefen_eintrag(eintrag: dict) -> list[str]:
    fehler = []
    typ = eintrag.get("typ") or "satz"
    if typ not in TYPEN:
        fehler.append(f"Unbekannter Typ {typ!r}. Möglich: {', '.join(TYPEN)}")
    if not (eintrag.get("zielsprache") or "").strip() \
            and not eintrag.get("abschnitte"):
        fehler.append("Keine Zielsprache angegeben")
    # Die Richtungen prüft _richtungen_lesen: dort ist die Sammlung bekannt,
    # und nur mit ihr lässt sich "el-de" überhaupt beurteilen.
    quelle = eintrag.get("quelle") or {}
    if isinstance(quelle, dict):
        art = quelle.get("art", "ki")
        if art not in QUELLENARTEN:
            fehler.append(f"Unbekannte Quellenart {art!r}. "
                          f"Möglich: {', '.join(sorted(QUELLENARTEN))}")
        if art == "verweis" and not (quelle.get("url") or quelle.get("titel")):
            fehler.append("Quellenart 'verweis' ohne Titel und ohne Adresse")
    return fehler


def _richtungen_lesen(eintrag: dict, code: str, grundsprache: str) -> list[str]:
    """Nimmt sowohl ["hin", "rueck"] als auch ["el-de", "de-el"] an.

    Die Sprachpaarschreibweise ist die, in der ein Lehrwerk denkt; intern
    ist nur wichtig, in welche Richtung übersetzt wird.
    """
    roh = eintrag.get("richtungen")
    if roh is None:
        return ["hin", "rueck"]
    ergebnis = []
    for r in roh:
        if r in RICHTUNGEN:
            ergebnis.append(r)
        elif isinstance(r, str) and "-" in r:
            von, _, nach = r.partition("-")
            if von == code and nach == grundsprache:
                ergebnis.append("hin")
            elif von == grundsprache and nach == code:
                ergebnis.append("rueck")
            else:
                raise UebungFehler(
                    f"Richtung {r!r} passt nicht zu dieser Sammlung "
                    f"({code} / {grundsprache})")
        else:
            raise UebungFehler(f"Unbekannte Richtung {r!r}")
    # Reihenfolge erhalten, Doppelte weg
    return list(dict.fromkeys(ergebnis))


def _abschnitte_schreiben(db: sqlite3.Connection, text_id: int,
                          gebildet: list[dict]) -> tuple[int, int, list[dict]]:
    """Schreibt die Abschnitte. Geprüfte Übungen werden nicht überschrieben.

    Wie bei den Formen: hat ein Mensch freigegeben, meldet ein Import die
    Abweichung und entscheidet nicht selbst.
    """
    t = dbm.zeile(db, "SELECT geprueft FROM text WHERE id = ?", (text_id,))
    geschuetzt = bool(t["geprueft"])
    vorhanden = dbm.zeilen(db, """SELECT * FROM textabschnitt
                                   WHERE text_id = ? ORDER BY reihenfolge, id""",
                           (text_id,))
    neu = geaendert = 0
    abweichungen: list[dict] = []
    for i, a in enumerate(gebildet):
        alt = vorhanden[i] if i < len(vorhanden) else None
        if alt is None:
            db.execute("""INSERT INTO textabschnitt
                            (text_id, reihenfolge, original, referenz,
                             varianten, referenz_varianten, notiz)
                          VALUES (?, ?, ?, ?, ?, ?, ?)""",
                       (text_id, i, a["original"], a["referenz"],
                        dbm.j_schreiben(a["varianten"]),
                        dbm.j_schreiben(a["referenz_varianten"]), a["notiz"]))
            neu += 1
            continue
        gleich = (alt["original"] == a["original"]
                  and (alt["referenz"] or None) == (a["referenz"] or None)
                  and dbm.j_lesen(alt["varianten"]) == a["varianten"]
                  and dbm.j_lesen(alt["referenz_varianten"])
                  == a["referenz_varianten"])
        if gleich:
            continue
        if geschuetzt:
            abweichungen.append({
                "abschnitt": i + 1, "steht": alt["original"],
                "wollte": a["original"],
                "grund": "Die Übung ist freigegeben und wird nicht "
                         "überschrieben."})
            continue
        db.execute("""UPDATE textabschnitt
                         SET original = ?, referenz = ?, varianten = ?,
                             referenz_varianten = ?, notiz = ?
                       WHERE id = ?""",
                   (a["original"], a["referenz"],
                    dbm.j_schreiben(a["varianten"]),
                    dbm.j_schreiben(a["referenz_varianten"]), a["notiz"],
                    alt["id"]))
        geaendert += 1
    # Überzählige Abschnitte eines gekürzten Textes weg — aber nie bei
    # einer freigegebenen Übung.
    if not geschuetzt:
        for alt in vorhanden[len(gebildet):]:
            db.execute("DELETE FROM textabschnitt WHERE id = ?", (alt["id"],))
    return neu, geaendert, abweichungen


def _eintrag_schreiben(db: sqlite3.Connection, sammlung: dict, eintrag: dict,
                       uebung_id: int | None = None) -> dict:
    """Legt eine Übung an oder bessert sie nach. Gibt einen Bericht zurück.

    `uebung_id` nennt den Eintrag unmittelbar. Beim Ändern ist das
    unerlässlich: wird der Zieltext geändert, findet die Suche über den
    Zieltext ihn nicht mehr und legte einen zweiten an.
    """
    code, grundsprache = sammlung["sprache"], sammlung["grundsprache"]
    fehler = _pruefen_eintrag(eintrag)
    if fehler:
        return {"zustand": "abgelehnt", "fehler": fehler}

    typ = eintrag.get("typ") or "satz"
    richtungen = _richtungen_lesen(eintrag, code, grundsprache)
    gebildet, hinweise = abschnitte_bilden(eintrag)
    quelle = eintrag.get("quelle") or {}
    if isinstance(quelle, str):
        quelle = {"art": quelle}
    art = quelle.get("art", "ki")
    lektion_id = sammelimport.lektion_sichern(
        db, sammlung["id"], eintrag.get("lektion_nr"),
        eintrag.get("lektion_titel"))

    inhalt = (eintrag.get("zielsprache") or "").strip() or "\n".join(
        a["original"] for a in gebildet)
    uebersetzung = (eintrag.get("grundsprache") or "").strip() or "\n".join(
        a["referenz"] or "" for a in gebildet).strip() or None
    titel = eintrag.get("titel") or _titel_bilden(typ, gebildet)

    kennung = eintrag.get("kennung")
    alt = None
    if uebung_id is not None:
        alt = dbm.zeile(db, "SELECT * FROM text WHERE id = ?", (uebung_id,))
    if alt is None and kennung:
        alt = dbm.zeile(db, "SELECT * FROM text WHERE sammlung_id = ? AND kennung = ?",
                        (sammlung["id"], kennung))
    if alt is None:
        # Ohne Kennung ist der Zieltext selbst der Schlüssel. Sonst
        # verdoppelte ein zweiter Lauf den ganzen Bestand.
        alt = dbm.zeile(db, """SELECT * FROM text
                                WHERE sammlung_id = ? AND inhalt = ?""",
                        (sammlung["id"], inhalt))

    felder = (titel, code, inhalt, uebersetzung, eintrag.get("niveau"),
              QUELLENARTEN[art], eintrag.get("notiz"), typ,
              dbm.j_schreiben(richtungen),
              quelle.get("titel") if art == "verweis" else None,
              quelle.get("url") if art == "verweis" else None,
              int(bool(eintrag.get("geprueft"))), kennung,
              int(eintrag.get("reihenfolge") or 0), lektion_id)
    if alt is None:
        cur = db.execute("""INSERT INTO text
              (titel, sprache, inhalt, uebersetzung, niveau, quelle, notiz,
               typ, richtungen, verweis_titel, verweis_url, geprueft, kennung,
               reihenfolge, lektion_id, sammlung_id)
              VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (*felder, sammlung["id"]))
        text_id, zustand = cur.lastrowid, "angelegt"
    else:
        text_id, zustand = alt["id"], "aktualisiert"
        if alt["geprueft"] and not eintrag.get("geprueft"):
            # Die Freigabe wird von einem Import nicht zurückgenommen.
            felder = (*felder[:11], 1, *felder[12:])
        db.execute("""UPDATE text SET titel = ?, sprache = ?, inhalt = ?,
                         uebersetzung = ?, niveau = ?, quelle = ?, notiz = ?,
                         typ = ?, richtungen = ?, verweis_titel = ?,
                         verweis_url = ?, geprueft = ?, kennung = ?,
                         reihenfolge = ?, lektion_id = ?,
                         geaendert = datetime('now')
                       WHERE id = ?""", (*felder, text_id))

    neu, geaendert, abweichungen = _abschnitte_schreiben(db, text_id, gebildet)
    aufgabenbericht = aufgaben_erzeugen(db, text_id)
    bericht = {"zustand": zustand, "uebung_id": text_id,
               "abschnitte": len(gebildet),
               "aufgaben": aufgabenbericht["aktiv"]}
    if neu or geaendert:
        bericht["abschnitte_neu"] = neu
        bericht["abschnitte_geaendert"] = geaendert
    if abweichungen:
        bericht["abweichungen"] = abweichungen
    befunde = hinweise + _befunde(gebildet, richtungen, typ)
    if befunde:
        bericht["befunde"] = befunde
    return bericht


def _titel_bilden(typ: str, gebildet: list[dict]) -> str:
    erster = gebildet[0]["original"] if gebildet else ""
    kurz = erster if len(erster) <= 60 else erster[:57].rstrip() + "…"
    return kurz or typ


def _befunde(gebildet: list[dict], richtungen: list[str], typ: str) -> list[str]:
    befunde = []
    ohne_referenz = [i + 1 for i, a in enumerate(gebildet) if not a["referenz"]]
    if ohne_referenz and "hin" in richtungen:
        befunde.append(
            f"Ohne Übersetzung in der Grundsprache: Abschnitt "
            f"{', '.join(str(i) for i in ohne_referenz)}. In dieser Richtung "
            f"entsteht dort keine Aufgabe.")
    if not richtungen:
        befunde.append("Keine Richtung angegeben — es entsteht keine Aufgabe.")
    if typ != "satz" and len(gebildet) == 1 and len(saetze(
            gebildet[0]["original"])) > 1:
        befunde.append(
            "Mehrere Sätze in einem Abschnitt. Bewertet wird dann nur im "
            "Ganzen; satzweise wäre die Rückmeldung genauer.")
    return befunde


def anlegen(db: sqlite3.Connection, sammlung_id: int, eintrag: dict) -> dict:
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (sammlung_id,))
    if s is None:
        raise UebungFehler(f"Sammlung {sammlung_id} gibt es nicht")
    bericht = _eintrag_schreiben(db, dict(s), eintrag)
    if bericht["zustand"] == "abgelehnt":
        raise UebungFehler("; ".join(bericht["fehler"]))
    return lesen(db, bericht["uebung_id"])


def importieren(db: sqlite3.Connection, sammlung_id: int, eintraege: list,
                nur_pruefen: bool = False) -> dict:
    """Viele Übungen auf einmal, mit Probelauf und wiederholbar."""
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (sammlung_id,))
    if s is None:
        raise UebungFehler(f"Sammlung {sammlung_id} gibt es nicht")
    ergebnis = {"sammlung_id": sammlung_id, "nur_pruefen": nur_pruefen,
                "eingereicht": len(eintraege), "angelegt": 0,
                "aktualisiert": 0, "abgelehnt": 0, "aufgaben": 0,
                "lektionen_neu": [], "eintraege": []}
    # Schachtelbar: beim Paketimport läuft schon eine Klammer darum.
    with dbm.Klammer(db) as klammer:
        vorher = {z["nr"] for z in sammelimport.lektionen(db, sammlung_id)
                  if z["nr"] is not None}
        for nr, eintrag in enumerate(eintraege, 1):
            if not isinstance(eintrag, dict):
                ergebnis["abgelehnt"] += 1
                ergebnis["eintraege"].append(
                    {"nr": nr, "zustand": "abgelehnt",
                     "fehler": ["Kein Datensatz"]})
                continue
            try:
                bericht = _eintrag_schreiben(db, dict(s), eintrag)
            except UebungFehler as fehler:
                ergebnis["abgelehnt"] += 1
                ergebnis["eintraege"].append(
                    {"nr": nr, "zustand": "abgelehnt", "fehler": [str(fehler)]})
                continue
            ergebnis[bericht["zustand"]] += 1
            ergebnis["aufgaben"] += bericht.get("aufgaben", 0)
            ergebnis["eintraege"].append({"nr": nr, **bericht})
        ergebnis["lektionen_neu"] = sorted(
            {z["nr"] for z in sammelimport.lektionen(db, sammlung_id)
             if z["nr"] is not None} - vorher)
        if nur_pruefen:
            klammer.zuruecknehmen()
    ergebnis["eintraege"] = [e for e in ergebnis["eintraege"]
                             if e.get("befunde") or e.get("abweichungen")
                             or e.get("fehler") or e["zustand"] == "abgelehnt"]
    ergebnis["mit_befunden"] = len(ergebnis["eintraege"])
    return ergebnis


def aendern(db: sqlite3.Connection, uebung_id: int, aenderung: dict) -> dict:
    """Ändert eine Übung. Geänderter Inhalt fällt auf ungeprüft zurück."""
    t = dbm.zeile(db, "SELECT * FROM text WHERE id = ?", (uebung_id,))
    if t is None:
        raise UebungFehler(f"Übung {uebung_id} gibt es nicht")
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (t["sammlung_id"],))
    inhaltlich = any(k in aenderung for k in (
        "zielsprache", "grundsprache", "alternativen_zielsprache",
        "alternativen_grundsprache", "abschnitte", "typ"))
    # Das Bisherige als Grundlage, damit eine Teiländerung nichts wegräumt.
    abschnitte = dbm.zeilen(db, """SELECT * FROM textabschnitt
                                    WHERE text_id = ? ORDER BY reihenfolge, id""",
                            (uebung_id,))
    vorlage = {
        "typ": t["typ"], "titel": t["titel"], "niveau": t["niveau"],
        "notiz": t["notiz"], "kennung": t["kennung"],
        "reihenfolge": t["reihenfolge"],
        "richtungen": dbm.j_lesen(t["richtungen"]),
        "zielsprache": t["inhalt"], "grundsprache": t["uebersetzung"],
        "abschnitte": [{"zielsprache": a["original"],
                        "grundsprache": a["referenz"],
                        "alternativen_zielsprache": dbm.j_lesen(a["varianten"]),
                        "alternativen_grundsprache":
                            dbm.j_lesen(a["referenz_varianten"]),
                        "notiz": a["notiz"]} for a in abschnitte],
        "geprueft": bool(t["geprueft"]),
        "lektion_nr": dbm.wert(db, "SELECT nr FROM lektion WHERE id = ?",
                               (t["lektion_id"],)) if t["lektion_id"] else None,
    }
    if t["verweis_url"] or t["verweis_titel"]:
        vorlage["quelle"] = {"art": "verweis", "titel": t["verweis_titel"],
                             "url": t["verweis_url"]}
    else:
        vorlage["quelle"] = {"art": "ki" if t["quelle"] == "ki" else "eigen"}

    neu = {**vorlage, **aenderung}
    if inhaltlich and "abschnitte" not in aenderung:
        # Der Textkörper hat sich geändert: die alte Abschnittsliste darf
        # ihn nicht überstimmen.
        neu.pop("abschnitte", None)
    if inhaltlich and "geprueft" not in aenderung:
        # Wie bei den Formen: was sich geändert hat, ist nicht mehr das,
        # was jemand freigegeben hat.
        neu["geprueft"] = False
        db.execute("UPDATE text SET geprueft = 0 WHERE id = ?", (uebung_id,))
    bericht = _eintrag_schreiben(db, dict(s), neu, uebung_id=uebung_id)
    if bericht["zustand"] == "abgelehnt":
        raise UebungFehler("; ".join(bericht["fehler"]))
    return lesen(db, uebung_id)


def loeschen(db: sqlite3.Connection, uebung_id: int) -> None:
    if dbm.zeile(db, "SELECT 1 FROM text WHERE id = ?", (uebung_id,)) is None:
        raise UebungFehler(f"Übung {uebung_id} gibt es nicht")
    db.execute("DELETE FROM text WHERE id = ?", (uebung_id,))


def freigeben(db: sqlite3.Connection, uebung_id: int,
              geprueft: bool = True) -> dict:
    if dbm.zeile(db, "SELECT 1 FROM text WHERE id = ?", (uebung_id,)) is None:
        raise UebungFehler(f"Übung {uebung_id} gibt es nicht")
    db.execute("UPDATE text SET geprueft = ?, geaendert = datetime('now') "
               "WHERE id = ?", (int(bool(geprueft)), uebung_id))
    return lesen(db, uebung_id)


# ---------------------------------------------------------------- Lesen

def lesen(db: sqlite3.Connection, uebung_id: int) -> dict:
    t = dbm.zeile(db, "SELECT * FROM text WHERE id = ?", (uebung_id,))
    if t is None:
        raise UebungFehler(f"Übung {uebung_id} gibt es nicht")
    abschnitte = dbm.zeilen(db, """SELECT * FROM textabschnitt
                                    WHERE text_id = ? ORDER BY reihenfolge, id""",
                            (uebung_id,))
    for a in abschnitte:
        a["varianten"] = dbm.j_lesen(a["varianten"])
        a["referenz_varianten"] = dbm.j_lesen(a["referenz_varianten"])
    lektion = None
    if t["lektion_id"]:
        lektion = dbm.zeile(db, "SELECT id, nr, name FROM lektion WHERE id = ?",
                            (t["lektion_id"],))
    return {
        **t, "richtungen": dbm.j_lesen(t["richtungen"]),
        "geprueft": bool(t["geprueft"]),
        "quelle": ({"art": "verweis", "titel": t["verweis_titel"],
                    "url": t["verweis_url"]} if t["verweis_url"]
                   or t["verweis_titel"]
                   else {"art": "ki" if t["quelle"] == "ki" else "eigen"}),
        "lektion": lektion, "abschnitte": abschnitte,
        "aufgaben": dbm.zeilen(db, """SELECT id, abschnitt_id, typ,
                                             bewertung_art, aktiv
                                        FROM textaufgabe
                                       WHERE text_id = ? ORDER BY id""",
                               (uebung_id,)),
    }


def auflisten(db: sqlite3.Connection, sammlung_id: int,
              lektion_nr: int | None = None, typ: str | None = None,
              bis_lektion: int | None = None,
              nur_ungepruefte: bool = False,
              ab: int = 0, anzahl: int = 50) -> dict:
    if dbm.zeile(db, "SELECT 1 FROM sammlung WHERE id = ?", (sammlung_id,)) is None:
        raise UebungFehler(f"Sammlung {sammlung_id} gibt es nicht")
    wo, werte = ["t.sammlung_id = ?"], [sammlung_id]
    if lektion_nr is not None:
        wo.append("k.nr = ?"); werte.append(lektion_nr)
    if bis_lektion is not None:
        wo.append("(k.nr IS NULL OR k.nr <= ?)"); werte.append(bis_lektion)
    if typ:
        wo.append("t.typ = ?"); werte.append(typ)
    if nur_ungepruefte:
        wo.append("t.geprueft = 0")
    bedingung = " AND ".join(wo)
    gesamt = dbm.wert(db, f"""SELECT COUNT(*) FROM text t
                               LEFT JOIN lektion k ON k.id = t.lektion_id
                              WHERE {bedingung}""", werte)
    zeilen = dbm.zeilen(db, f"""
        SELECT t.id, t.typ, t.titel, t.inhalt, t.uebersetzung, t.geprueft,
               t.kennung, t.reihenfolge, t.niveau, t.richtungen,
               k.nr AS lektion_nr, k.name AS lektion_name,
               (SELECT COUNT(*) FROM textabschnitt a WHERE a.text_id = t.id)
                   AS abschnitte,
               (SELECT COUNT(*) FROM textaufgabe x
                 WHERE x.text_id = t.id AND x.aktiv = 1) AS aufgaben
          FROM text t LEFT JOIN lektion k ON k.id = t.lektion_id
         WHERE {bedingung}
         ORDER BY k.nr, t.reihenfolge, t.id
         LIMIT ? OFFSET ?""", (*werte, anzahl, ab))
    for z in zeilen:
        z["richtungen"] = dbm.j_lesen(z["richtungen"])
        z["geprueft"] = bool(z["geprueft"])
    return {"gesamt": gesamt, "ab": ab, "anzahl": len(zeilen),
            "uebungen": zeilen}


# ------------------------------------------------------------ Bewerten

def bewerten(db: sqlite3.Connection, textaufgabe_id: int,
             antwort: str) -> dict:
    """Bewertet eine freie Übersetzung.

    Bei `bewertung_art: "selbst"` wird genauso verglichen — die
    Einschätzung bleibt aber beim Menschen, der Vergleich ist dort nur
    Hilfestellung. Bei einem Satz zählt das Urteil.
    """
    a = dbm.zeile(db, """SELECT x.*, t.sammlung_id, t.sprache, t.typ
                           FROM textaufgabe x JOIN text t ON t.id = x.text_id
                          WHERE x.id = ?""", (textaufgabe_id,))
    if a is None:
        raise UebungFehler(f"Textaufgabe {textaufgabe_id} gibt es nicht")
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (a["sammlung_id"],))
    # Geprüft wird nach den Regeln der Sprache, in der GEANTWORTET wird:
    # "hin" heißt in die Grundsprache übersetzen. Mit dem griechischen
    # Profil geprüft, würde eine deutsche Antwort nach griechischen
    # Akzentregeln beurteilt.
    code = (s["grundsprache"] if a["typ"] == "uebersetzung_hin"
            else a["sprache"])
    profil = sprachen.profil(code)
    urteil = satzpruefung.pruefen(antwort, dbm.j_lesen(a["erwartet"]) or [],
                                  profil)
    return {"textaufgabe_id": textaufgabe_id,
            "bewertung_art": a["bewertung_art"],
            # Wortgleich heißt: nichts mehr einzuschätzen. Dieselbe
            # Regel wie in `uebung_lernen.pruefen` — zwei Maßstäbe für
            # dieselbe Antwort wären schlimmer als ein unbequemer.
            "zaehlt": a["bewertung_art"] == "genau" or urteil.wortgleich,
            "sprache": code, **urteil.als_dict()}


# ------------------------------------------------- Deckung eines Textes

def _wortliste(text: str) -> list[str]:
    return [w for w in _WORTTRENNER.split(text or "") if w]


def text_pruefen(db: sqlite3.Connection, sammlung_id: int, text: str,
                 bis_lektion: int | None = None) -> dict:
    """Welche Wörter des Textes stehen noch nicht im Bestand?

    Der Zweck ist, Texte VORHER passgenau zu schreiben. Ein Text mit
    dreißig unbekannten Wörtern ist keine Übung, sondern eine Enttäuschung
    — und das stellt sich sonst erst beim Lernen heraus.

    Verglichen wird über alle Formen, nicht nur über die Lemmata: wer
    έγραψαν liest, hat γράφω vor sich.
    """
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (sammlung_id,))
    if s is None:
        raise UebungFehler(f"Sammlung {sammlung_id} gibt es nicht")
    profil = sprachen.profil(s["sprache"])

    def schluessel(w: str) -> str:
        return pruefung.ohne_diakritika(pruefung.normalisieren(w, profil))

    # Der ganze Bestand auf einmal — ein Textabgleich darf nicht je Wort
    # eine Abfrage absetzen.
    bestand: dict[str, list[dict]] = {}
    for z in dbm.zeilen(db, """
            SELECT f.text AS form, f.merkmale, l.id AS lexem_id, l.lemma,
                   l.wortart, k.nr AS lektion_nr
              FROM form f JOIN lexem l ON l.id = f.lexem_id
              LEFT JOIN lektion k ON k.id = l.lektion_id
             WHERE l.sammlung_id = ?""", (sammlung_id,)):
        bestand.setdefault(schluessel(z["form"]), []).append(z)
    for z in dbm.zeilen(db, """SELECT l.id AS lexem_id, l.lemma, l.wortart,
                                      l.lemma AS form, '{}' AS merkmale,
                                      k.nr AS lektion_nr
                                 FROM lexem l
                                 LEFT JOIN lektion k ON k.id = l.lektion_id
                                WHERE l.sammlung_id = ?""", (sammlung_id,)):
        bestand.setdefault(schluessel(z["form"]), []).append(z)

    partikeln = {schluessel(p) for p in sprachen.partikeln(s["sprache"])}
    bekannt: dict[str, dict] = {}
    zu_spaet: dict[str, dict] = {}
    unbekannt: dict[str, dict] = {}
    for wort in _wortliste(text):
        sch = schluessel(wort)
        if not sch:
            continue
        treffer = bestand.get(sch)
        if treffer is None:
            if sch in partikeln:
                continue          # θα, να, δεν — Teil der Form, kein Eintrag
            eintrag = unbekannt.setdefault(sch, {"wort": wort, "anzahl": 0})
            eintrag["anzahl"] += 1
            continue
        rechtzeitig = [t for t in treffer
                       if bis_lektion is None or t["lektion_nr"] is None
                       or t["lektion_nr"] <= bis_lektion]
        ziel = bekannt if rechtzeitig else zu_spaet
        quelle = rechtzeitig or treffer
        eintrag = ziel.setdefault(sch, {
            "wort": wort, "anzahl": 0,
            "lemma": quelle[0]["lemma"], "wortart": quelle[0]["wortart"],
            "lexem_id": quelle[0]["lexem_id"],
            "lektion_nr": quelle[0]["lektion_nr"]})
        eintrag["anzahl"] += 1

    worte_gesamt = sum(e["anzahl"] for e in
                       (*bekannt.values(), *zu_spaet.values(),
                        *unbekannt.values()))
    gedeckt = sum(e["anzahl"] for e in bekannt.values())
    def folge(d): return sorted(d.values(), key=lambda e: -e["anzahl"])
    return {
        "sammlung_id": sammlung_id, "bis_lektion": bis_lektion,
        "woerter_gesamt": worte_gesamt,
        "verschiedene": len(bekannt) + len(zu_spaet) + len(unbekannt),
        "deckung": round(gedeckt / worte_gesamt, 3) if worte_gesamt else 0.0,
        "bekannt": folge(bekannt),
        "zu_spaet": folge(zu_spaet),
        "unbekannt": folge(unbekannt),
        "hinweis": "zu_spaet sind Wörter, die im Bestand stehen, aber erst "
                   "nach dieser Lektion kommen. unbekannt steht gar nicht "
                   "im Bestand — entweder eintragen oder im Text vermeiden.",
    }
