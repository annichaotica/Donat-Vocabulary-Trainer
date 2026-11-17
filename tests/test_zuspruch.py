"""Punkte, Stufen und Zuspruch.

»Wir brauchen auf jeden Fall einen Streak, XP, Leistungslevels und
Motivationsbringer. Auch möchte ich meiner Tochter Boosts schicken
können.«

Zwei Dinge hält diese Datei fest, und beide sind Entscheidungen, die
man später versehentlich rückgängig machen könnte:

  **Punkte sind nicht zu schinden.** Dieselbe Karte fünfzigmal
  durchzuklicken bringt genau einmal Punkte — »eine Aufgabe, an einem
  Tag«. Und es gibt sie unabhängig davon, ob die Antwort stimmte, weil
  sonst genau dort ein Anreiz entstünde, sich großzügig zu bewerten.

  **Ein Zuspruch ändert das Protokoll nicht.** Verdoppler und Joker
  wirken beim AUSWERTEN. Es darf nie eine zweite Wahrheit über einen
  Tag geben.
"""

import datetime as dt

import pytest


@pytest.fixture()
def zwei(klient):
    """Mutter und Tochter, mit einer geteilten Sammlung."""
    mutter = klient.post("/api/benutzer", json={"name": "Lernende 1"}).json()
    kind = klient.post("/api/benutzer", json={"name": "Lernende 2"}).json()
    for p in (mutter, kind):
        klient.patch(f"/api/benutzer/{p['id']}",
                     json={"fragen_je_tag": 200, "tagesziel": 20})
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": kind["id"], "name": "Französisch", "sprache": "fr"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": f"mot{i}", "wortart": "substantiv",
                       "bedeutungen": [{"uebersetzungen": [f"Wort {i}"]}]}
                      for i in range(40)]})
    # Die Mutter darf mitpflegen — darüber läuft auch der Zuspruch.
    klient.put(f"/api/sammlungen/{s['id']}/zugriff", json={
        "benutzer_id": mutter["id"], "recht": "schreiben"})
    return mutter, kind, s


@pytest.fixture()
def db_des_klienten(klient):
    import datenbank as dbm
    v = dbm.verbindung()
    yield v
    v.close()


def _antwort(db, aufgabe_id, benutzer_id, tag, bewertung=3,
             intervall=1.0, erste=False):
    db.execute("""INSERT INTO wiederholung
                    (aufgabe_id, benutzer_id, zeitpunkt, bewertung, urteil,
                     stabilitaet_vor, intervall_tage)
                  VALUES (?, ?, ?, ?, 'richtig', ?, ?)""",
               (aufgabe_id, benutzer_id,
                dt.datetime.combine(tag, dt.time(18, 0)).isoformat(
                    timespec="seconds"),
                bewertung, None if erste else 2.0, intervall))


def _aufgaben(db, anzahl):
    return [z["id"] for z in db.execute(
        "SELECT id FROM aufgabe ORDER BY id LIMIT ?", (anzahl,))]


def _spiel(klient, p):
    return klient.get(f"/api/spiel/{p['id']}").json()


# ------------------------------------------------------------- Punkte

def test_dieselbe_karte_bringt_nur_einmal_punkte(klient, zwei,
                                                 db_des_klienten):
    """Die Regel, die das Schinden von Punkten verhindert.

    Nicht als zusätzlicher Tagesdeckel gebaut, sondern als Form der
    Vergabe selbst: eine Aufgabe, an einem Tag. Ein Deckel wäre eine
    zweite Regel für dieselbe Sache, und zwei Regeln widersprechen sich
    irgendwann.
    """
    _, kind, _ = zwei
    # Das Tagesziel aus dem Weg räumen: es zählt ANTWORTEN, so wie die
    # Fortschrittsleiste in der Abfrage auch, und fiele hier sonst mit
    # seinen 50 Punkten in die Rechnung. Geprüft wird die Vergabe je
    # Aufgabe, nicht das Zusammenspiel.
    klient.patch(f"/api/benutzer/{kind['id']}", json={"tagesziel": 100})
    db = db_des_klienten
    heute = dt.date.today()
    eine = _aufgaben(db, 1)[0]
    for _ in range(50):
        _antwort(db, eine, kind["id"], heute)

    p = _spiel(klient, kind)["punkte"]
    # 10 für die eine Aufgabe an diesem Tag. Nichts Neues
    # (stabilitaet_vor ist gesetzt), nichts gereift.
    assert p["gesamt"] == 10, p


def test_punkte_gibt_es_auch_fuer_falsche_antworten(klient, zwei,
                                                    db_des_klienten):
    """Belohnt wird Erscheinen, nicht Trefferquote.

    Die Gegenprobe zu einem naheliegenden Entwurf: Punkte für
    »richtig«. Daran hinge ein Anreiz, sich großzügig zu bewerten — und
    der Schaden wäre nicht der erschlichene Punkt, sondern ein
    verdorbener Terminplan.
    """
    _, kind, _ = zwei
    db = db_des_klienten
    heute = dt.date.today()
    for a in _aufgaben(db, 3):
        db.execute("""INSERT INTO wiederholung
                        (aufgabe_id, benutzer_id, zeitpunkt, bewertung,
                         urteil, stabilitaet_vor, intervall_tage)
                      VALUES (?, ?, ?, 1, 'falsch', 2.0, 0.0)""",
                   (a, kind["id"],
                    dt.datetime.combine(heute, dt.time(9)).isoformat(
                        timespec="seconds")))

    assert _spiel(klient, kind)["punkte"]["gesamt"] == 30


def test_dauerhaft_gesessen_bringt_den_grossen_posten(klient, zwei,
                                                      db_des_klienten):
    """Der einzige Posten, den man nicht an einem Nachmittag holt.

    Dorthin führt nur ein Intervall über der Reifegrenze, und das
    entsteht erst nach Wochen. Gezählt wird der SPRUNG: wer schon
    dauerhaft saß und wieder richtig antwortet, bekommt ihn nicht noch
    einmal.
    """
    import fsrs
    _, kind, _ = zwei
    db = db_des_klienten
    heute = dt.date.today()
    eine = _aufgaben(db, 1)[0]
    _antwort(db, eine, kind["id"], heute - dt.timedelta(days=2),
             intervall=fsrs.REIF_AB_TAGEN + 5)      # Sprung
    _antwort(db, eine, kind["id"], heute - dt.timedelta(days=1),
             intervall=fsrs.REIF_AB_TAGEN + 9)      # bleibt reif
    _antwort(db, eine, kind["id"], heute,
             intervall=fsrs.REIF_AB_TAGEN + 12)     # bleibt reif

    p = _spiel(klient, kind)["punkte"]
    assert p["gesamt"] == 3 * 10 + 25, f"genau EIN Sprung: {p}"


def test_die_stufe_steigt_und_faellt_nie(klient, zwei, db_des_klienten):
    """Eine Stufe, die fällt, weil man krank war, ist eine Strafe mit
    Konfetti. Darum hängt sie an der Summe und nicht am Zustand."""
    import spiel
    assert spiel.stufe(0)["name"] == "Buchstaben"
    assert spiel.stufe(0)["nummer"] == 1
    assert spiel.stufe(249)["name"] == "Buchstaben"
    assert spiel.stufe(250)["name"] == "Wörter"
    assert spiel.stufe(10**9)["name"] == spiel.STUFEN[-1][1]
    # Oben offen: kein Balken, der nie voll wird.
    assert spiel.stufe(10**9)["naechste"] is None
    assert spiel.stufe(10**9)["anteil"] is None
    assert 0 < spiel.stufe(500)["anteil"] < 1


# ------------------------------------------------------------ Zuspruch

def test_zuspruch_nur_an_wen_man_etwas_teilt(klient, zwei):
    """Wer keine Sammlung mit jemandem teilt, hat in dessen Trainer
    nichts zu melden."""
    mutter, kind, _ = zwei
    fremd = klient.post("/api/benutzer", json={"name": "Lernender 3"}).json()

    wem = klient.get(f"/api/zuspruch/{kind['id']}").json()["empfaenger"]
    assert [e["id"] for e in wem] == [mutter["id"]], wem

    a = klient.post("/api/zuspruch", json={
        "von_id": kind["id"], "an_id": fremd["id"], "art": "botschaft",
        "text": "hallo"})
    assert a.status_code == 403, a.text


def test_eine_botschaft_kommt_an_und_ist_mit_dem_lesen_erledigt(klient, zwei):
    mutter, kind, _ = zwei
    z = klient.post("/api/zuspruch", json={
        "von_id": mutter["id"], "an_id": kind["id"], "art": "botschaft",
        "text": "Heute nur 15 Wörter, dann ist Feierabend."}).json()

    meins = klient.get(f"/api/zuspruch/{kind['id']}").json()["fuer_mich"]
    assert [x["id"] for x in meins] == [z["id"]]
    assert meins[0]["von_name"] == "Lernende 1"

    klient.post(f"/api/zuspruch/{z['id']}/gesehen",
                params={"benutzer_id": kind["id"]})
    # Eine Botschaft will gelesen werden, nicht abgearbeitet.
    assert klient.get(f"/api/zuspruch/{kind['id']}").json()["fuer_mich"] == []


def test_der_verdoppler_wirkt_am_eingeloesten_tag(klient, zwei,
                                                  db_des_klienten):
    """Und er ändert dabei NICHTS am Protokoll.

    Er sagt nur, dass ein bestimmter Tag doppelt gezählt wird. Sonst
    gäbe es zwei Wahrheiten über denselben Tag.
    """
    mutter, kind, _ = zwei
    db = db_des_klienten
    heute = dt.date.today()
    for a in _aufgaben(db, 4):
        _antwort(db, a, kind["id"], heute)
    vorher = _spiel(klient, kind)["punkte"]["gesamt"]
    zeilen_vorher = db.execute("SELECT COUNT(*) FROM wiederholung").fetchone()[0]

    z = klient.post("/api/zuspruch", json={
        "von_id": mutter["id"], "an_id": kind["id"], "art": "verdoppler"}).json()
    assert _spiel(klient, kind)["punkte"]["gesamt"] == vorher, \
        "vor dem Einlösen darf er nichts tun"

    klient.post(f"/api/zuspruch/{z['id']}/einloesen",
                params={"benutzer_id": kind["id"]})
    nachher = _spiel(klient, kind)
    assert nachher["punkte"]["gesamt"] == 2 * vorher, nachher["punkte"]
    assert nachher["punkte"]["heute_verdoppelt"] is True
    assert db.execute("SELECT COUNT(*) FROM wiederholung").fetchone()[0] \
        == zeilen_vorher, "das Protokoll bleibt unberührt"


def test_ein_geschenkter_joker_traegt_einen_fehltag_mehr(klient, zwei,
                                                         db_des_klienten):
    """Drei Fehltage reißen sonst — mit dem Geschenk nicht."""
    mutter, kind, _ = zwei
    db = db_des_klienten
    heute = dt.date.today()
    aufgaben = _aufgaben(db, 20)
    for zurueck in (0, 4, 5, 6):
        for a in aufgaben:
            _antwort(db, a, kind["id"], heute - dt.timedelta(days=zurueck))

    assert _spiel(klient, kind)["straehne"]["laufend"] == 1, "drei Fehltage"

    klient.post("/api/zuspruch", json={
        "von_id": mutter["id"], "an_id": kind["id"], "art": "joker"})
    folge = _spiel(klient, kind)["straehne"]
    assert folge["laufend"] == 4, folge
    assert folge["joker_geschenkt"] == 1


def test_ein_versprechen_hakt_nur_ab_wer_es_gegeben_hat(klient, zwei):
    """Wer sich selbst bescheinigen könnte, das Kino sei abgegolten,
    bräuchte kein Versprechen."""
    mutter, kind, _ = zwei
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": kind["id"], "name": "Vokabeltest",
        "umfang": {}, "termin": "2026-12-01"}).json()
    z = klient.post("/api/zuspruch", json={
        "von_id": mutter["id"], "an_id": kind["id"], "art": "versprechen",
        "belohnung": "Kino", "lernziel_id": ziel["id"]}).json()
    assert z["ziel_text"] == "Vokabeltest"
    assert z["gueltig_bis"] == "2026-12-01"

    selbst = klient.post(f"/api/zuspruch/{z['id']}/erledigt",
                         params={"benutzer_id": kind["id"]})
    assert selbst.status_code == 403, selbst.text
    gegeben = klient.post(f"/api/zuspruch/{z['id']}/erledigt",
                          params={"benutzer_id": mutter["id"]})
    assert gegeben.status_code == 200, gegeben.text


def test_ein_geloeschtes_lernziel_nimmt_das_versprechen_nicht_mit(klient, zwei):
    """Ein Versprechen, das plötzlich »zu nichts« gehört, wäre
    schlimmer als eines, dessen Ziel es nicht mehr gibt."""
    mutter, kind, _ = zwei
    ziel = klient.post("/api/lernziele", json={
        "benutzer_id": kind["id"], "name": "Vokabeltest", "umfang": {}}).json()
    klient.post("/api/zuspruch", json={
        "von_id": mutter["id"], "an_id": kind["id"], "art": "versprechen",
        "belohnung": "Kino", "lernziel_id": ziel["id"]})

    klient.delete(f"/api/lernziele/{ziel['id']}",
                  params={"benutzer_id": kind["id"]})

    meins = klient.get(f"/api/zuspruch/{kind['id']}").json()["fuer_mich"]
    assert len(meins) == 1, meins
    assert meins[0]["belohnung"] == "Kino"
    assert meins[0]["ziel_text"] == "Vokabeltest", "der Name muss bleiben"
    assert meins[0]["lernziel_id"] is None


def test_gelesenes_laesst_sich_nicht_zurueckziehen(klient, zwei):
    mutter, kind, _ = zwei
    z = klient.post("/api/zuspruch", json={
        "von_id": mutter["id"], "an_id": kind["id"], "art": "botschaft",
        "text": "Du schaffst das."}).json()
    weg = klient.delete(f"/api/zuspruch/{z['id']}",
                        params={"benutzer_id": mutter["id"]})
    assert weg.status_code == 204

    z2 = klient.post("/api/zuspruch", json={
        "von_id": mutter["id"], "an_id": kind["id"], "art": "botschaft",
        "text": "Doch."}).json()
    klient.post(f"/api/zuspruch/{z2['id']}/gesehen",
                params={"benutzer_id": kind["id"]})
    spaet = klient.delete(f"/api/zuspruch/{z2['id']}",
                          params={"benutzer_id": mutter["id"]})
    assert spaet.status_code == 403, spaet.text


def test_aus_zuspruch_wird_kein_rauschen(klient, zwei):
    """Höchstens ein paar am Tag — einer wirkt, wenn er selten ist."""
    mutter, kind, _ = zwei
    for i in range(5):
        a = klient.post("/api/zuspruch", json={
            "von_id": mutter["id"], "an_id": kind["id"], "art": "botschaft",
            "text": f"Nummer {i}"})
        assert a.status_code == 200, a.text
    zuviel = klient.post("/api/zuspruch", json={
        "von_id": mutter["id"], "an_id": kind["id"], "art": "botschaft",
        "text": "und noch einer"})
    assert zuviel.status_code == 403, zuviel.text


def test_abgelaufener_zuspruch_verschwindet(klient, zwei):
    mutter, kind, _ = zwei
    klient.post("/api/zuspruch", json={
        "von_id": mutter["id"], "an_id": kind["id"], "art": "botschaft",
        "text": "Viel Erfolg heute!"})
    assert klient.get(f"/api/zuspruch/{kind['id']}").json()["fuer_mich"]

    import lernen
    import zuspruch
    spaeter = dt.date.today() + dt.timedelta(days=30)
    alt_h, alt_z = lernen.heute, zuspruch._heute
    lernen.heute = lambda: spaeter
    try:
        leer = klient.get(f"/api/zuspruch/{kind['id']}").json()
        assert leer["fuer_mich"] == [], leer
        # Verschwunden heißt nicht gelöscht — wer zurückblickt, sieht ihn.
        assert klient.get(f"/api/zuspruch/{kind['id']}",
                          params={"alle": True}).json()["fuer_mich"]
    finally:
        lernen.heute, zuspruch._heute = alt_h, alt_z
