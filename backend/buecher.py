"""Bücher — die Klammer über den Texten.

»Es gibt noch keine Bücher, das wäre noch gut. Und tatsächlich würde
ich behaupten, die Texte gehören dem Konto und nicht der Sammlung,
also können sie auch außerhalb der Sammlungskarte dargestellt werden,
als eigene Karte.«

Das ist eine Behauptung über die Ordnung der Dinge, und sie stimmt.
Der Iwein gehört nicht zu »Mittelhochdeutsch, Stammformen«. Er ist
Literatur, die man MIT diesem Wortschatz liest. Als Unterpunkt einer
Vokabelsammlung stand er am falschen Ort — und bei drei Sammlungen
stand der Knopf »Texte« dreimal auf der Übersicht, jedes Mal mit einem
anderen Ausschnitt dahinter.

DIE SAMMLUNG BLEIBT TROTZDEM DRAN, aber am Buch und nicht als Besitz:
an ihr hängt die Deckung — »kann ich das schon lesen?« —, und ohne
einen Wortschatz, gegen den gerechnet wird, gibt es diese Auskunft
nicht. Ein Buch wird gegen einen Wortschatz GELESEN. Das ist etwas
anderes, als ihm zu gehören.

DREI EBENEN: Buch — Kapitel — Text. Beim Iwein sind das 173 Stücke;
ohne die mittlere Ebene wäre das eine Liste, die niemand durchsieht.

Das Kapitel ist ein NAME am Text, keine eigene Tabelle. Es hat keine
Eigenschaften außer seinem Namen und seiner Stelle, und die Stelle
ergibt sich aus der Reihenfolge der Texte. Eine Tabelle dafür wäre
Verwaltung ohne Gegenwert.
"""

from __future__ import annotations

import sqlite3

import datenbank as dbm


def _zugaenglich(db: sqlite3.Connection, benutzer_id: int) -> list[int]:
    """Sammlungen, die diese Person sehen darf — eigene und freigegebene."""
    return [z["id"] for z in dbm.zeilen(db, """
        SELECT s.id FROM sammlung s WHERE s.besitzer_id = ?
        UNION
        SELECT f.sammlung_id FROM freigabe f WHERE f.benutzer_id = ?""",
        (benutzer_id, benutzer_id))]


def auflisten(db: sqlite3.Connection, benutzer_id: int) -> list[dict]:
    """Alle Bücher, die diese Person erreichen kann — über alle Sammlungen.

    Darin liegt der Punkt: die Liste fragt NICHT nach einer Sammlung.
    Wer drei Sprachen lernt, hat ein Regal und nicht drei.

    Eigene Bücher und die aus freigegebenen Sammlungen. Ein Buch, das
    in einer mitgelesenen Sammlung liegt, gehört zwar jemand anderem —
    aber wer den Wortschatz teilt, teilt auch die Lektüre.
    """
    sammlungen = _zugaenglich(db, benutzer_id)
    if not sammlungen:
        return []
    platz = ",".join("?" * len(sammlungen))
    return dbm.zeilen(db, f"""
        SELECT b.*, s.name AS sammlung, s.sprache, s.farbe AS sammlungsfarbe,
               (SELECT COUNT(*) FROM text t
                 WHERE t.buch_id = b.id AND t.typ = 'lesetext') AS texte,
               (SELECT COUNT(*) FROM textabschnitt a
                  JOIN text t ON t.id = a.text_id
                 WHERE t.buch_id = b.id) AS abschnitte,
               (SELECT COUNT(*) FROM textabschnitt a
                  JOIN text t ON t.id = a.text_id
                 WHERE t.buch_id = b.id
                   AND a.referenz IS NOT NULL AND TRIM(a.referenz) != '')
                 AS uebersetzt
          FROM buch b
          JOIN sammlung s ON s.id = b.sammlung_id
         WHERE b.sammlung_id IN ({platz})
         ORDER BY b.reihenfolge, b.titel""", sammlungen)


def lesen(db: sqlite3.Connection, buch_id: int) -> dict:
    b = dbm.zeile(db, """SELECT b.*, s.name AS sammlung, s.sprache
                           FROM buch b JOIN sammlung s ON s.id = b.sammlung_id
                          WHERE b.id = ?""", (buch_id,))
    if b is None:
        raise KeyError(f"Buch {buch_id} gibt es nicht")
    return dict(b)


def anlegen(db: sqlite3.Connection, benutzer_id: int, sammlung_id: int,
            titel: str, verfasser: str | None = None,
            notiz: str | None = None) -> dict:
    titel = (titel or "").strip()
    if not titel:
        raise ValueError("Ein Buch braucht einen Titel")
    if dbm.zeile(db, "SELECT 1 FROM sammlung WHERE id = ?",
                 (sammlung_id,)) is None:
        raise KeyError(f"Sammlung {sammlung_id} gibt es nicht")
    cur = db.execute("""INSERT INTO buch
                          (benutzer_id, sammlung_id, titel, verfasser, notiz)
                        VALUES (?, ?, ?, ?, ?)""",
                     (benutzer_id, sammlung_id, titel,
                      (verfasser or "").strip() or None,
                      (notiz or "").strip() or None))
    return lesen(db, cur.lastrowid)


def aendern(db: sqlite3.Connection, buch_id: int, **felder) -> dict:
    lesen(db, buch_id)
    erlaubt = {"titel", "verfasser", "notiz", "reihenfolge", "sammlung_id"}
    setzen, werte = [], []
    for name, wert in felder.items():
        if name not in erlaubt or wert is None:
            continue
        if name == "titel" and not str(wert).strip():
            raise ValueError("Ein Buch braucht einen Titel")
        setzen.append(f"{name} = ?")
        werte.append(str(wert).strip() if isinstance(wert, str) else wert)
    if setzen:
        db.execute(f"UPDATE buch SET {', '.join(setzen)} WHERE id = ?",
                   (*werte, buch_id))
    return lesen(db, buch_id)


def loeschen(db: sqlite3.Connection, buch_id: int) -> dict:
    """Das Buch weg — die Texte bleiben.

    Ein Buch ist eine Klammer, kein Behälter. Wer die Klammer entfernt,
    will nicht 173 Texte und ihre Übersetzungen verlieren; sie stehen
    danach unter »ohne Buch« und lassen sich neu einsortieren.

    Die Texte werden AUSDRÜCKLICH gelöst und nicht dem Fremdschlüssel
    überlassen: in einem gewanderten Bestand hat `text.buch_id` keinen,
    weil SQLite ihn per ALTER TABLE nicht annimmt.
    """
    lesen(db, buch_id)
    db.execute("UPDATE text SET buch_id = NULL, kapitel = NULL "
               "WHERE buch_id = ?", (buch_id,))
    db.execute("DELETE FROM buch WHERE id = ?", (buch_id,))
    return {"buch_id": buch_id}


def texte_zuordnen(db: sqlite3.Connection, benutzer_id: int,
                   text_ids: list[int], buch_id: int | None,
                   kapitel: str | None = None) -> dict:
    """Texte in ein Buch und ein Kapitel hängen — oder wieder heraus.

    Anders als beim Wortschatz entscheidet das über nichts: kein Text
    wird dadurch früher oder später fällig. Es ordnet nur.

    Fremde Texte werden abgewiesen statt still übergangen — still
    übergangen sähe aus, als wäre zugeordnet worden.
    """
    if not text_ids:
        return {"zugeordnet": 0, "buch_id": buch_id, "kapitel": kapitel}
    sammlungen = _zugaenglich(db, benutzer_id)
    if not sammlungen:
        raise PermissionError("Keine zugängliche Sammlung.")
    kapitel = (kapitel or "").strip() or None

    if buch_id is not None:
        b = lesen(db, buch_id)
        if b["sammlung_id"] not in sammlungen:
            raise PermissionError("Dieses Buch gehört nicht zu dir.")

    platz = ",".join("?" * len(text_ids))
    s_platz = ",".join("?" * len(sammlungen))
    eigene = {z["id"]: z["sammlung_id"] for z in dbm.zeilen(
        db, f"""SELECT id, sammlung_id FROM text
                 WHERE id IN ({platz}) AND sammlung_id IN ({s_platz})""",
        (*text_ids, *sammlungen))}
    fremd = [i for i in text_ids if i not in eigene]
    if fremd:
        raise PermissionError(
            f"{len(fremd)} der Texte sind dir nicht zugänglich.")

    # Ein Buch wird gegen EINEN Wortschatz gelesen. Ein Text aus einer
    # anderen Sammlung darin hieße, die Deckung gegen den falschen
    # Bestand zu rechnen — und die Auskunft »kannst du schon lesen«
    # wäre schlicht erfunden.
    if buch_id is not None:
        falsch = [i for i, sid in eigene.items()
                  if sid != lesen(db, buch_id)["sammlung_id"]]
        if falsch:
            raise ValueError(
                f"{len(falsch)} der Texte gehören zu einem anderen "
                "Wortschatz als das Buch.")

    db.execute(f"""UPDATE text SET buch_id = ?, kapitel = ?,
                          geaendert = datetime('now')
                    WHERE id IN ({platz})""",
               (buch_id, kapitel if buch_id is not None else None, *text_ids))
    return {"zugeordnet": len(text_ids), "buch_id": buch_id,
            "kapitel": kapitel}


def inhalt(db: sqlite3.Connection, buch_id: int) -> dict:
    """Das Inhaltsverzeichnis: Kapitel, darin die Texte.

    Die Reihenfolge der KAPITEL ist die ihres ersten Textes — sonst
    bräuchte das Kapitel doch eine eigene Zeile, nur um eine Zahl zu
    tragen. Wer umsortieren will, sortiert die Texte.
    """
    b = lesen(db, buch_id)
    texte = dbm.zeilen(db, """
        SELECT t.id, t.titel, t.kapitel, t.niveau, t.angelegt,
               LENGTH(t.inhalt) AS zeichen,
               (SELECT COUNT(*) FROM textabschnitt a WHERE a.text_id = t.id)
                 AS abschnitte,
               (SELECT COUNT(*) FROM textabschnitt a
                 WHERE a.text_id = t.id
                   AND a.referenz IS NOT NULL AND TRIM(a.referenz) != '')
                 AS uebersetzt
          FROM text t
         WHERE t.buch_id = ? AND t.typ = 'lesetext'
         ORDER BY t.reihenfolge, t.angelegt, t.id""", (buch_id,))

    kapitel: list[dict] = []
    nach_name: dict[str | None, dict] = {}
    for t in texte:
        name = t["kapitel"] or None
        if name not in nach_name:
            nach_name[name] = {"titel": name, "texte": []}
            kapitel.append(nach_name[name])
        nach_name[name]["texte"].append(t)
    for k in kapitel:
        k["abschnitte"] = sum(t["abschnitte"] for t in k["texte"])
        k["uebersetzt"] = sum(t["uebersetzt"] for t in k["texte"])
    return {**b, "kapitel": kapitel, "texte": len(texte)}
