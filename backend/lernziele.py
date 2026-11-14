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
    """Dieselbe Uhr wie im Lernkern.

    Hier stand `dt.date.today()`. Die Tests stellen die Uhr über
    `lernen.heute` (»zwei Wochen später«) — die Lernzielrechnung blieb
    dabei im echten Heute stehen, und zwei Module waren verschiedener
    Meinung darüber, welcher Tag ist.
    """
    import lernen
    return lernen.heute()


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


def fortschritt(db: sqlite3.Connection, benutzer_id: int, lernziel_id: int,
                reihe: list[dict] | None = None, ziel: dict | None = None) -> dict:
    """Wie weit ist das Ziel, und was heißt das für heute?

    `reihe` und `ziel` dürfen mitgegeben werden, wenn der Aufrufer sie schon
    hat — sonst liefe die vollständige Abfrage zweimal je Blockaufruf.
    """
    ziel = ziel or lesen(db, lernziel_id)
    if reihe is None:
        reihe = aufgaben_im_umfang(db, benutzer_id, ziel["umfang"])
    heute = _heute().isoformat()

    gesamt = len(reihe)
    geschafft = sum(1 for r in reihe if _geschafft(r, ziel["ziel"]))
    neu = sum(1 for r in reihe if r["zustand"] in (None, "neu"))
    faellig = sum(1 for r in reihe
                  if r["zustand"] in ("lernen", "reif")
                  and r["faellig"] and r["faellig"] <= heute)
    verlernt = sum(1 for r in reihe if r["zustand"] == "verlernt")
    offen = gesamt - geschafft

    # Wie viele WÖRTER noch nicht angefangen sind. Das Ziel rechnet in
    # Aufgaben, die Tageseinstellung in Wörtern — ohne diese Zahl
    # verglich die Machbarkeitsprüfung Äpfel mit Birnen: »40 neue
    # Aufgaben« sind bei einem griechischen Verb mit vierzig Formen ein
    # einziges Wort.
    neue_woerter = len({r["lexem_id"] for r in reihe
                        if r["zustand"] in (None, "neu")})

    tage = None
    taeglich = None
    woerter_taeglich = None
    lage = "ohne Termin"
    if ziel["termin"]:
        tage = (dt.date.fromisoformat(ziel["termin"]) - _heute()).days
        if tage < 0:
            lage = f"Termin seit {abs(tage)} Tagen vorbei"
        elif tage == 0:
            lage = "heute fällig"
            taeglich = offen
            woerter_taeglich = neue_woerter
        else:
            # Was täglich neu dazukommen muss, damit es bis zum Termin reicht.
            # Eine neue Aufgabe braucht erfahrungsgemäß mehrere Wiederholungen
            # bis zur Reife, darum ein Sicherheitsabstand von drei Tagen.
            spanne = max(1, tage - 3)
            taeglich = -(-neu // spanne)        # aufgerundet
            woerter_taeglich = -(-neue_woerter // spanne)
            lage = (f"noch {tage} Tage — dafür täglich etwa {taeglich} neue "
                    f"Aufgaben")

    # Ist das mit den EIGENEN Einstellungen zu schaffen?
    #
    # Hier stand `taeglich <= 40` — eine fest eingebaute Zahl, die mit
    # niemandes Einstellung etwas zu tun hatte, und dazu in der falschen
    # Einheit. Die Tagesdosis kam gar nicht vor: ein Ziel konnte
    # »schaffbar« melden, während die Grenze es still unmöglich machte.
    #
    # Die Schranke fürs Neue ist exakt bekannt und nicht geschätzt: von
    # der Tagesdosis ist der Anteil NEU_ANTEIL fürs Neue reserviert.
    import lernen as lernmodul
    e = lernmodul.benutzer_einstellungen(db, benutzer_id)
    dosis = e["fragen_je_tag"]
    grenze_neu = round(dosis * lernmodul.NEU_ANTEIL) if dosis else None
    huerden = []
    if taeglich is not None:
        if woerter_taeglich > e["neu_je_sitzung"]:
            huerden.append(
                f"täglich {woerter_taeglich} neue Wörter nötig, eingestellt "
                f"sind {e['neu_je_sitzung']}")
        if grenze_neu is not None and taeglich > grenze_neu:
            huerden.append(
                f"täglich {taeglich} neue Aufgaben nötig, dein Pensum von "
                f"{dosis} Fragen lässt {grenze_neu} zu")
    # Welches Pensum nötig wäre, damit so viel Neues durchkommt. Keine
    # Schätzung: es ist die Umkehrung der Reservierung.
    pensum_noetig = (None if taeglich is None
                     else max(dosis or 0,
                              -(-taeglich * 100 // int(lernmodul.NEU_ANTEIL * 100))))

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
        "neue_woerter": neue_woerter,
        "woerter_taeglich_noetig": woerter_taeglich,
        # Was den Weg versperrt, im Klartext und in den eigenen Einheiten.
        # Leer heißt: es geht sich aus.
        "huerden": huerden,
        "pensum_noetig": pensum_noetig,
        "pensum_jetzt": dosis,
        "neue_woerter_jetzt": e["neu_je_sitzung"],
        "schaffbar": not huerden,
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


def _wortweise(reihe: list[dict]) -> list[dict]:
    """Reihum über die Wörter: erst von jedem die erste Aufgabe, dann von
    jedem die zweite.

    So reicht ein Tagesvorrat über viele Wörter statt über ein einziges
    Paradigma — und zwanzig neue Aufgaben sind zwanzig neue Wörter und
    nicht ein halbes Verb.
    """
    nach_wort: dict = {}
    for r in sorted(reihe, key=lambda r: (r["lektion_id"] or 0,
                                          r["lexem_id"], r["typ"])):
        nach_wort.setdefault(r["lexem_id"], []).append(r)
    ergebnis: list[dict] = []
    runde = 0
    while True:
        dazu = [liste[runde] for liste in nach_wort.values()
                if runde < len(liste)]
        if not dazu:
            return ergebnis
        ergebnis += dazu
        runde += 1


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
    """Stellt den nächsten Lernblock zusammen und begründet den Zuschnitt.

    Reihenfolge der Platzvergabe:

      1. **Fälliges** — es hat Vorrang, sonst wächst der Rückstand.
      2. **Wackliges** — ein fester Anteil, VOR dem Neuen reserviert. Sonst
         kommt es nie dran: wer im Rückstand ist, braucht viel Neues, und
         genau dann wären die Lücken am wichtigsten.
      3. **Neues** — so viel, wie der Termin verlangt.
      4. Was dann noch frei ist, wird mit weiterem Wackligem und Neuem
         aufgefüllt.

    Quer darüber liegt die RUNDE: innerhalb jeder dieser Gruppen kommen
    zuerst die Wörter, die heute noch nicht dran waren. Ohne das füllten
    nach zehn Antworten die zehn beantworteten Wörter den ganzen Block,
    und die restlichen kamen nie hinein — die Reihenfolge weiter hinten
    kann nur ordnen, was hier ausgewählt wurde.
    """
    ziel = lesen(db, lernziel_id)
    reihe = aufgaben_im_umfang(db, benutzer_id, ziel["umfang"])
    heute = _heute().isoformat()
    import lernen as lernmodul
    rundenstand = lernmodul._rundenstand(db, benutzer_id)
    stand = fortschritt(db, benutzer_id, lernziel_id, reihe, ziel)

    faellig, nicht_faellig, neu = [], [], []
    for r in reihe:
        if r["zustand"] in (None, "neu"):
            neu.append(r)
        elif r["zustand"] == "ausgesetzt":
            continue
        elif (r["zustand"] == "verlernt"
              # `or ""` machte aus einem fehlenden Termin »fällig«. In
              # SQL ist `faellig <= heute` für NULL unwahr — damit waren
              # Lernzielblock und Abfrage verschiedener Meinung darüber,
              # was heute dran ist.
              or (r["faellig"] and r["faellig"] <= heute)):
            faellig.append(r)
        else:
            nicht_faellig.append(r)

    faellig.sort(key=lambda r: _dringlichkeit(r, heute))
    wacklig = [r for r in sorted(nicht_faellig, key=_wackligkeit, reverse=True)
               if _wackligkeit(r) > 0.5]
    # Von jedem Wort erst die erste Aufgabe, dann von jedem die zweite.
    #
    # Vorher stand hier eine Sortierung nach Lexem — damit kamen alle
    # vierzig Formen eines Verbs an einem Stück, der Tagesvorrat war nach
    # einem halben Verb leer, und das anschließende Verschränken hatte
    # nichts mehr zu mischen, weil alles aus demselben Wort stammte.
    # Ein Verbstamm ist EIN Wort, auch wenn viel daran hängt.
    neu = _wortweise(neu)

    tagesbedarf = stand["neu_taeglich_noetig"]

    genommen: list[tuple[dict, str]] = []
    platz = anzahl

    def nimm(quelle: list[dict], hoechstens: int, herkunft: str) -> None:
        nonlocal platz
        for r in quelle[:max(0, min(hoechstens, platz))]:
            genommen.append((r, herkunft))
            platz -= 1

    # Erst jedes Wort einmal, dann das zweite Mal — in jeder Gruppe.
    faellig = lernmodul._rundenweise(faellig, rundenstand)
    rest_wacklig_quelle = lernmodul._rundenweise(wacklig, rundenstand)
    neu = lernmodul._rundenweise(neu, rundenstand)
    wacklig = rest_wacklig_quelle

    nimm(faellig, platz, "faellig")
    # Der Wacklig-Anteil wird VOR dem Neuen reserviert — sonst bliebe er
    # gerade bei Rückstand immer leer.
    rest_wacklig = wacklig[:]
    nimm(rest_wacklig, int(anzahl * ANTEIL_WACKLIG), "wacklig")
    genommen_wacklig = sum(1 for _r, h in genommen if h == "wacklig")
    rest_wacklig = wacklig[genommen_wacklig:]

    hoechstens_neu = platz if tagesbedarf is None else max(MINDESTENS_NEU,
                                                           tagesbedarf)
    nimm(neu, hoechstens_neu, "neu")
    genommen_neu = sum(1 for _r, h in genommen if h == "neu")

    # Rest auffüllen: erst weiteres Wackliges, dann weiteres Neues.
    nimm(rest_wacklig, platz, "wacklig")
    nimm(neu[genommen_neu:], platz, "neu")

    herkunft_nach_id = {r["aufgabe_id"]: h for r, h in genommen}
    gemischt = verschraenken([r for r, _h in genommen])

    zusammensetzung = {"faellig": 0, "wacklig": 0, "neu": 0}
    for h in herkunft_nach_id.values():
        zusammensetzung[h] += 1

    begruendung = []
    if zusammensetzung["faellig"]:
        begruendung.append(f"{zusammensetzung['faellig']} planmäßig fällig")
    if zusammensetzung["wacklig"]:
        begruendung.append(f"{zusammensetzung['wacklig']} wacklig "
                           f"(oft daneben oder dünn)")
    if zusammensetzung["neu"]:
        begruendung.append(f"{zusammensetzung['neu']} neu"
                           + (" — so viel verlangt der Termin"
                              if tagesbedarf else ""))

    return {
        "lernziel_id": lernziel_id,
        "name": ziel["name"],
        "aufgaben": [{"aufgabe_id": r["aufgabe_id"], "typ": r["typ"],
                      "lexem_id": r["lexem_id"], "lemma": r["lemma"],
                      "zustand": r["zustand"] or "neu",
                      "herkunft": herkunft_nach_id[r["aufgabe_id"]]}
                     for r in gemischt],
        "anzahl": len(gemischt),
        "zusammensetzung": zusammensetzung,
        "begruendung": ("Zusammengestellt aus " + ", ".join(begruendung) + ". "
                        "Verschränkt gemischt: aufeinanderfolgende Aufgaben "
                        "gehören nicht zum selben Wort."
                        if begruendung else "Im Umfang dieses Ziels ist gerade "
                                            "nichts zu tun."),
        "fortschritt": stand,
    }
