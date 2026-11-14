# Vokabeltrainer — Copyright (C) 2026 Annuschka Brenner
#
# Freie Software unter der GNU Affero General Public License, Fassung 3
# oder später. Herausgegeben in der Hoffnung, dass sie nützt, aber OHNE
# JEDE GEWÄHRLEISTUNG. Siehe die Datei LICENSE.
"""Grammatikregeln — das »Warum ist das so?« an der Frage.

Nicht ein Grammatikbuch zum Durchlesen, sondern die Antwort auf die eine
Frage, die man beim Üben gerade hat: warum heißt es έγραψα und nicht
γράφησα? Gezeigt wird darum immer nur, was zur laufenden Aufgabe passt.

**Gefunden wird über ein Muster, nicht über eine Zuordnung.** Eine Regel
sagt, worauf sie zutrifft — `{"wortart": "verb", "merkmale":
{"tempus": "aorist"}}` —, und greift damit bei jeder Aoristform jedes
Verbs, auch bei denen, die es noch gar nicht gibt. Dieselbe Mechanik wie
bei den erklärten Lücken und den Formgruppen. Wer eine Regel schreibt,
muss den Wortschatz nicht kennen.

**Je enger, desto wichtiger.** Passen mehrere, steht die spezifischste
vorn: die Regel zum Aorist von γράφω vor der zum Aorist überhaupt vor
der zu Verben allgemein. Gezählt wird, wie viele Bedingungen ein Muster
stellt — eine Regel ohne Muster passt überall und steht hinten.
"""

from __future__ import annotations

import sqlite3

import datenbank as dbm
import merkmale as mk

# Mehr als drei Erklärungen zu einer Frage liest niemand. Die Grenze
# steht hier und nicht in der Oberfläche, damit der Server nicht
# seitenweise Text ausliefert, den keiner sieht.
HOECHSTENS = 3


def _muster_passt(muster: dict, wortart: str | None, formgruppe: str | None,
                  merkmale: dict) -> bool:
    """Trifft diese Regel auf die Aufgabe zu?

    Ein leeres Muster trifft immer — so lässt sich eine allgemeine
    Erklärung zur Sammlung hinterlegen.
    """
    if not muster:
        return True
    if muster.get("wortart") and muster["wortart"] != wortart:
        return False
    if muster.get("formgruppe") and muster["formgruppe"] != formgruppe:
        return False
    return mk.passt_muster(muster.get("merkmale") or {}, merkmale or {})


def _enge(muster: dict) -> int:
    """Wie viele Bedingungen stellt das Muster? Mehr heißt spezifischer."""
    if not muster:
        return 0
    zahl = sum(1 for feld in ("wortart", "formgruppe") if muster.get(feld))
    return zahl + len(muster.get("merkmale") or {})


def passende(db: sqlite3.Connection, sammlung_id: int,
             wortart: str | None = None, formgruppe: str | None = None,
             merkmale: dict | None = None,
             nur_geprueft: bool = True) -> list[dict]:
    """Die Regeln, die zu dieser Aufgabe gehören — die engste zuerst."""
    bedingung = "sammlung_id = ?" + (" AND geprueft = 1" if nur_geprueft else "")
    alle = dbm.zeilen(db, f"SELECT * FROM regel WHERE {bedingung}",
                      (sammlung_id,))
    # Die Merkmale der Aufgabe in Normalform, das Muster nicht: gespeichert
    # wird eine Aktivform ohne `genus_verbi`, eine Regel zum Aktiv nennt es
    # aber ausdrücklich. Ohne Normieren träfe sie darum nie. Umgekehrt darf
    # das Muster nicht normiert werden — siehe pruefen_muster().
    if merkmale and wortart:
        try:
            merkmale = mk.normieren(merkmale, wortart)
        except Exception:
            pass                  # lieber ungenau vergleichen als abstürzen
    treffer = []
    for z in alle:
        muster = dbm.j_lesen(z["muster"]) or {}
        if not _muster_passt(muster, wortart, formgruppe, merkmale or {}):
            continue
        treffer.append((_enge(muster), z["reihenfolge"], z["id"],
                        _ausbauen(z, muster)))
    # Eng vor weit; bei gleicher Enge die eigene Reihenfolge, dann die
    # Kennung — damit dieselbe Frage immer dieselbe Antwort gibt.
    treffer.sort(key=lambda t: (-t[0], t[1], t[2]))
    return [t[3] for t in treffer[:HOECHSTENS]]


def fuer_aufgabe(db: sqlite3.Connection, aufgabe_id: int) -> list[dict]:
    """Die Regeln zu einer Aufgabe — das »Warum ist das so?« daneben.

    Zieht sich selbst zusammen, was die Aufgabe kennzeichnet: Wortart,
    Formgruppe und Merkmalsbündel. Bei einer Bedeutungsaufgabe gibt es
    keine Form, dann greifen nur die Regeln zur Wortart und die
    allgemeinen.
    """
    import aufgaben                      # erst hier: sonst im Kreis herum
    a = dbm.zeile(db, """SELECT a.ziel_art, a.ziel_id, l.sammlung_id,
                                l.wortart, l.merkmale AS lexemmerkmale
                           FROM aufgabe a
                           JOIN lexem l ON l.id = a.lexem_id
                          WHERE a.id = ?""", (aufgabe_id,))
    if a is None:
        return []
    merkmale: dict = {}
    gruppe = None
    if a["ziel_art"] == "form":
        f = dbm.zeile(db, "SELECT merkmale FROM form WHERE id = ?",
                      (a["ziel_id"],))
        if f is not None:
            merkmale = dbm.j_lesen(f["merkmale"]) or {}
            e = aufgaben.sammlung_einstellungen(db, a["sammlung_id"])
            g = aufgaben._gruppe_der_form(e["sprache"], a["wortart"],
                                          merkmale)
            gruppe = g["kennung"] if g else None
    return passende(db, a["sammlung_id"], a["wortart"], gruppe, merkmale)


def _ausbauen(z, muster: dict | None = None) -> dict:
    return {
        "id": z["id"],
        "kennung": z["kennung"],
        "titel": z["titel"],
        "text": z["text"],
        "beispiele": dbm.j_lesen(z["beispiele"]) or [],
        "muster": muster if muster is not None else (dbm.j_lesen(z["muster"]) or {}),
        "geprueft": bool(z["geprueft"]),
        "quelle": z["quelle"],
    }


def auflisten(db: sqlite3.Connection, sammlung_id: int,
              nur_ungepruefte: bool = False) -> list[dict]:
    bedingung = "sammlung_id = ?" + (" AND geprueft = 0" if nur_ungepruefte else "")
    return [_ausbauen(z) for z in dbm.zeilen(db, f"""
        SELECT * FROM regel WHERE {bedingung}
         ORDER BY reihenfolge, titel""", (sammlung_id,))]


def lesen(db: sqlite3.Connection, regel_id: int) -> dict | None:
    z = dbm.zeile(db, "SELECT * FROM regel WHERE id = ?", (regel_id,))
    return _ausbauen(z) if z else None


def pruefen_muster(muster: dict | None, sprache: str) -> dict:
    """Weist ein Muster zurück, das nie greifen kann.

    Ein Tippfehler im Merkmalsnamen fällt sonst nie auf: die Regel wird
    angelegt, gilt als geprüft und erscheint trotzdem nirgends. Lieber
    beim Eintragen eine klare Absage.
    """
    muster = dict(muster or {})
    if muster.get("wortart") and muster["wortart"] not in mk.WORTARTEN:
        raise ValueError(f"Unbekannte Wortart: {muster['wortart']!r} "
                         f"(möglich: {', '.join(sorted(mk.WORTARTEN))})")
    mm = muster.get("merkmale") or {}
    if mm:
        try:
            geprueft = mk.pruefen(mm)
        except mk.MerkmalFehler as fehler:
            raise ValueError(str(fehler)) from fehler
        # NICHT normieren: normieren() ergänzt die unmarkierten Merkmale
        # (Aktiv, Indikativ, Singular). In einem MUSTER wäre das falsch —
        # aus »alles im Aorist« würde »Aorist, Aktiv, Indikativ,
        # Singular«, und die Regel griffe bei den Passivformen nicht
        # mehr, für die sie gerade geschrieben wurde.
        muster["merkmale"] = geprueft
    return muster


def anlegen(db: sqlite3.Connection, sammlung_id: int, titel: str, text: str,
            sprache: str, muster: dict | None = None,
            beispiele: list | None = None, kennung: str | None = None,
            quelle: str | None = None, reihenfolge: int = 0,
            geprueft: bool = False) -> dict:
    """Legt eine Regel an — oder berichtigt die mit derselben Kennung.

    Beim Berichtigen fällt `geprueft` zurück auf 0: ein geänderter Text
    ist nicht derselbe, den jemand freigegeben hat.
    """
    muster = pruefen_muster(muster, sprache)
    vorhanden = None
    if kennung:
        vorhanden = dbm.zeile(db, """SELECT * FROM regel
                                      WHERE sammlung_id = ? AND kennung = ?""",
                              (sammlung_id, kennung))
    if vorhanden is not None:
        db.execute("""UPDATE regel SET titel = ?, text = ?, beispiele = ?,
                             muster = ?, quelle = ?, reihenfolge = ?,
                             geprueft = ?, geaendert = datetime('now')
                       WHERE id = ?""",
                   (titel, text, dbm.j_schreiben(beispiele or []),
                    dbm.j_schreiben(muster), quelle, reihenfolge,
                    int(geprueft), vorhanden["id"]))
        return lesen(db, vorhanden["id"])
    cur = db.execute("""INSERT INTO regel
                          (sammlung_id, kennung, titel, text, beispiele,
                           muster, reihenfolge, geprueft, quelle)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                     (sammlung_id, kennung, titel, text,
                      dbm.j_schreiben(beispiele or []),
                      dbm.j_schreiben(muster), reihenfolge,
                      int(geprueft), quelle))
    return lesen(db, cur.lastrowid)


def aendern(db: sqlite3.Connection, regel_id: int, sprache: str,
            **felder) -> dict:
    """Teiländerung. Was nicht genannt ist, bleibt."""
    z = dbm.zeile(db, "SELECT * FROM regel WHERE id = ?", (regel_id,))
    if z is None:
        raise KeyError(f"Regel {regel_id} gibt es nicht")
    setzen, werte = [], []
    for feld in ("titel", "text", "kennung", "quelle", "reihenfolge"):
        if felder.get(feld) is not None:
            setzen.append(f"{feld} = ?"); werte.append(felder[feld])
    if felder.get("beispiele") is not None:
        setzen.append("beispiele = ?")
        werte.append(dbm.j_schreiben(felder["beispiele"]))
    if felder.get("muster") is not None:
        setzen.append("muster = ?")
        werte.append(dbm.j_schreiben(pruefen_muster(felder["muster"], sprache)))
    # Am Inhalt geändert heißt: die Freigabe gilt nicht mehr. Wer nur die
    # Reihenfolge verschiebt, soll dafür nicht noch einmal freigeben.
    inhalt = {"titel", "text", "beispiele", "muster"}
    if any(felder.get(f) is not None for f in inhalt):
        setzen.append("geprueft = 0")
    if not setzen:
        return _ausbauen(z)
    setzen.append("geaendert = datetime('now')")
    db.execute(f"UPDATE regel SET {', '.join(setzen)} WHERE id = ?",
               (*werte, regel_id))
    return lesen(db, regel_id)


def freigeben(db: sqlite3.Connection, regel_id: int, geprueft: bool = True) -> dict:
    db.execute("UPDATE regel SET geprueft = ? WHERE id = ?",
               (int(geprueft), regel_id))
    z = lesen(db, regel_id)
    if z is None:
        raise KeyError(f"Regel {regel_id} gibt es nicht")
    return z


def loeschen(db: sqlite3.Connection, regel_id: int) -> None:
    db.execute("DELETE FROM regel WHERE id = ?", (regel_id,))
