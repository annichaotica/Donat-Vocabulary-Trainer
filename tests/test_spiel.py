"""Tagesziel und Strähne — eine Zahl, die nicht zu erschleichen ist.

»Wir brauchen auf jeden Fall einen Streak.«

Es gab schon einen: er zählte Tage mit MINDESTENS EINER Antwort,
innerhalb eines Fensters von dreißig Tagen. Beides war falsch, und
diese Datei hält beides fest:

  Eine einzige Karte genügte für einen gelernten Tag. Eine Strähne,
  die man mit einem Klick hält, belohnt das Öffnen der App und nicht
  das Lernen.

  Über dreißig kam die Zahl nie hinaus — nach zwei Monaten Disziplin
  stand da dasselbe wie nach einem.

Und die Gegenprobe zur neuen Milde: zwei Fehltage im Monat trägt der
Joker, der dritte reißt. Ohne diese Grenze wäre die Zahl geschenkt.
"""

import datetime as dt

import pytest


@pytest.fixture()
def bestand(klient):
    """Eine Person mit Tagesdosis 20 und genug Wörtern für viele Runden."""
    b = klient.post("/api/benutzer", json={"name": "Lernender 1"}).json()
    klient.patch(f"/api/benutzer/{b['id']}", json={"fragen_je_tag": 20})
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Französisch", "sprache": "fr"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": f"mot{i}", "wortart": "substantiv",
                       "bedeutungen": [{"uebersetzungen": [f"Wort {i}"]}]}
                      for i in range(60)]})
    return b, s


def _irgendeine_aufgabe(db, benutzer_id: int) -> int:
    z = db.execute("SELECT id FROM aufgabe ORDER BY id LIMIT 1").fetchone()
    return z["id"]


def _antworten(db, benutzer_id: int, tag: dt.date, anzahl: int) -> None:
    """Antworten an einem bestimmten Tag ins Protokoll schreiben.

    Unmittelbar in die Tabelle und nicht über die Abfrage: geprüft wird
    die REGEL, nach der aus Tagen eine Strähne wird, und die hängt nur
    an Datum und Anzahl. Über die Abfrage bräuchte jeder der vierzig
    Tage eine vorgestellte Uhr und vierzig echte Runden — der Test
    liefe Minuten und prüfte am Ende FSRS mit.
    """
    aufgabe_id = _irgendeine_aufgabe(db, benutzer_id)
    for i in range(anzahl):
        db.execute("""INSERT INTO wiederholung
                        (aufgabe_id, benutzer_id, zeitpunkt, bewertung, urteil)
                      VALUES (?, ?, ?, 3, 'richtig')""",
                   (aufgabe_id, benutzer_id,
                    dt.datetime.combine(tag, dt.time(18, 0 + i % 50))
                      .isoformat(timespec="seconds")))


@pytest.fixture()
def db_des_klienten(klient):
    import datenbank as dbm
    v = dbm.verbindung()
    yield v
    v.close()


def _folge(klient, b):
    return klient.get(f"/api/spiel/{b['id']}").json()["straehne"]


# ----------------------------------------------------- die Latte selbst

def test_eine_einzige_antwort_ist_kein_gelernter_tag(klient, bestand,
                                                     db_des_klienten):
    """Die Gegenprobe zum alten Zähler.

    Dosis 20, eine Antwort. Früher stand hier eine Strähne von 1 — und
    damit war die Zahl mit einem Klick zu halten.
    """
    b, _ = bestand
    heute = dt.date.today()
    _antworten(db_des_klienten, b["id"], heute - dt.timedelta(days=1), 1)
    _antworten(db_des_klienten, b["id"], heute, 1)

    folge = _folge(klient, b)
    assert folge["laufend"] == 0, \
        f"eine Karte darf keine Strähne machen: {folge}"
    assert folge["ziel"] == 20


def test_die_tagesdosis_macht_den_tag(klient, bestand, db_des_klienten):
    b, _ = bestand
    heute = dt.date.today()
    for zurueck in range(3):
        _antworten(db_des_klienten, b["id"],
                   heute - dt.timedelta(days=zurueck), 20)

    folge = _folge(klient, b)
    assert folge["laufend"] == 3, folge
    assert folge["heute_geschafft"] is True


def test_die_straehne_ist_nicht_auf_dreissig_tage_begrenzt(
        klient, bestand, db_des_klienten):
    """Die zweite Gegenprobe: das alte Fenster endete bei dreißig."""
    b, _ = bestand
    heute = dt.date.today()
    for zurueck in range(45):
        _antworten(db_des_klienten, b["id"],
                   heute - dt.timedelta(days=zurueck), 20)

    folge = _folge(klient, b)
    assert folge["laufend"] == 45, f"das Fenster steckt noch drin: {folge}"


def test_die_obergrenze_ist_nicht_die_latte(klient, db_des_klienten):
    """Der Fehler, den erst die echten Daten gezeigt haben.

    Die Strähne hing zuerst an der Tagesdosis — sie stand ja schon da,
    und eine zweite Zahl wollte ich vermeiden. Dann die Messung am
    laufenden Bestand: Strähne 0, obwohl an vier Tagen hintereinander
    zwischen 29 und 123 Fragen beantwortet worden waren.

    Die Dosis ist eine OBERGRENZE und wird absichtlich hoch gesetzt;
    der Lernzielhelfer setzt sie noch höher, damit genug Neues
    durchkommt (bei Lernende 2 auf 224). Als Latte ist sie unerreichbar,
    und eine Latte, die niemand erreicht, ist keine.

    Hier also beides zugleich: eine hohe Grenze und ein erreichbares
    Ziel.
    """
    b = klient.post("/api/benutzer", json={"name": "Lernender 3"}).json()
    klient.patch(f"/api/benutzer/{b['id']}",
                 json={"fragen_je_tag": 224, "tagesziel": 20})
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Französisch", "sprache": "fr"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": f"mot{i}", "wortart": "substantiv",
                       "bedeutungen": [{"uebersetzungen": [f"Wort {i}"]}]}
                      for i in range(60)]})

    heute = dt.date.today()
    for zurueck, anzahl in enumerate([39, 29, 123, 32]):
        _antworten(db_des_klienten, b["id"],
                   heute - dt.timedelta(days=zurueck), anzahl)

    folge = _folge(klient, b)
    assert folge["ziel"] == 20, "die Grenze darf die Latte nicht sein"
    assert folge["laufend"] == 4, f"vier gelernte Tage am Stück: {folge}"


def test_die_latte_kann_die_grenze_nicht_ueberschreiten(klient):
    """Mehr als serviert wird, kann niemand beantworten.

    Wer seine Grenze auf zehn stellt, hat damit auch sein Ziel auf zehn
    gestellt — sonst stünde eine Latte da, die der Trainer selbst
    verhindert.
    """
    b = klient.post("/api/benutzer", json={"name": "Lernender 4"}).json()
    klient.patch(f"/api/benutzer/{b['id']}",
                 json={"fragen_je_tag": 10, "tagesziel": 20})
    e = klient.get(f"/api/benutzer/{b['id']}/einstellungen").json()
    assert e["tagesziel"] == 10, e


# --------------------------------------------------------------- Milde

def test_heute_reisst_die_straehne_nie(klient, bestand, db_des_klienten):
    """Morgens um acht hat noch niemand sein Pensum gemacht.

    Stünde die Strähne dann auf null, wäre sie eine Drohung und kein
    Anreiz — und sie stünde den halben Tag falsch da.
    """
    b, _ = bestand
    heute = dt.date.today()
    for zurueck in (1, 2, 3):
        _antworten(db_des_klienten, b["id"],
                   heute - dt.timedelta(days=zurueck), 20)

    folge = _folge(klient, b)
    assert folge["laufend"] == 3, f"heute ist noch nicht vorbei: {folge}"
    assert folge["heute_geschafft"] is False


def test_der_joker_traegt_zwei_fehltage(klient, bestand, db_des_klienten):
    b, _ = bestand
    heute = dt.date.today()
    # Heute und gestern gelernt, davor zwei Tage Pause, davor vier Tage.
    for zurueck in (0, 1, 4, 5, 6, 7):
        _antworten(db_des_klienten, b["id"],
                   heute - dt.timedelta(days=zurueck), 20)

    folge = _folge(klient, b)
    assert folge["laufend"] == 6, f"der Joker trägt nicht: {folge}"
    assert len(folge["joker_benutzt"]) == 2
    # Die Joker sollen GENANNT werden: die Anzeige darf nicht behaupten,
    # an diesen Tagen wäre gelernt worden.
    assert (heute - dt.timedelta(days=2)).isoformat() in folge["joker_benutzt"]


def test_der_dritte_fehltag_reisst(klient, bestand, db_des_klienten):
    """Die Gegenprobe zur Milde — sonst wäre die Zahl geschenkt."""
    b, _ = bestand
    heute = dt.date.today()
    for zurueck in (0, 4, 5, 6):
        _antworten(db_des_klienten, b["id"],
                   heute - dt.timedelta(days=zurueck), 20)

    folge = _folge(klient, b)
    assert folge["laufend"] == 1, f"drei Fehltage müssen reißen: {folge}"
    assert folge["laengste"] == 3, \
        f"die längste Strähne muss stehen bleiben: {folge}"


def test_ein_kurzer_tag_zaehlt_wenn_nichts_mehr_faellig_war(klient):
    """Der Tag, an dem die App selbst nichts mehr hergibt.

    Vier Aufgaben, Dosis zwanzig. Wer alle vier beantwortet hat, hat
    seinen Tag gemacht — sonst erzieht die Strähne dazu, gegen den
    eigenen Terminplan zu arbeiten, nur damit eine Zahl stehen bleibt.
    """
    b = klient.post("/api/benutzer", json={"name": "Lernender 2"}).json()
    klient.patch(f"/api/benutzer/{b['id']}", json={"fragen_je_tag": 20})
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Klein", "sprache": "fr"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "un", "wortart": "numerale",
                       "bedeutungen": [{"uebersetzungen": ["eins"]}]},
                      {"lemma": "deux", "wortart": "numerale",
                       "bedeutungen": [{"uebersetzungen": ["zwei"]}]}]})

    while True:
        reihe = klient.get("/api/lernen/naechste", params={
            "benutzer_id": b["id"], "anzahl": 1}).json()
        if not reihe:
            break
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": reihe[0]["aufgabe_id"],
            "bewertung": 4})          # »leicht« — kommt heute nicht wieder

    spiel = klient.get(f"/api/spiel/{b['id']}").json()
    assert spiel["tagesziel"]["erledigt"] < spiel["tagesziel"]["ziel"]
    assert spiel["tagesziel"]["offen"] == 0
    assert spiel["tagesziel"]["geschafft"] is True, spiel
    assert spiel["tagesziel"]["nichts_mehr_faellig"] is True
    assert spiel["straehne"]["laufend"] == 1, spiel


# ------------------------------------------------- nur eine einzige Zahl

def test_kopfzeile_und_fortschritt_nennen_dieselbe_straehne(
        klient, bestand, db_des_klienten):
    """Zwei verschiedene Zahlen für dasselbe wären der schlimmere Fehler.

    Die Statistik hatte ihre eigene Rechnung. Stünde in der Kopfzeile
    »Strähne 3« und im Fortschritt »Strähne 31«, wüsste man bei keiner
    mehr, was sie bedeutet.
    """
    b, s = bestand
    heute = dt.date.today()
    for zurueck in range(35):
        _antworten(db_des_klienten, b["id"],
                   heute - dt.timedelta(days=zurueck), 20)

    kopf = klient.get(f"/api/spiel/{b['id']}").json()["straehne"]["laufend"]
    seite = klient.get("/api/statistik", params={
        "benutzer_id": b["id"]}).json()["gesamt"]["straehne"]
    # Und auch dann dieselbe, wenn der Fortschritt auf eine Sammlung
    # eingeschränkt ist: die Strähne gilt für die Person, wie die Dosis.
    eine = klient.get("/api/statistik", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"]}).json()["gesamt"]["straehne"]

    assert kopf == seite == eine == 35, (kopf, seite, eine)


def test_ohne_protokoll_steht_alles_auf_null(klient, bestand):
    b, _ = bestand
    spiel = klient.get(f"/api/spiel/{b['id']}").json()
    assert spiel["straehne"] == {
        "laufend": 0, "laengste": 0, "ziel": 20,
        "joker_frei": 2, "joker_benutzt": [], "heute_geschafft": False}
    assert spiel["tagesziel"]["erledigt"] == 0
    assert spiel["tagesziel"]["geschafft"] is False
