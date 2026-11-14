"""Sammelimport: viele Wörter in einem Aufruf.

Ein Wort je Aufruf anzulegen ist in Ordnung, solange es zehn sind. Bei
sechzehnhundert mit vollständigen Paradigmen ist es weder schnell noch
wiederholbar — und wiederholbar muss es sein, denn beim Befüllen stellt sich
immer erst hinterher heraus, dass eine Zeile falsch war.

Darum drei Eigenschaften, die wichtiger sind als Geschwindigkeit:

**Probelauf.** `nur_pruefen` schreibt nichts und meldet trotzdem alle
Befunde. Man sieht also vorher, was herauskäme.

**Wiederholbar.** Derselbe Eintrag landet nicht zweimal im Bestand. Als
Schlüssel dient die mitgegebene Kennung, sonst Lemma und Wortart. Ein
zweiter Lauf mit berichtigten Daten bessert nach, statt zu verdoppeln.

**Geprüftes bleibt unangetastet.** Hat ein Mensch eine Form bestätigt, wird
sie von einem Import nie überschrieben — die Abweichung wird gemeldet und
die Entscheidung bleibt beim Menschen. Sonst könnte ein fehlerhafter
Durchlauf stillschweigend wegräumen, was jemand mühsam richtiggestellt hat.
"""

from __future__ import annotations

import sqlite3

import aufgaben
import datenbank as dbm
import merkmale as mk
import qualitaet
import sprachen


class ImportFehler(ValueError):
    pass


# ----------------------------------------------------------- Lektionen

def lektion_sichern(db: sqlite3.Connection, sammlung_id: int,
                    nr: int | None, titel: str | None = None,
                    beschreibung: str | None = None) -> int | None:
    """Findet die Lektion zur Nummer oder legt sie an.

    Die Nummer ist der Schlüssel, nicht der Name: Lehrwerke benennen ihre
    Lektionen um, nummerieren sie aber nicht neu.
    """
    if nr is None:
        return None
    vorhanden = dbm.zeile(db, """SELECT * FROM lektion
                                  WHERE sammlung_id = ? AND nr = ?""",
                          (sammlung_id, nr))
    if vorhanden:
        if titel and titel != vorhanden["name"]:
            db.execute("UPDATE lektion SET name = ? WHERE id = ?",
                       (titel, vorhanden["id"]))
        if beschreibung:
            db.execute("UPDATE lektion SET beschreibung = ? WHERE id = ?",
                       (beschreibung, vorhanden["id"]))
        return vorhanden["id"]
    cur = db.execute("""INSERT INTO lektion
                          (sammlung_id, nr, name, beschreibung, reihenfolge)
                        VALUES (?, ?, ?, ?, ?)""",
                     (sammlung_id, nr, titel or f"Lektion {nr}", beschreibung, nr))
    return cur.lastrowid


def lektionen(db: sqlite3.Connection, sammlung_id: int) -> list[dict]:
    return dbm.zeilen(db, """
        SELECT k.id, k.nr, k.name, k.beschreibung, k.reihenfolge,
               (SELECT COUNT(*) FROM lexem l WHERE l.lektion_id = k.id) AS lexeme
          FROM lektion k WHERE k.sammlung_id = ?
         ORDER BY k.nr IS NULL, k.nr, k.reihenfolge, k.name""", (sammlung_id,))


# ------------------------------------------------------------- Zuordnen

def _vorhandenes_lexem(db: sqlite3.Connection, sammlung_id: int,
                       eintrag: dict) -> dict | None:
    kennung = (eintrag.get("kennung") or "").strip()
    if kennung:
        return dbm.zeile(db, """SELECT * FROM lexem
                                 WHERE sammlung_id = ? AND kennung = ?""",
                         (sammlung_id, kennung))
    treffer = dbm.zeilen(db, """SELECT * FROM lexem
                                 WHERE sammlung_id = ? AND lemma = ? AND wortart = ?
                                 ORDER BY id""",
                         (sammlung_id, eintrag["lemma"], eintrag.get("wortart")))
    return treffer[0] if treffer else None


def _formschluessel(merkmale: dict) -> str:
    return mk.schluessel(merkmale)


# -------------------------------------------------------------- Import

def _eintrag_pruefen(code: str, eintrag: dict) -> list[str]:
    """Formale Prüfung vor dem Schreiben. Gibt Beanstandungen zurück."""
    fehler = []
    if not (eintrag.get("lemma") or "").strip():
        fehler.append("lemma fehlt")
    wortart = eintrag.get("wortart") or "sonstiges"
    if wortart not in mk.WORTARTEN:
        fehler.append(f"unbekannte Wortart {wortart!r}")
    try:
        sprachen.pruefen_lexemmerkmale(code, wortart, eintrag.get("merkmale") or {})
    except mk.MerkmalFehler as f:
        fehler.append(str(f))
    for i, f_ in enumerate(eintrag.get("formen") or []):
        if not (f_.get("text") or "").strip():
            fehler.append(f"Form {i + 1}: text fehlt")
        try:
            mk.pruefen(f_.get("merkmale") or {})
        except mk.MerkmalFehler as f:
            fehler.append(f"Form {i + 1}: {f}")
    for i, b in enumerate(eintrag.get("bedeutungen") or []):
        if not (b.get("uebersetzungen") or []):
            fehler.append(f"Bedeutung {i + 1}: keine Übersetzung")
    return fehler


def _uebersetzungen_normieren(bedeutung: dict, grundsprache: str,
                              quelle: str) -> list[dict]:
    reihe = []
    for i, u in enumerate(bedeutung.get("uebersetzungen") or []):
        if isinstance(u, str):
            u = {"text": u}
        text = (u.get("text") or "").strip()
        if not text:
            continue
        reihe.append({"text": text,
                      "sprache": u.get("sprache") or grundsprache,
                      "ist_haupt": int(u.get("ist_haupt", i == 0)),
                      "quelle": u.get("quelle", quelle),
                      "geprueft": int(u.get("geprueft", False))})
    return reihe


def _formen_schreiben(db: sqlite3.Connection, lexem_id: int, formen: list,
                      quelle: str) -> tuple[int, int, list[str]]:
    """Formen anlegen oder nachziehen. Geprüfte werden nie überschrieben."""
    vorhanden = {}
    for z in dbm.zeilen(db, "SELECT * FROM form WHERE lexem_id = ?", (lexem_id,)):
        vorhanden.setdefault(_formschluessel(dbm.j_lesen(z["merkmale"])), []).append(z)

    neu = geaendert = 0
    abweichungen: list[str] = []
    for f in formen:
        merkmale = mk.pruefen(f.get("merkmale") or {})
        schluessel = _formschluessel(merkmale)
        text = f["text"].strip()
        alt_liste = vorhanden.get(schluessel, [])
        gleich = next((a for a in alt_liste if a["text"] == text), None)
        if gleich is not None:
            continue                                   # schon genau so da
        geprueft_alt = [a for a in alt_liste if a["geprueft"]]
        if geprueft_alt:
            # Ein Mensch hat hier schon entschieden. Nicht anrühren.
            abweichungen.append(
                f"{geprueft_alt[0]['text']} ist geprüft, der Import wollte "
                f"{text} — nicht überschrieben")
            continue
        ungeprueft = [a for a in alt_liste if not a["geprueft"]]
        if ungeprueft:
            db.execute("""UPDATE form SET text = ?, aussprache = ?, quelle = ?,
                                 notiz = ?
                           WHERE id = ?""",
                       (text, f.get("aussprache"), f.get("quelle", quelle),
                        f.get("notiz"), ungeprueft[0]["id"]))
            geaendert += 1
            continue
        db.execute("""INSERT INTO form (lexem_id, text, merkmale, ist_grundform,
                                        aussprache, quelle, geprueft, notiz)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                   (lexem_id, text, dbm.j_schreiben(merkmale),
                    int(f.get("ist_grundform", False)), f.get("aussprache"),
                    f.get("quelle", quelle), int(f.get("geprueft", False)),
                    f.get("notiz")))
        neu += 1
    return neu, geaendert, abweichungen


def _bedeutungen_schreiben(db: sqlite3.Connection, lexem_id: int,
                           bedeutungen: list, grundsprache: str,
                           quelle: str) -> int:
    """Bedeutungen ergänzen, nicht ersetzen.

    Ersetzen wäre gefährlich: ein Import mit nur einer Übersetzung würde
    sonst die übrigen wegräumen, obwohl gerade mehrere gültige der
    Normalfall sind.
    """
    vorhandene_texte = {
        (z["text"] or "").casefold()
        for z in dbm.zeilen(db, """SELECT u.text FROM uebersetzung u
                                    JOIN bedeutung b ON b.id = u.bedeutung_id
                                   WHERE b.lexem_id = ?""", (lexem_id,))}
    anzahl = dbm.wert(db, "SELECT COUNT(*) FROM bedeutung WHERE lexem_id = ?",
                      (lexem_id,)) or 0
    dazu = 0
    for b in bedeutungen:
        reihe = _uebersetzungen_normieren(b, grundsprache, quelle)
        neue = [u for u in reihe if u["text"].casefold() not in vorhandene_texte]
        if not neue:
            continue
        cur = db.execute("""INSERT INTO bedeutung (lexem_id, reihenfolge, kontext,
                                                   notiz)
                            VALUES (?, ?, ?, ?)""",
                         (lexem_id, b.get("reihenfolge", anzahl), b.get("kontext"),
                          b.get("notiz")))
        anzahl += 1
        for u in neue:
            db.execute("""INSERT INTO uebersetzung
                            (bedeutung_id, sprache, text, ist_haupt, quelle,
                             geprueft)
                          VALUES (?, ?, ?, ?, ?, ?)""",
                       (cur.lastrowid, u["sprache"], u["text"], u["ist_haupt"],
                        u["quelle"], u["geprueft"]))
            vorhandene_texte.add(u["text"].casefold())
            dazu += 1
    return dazu


def importieren(db: sqlite3.Connection, sammlung_id: int, eintraege: list,
                nur_pruefen: bool = False, quelle: str = "ki") -> dict:
    """Trägt viele Wörter auf einmal ein.

    Bei `nur_pruefen` wird am Ende zurückgerollt — geschrieben wird nichts,
    aber alle Befunde entstehen so, als wäre geschrieben worden. Nur so
    lässt sich vorher sagen, was herauskäme.
    """
    s = dbm.zeile(db, "SELECT * FROM sammlung WHERE id = ?", (sammlung_id,))
    if s is None:
        raise ImportFehler(f"Sammlung {sammlung_id} gibt es nicht")
    code, grundsprache = s["sprache"], s["grundsprache"]

    ergebnis = {"sammlung_id": sammlung_id, "nur_pruefen": nur_pruefen,
                "eingereicht": len(eintraege), "angelegt": 0, "aktualisiert": 0,
                "abgelehnt": 0, "formen_neu": 0, "formen_geaendert": 0,
                "lektionen_neu": [], "eintraege": []}

    db.execute("BEGIN")
    try:
        lektionen_vorher = {z["nr"] for z in lektionen(db, sammlung_id)
                            if z["nr"] is not None}
        for nr, eintrag in enumerate(eintraege, 1):
            if not isinstance(eintrag, dict):
                ergebnis["abgelehnt"] += 1
                ergebnis["eintraege"].append(
                    {"nr": nr, "zustand": "abgelehnt",
                     "befunde": ["kein Objekt"]})
                continue

            beanstandet = _eintrag_pruefen(code, eintrag)
            if beanstandet:
                ergebnis["abgelehnt"] += 1
                ergebnis["eintraege"].append(
                    {"nr": nr, "lemma": eintrag.get("lemma"),
                     "zustand": "abgelehnt", "befunde": beanstandet})
                continue

            lektion_id = lektion_sichern(db, sammlung_id,
                                         eintrag.get("lektion_nr"),
                                         eintrag.get("lektion_titel"))
            wortart = eintrag.get("wortart") or "sonstiges"
            merkmale = sprachen.pruefen_lexemmerkmale(
                code, wortart, eintrag.get("merkmale") or {})

            alt = _vorhandenes_lexem(db, sammlung_id, eintrag)
            if alt is None:
                cur = db.execute("""INSERT INTO lexem
                                      (sammlung_id, lektion_id, lemma, wortart,
                                       merkmale, notiz, reihenfolge, kennung)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                 (sammlung_id, lektion_id, eintrag["lemma"].strip(),
                                  wortart, dbm.j_schreiben(merkmale),
                                  eintrag.get("notiz"),
                                  int(eintrag.get("reihenfolge", 0)),
                                  (eintrag.get("kennung") or "").strip() or None))
                lexem_id = cur.lastrowid
                zustand = "angelegt"
                ergebnis["angelegt"] += 1
            else:
                lexem_id = alt["id"]
                db.execute("""UPDATE lexem
                                 SET lektion_id = COALESCE(?, lektion_id),
                                     merkmale = ?, reihenfolge = ?,
                                     notiz = COALESCE(?, notiz),
                                     geaendert = datetime('now')
                               WHERE id = ?""",
                           (lektion_id, dbm.j_schreiben({**dbm.j_lesen(alt["merkmale"]),
                                                         **merkmale}),
                            int(eintrag.get("reihenfolge", alt["reihenfolge"])),
                            eintrag.get("notiz"), lexem_id))
                zustand = "aktualisiert"
                ergebnis["aktualisiert"] += 1

            neu, geaendert, abweichungen = _formen_schreiben(
                db, lexem_id, eintrag.get("formen") or [], quelle)
            ergebnis["formen_neu"] += neu
            ergebnis["formen_geaendert"] += geaendert
            _bedeutungen_schreiben(db, lexem_id, eintrag.get("bedeutungen") or [],
                                   grundsprache, quelle)
            aufgaben.erzeugen(db, lexem_id)

            bericht = qualitaet.pruefen(db, lexem_id)
            befunde = [{"schwere": b["schwere"], "art": b["art"], "text": b["text"]}
                       for b in bericht["befunde"]]
            eintrag_ergebnis = {"nr": nr, "lemma": eintrag["lemma"],
                                "lexem_id": lexem_id, "zustand": zustand}
            if neu or geaendert:
                eintrag_ergebnis["formen"] = {"neu": neu, "geaendert": geaendert}
            if abweichungen:
                eintrag_ergebnis["abweichungen"] = abweichungen
            if befunde:
                eintrag_ergebnis["befunde"] = befunde
            ergebnis["eintraege"].append(eintrag_ergebnis)

        ergebnis["lektionen_neu"] = sorted(
            {z["nr"] for z in lektionen(db, sammlung_id) if z["nr"] is not None}
            - lektionen_vorher)

        if nur_pruefen:
            db.execute("ROLLBACK")
        else:
            db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise

    # Nur die Einträge zurückgeben, zu denen es etwas zu sagen gibt —
    # bei sechzehnhundert Wörtern will niemand sechzehnhundert Zeilen lesen.
    ergebnis["eintraege"] = [e for e in ergebnis["eintraege"]
                             if e.get("befunde") or e.get("abweichungen")
                             or e["zustand"] == "abgelehnt"]
    ergebnis["mit_befunden"] = len(ergebnis["eintraege"])
    return ergebnis
