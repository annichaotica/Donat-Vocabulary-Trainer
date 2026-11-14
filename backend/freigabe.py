"""Freigabe in großen Mengen.

Wenn ein Agent sechzehnhundert Wörter mit vollständigen Paradigmen einträgt,
entstehen mehrere tausend Formen. Jede einzeln zu bestätigen ist nicht
machbar — und ungeprüft wird nichts abgefragt. Ohne einen Weg, ganze
Lektionen auf einmal anzusehen, wäre der ganze Sammelimport wertlos.

Zwei Dinge leistet dieses Modul:

**Ansehen.** Je Wort die Formen als Paradigmentabelle, Zelle für Zelle nach
den Formgruppen der Sprache geordnet — so, wie es im Lehrbuch steht. Eine
Liste von Formen in Eingabereihenfolge lässt sich nicht prüfen; eine Tabelle
mit einer leeren oder doppelt besetzten Zelle sieht man auf einen Blick.
Dazu die Befunde der Qualitätsprüfung, damit nicht geraten werden muss,
warum etwas nicht stimmt.

**Freigeben.** Je Wort oder je Lektion, mit einzeln abwählbaren Zellen.

**Die Freigabe bleibt beim Menschen.** Es gibt dafür absichtlich kein
MCP-Werkzeug: ein Agent, der seine eigenen Einträge im Stapel freigibt,
hätte die Prüfung abgeschafft, nicht erledigt.
"""

from __future__ import annotations

import sqlite3

import aufgaben
import datenbank as dbm
import merkmale as mk
import qualitaet
import sprachen


class FreigabeFehler(ValueError):
    pass


def _formen_ordnen(code: str, wortart: str, formen: list[dict],
                   luecken: list) -> tuple[list[dict], list[dict]]:
    """Ordnet die Formen in die Formgruppen der Sprache ein.

    Gibt die Gruppen und die Formen zurück, die in keine passen. Letztere
    sind kein Fehler, aber sie gehören sichtbar gemacht: sie erscheinen in
    keiner Tabelle und lassen sich nicht gemeinsam zuschalten.
    """
    # Über die Normalform, nicht über das rohe Bündel: eine griechische
    # Aktivform trägt kein genus_verbi, die Aktivgruppe aber schon. Ohne
    # normieren fiele jede Verbform aus ihrer eigenen Tabelle heraus.
    nach_schluessel: dict[str, list[dict]] = {}
    for f in formen:
        if f["ist_grundform"] and not f["merkmale"]:
            continue
        schluessel = mk.schluessel(mk.normieren(f["merkmale"], wortart))
        nach_schluessel.setdefault(schluessel, []).append(f)

    gruppen, benutzt = [], set()
    for g in sprachen.formgruppen(code, wortart):
        zellen, belegt, erklaert = [], 0, 0
        for zelle in g["zellen"]:
            dazu = nach_schluessel.get(
                mk.schluessel(mk.normieren(zelle, wortart)), [])
            for f in dazu:
                benutzt.add(f["id"])
            if dazu:
                belegt += 1
            elif mk.ist_erklaerte_luecke(luecken, zelle):
                erklaert += 1
            # In der Tabelle nur, was die Zelle von ihren Geschwistern
            # unterscheidet. Der Gruppenname steht als Überschrift darüber;
            # ihn in jeder Zeile zu wiederholen ("Ενεστώτας, 1. Sg." sechsmal)
            # verdeckt gerade das, worauf es ankommt.
            eigen = {d: w for d, w in zelle.items()
                     if d not in g["merkmale"]}
            # Hat die Zelle nichts Eigenes, IST sie die Gruppe — dann sagt
            # der Gruppenname schon alles, und die Zeile bleibt unbeschriftet.
            zellen.append({
                "merkmale": zelle,
                "beschriftung": mk.beschriften(eigen) if eigen else "",
                "erklaerte_luecke": mk.ist_erklaerte_luecke(luecken, zelle),
                "formen": [_form(f) for f in dazu],
            })
        if not belegt:
            # Eine ganz leere Gruppe ist hier nur Rauschen — zu prüfen ist,
            # was eingetragen wurde.
            continue
        gruppen.append({"kennung": g["kennung"], "name": g["name"],
                        "kurz": g.get("kurz") or g["name"],
                        "zellen": zellen, "belegt": belegt,
                        "erklaert": erklaert,
                        # Erklärte Lücken zählen nicht gegen das Paradigma.
                        # πρέπει als "1 von 6" zu zeigen, wäre ein Vorwurf
                        # an ein vollständiges Wort.
                        "von": len(g["zellen"]) - erklaert})

    ausserhalb = [_form(f) for f in formen
                  if f["id"] not in benutzt
                  and not (f["ist_grundform"] and not f["merkmale"])]
    return gruppen, ausserhalb


def _form(f: dict) -> dict:
    return {"form_id": f["id"], "text": f["text"],
            "geprueft": bool(f["geprueft"]), "quelle": f["quelle"],
            "ist_grundform": bool(f["ist_grundform"]),
            "ist_variante": bool(f["ist_variante"]),
            "aussprache": f["aussprache"], "notiz": f["notiz"]}


def uebersicht(db: sqlite3.Connection, sammlung_id: int,
               lektion_nr: int | None = None, wortart: str | None = None,
               nur_offene: bool = True, ab: int = 0,
               anzahl: int = 25) -> dict:
    """Die Prüfansicht: Wörter mit ihren Paradigmen als Tabellen."""
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (sammlung_id,))
    if s is None:
        raise FreigabeFehler(f"Sammlung {sammlung_id} gibt es nicht")
    code = s["sprache"]

    wo, werte = ["l.sammlung_id = ?"], [sammlung_id]
    if lektion_nr is not None:
        wo.append("""l.lektion_id IN (SELECT id FROM lektion
                       WHERE sammlung_id = ? AND nr = ?)""")
        werte += [sammlung_id, lektion_nr]
    if wortart:
        wo.append("l.wortart = ?"); werte.append(wortart)
    if nur_offene:
        wo.append("""EXISTS (SELECT 1 FROM form f
                       WHERE f.lexem_id = l.id AND f.geprueft = 0)""")
    bedingung = " AND ".join(wo)

    gesamt = dbm.wert(db, f"SELECT COUNT(*) FROM lexem l WHERE {bedingung}",
                      werte)
    offen_gesamt = dbm.wert(db, f"""
        SELECT COUNT(*) FROM form f JOIN lexem l ON l.id = f.lexem_id
         WHERE f.geprueft = 0 AND {bedingung}""", werte)
    zeilen = dbm.zeilen(db, f"""
        SELECT l.*, k.nr AS lektion_nr, k.name AS lektion_name
          FROM lexem l LEFT JOIN lektion k ON k.id = l.lektion_id
         WHERE {bedingung}
         ORDER BY k.nr, l.reihenfolge, l.lemma
         LIMIT ? OFFSET ?""", (*werte, anzahl, ab))

    woerter = []
    for z in zeilen:
        formen = dbm.zeilen(db, "SELECT * FROM form WHERE lexem_id = ?", (z["id"],))
        for f in formen:
            f["merkmale"] = dbm.j_lesen(f["merkmale"])
        formen.sort(key=lambda f: mk.sortierbar(f["merkmale"]))
        luecken = dbm.j_lesen(z["luecken"]) or []
        gruppen, ausserhalb = _formen_ordnen(code, z["wortart"], formen, luecken)
        grundform = next((_form(f) for f in formen if f["ist_grundform"]), None)
        bericht = qualitaet.pruefen(db, z["id"])
        woerter.append({
            "lexem_id": z["id"], "lemma": z["lemma"], "wortart": z["wortart"],
            "wortart_name": mk.WORTARTEN.get(z["wortart"], z["wortart"]),
            "merkmale": dbm.j_lesen(z["merkmale"]),
            "lektion_nr": z["lektion_nr"], "lektion_name": z["lektion_name"],
            "notiz": z["notiz"], "grundform": grundform,
            "bedeutungen": [
                {"kontext": b["kontext"],
                 "uebersetzungen": [u["text"] for u in dbm.zeilen(db, """
                     SELECT text FROM uebersetzung WHERE bedeutung_id = ?
                      ORDER BY ist_haupt DESC, id""", (b["id"],))]}
                for b in dbm.zeilen(db, """SELECT * FROM bedeutung
                                            WHERE lexem_id = ?
                                            ORDER BY reihenfolge, id""",
                                    (z["id"],))],
            "gruppen": gruppen, "ausserhalb": ausserhalb,
            "offen": sum(1 for f in formen if not f["geprueft"]),
            "formen_gesamt": len(formen),
            # Nur, was wirklich zu sagen ist. "Alles in Ordnung" soll man
            # ohne Nachdenken drücken können, wenn hier nichts steht.
            "befunde": [{"art": b["art"], "schwere": b["schwere"],
                         "text": b["text"], "betrifft": b["betrifft"],
                         "rat": b["rat"]}
                        for b in bericht["befunde"]
                        if b["schwere"] != "notiz"],
        })

    return {"sammlung_id": sammlung_id, "sprache": code,
            "lektion_nr": lektion_nr, "gesamt": gesamt,
            "offen_gesamt": offen_gesamt, "ab": ab, "anzahl": len(woerter),
            "woerter": woerter}


def offene_lektionen(db: sqlite3.Connection, sammlung_id: int) -> dict:
    """Wo ist noch etwas freizugeben? Der Einstieg in die Prüfansicht."""
    if dbm.zeile(db, "SELECT 1 FROM sammlung WHERE id = ?", (sammlung_id,)) is None:
        raise FreigabeFehler(f"Sammlung {sammlung_id} gibt es nicht")
    zeilen = dbm.zeilen(db, """
        SELECT k.id AS lektion_id, k.nr, k.name,
               COUNT(DISTINCT l.id) AS woerter,
               SUM(CASE WHEN f.geprueft = 0 THEN 1 ELSE 0 END) AS offen
          FROM lexem l
          LEFT JOIN lektion k ON k.id = l.lektion_id
          LEFT JOIN form f ON f.lexem_id = l.id
         WHERE l.sammlung_id = ?
         GROUP BY k.id
         HAVING offen > 0
         ORDER BY k.nr""", (sammlung_id,))
    return {"sammlung_id": sammlung_id, "lektionen": zeilen,
            "offen_gesamt": sum(z["offen"] or 0 for z in zeilen)}


def _betroffene(db: sqlite3.Connection, sammlung_id: int,
                form_ids: list | None, lexem_ids: list | None,
                lektion_nr: int | None, ausser: list | None) -> list[int]:
    """Welche Formen sind gemeint? Immer nur innerhalb dieser Sammlung.

    Die Einschränkung ist nicht formal: ohne sie gäbe eine fremde Kennung
    im Stapel eine Freigabe auf einem Bestand, der jemand anderem gehört.
    """
    wo, werte = ["l.sammlung_id = ?"], [sammlung_id]
    genannt = False
    if form_ids:
        wo.append(f"f.id IN ({','.join('?' * len(form_ids))})")
        werte += [int(x) for x in form_ids]
        genannt = True
    if lexem_ids:
        wo.append(f"l.id IN ({','.join('?' * len(lexem_ids))})")
        werte += [int(x) for x in lexem_ids]
        genannt = True
    if lektion_nr is not None:
        wo.append("""l.lektion_id IN (SELECT id FROM lektion
                       WHERE sammlung_id = ? AND nr = ?)""")
        werte += [sammlung_id, lektion_nr]
        genannt = True
    if not genannt:
        raise FreigabeFehler(
            "Es ist nicht gesagt, was freigegeben werden soll. Eine ganze "
            "Sammlung auf einmal freizugeben wäre keine Prüfung.")
    if ausser:
        wo.append(f"f.id NOT IN ({','.join('?' * len(ausser))})")
        werte += [int(x) for x in ausser]
    return [z["id"] for z in dbm.zeilen(db, f"""
        SELECT f.id FROM form f JOIN lexem l ON l.id = f.lexem_id
         WHERE {' AND '.join(wo)}""", werte)]


def setzen(db: sqlite3.Connection, sammlung_id: int,
           form_ids: list | None = None, lexem_ids: list | None = None,
           lektion_nr: int | None = None, ausser: list | None = None,
           geprueft: bool = True) -> dict:
    """Gibt Formen frei oder nimmt die Freigabe zurück.

    `ausser` ist der Weg für die abgewählten Zellen: man sieht eine Lektion
    an, hakt die zwei falschen Formen ab und gibt den Rest frei.
    """
    if dbm.zeile(db, "SELECT 1 FROM sammlung WHERE id = ?", (sammlung_id,)) is None:
        raise FreigabeFehler(f"Sammlung {sammlung_id} gibt es nicht")
    ziele = _betroffene(db, sammlung_id, form_ids, lexem_ids, lektion_nr, ausser)
    if not ziele:
        return {"gesetzt": 0, "geprueft": geprueft, "lexeme": 0}
    betroffene_lexeme = {z["lexem_id"] for z in dbm.zeilen(db, f"""
        SELECT DISTINCT lexem_id FROM form
         WHERE id IN ({','.join('?' * len(ziele))})""", ziele)}
    db.execute(f"""UPDATE form SET geprueft = ?
                    WHERE id IN ({','.join('?' * len(ziele))})""",
               (int(bool(geprueft)), *ziele))
    # Die Aufgaben hängen daran: ungeprüfte Formen werden nicht abgefragt.
    for lexem_id in betroffene_lexeme:
        aufgaben.erzeugen(db, lexem_id)
    return {"gesetzt": len(ziele), "geprueft": bool(geprueft),
            "lexeme": len(betroffene_lexeme)}
