"""Lernziele und dynamisch zusammengestellte Lernblöcke.

Ein **Lernziel** ist ein Ausschnitt des Bestands mit einem Termin. Der
Ausschnitt ist ausdrücklich nicht an eine Lektion gebunden: er darf über
Lektionen und über Sammlungen greifen — "alle Verben im Passé composé" ist
ein genauso gültiges Ziel wie "Lektion 3 bis Freitag".

Ein **Lernblock** wird daraus errechnet und nicht gespeichert. Er ist immer
der aktuelle Zuschnitt und mischt drei Dinge:

    fällig    was planmäßig dran ist — hat Vorrang
    wacklig   was oft danebenging oder dünn sitzt, auch wenn es nicht fällig
              ist; sonst schleppt man Lücken bis zum Termin mit
    neu       so viel, wie der Termin verlangt — nicht mehr

Und er **verschränkt**: aufeinanderfolgende Aufgaben sollen nicht zum selben
Wort gehören. Verschränktes Üben führt zu schlechteren Sitzungen und besserem
Behalten als blockweises — man merkt sich dabei weniger die Reihenfolge und
mehr die Sache.
"""

from __future__ import annotations

import datetime as dt
import sqlite3

import aufgaben
import datenbank as dbm
import sprachen

# Zuschnitt eines Blocks. Fälliges hat Vorrang, Neues füllt den Rest auf.
ANTEIL_WACKLIG = 0.2
MINDESTENS_NEU = 2


def _heute() -> dt.date:
    return dt.date.today()


# --------------------------------------------------------------- Verwaltung

def anlegen(db: sqlite3.Connection, benutzer_id: int, name: str, umfang: dict,
            termin: str | None = None, ziel: str = "reif",
            notiz: str | None = None) -> dict:
    if termin:
        dt.date.fromisoformat(termin)
    cur = db.execute("""INSERT INTO lernziel
                          (benutzer_id, name, umfang, termin, ziel, notiz)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                     (benutzer_id, name, dbm.j_schreiben(umfang or {}),
                      termin, ziel, notiz))
    return lesen(db, cur.lastrowid)


def lesen(db: sqlite3.Connection, lernziel_id: int) -> dict:
    z = dbm.zeile(db, "SELECT * FROM lernziel WHERE id = ?", (lernziel_id,))
    if z is None:
        raise KeyError(f"Lernziel {lernziel_id} gibt es nicht")
    z["umfang"] = dbm.j_lesen(z["umfang"])
    return z


def auflisten(db: sqlite3.Connection, benutzer_id: int,
              nur_aktive: bool = True) -> list[dict]:
    sql = "SELECT * FROM lernziel WHERE benutzer_id = ?"
    if nur_aktive:
        sql += " AND aktiv = 1"
    liste = dbm.zeilen(db, sql + " ORDER BY termin IS NULL, termin, name",
                       (benutzer_id,))
    for z in liste:
        z["umfang"] = dbm.j_lesen(z["umfang"])
    return liste


# ------------------------------------------------------------------- Umfang

def _zugaenglich(db: sqlite3.Connection, benutzer_id: int) -> list[int]:
    return [z["id"] for z in dbm.zeilen(db, """
        SELECT s.id FROM sammlung s WHERE s.besitzer_id = ?
        UNION
        SELECT f.sammlung_id FROM freigabe f WHERE f.benutzer_id = ?""",
        (benutzer_id, benutzer_id))]


def aufgaben_im_umfang(db: sqlite3.Connection, benutzer_id: int,
                       umfang: dict) -> list[dict]:
    """Alle aktiven Aufgaben, die in den Ausschnitt fallen, mit Lernstand.

    Die Formgruppe wird nachträglich in Python geprüft, nicht in SQL: sie
    ergibt sich aus dem Merkmalsbündel der Form und dem Sprachprofil, und das
    lässt sich nicht als Spaltenvergleich ausdrücken. Bei Familienmengen ist
    das ohne Belang.
    """
    sammlungen = umfang.get("sammlungen") or _zugaenglich(db, benutzer_id)
    if not sammlungen:
        return []
    bedingungen = [f"l.sammlung_id IN ({','.join('?' * len(sammlungen))})",
                   "a.aktiv = 1"]
    werte: list = [benutzer_id, *sammlungen]

    for feld, spalte in (("lektionen", "l.lektion_id"),
                         ("wortarten", "l.wortart"),
                         ("typen", "a.typ"),
                         ("lexeme", "l.id")):
        auswahl = umfang.get(feld)
        if auswahl:
            bedingungen.append(f"{spalte} IN ({','.join('?' * len(auswahl))})")
            werte += list(auswahl)

    reihe = dbm.zeilen(db, f"""
        SELECT a.id AS aufgabe_id, a.typ, a.ziel_art, a.ziel_id,
               l.id AS lexem_id, l.lemma, l.wortart, l.lektion_id,
               l.sammlung_id, s.sprache,
               z.zustand, z.stabilitaet, z.schwierigkeit, z.faellig,
               z.letzte_wiederholung, z.anzahl, z.anzahl_fehler
          FROM aufgabe a
          JOIN lexem l ON l.id = a.lexem_id
          JOIN sammlung s ON s.id = l.sammlung_id
          LEFT JOIN lernzustand z
                 ON z.aufgabe_id = a.id AND z.benutzer_id = ?
         WHERE {' AND '.join(bedingungen)}""", werte)

    gewuenschte_gruppen = set(umfang.get("formgruppen") or [])
    if not gewuenschte_gruppen:
        return reihe

    gefiltert = []
    for r in reihe:
        if r["ziel_art"] != "form" or not r["ziel_id"]:
            continue
        f = dbm.zeile(db, "SELECT merkmale FROM form WHERE id = ?", (r["ziel_id"],))
        if f is None:
            continue
        gruppe = aufgaben._gruppe_der_form(r["sprache"], r["wortart"],
                                           dbm.j_lesen(f["merkmale"]))
        if gruppe and gruppe["kennung"] in gewuenschte_gruppen:
            gefiltert.append(r)
    return gefiltert


def umfang_beschreiben(db: sqlite3.Connection, umfang: dict) -> str:
    """Den Ausschnitt in einem Satz. Damit auf der Übersicht steht, worum es
    geht, und nicht nur eine Zahl."""
    teile = []
    if umfang.get("sammlungen"):
        namen = [dbm.wert(db, "SELECT name FROM sammlung WHERE id = ?", (i,))
                 for i in umfang["sammlungen"]]
        teile.append(", ".join(n for n in namen if n))
    if umfang.get("lektionen"):
        namen = [dbm.wert(db, "SELECT name FROM lektion WHERE id = ?", (i,))
                 for i in umfang["lektionen"]]
        teile.append("Lektion " + ", ".join(n for n in namen if n))
    if umfang.get("wortarten"):
        import merkmale as mk
        teile.append(", ".join(mk.WORTARTEN.get(w, w) for w in umfang["wortarten"]))
    if umfang.get("formgruppen"):
        namen = []
        for kennung in umfang["formgruppen"]:
            for code in sprachen.PROFILE:
                g = sprachen.formgruppe(code, kennung)
                if g:
                    namen.append(g["name"])
                    break
        teile.append(", ".join(namen) if namen
                     else ", ".join(umfang["formgruppen"]))
    if umfang.get("typen"):
        teile.append(", ".join(aufgaben.TYPEN[t]["name"]
                               for t in umfang["typen"] if t in aufgaben.TYPEN))
    if umfang.get("lexeme"):
        teile.append(f"{len(umfang['lexeme'])} ausgewählte Wörter")
    return " · ".join(teile) if teile else "der ganze zugängliche Bestand"


# --------------------------------------------------------------- Fortschritt

def _geschafft(r: dict, ziel: str) -> bool:
    if ziel == "einmal_richtig":
        return bool(r["anzahl"]) and r["zustand"] not in (None, "neu", "verlernt")
    return r["zustand"] == "reif"


def fortschritt(db: sqlite3.Connection, benutzer_id: int,
                lernziel_id: int) -> dict:
    """Wie weit ist das Ziel, und was heißt das für heute?"""
    ziel = lesen(db, lernziel_id)
    reihe = aufgaben_im_umfang(db, benutzer_id, ziel["umfang"])
    heute = _heute().isoformat()

    gesamt = len(reihe)
    geschafft = sum(1 for r in reihe if _geschafft(r, ziel["ziel"]))
    neu = sum(1 for r in reihe if r["zustand"] in (None, "neu"))
    faellig = sum(1 for r in reihe
                  if r["zustand"] in ("lernen", "reif") and (r["faellig"] or "") <= heute)
    verlernt = sum(1 for r in reihe if r["zustand"] == "verlernt")
    offen = gesamt - geschafft

    tage = None
    taeglich = None
    lage = "ohne Termin"
    if ziel["termin"]:
        tage = (dt.date.fromisoformat(ziel["termin"]) - _heute()).days
        if tage < 0:
            lage = f"Termin seit {abs(tage)} Tagen vorbei"
        elif tage == 0:
            lage = "heute fällig"
            taeglich = offen
        else:
            # Was täglich neu dazukommen muss, damit es bis zum Termin reicht.
            # Eine neue Aufgabe braucht erfahrungsgemäß mehrere Wiederholungen
            # bis zur Reife, darum ein Sicherheitsabstand von drei Tagen.
            spanne = max(1, tage - 3)
            taeglich = -(-neu // spanne)        # aufgerundet
            lage = (f"noch {tage} Tage — dafür täglich etwa {taeglich} neue "
                    f"Aufgaben")

    return {
        "lernziel_id": lernziel_id,
        "name": ziel["name"],
        "umfang_text": umfang_beschreiben(db, ziel["umfang"]),
        "ziel": ziel["ziel"],
        "termin": ziel["termin"],
        "tage_bis_termin": tage,
        "lage": lage,
        "gesamt": gesamt,
        "geschafft": geschafft,
        "offen": offen,
        "anteil": round(geschafft / gesamt, 3) if gesamt else 0.0,
        "neu": neu,
        "faellig": faellig,
        "verlernt": verlernt,
        "neu_taeglich_noetig": taeglich,
        "schaffbar": (taeglich is None or taeglich <= 40),
    }


# ----------------------------------------------------------------- Lernblock

def _dringlichkeit(r: dict, heute: str) -> float:
    """Je überfälliger und je wackliger, desto weiter nach vorn."""
    if r["zustand"] == "verlernt":
        return -1000.0
    if not r["faellig"]:
        return 0.0
    try:
        tage_ueber = (dt.date.fromisoformat(heute)
                      - dt.date.fromisoformat(r["faellig"])).days
    except ValueError:
        return 0.0
    # Überfälliges zuerst; bei gleichem Rückstand das Dünnere zuerst.
    return -(tage_ueber * 10 + (100.0 / max(1.0, r["stabilitaet"] or 1.0)))


def _wackligkeit(r: dict) -> float:
    if not r["anzahl"]:
        return 0.0
    fehlerquote = r["anzahl_fehler"] / r["anzahl"]
    duenn = 1.0 / max(1.0, r["stabilitaet"] or 1.0)
    return fehlerquote * 2 + duenn


def verschraenken(reihe: list[dict]) -> list[dict]:
    """Mischt so, dass aufeinanderfolgende Aufgaben nicht zum selben Wort
    gehören.

    Verschränktes Üben führt zu schlechteren Sitzungen und besserem Behalten
    als blockweises: wer sechs Formen desselben Verbs hintereinander bekommt,
    merkt sich die Reihenfolge statt der Formen.
    """
    rest = list(reihe)
    ergebnis: list[dict] = []
    letztes_lexem = None
    while rest:
        gewaehlt = next((r for r in rest if r["lexem_id"] != letztes_lexem), rest[0])
        rest.remove(gewaehlt)
        ergebnis.append(gewaehlt)
        letztes_lexem = gewaehlt["lexem_id"]
    return ergebnis


def block(db: sqlite3.Connection, benutzer_id: int, lernziel_id: int,
          anzahl: int = 20) -> dict:
    """Stellt den nächsten Lernblock zusammen und begründet den Zuschnitt."""
    ziel = lesen(db, lernziel_id)
    reihe = aufgaben_im_umfang(db, benutzer_id, ziel["umfang"])
    heute = _heute().isoformat()
    stand = fortschritt(db, benutzer_id, lernziel_id)

    faellig = [r for r in reihe
               if r["zustand"] == "verlernt"
               or (r["zustand"] in ("lernen", "reif") and (r["faellig"] or "") <= heute)]
    faellig.sort(key=lambda r: _dringlichkeit(r, heute))

    nicht_faellig = [r for r in reihe
                     if r not in faellig and r["zustand"] not in (None, "neu",
                                                                  "ausgesetzt")]
    wacklig = sorted(nicht_faellig, key=_wackligkeit, reverse=True)
    wacklig = [r for r in wacklig if _wackligkeit(r) > 0.5]

    neu = [r for r in reihe if r["zustand"] in (None, "neu")]
    # Reihenfolge der Neuen: nach Lektion und Wort, damit Zusammengehöriges
    # zusammen eingeführt wird — verschränkt wird erst danach.
    neu.sort(key=lambda r: (r["lektion_id"] or 0, r["lexem_id"], r["typ"]))

    # --- Zuschnitt
    platz = anzahl
    genommen_faellig = faellig[:platz]
    platz -= len(genommen_faellig)

    tagesbedarf = stand["neu_taeglich_noetig"]
    hoechstens_neu = platz if tagesbedarf is None else min(platz, max(
        MINDESTENS_NEU, tagesbedarf))

    genommen_wacklig = []
    if platz > hoechstens_neu:
        raum = min(int(anzahl * ANTEIL_WACKLIG), platz - hoechstens_neu)
        genommen_wacklig = wacklig[:max(0, raum)]
        platz -= len(genommen_wacklig)

    genommen_neu = neu[:min(platz, hoechstens_neu)]
    platz -= len(genommen_neu)

    # Bleibt Platz, mit weiterem Wackligem auffüllen.
    if platz > 0:
        weitere = [r for r in wacklig if r not in genommen_wacklig][:platz]
        genommen_wacklig += weitere

    zusammen = genommen_faellig + genommen_wacklig + genommen_neu
    gemischt = verschraenken(zusammen)

    begruendung = []
    if genommen_faellig:
        begruendung.append(f"{len(genommen_faellig)} planmäßig fällig")
    if genommen_wacklig:
        begruendung.append(f"{len(genommen_wacklig)} wacklig "
                           f"(oft daneben oder dünn)")
    if genommen_neu:
        if tagesbedarf:
            begruendung.append(f"{len(genommen_neu)} neu — so viel verlangt "
                               f"der Termin")
        else:
            begruendung.append(f"{len(genommen_neu)} neu")

    return {
        "lernziel_id": lernziel_id,
        "name": ziel["name"],
        "aufgaben": [{"aufgabe_id": r["aufgabe_id"], "typ": r["typ"],
                      "lexem_id": r["lexem_id"], "lemma": r["lemma"],
                      "zustand": r["zustand"] or "neu",
                      "herkunft": ("faellig" if r in genommen_faellig
                                   else "wacklig" if r in genommen_wacklig
                                   else "neu")}
                     for r in gemischt],
        "anzahl": len(gemischt),
        "zusammensetzung": {
            "faellig": len(genommen_faellig),
            "wacklig": len(genommen_wacklig),
            "neu": len(genommen_neu),
        },
        "begruendung": ("Zusammengestellt aus " + ", ".join(begruendung) + ". "
                        "Verschränkt gemischt: aufeinanderfolgende Aufgaben "
                        "gehören nicht zum selben Wort."
                        if begruendung else "Im Umfang dieses Ziels ist gerade "
                                            "nichts zu tun."),
        "fortschritt": stand,
    }
