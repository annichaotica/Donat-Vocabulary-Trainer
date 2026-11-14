"""Passiv, Deponentien, Partizip, Gerundium, Steigerung (Griechisch).

Das Neugriechische hat kein eigenes Passivparadigma im Sinne eines Anhängsels
ans Aktiv: die Endungen sind andere, und eine ganze Klasse von Verben
(θυμάμαι, έρχομαι, κοιμάμαι) hat ÜBERHAUPT nur diese Endungen, bedeutet damit
aber nichts Passives. Wer das nicht unterscheidet, bekommt zwei falsche
Ergebnisse: Passivformen rutschen in die Aktivtabelle, und Deponentien melden
ein halbes Dutzend Mängel, die keine sind.
"""


def _aufbau(klient, sprache="el"):
    b = klient.post("/api/benutzer", json={"name": "Passivtester"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": sprache}).json()
    return b, s


def importieren(klient, sammlung_id, eintraege, **kw):
    return klient.post(f"/api/sammlungen/{sammlung_id}/import/vokabeln",
                       json={"eintraege": eintraege, **kw}).json()


def _erstes(klient, sammlung):
    return klient.get(f"/api/sammlungen/{sammlung['id']}/lexeme"
                      ).json()["lexeme"][0]


def befunde(ergebnis, nr=0):
    if not ergebnis["eintraege"]:
        return set()
    return {b["art"] for b in ergebnis["eintraege"][nr].get("befunde", [])}


def _reihe(gruppe_merkmale, texte):
    personen = [("1", "sg"), ("2", "sg"), ("3", "sg"),
                ("1", "pl"), ("2", "pl"), ("3", "pl")]
    return [{"text": t, "merkmale": {**gruppe_merkmale,
                                     "person": p, "numerus": n}}
            for t, (p, n) in zip(texte, personen)]


PRAESENS_PASSIV = {"modus": "indikativ", "tempus": "praesens",
                   "genus_verbi": "passiv"}
PRAESENS_AKTIV = {"modus": "indikativ", "tempus": "praesens"}


# ------------------------------------------------------------------ Passiv

def test_passivformen_landen_in_der_passivgruppe(klient):
    """γράφομαι ist keine Form von γράφω in der Aktivtabelle. Vor der
    Trennung passte sie dort hinein, weil die Aktivgruppe nichts zum
    Genus verbi sagte."""
    import sys
    sys.path.insert(0, "backend")
    import aufgaben
    aktiv = aufgaben._gruppe_der_form("el", "verb", {
        **PRAESENS_AKTIV, "person": "1", "numerus": "sg"})
    passiv = aufgaben._gruppe_der_form("el", "verb", {
        **PRAESENS_PASSIV, "person": "1", "numerus": "sg"})
    assert aktiv["kennung"] == "enestotas"
    assert passiv["kennung"] == "enestotas_pass"


def test_passiv_wird_abgefragt_und_als_passiv_beschriftet(klient):
    _b, s = _aufbau(klient)
    ergebnis = importieren(klient, s["id"], [{
        "lemma": "γράφω", "wortart": "verb",
        "bedeutungen": [{"uebersetzungen": ["schreiben"]}],
        "formen": _reihe(PRAESENS_AKTIV, ["γράφω", "γράφεις", "γράφει",
                                          "γράφουμε", "γράφετε", "γράφουν"])
                  + _reihe(PRAESENS_PASSIV, [
                      "γράφομαι", "γράφεσαι", "γράφεται",
                      "γραφόμαστε", "γράφεστε", "γράφονται"])}])
    assert ergebnis["angelegt"] == 1
    lexem_id = _erstes(klient, s)["id"]
    bericht = klient.get(f"/api/lexeme/{lexem_id}/pruefung").json()
    assert "paradigma_lueckig" not in {b["art"] for b in bericht["befunde"]}
    assert "ausserhalb_der_formgruppen" not in {b["art"] for b in bericht["befunde"]}
    # Die Passivformen sind als solche benannt, sonst stünde in der Frage
    # "1. Person Singular Präsens" zweimal dasselbe.
    formen = klient.get(f"/api/lexeme/{lexem_id}").json()["formen"]
    bezeichnungen = [f["beschriftung"] for f in formen]
    assert any("Παθητικής" in b for b in bezeichnungen)
    assert len({b for b in bezeichnungen}) == len(bezeichnungen)


# ------------------------------------------------------------ Deponentien

def test_deponens_meldet_keine_fehlenden_aktivformen(klient):
    """θυμάμαι heißt "ich erinnere mich", nicht "ich werde erinnert".
    Ein Aktiv *θυμάω gibt es nicht."""
    _b, s = _aufbau(klient)
    formen = _reihe({"modus": "indikativ", "tempus": "praesens",
                     "genus_verbi": "passiv"},
                    ["θυμάμαι", "θυμάσαι", "θυμάται",
                     "θυμόμαστε", "θυμάστε", "θυμούνται"])
    gemein = {"lemma": "θυμάμαι", "wortart": "verb",
              "bedeutungen": [{"uebersetzungen": ["sich erinnern", "gedenken"]}],
              "formen": formen}

    # Ohne die Angabe hält der Trainer das halbe Paradigma für fehlend …
    ohne = importieren(klient, s["id"], [gemein], nur_pruefen=True)
    # … mit ihr nicht.
    mit = importieren(klient, s["id"], [{
        **gemein, "merkmale": {"diathese": "deponens"}}], nur_pruefen=True)
    assert "paradigma_lueckig" not in befunde(mit)
    assert befunde(mit) <= befunde(ohne)


def test_deponens_ohne_passivformen_meldet_sehr_wohl(klient):
    """Die Ausnahme darf nicht alles stummschalten: fehlt im Passiv etwas,
    bleibt es ein Mangel."""
    _b, s = _aufbau(klient)
    ergebnis = importieren(klient, s["id"], [{
        "lemma": "θυμάμαι", "wortart": "verb",
        "merkmale": {"diathese": "deponens"},
        "bedeutungen": [{"uebersetzungen": ["sich erinnern", "gedenken"]}],
        "formen": _reihe({"modus": "indikativ", "tempus": "praesens",
                          "genus_verbi": "passiv"},
                         ["θυμάμαι", "θυμάσαι"])}], nur_pruefen=True)
    assert "paradigma_lueckig" in befunde(ergebnis)


def test_passivklassen_sind_eintragbar(klient):
    _b, s = _aufbau(klient)
    for klasse in ("-ομαι", "-άμαι", "-ούμαι", "-ιέμαι"):
        ergebnis = importieren(klient, s["id"], [{
            "lemma": f"Probe{klasse}", "wortart": "verb",
            "merkmale": {"klasse": klasse},
            "bedeutungen": [{"uebersetzungen": ["eins", "zwei"]}],
            "formen": _reihe(PRAESENS_PASSIV, ["a", "b", "c", "d", "e", "f"]),
        }], nur_pruefen=True)
        assert ergebnis["abgelehnt"] == 0, (klasse, ergebnis["eintraege"])


# --------------------------------------------- Partizip, Gerundium, Steigerung

def test_partizip_und_gerundium_werden_abgefragt(klient):
    """γραμμένος und γράφοντας gehören zu γράφω, haben aber keine Person."""
    _b, s = _aufbau(klient)
    ergebnis = importieren(klient, s["id"], [{
        "lemma": "γράφω", "wortart": "verb",
        "bedeutungen": [{"uebersetzungen": ["schreiben"]}],
        "formen": _reihe(PRAESENS_AKTIV, ["γράφω", "γράφεις", "γράφει",
                                          "γράφουμε", "γράφετε", "γράφουν"])
                  + [{"text": "γραμμένος",
                      "merkmale": {"nonfinit": "partizip_perfekt",
                                   "genus_verbi": "passiv"}},
                     {"text": "γράφοντας",
                      "merkmale": {"nonfinit": "gerundium"}}]}])
    assert ergebnis["angelegt"] == 1
    lexem = _erstes(klient, s)
    bericht = klient.get(f"/api/lexeme/{lexem['id']}/pruefung").json()
    arten = {b["art"] for b in bericht["befunde"]}
    assert "ausserhalb_der_formgruppen" not in arten
    # Einzelzellen dürfen keine Stammprüfung auslösen — ein Stamm aus einer
    # einzigen Form ist die Form selbst.
    assert "stamm_nicht_ableitbar" not in arten
    texte = [f["text"] for f in klient.get(
        f"/api/lexeme/{lexem['id']}").json()["formen"]]
    assert "γραμμένος" in texte and "γράφοντας" in texte


def test_steigerung_des_adjektivs(klient):
    _b, s = _aufbau(klient)
    ergebnis = importieren(klient, s["id"], [{
        "lemma": "καλός", "wortart": "adjektiv",
        "bedeutungen": [{"uebersetzungen": ["gut", "schön"]}],
        "formen": [
            {"text": "καλός", "merkmale": {"genus": "m", "kasus": "nom",
                                           "numerus": "sg"}},
            {"text": "καλή", "merkmale": {"genus": "f", "kasus": "nom",
                                          "numerus": "sg"}},
            {"text": "καλό", "merkmale": {"genus": "n", "kasus": "nom",
                                          "numerus": "sg"}},
            {"text": "καλύτερος", "merkmale": {"stufe": "komparativ"}},
            {"text": "ο καλύτερος", "merkmale": {"stufe": "superlativ"}}]}])
    assert ergebnis["angelegt"] == 1
    lexem = _erstes(klient, s)
    arten = {b["art"] for b in klient.get(
        f"/api/lexeme/{lexem['id']}/pruefung").json()["befunde"]}
    assert "ausserhalb_der_formgruppen" not in arten


def test_form_bestimmen_fragt_nach_aktiv_oder_passiv(klient):
    """Die Auswahlfelder entstehen aus den Formgruppen. Seit es Passiv gibt,
    muss "Form bestimmen" danach fragen können."""
    import sys
    sys.path.insert(0, "backend")
    import aufgaben
    dimensionen = {d["dimension"] for d in aufgaben._dimensionen("el", "verb")}
    assert "genus_verbi" in dimensionen
    stufen = {d["dimension"] for d in aufgaben._dimensionen("el", "adjektiv")}
    assert "stufe" in stufen
