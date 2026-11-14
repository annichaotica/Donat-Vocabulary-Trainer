"""Die ganze Reihe auf einmal — ich gehe, du gehst, er/sie/es geht.

So lernt man Konjugationen wirklich: nicht als sechs einzelne Fragen,
sondern als Tabelle. Und sie prüft etwas anderes — ob die Reihe als Ganzes
sitzt, nicht ob eine herausgegriffene Form zufällig da war.
"""

import pytest

P = [("1", "sg"), ("2", "sg"), ("3", "sg"),
     ("1", "pl"), ("2", "pl"), ("3", "pl")]
PRAESENS = ["γράφω", "γράφεις", "γράφει", "γράφουμε", "γράφετε", "γράφουν"]


def _aufbau(klient, formen=None, typen=None):
    b = klient.post("/api/benutzer", json={"name": "Konjugierende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.put(f"/api/sammlungen/{s['id']}/einstellungen", json={
        "typen": typen or ["formenreihe", "bedeutung_fremd_deutsch"]})
    texte = PRAESENS if formen is None else formen
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": "γράφω", "wortart": "verb",
            "bedeutungen": [{"uebersetzungen": ["schreiben", "aufschreiben"]}],
            "formen": [{"text": t, "merkmale": {
                "modus": "indikativ", "tempus": "praesens",
                "person": p, "numerus": n}}
                for t, (p, n) in zip(texte, P[:len(texte)])]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lexem_ids": [1]})
    return b, s


def _reihe(klient, b, s):
    aufgaben = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"],
        "nur": "frei", "anzahl": 20}).json()
    return next((a for a in aufgaben if a["typ"] == "formenreihe"), None)


def pruefen(klient, b, aufgabe, antwort):
    a = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "antwort": antwort})
    assert a.status_code == 200, a.text
    return a.json()


# ------------------------------------------------------------ Entstehen

def test_eine_aufgabe_je_tabelle_nicht_je_form(klient):
    b, s = _aufbau(klient)
    aufgaben = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"],
        "nur": "frei", "anzahl": 20}).json()
    reihen = [a for a in aufgaben if a["typ"] == "formenreihe"]
    assert len(reihen) == 1, "sechs Formen, aber nur EINE Reihe"
    assert reihen[0]["frage_text"] == "γράφω"
    assert "Ενεστώτας" in reihen[0]["frage_zusatz"]
    assert [z["beschriftung"] for z in reihen[0]["zellen"]] == [
        "1. Person Singular", "2. Person Singular", "3. Person Singular",
        "1. Person Plural", "2. Person Plural", "3. Person Plural"]


def test_die_frage_verraet_die_loesung_nicht(klient):
    b, s = _aufbau(klient)
    reihe = _reihe(klient, b, s)
    assert "erwartet" not in str(reihe)
    for form in PRAESENS:
        assert form not in str(reihe["zellen"]), form


def test_jede_zelle_bringt_ihr_beispiel_mit(klient):
    """»2. Person Singular« ist für viele eine Mauer. »du gehst« nicht."""
    b, s = _aufbau(klient)
    reihe = _reihe(klient, b, s)
    assert [z["beispiel"] for z in reihe["zellen"]] == [
        "ich gehe", "du gehst", "er/sie/es geht",
        "wir gehen", "ihr geht", "sie gehen"]


def test_eine_halbe_tabelle_wird_nicht_abgefragt(klient):
    """Man tippte sonst in Felder, zu denen es gar keine Antwort gibt."""
    b, s = _aufbau(klient, formen=PRAESENS[:3])
    assert _reihe(klient, b, s) is None


def test_erklaerte_luecken_verhindern_die_reihe_nicht(klient):
    """πρέπει gibt es nur in der 3. Person — das ist die ganze Tabelle."""
    b = klient.post("/api/benutzer", json={"name": "Lückige"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.put(f"/api/sammlungen/{s['id']}/einstellungen",
               json={"typen": ["formenreihe"]})
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": "πρέπει", "wortart": "verb",
            "luecken": [{"person": "1"}, {"person": "2"},
                        {"person": "3", "numerus": "pl"}],
            "bedeutungen": [{"uebersetzungen": ["müssen", "sollen"]}],
            "formen": [{"text": "πρέπει", "merkmale": {
                "modus": "indikativ", "tempus": "praesens",
                "person": "3", "numerus": "sg"}}]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lexem_ids": [1]})
    reihe = _reihe(klient, b, s)
    assert reihe is not None
    assert len(reihe["zellen"]) == 1


# ------------------------------------------------------------- Bewerten

def _alle(reihe, texte):
    return {z["zelle"]: t for z, t in zip(reihe["zellen"], texte)}


def test_die_ganze_reihe_richtig(klient):
    b, s = _aufbau(klient)
    reihe = _reihe(klient, b, s)
    ergebnis = pruefen(klient, b, reihe, _alle(reihe, PRAESENS))
    assert ergebnis["urteil"]["urteil"] == "richtig"
    a = ergebnis["aufloesung"]
    assert a["richtig"] == 6 and a["gesamt"] == 6
    assert all(z["urteil"] == "richtig" for z in a["zellen"])


def test_eine_falsche_form_laesst_die_reihe_durchfallen(klient):
    """Wer fünf von sechs kann, kann die Tabelle noch nicht.

    Die Nachbarform ist dabei der härteste Fall: γράφετε IST ein Wort,
    nur eben das der 2. Person — in der Zeile der 1. Person Plural ist es
    schlicht falsch.
    """
    b, s = _aufbau(klient)
    reihe = _reihe(klient, b, s)
    falsch = list(PRAESENS)
    falsch[3] = "γράφετε"
    ergebnis = pruefen(klient, b, reihe, _alle(reihe, falsch))
    assert ergebnis["urteil"]["urteil"] == "falsch"
    a = ergebnis["aufloesung"]
    assert a["richtig"] == 5
    assert ergebnis["urteil"]["hinweis"] == "5 von 6 Formen sitzen, 1 noch nicht."
    # Und es steht da, WELCHE Zeile es war.
    daneben = [z for z in a["zellen"] if z["urteil"] != "richtig"]
    assert len(daneben) == 1
    assert daneben[0]["beschriftung"] == "1. Person Plural"
    assert daneben[0]["erwartet"] == ["γράφουμε"]


def test_nur_akzente_daneben_ist_fast(klient):
    b, s = _aufbau(klient)
    reihe = _reihe(klient, b, s)
    ohne = ["γραφω", "γραφεις", "γραφει", "γραφουμε", "γραφετε", "γραφουν"]
    ergebnis = pruefen(klient, b, reihe, _alle(reihe, ohne))
    assert ergebnis["urteil"]["urteil"] == "fast"


def test_leere_felder_zaehlen_als_nicht_gewusst(klient):
    b, s = _aufbau(klient)
    reihe = _reihe(klient, b, s)
    halb = _alle(reihe, PRAESENS[:3] + ["", "", ""])
    ergebnis = pruefen(klient, b, reihe, halb)
    assert ergebnis["urteil"]["urteil"] == "falsch"
    assert ergebnis["aufloesung"]["richtig"] == 3


def test_die_reihe_ist_abwaehlbar(klient):
    """Sie ist ein eigener Aufgabentyp, kein Zwang."""
    b, s = _aufbau(klient, typen=["bedeutung_fremd_deutsch", "form_bilden"])
    assert _reihe(klient, b, s) is None


# ------------------------------------------------- Beispiele anderswo

def test_formaufgaben_bringen_ein_beispiel_mit(klient):
    """»Akkusativ Singular« ist für Nicht-Lateiner eine Mauer."""
    b = klient.post("/api/benutzer", json={"name": "Fragende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": "το καρότο", "wortart": "substantiv",
            "merkmale": {"genus": "n"},
            "bedeutungen": [{"uebersetzungen": ["die Karotte", "die Möhre"]}],
            "formen": [{"text": "καρότο", "merkmale": {
                "kasus": "akk", "numerus": "sg"}}]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lexem_ids": [1]})
    aufgaben = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"],
        "nur": "frei", "anzahl": 20}).json()
    form = next(a for a in aufgaben if a["typ"] == "form_bilden")
    assert form["frage_zusatz"] == "Akkusativ Singular"
    assert form["frage_hilfe"] == "ich sehe den Hund"


def test_jeder_aufgabentyp_erklaert_sich_mit_beispiel(klient):
    """In der Auswahl, was abgefragt werden soll, muss man verstehen, was
    man da anhakt."""
    typen = klient.get("/api/aufgabentypen").json()["typen"]
    for kennung, t in typen.items():
        assert t.get("beschreibung"), kennung
        assert t.get("beispiel"), kennung


def test_ein_tippfehler_laesst_die_reihe_nicht_durchfallen(klient):
    """Ein fehlendes υ in γράφουμε ist ein Tippfehler, kein Nichtwissen.
    Dieselbe Regel wie bei der einzelnen Vokabel."""
    b, s = _aufbau(klient)
    reihe = _reihe(klient, b, s)
    fast = list(PRAESENS)
    fast[3] = "γράφομε"
    ergebnis = pruefen(klient, b, reihe, _alle(reihe, fast))
    assert ergebnis["urteil"]["urteil"] == "fast"
    assert ergebnis["aufloesung"]["richtig"] == 5


# ------------------------------------------------- Personalpronomen

def test_die_reihe_zeigt_wer_gemeint_ist(klient):
    """»2. Person Singular« sagt es über einen Umweg, »εσύ« sagt es direkt."""
    b, s = _aufbau(klient)
    reihe = _reihe(klient, b, s)
    assert [z["pronomen"] for z in reihe["zellen"]] == [
        ["εγώ"], ["εσύ"], ["αυτός", "αυτή", "αυτό"],
        ["εμείς"], ["εσείς"], ["αυτοί", "αυτές", "αυτά"]]


def test_mitgeschriebenes_pronomen_ist_kein_fehler(klient):
    """Im Griechischen ist es freiwillig — wer es dazuschreibt, hat nichts
    falsch gemacht."""
    b, s = _aufbau(klient)
    reihe = _reihe(klient, b, s)
    mit = ["εγώ γράφω", "εσύ γράφεις", "αυτός γράφει",
           "εμείς γράφουμε", "εσείς γράφετε", "αυτοί γράφουν"]
    ergebnis = pruefen(klient, b, reihe, _alle(reihe, mit))
    assert ergebnis["urteil"]["urteil"] == "richtig"


def test_auch_bei_der_einzelnen_form(klient):
    b = klient.post("/api/benutzer", json={"name": "Pronominale"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": "γράφω", "wortart": "verb",
            "bedeutungen": [{"uebersetzungen": ["schreiben", "reden"]}],
            "formen": [{"text": "γράφεις", "merkmale": {
                "modus": "indikativ", "tempus": "praesens",
                "person": "2", "numerus": "sg"}}]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lexem_ids": [1]})
    aufgaben = klient.get("/api/lernen/naechste", params={
        "benutzer_id": b["id"], "sammlung_id": s["id"],
        "nur": "frei", "anzahl": 20}).json()
    form = next(a for a in aufgaben if a["typ"] == "form_bilden")
    assert form["pronomen"] == ["εσύ"]
    assert form["pronomen_pflicht"] is False
    antwort = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": form["aufgabe_id"],
        "antwort": "εσύ γράφεις"}).json()
    assert antwort["urteil"]["urteil"] == "richtig"


def test_beim_imperativ_steht_kein_pronomen(klient):
    """»du geh!« sagt niemand."""
    import sys
    sys.path.insert(0, "backend")
    import sprachen
    assert sprachen.personalpronomen("el", {
        "modus": "imperativ", "person": "2", "numerus": "sg"}) == []
    assert sprachen.personalpronomen("de", {
        "person": "1", "numerus": "pl"}) == ["wir"]
