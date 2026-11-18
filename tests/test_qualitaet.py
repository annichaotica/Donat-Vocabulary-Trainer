"""Qualitätsprüfung der Einträge und Sprachprofile aus der Datenbank."""


def _aufbau(klient, sprache="fr"):
    b = klient.post("/api/benutzer", json={"name": "Prüfer"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Probe", "sprache": sprache}).json()
    return b, s


def arten(bericht):
    return {b["art"] for b in bericht["befunde"]}


# ------------------------------------------------------- Eintrag prüfen

def test_eintrag_ohne_uebersetzung_ist_ein_fehler(klient):
    _b, s = _aufbau(klient)
    lexem = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "aller", "wortart": "verb"}).json()
    bericht = klient.get(f"/api/lexeme/{lexem['id']}/pruefung").json()
    assert bericht["gut"] is False
    assert "ohne_bedeutung" in arten(bericht)
    # Der Rat muss sagen, WAS die Folge ist, nicht nur dass etwas fehlt.
    rat = next(x for x in bericht["befunde"] if x["art"] == "ohne_bedeutung")["rat"]
    assert "Bedeutungsaufgabe" in rat


def test_nur_eine_uebersetzung_ist_ein_hinweis(klient):
    _b, s = _aufbau(klient)
    lexem = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "aller", "wortart": "verb",
        "bedeutungen": [{"uebersetzungen": [{"text": "gehen"}]}]}).json()
    bericht = klient.get(f"/api/lexeme/{lexem['id']}/pruefung").json()
    assert bericht["gut"] is True              # kein Fehler
    assert "nur_eine_uebersetzung" in arten(bericht)


def test_vollstaendiger_eintrag_ist_sauber(klient):
    _b, s = _aufbau(klient)
    formen = [{"text": "parler", "merkmale": {"nonfinit": "infinitiv"},
               "ist_grundform": True}]
    for t, (p, n) in zip(["parle", "parles", "parle", "parlons", "parlez", "parlent"],
                         [("1", "sg"), ("2", "sg"), ("3", "sg"),
                          ("1", "pl"), ("2", "pl"), ("3", "pl")]):
        formen.append({"text": t, "merkmale": {"modus": "indikativ",
                                               "tempus": "praesens",
                                               "person": p, "numerus": n}})
    lexem = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "parler", "wortart": "verb",
        "formen": formen,
        "bedeutungen": [{"uebersetzungen": [{"text": "sprechen"},
                                            {"text": "reden"}]}]}).json()
    bericht = klient.get(f"/api/lexeme/{lexem['id']}/pruefung").json()
    assert bericht["gut"] is True
    assert "paradigma_lueckig" not in arten(bericht)
    assert "stamm_nicht_ableitbar" not in arten(bericht)


def test_lueckiges_paradigma_wird_benannt(klient):
    _b, s = _aufbau(klient)
    lexem = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "parler", "wortart": "verb",
        "formen": [
            {"text": "parler", "merkmale": {"nonfinit": "infinitiv"},
             "ist_grundform": True},
            {"text": "parle", "merkmale": {"modus": "indikativ",
                                           "tempus": "praesens",
                                           "person": "1", "numerus": "sg"}}],
        "bedeutungen": [{"uebersetzungen": [{"text": "sprechen"},
                                            {"text": "reden"}]}]}).json()
    bericht = klient.get(f"/api/lexeme/{lexem['id']}/pruefung").json()
    befund = next(b for b in bericht["befunde"] if b["art"] == "paradigma_lueckig")
    assert "1 von 6" in befund["text"]
    assert any("2." in x for x in befund["betrifft"])


def test_nicht_ableitbarer_stamm_wird_gemeldet(klient):
    """Bei "aller" ist das richtig so — vais und allons haben keinen
    gemeinsamen Stamm. Der Hinweis sagt beides: dass es sein kann, und
    dass es sonst ein Tippfehler wäre."""
    _b, s = _aufbau(klient)
    formen = [{"text": "aller", "merkmale": {"nonfinit": "infinitiv"},
               "ist_grundform": True}]
    for t, (p, n) in zip(["vais", "vas", "va", "allons", "allez", "vont"],
                         [("1", "sg"), ("2", "sg"), ("3", "sg"),
                          ("1", "pl"), ("2", "pl"), ("3", "pl")]):
        formen.append({"text": t, "merkmale": {"modus": "indikativ",
                                               "tempus": "praesens",
                                               "person": p, "numerus": n}})
    lexem = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "aller", "wortart": "verb",
        "formen": formen,
        "bedeutungen": [{"uebersetzungen": [{"text": "gehen"},
                                            {"text": "laufen"}]}]}).json()
    bericht = klient.get(f"/api/lexeme/{lexem['id']}/pruefung").json()
    befund = next(b for b in bericht["befunde"]
                  if b["art"] == "stamm_nicht_ableitbar")
    assert befund["schwere"] == "hinweis"
    assert "unregelmäßig" in befund["rat"]


def test_doppeltes_lemma_wird_gemeldet(klient):
    _b, s = _aufbau(klient)
    daten = {"sammlung_id": s["id"], "lemma": "la banque", "wortart": "substantiv",
             "merkmale": {"genus": "f"},
             "bedeutungen": [{"uebersetzungen": [{"text": "die Bank"}]}]}
    klient.post("/api/lexeme", json=daten)
    zweites = klient.post("/api/lexeme", json=daten).json()
    bericht = klient.get(f"/api/lexeme/{zweites['id']}/pruefung").json()
    assert "lemma_doppelt" in arten(bericht)


def test_sammlung_im_ganzen_pruefen(klient):
    _b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "aller", "wortart": "verb"})
    bericht = klient.get(f"/api/sammlungen/{s['id']}/pruefung").json()
    assert bericht["zaehler"]["fehler"] >= 1
    assert bericht["eintraege"][0]["lemma"] == "aller"


# --------------------------------------------------- Sprachprofile als Daten

MONGOLISCH = {
    "pruefung": {"gross_klein": "ignorieren", "diakritika": "hinweis",
                 "satzzeichen": "ignorieren", "schriftregeln": []},
    "artikel": {"bestimmt": [], "unbestimmt": [], "regel": "ignorieren",
                "genus_artikel": {}},
    "formgruppen": {
        "substantiv": [
            {"kennung": "nom_sg", "name": "Nominativ Singular", "kurz": "Nom. Sg.",
             "merkmale": {"kasus": "nom", "numerus": "sg"},
             "zellen": [{"kasus": "nom", "numerus": "sg"}]},
            {"kennung": "gen_sg", "name": "Genitiv Singular", "kurz": "Gen. Sg.",
             "merkmale": {"kasus": "gen", "numerus": "sg"},
             "zellen": [{"kasus": "gen", "numerus": "sg"}]},
        ],
    },
    "formgruppen_standard": {"substantiv": "alle"},
}


def test_neue_sprache_anlegen_und_benutzen(klient):
    """Ein Agent am MCP muss eine Sprache einrichten können, ohne dass
    jemand Code ändert."""
    antwort = klient.post("/api/sprachen", json={
        "code": "mn", "name": "Mongolisch", "schrift": "kyrillisch",
        "profil": MONGOLISCH})
    assert antwort.status_code == 201
    assert antwort.json()["im_code_hinterlegt"] is False

    b = klient.post("/api/benutzer", json={"name": "Lerner"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Mongolisch", "sprache": "mn"}).json()
    lexem = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "ном", "wortart": "substantiv",
        "formen": [
            {"text": "ном", "merkmale": {"kasus": "nom", "numerus": "sg"},
             "ist_grundform": True},
            {"text": "номын", "merkmale": {"kasus": "gen", "numerus": "sg"}}],
        "bedeutungen": [{"uebersetzungen": [{"text": "das Buch"}]}]}).json()
    # Die Formgruppe aus der Datenbank wird für die Beschriftung benutzt.
    beschriftung = {f["text"]: f["beschriftung"] for f in lexem["formen"]}
    assert beschriftung["номын"] == "Genitiv Singular"
    assert len([a for a in lexem["aufgaben"] if a["aktiv"]]) >= 2


def test_bestehende_sprache_um_eine_zeit_erweitern(klient):
    """Eine Zeit anfügen, ohne die anderen vierzehn zu wiederholen."""
    vorher = len(klient.get("/api/sprachen/fr/formgruppen").json()["wortarten"]["verb"])
    antwort = klient.put("/api/sprachen/fr/profil", json={"profil": {
        "formgruppen": {"verb": [
            {"kennung": "subjonctif_imparfait", "name": "Subjonctif imparfait",
             "kurz": "Subj. imp.",
             "merkmale": {"modus": "konjunktiv", "tempus": "imperfekt"},
             "zellen": [{"modus": "konjunktiv", "tempus": "imperfekt",
                         "person": p, "numerus": n}
                        for p, n in [("1", "sg"), ("2", "sg"), ("3", "sg"),
                                     ("1", "pl"), ("2", "pl"), ("3", "pl")]]}]}}})
    assert antwort.status_code == 200
    nachher = klient.get("/api/sprachen/fr/formgruppen").json()["wortarten"]["verb"]
    assert len(nachher) == vorher + 1
    assert any(g["kennung"] == "subjonctif_imparfait" for g in nachher)
    # Die im Code hinterlegten Gruppen bleiben erhalten.
    assert any(g["kennung"] == "passe_compose" for g in nachher)


def test_gleiche_kennung_ersetzt_die_gruppe_aus_dem_code(klient):
    klient.put("/api/sprachen/fr/profil", json={"profil": {
        "formgruppen": {"verb": [
            {"kennung": "passe_compose", "name": "Perfekt (umbenannt)",
             "kurz": "Perf.",
             "merkmale": {"modus": "indikativ", "tempus": "perfekt"},
             "zellen": [{"modus": "indikativ", "tempus": "perfekt",
                         "person": "1", "numerus": "sg"}]}]}}})
    gruppen = klient.get("/api/sprachen/fr/formgruppen").json()["wortarten"]["verb"]
    passe = next(g for g in gruppen if g["kennung"] == "passe_compose")
    assert passe["name"] == "Perfekt (umbenannt)"
    assert passe["zellen"] == 1


def test_unbrauchbares_profil_wird_abgelehnt(klient):
    # Zelle ohne die Merkmale ihrer Gruppe
    antwort = klient.put("/api/sprachen/fr/profil", json={"profil": {
        "formgruppen": {"verb": [
            {"kennung": "kaputt", "name": "Kaputt", "kurz": "k",
             "merkmale": {"tempus": "praesens"},
             "zellen": [{"tempus": "futur", "person": "1", "numerus": "sg"}]}]}}})
    assert antwort.status_code == 400
    assert "Zelle" in antwort.json()["detail"]


def test_unbekanntes_merkmal_im_profil_wird_abgelehnt(klient):
    antwort = klient.put("/api/sprachen/fr/profil", json={"profil": {
        "formgruppen": {"verb": [
            {"kennung": "x", "name": "X", "kurz": "x",
             "merkmale": {"erfunden": "ja"}, "zellen": [{"erfunden": "ja"}]}]}}})
    assert antwort.status_code == 400


def test_unbekannter_profilschluessel_wird_abgelehnt(klient):
    antwort = klient.put("/api/sprachen/fr/profil",
                         json={"profil": {"farbe": "blau"}})
    assert antwort.status_code == 400
    assert "Unbekannte Einträge" in antwort.json()["detail"]


def test_profilaenderung_rechnet_die_aufgaben_neu(klient):
    _b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "parler", "wortart": "verb",
        "bedeutungen": [{"uebersetzungen": [{"text": "sprechen"}]}]})
    antwort = klient.put("/api/sprachen/fr/profil", json={
        "profil": {"pruefung": {"diakritika": "streng"}}}).json()
    assert antwort["aufgaben"]["sammlungen"] == 1


def test_geaenderte_pruefregel_wirkt_sofort(klient):
    b, s = _aufbau(klient)
    lexem = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "élève", "wortart": "substantiv",
        "merkmale": {"genus": "m"},
        "bedeutungen": [{"uebersetzungen": [{"text": "der Schüler"}]}]}).json()
    aufgabe = next(a for a in lexem["aufgaben"]
                   if a["typ"] == "bedeutung_deutsch_fremd")
    daten = {"benutzer_id": b["id"], "aufgabe_id": aufgabe["id"], "antwort": "eleve"}
    assert klient.post("/api/lernen/pruefen", json=daten).json()["urteil"]["urteil"] == "fast"

    klient.put("/api/sprachen/fr/profil",
               json={"profil": {"pruefung": {"diakritika": "streng"}}})
    assert klient.post("/api/lernen/pruefen", json=daten).json()["urteil"]["urteil"] == "falsch"


# -------------------------------------------------------------- Wörterbuch

def test_woerterbuch_findet_ueber_jede_form(klient):
    """Wer im Text »έγραψαν« liest, muss γράφω finden — und erfahren,
    welche Form das ist."""
    _b, s = _aufbau(klient, "el")
    klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "γράφω", "wortart": "verb",
        "formen": [
            {"text": "γράφω", "merkmale": {"modus": "indikativ",
                                           "tempus": "praesens",
                                           "person": "1", "numerus": "sg"},
             "ist_grundform": True},
            {"text": "έγραψαν", "merkmale": {"modus": "indikativ",
                                             "tempus": "aorist",
                                             "person": "3", "numerus": "pl"}}],
        "bedeutungen": [{"uebersetzungen": [{"text": "schreiben"}]}]})
    ergebnis = klient.get(f"/api/sammlungen/{s['id']}/woerterbuch",
                          params={"suche": "έγραψαν"}).json()
    assert ergebnis["gefunden"] == 1
    eintrag = ergebnis["eintraege"][0]
    assert eintrag["lemma"] == "γράφω"
    fund = next(f for f in eintrag["fundstellen"] if f["wo"] == "form")
    assert fund["beschriftung"] == "Αόριστος (Aorist), 3. Person Plural"


def test_woerterbuch_findet_ueber_die_uebersetzung(klient):
    _b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "la table", "wortart": "substantiv",
        "merkmale": {"genus": "f"},
        "bedeutungen": [{"uebersetzungen": [{"text": "der Tisch"},
                                            {"text": "die Tafel"}]}]})
    ergebnis = klient.get(f"/api/sammlungen/{s['id']}/woerterbuch",
                          params={"suche": "Tafel"}).json()
    assert ergebnis["gefunden"] == 1
    assert ergebnis["eintraege"][0]["fundstellen"][0]["wo"] == "uebersetzung"


def test_woerterbuch_stellt_genaue_treffer_nach_vorn(klient):
    _b, s = _aufbau(klient)
    for lemma in ("parler", "parlementaire"):
        klient.post("/api/lexeme", json={
            "sammlung_id": s["id"], "lemma": lemma, "wortart": "verb",
            "bedeutungen": [{"uebersetzungen": [{"text": "x"}]}]})
    ergebnis = klient.get(f"/api/sammlungen/{s['id']}/woerterbuch",
                          params={"suche": "parler"}).json()
    assert ergebnis["eintraege"][0]["lemma"] == "parler"


def test_schraegstrich_in_der_uebersetzung_wird_gemeldet(klient):
    """»Da ist die Pflege falsch, oder?« — ja.

    Der Eintrag »πώς είστε« hatte eine einzige Übersetzung: »wie geht
    es Ihnen / euch?«. Der Trainer nimmt jede HINTERLEGTE Übersetzung
    als richtig an, aber nur als Ganzes — wer »wie geht es euch«
    tippt, bekommt ein »falsch« für eine Antwort, die stimmt.

    Im Bestand waren es sechs solche Einträge, alle aus einem frühen
    KI-Import. Damit es nicht wiederkommt, meldet die Qualitätsprüfung
    es jetzt.
    """
    b = klient.post("/api/benutzer", json={"name": "Prüfende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "πώς είστε", "wortart": "wendung",
                       "bedeutungen": [{"uebersetzungen":
                                        ["wie geht es Ihnen / euch?"]}]}]})
    lexem = klient.get(f"/api/sammlungen/{s['id']}/lexeme",
                       params={"suche": "πώς"}).json()["lexeme"][0]
    d = klient.get(f"/api/lexeme/{lexem['id']}/pruefung").json()
    arten = [b["art"] for b in d["befunde"]]
    assert "uebersetzung_gebuendelt" in arten, arten


def test_getrennte_uebersetzungen_werden_nicht_gemeldet(klient):
    """Richtig gepflegt — dann soll der Hinweis schweigen."""
    b = klient.post("/api/benutzer", json={"name": "Prüfende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "πώς είστε", "wortart": "wendung",
                       "bedeutungen": [{"uebersetzungen":
                                        ["wie geht es Ihnen?",
                                         "wie geht es euch?"]}]}]})
    lexem = klient.get(f"/api/sammlungen/{s['id']}/lexeme",
                       params={"suche": "πώς"}).json()["lexeme"][0]
    d = klient.get(f"/api/lexeme/{lexem['id']}/pruefung").json()
    assert "uebersetzung_gebuendelt" not in [b["art"] for b in d["befunde"]]


def test_der_mcp_ruft_routenfunktionen_mit_namen():
    """Sonst verschiebt ein neuer Parameter stillschweigend alles.

    Am 17.11.2026 bekam `lexeme_liste` einen Filter in der Mitte der
    Signatur. Der MCP rief sie mit neun Stellungsargumenten auf: die
    Lektionsnummer landete im neuen Feld, die Wortart in der
    Lektionsnummer, und am Ende stand die Datenbankverbindung an der
    Stelle der Seitenlänge. Vierzehn Tests fielen gleichzeitig um — das
    war der Glücksfall. Ohne sie wäre es eine stille Fehlfunktion
    gewesen, denn die Typen passen zufällig zusammen.

    Die Regel ist darum: höchstens die KENNUNG steht an ihrem Platz,
    alles Weitere bekommt einen Namen. Ein Name kann nicht verrutschen.
    """
    import ast
    import pathlib

    quelle = pathlib.Path("backend/mcp_dienst.py").read_text()
    schlimm = []
    for knoten in ast.walk(ast.parse(quelle)):
        if not isinstance(knoten, ast.Call):
            continue
        if not (isinstance(knoten.func, ast.Name)
                and knoten.func.id == "_fehler_wandeln"):
            continue
        ziel = knoten.args[0] if knoten.args else None
        # Nur Aufrufe in die Routenfunktionen: _app().name
        if not (isinstance(ziel, ast.Attribute)
                and isinstance(ziel.value, ast.Call)
                and getattr(ziel.value.func, "id", None) == "_app"):
            continue
        # args[0] ist die Routenfunktion selbst, args[1] die Kennung.
        if len(knoten.args) > 2:
            schlimm.append(f"{ziel.attr} (Zeile {knoten.lineno}): "
                           f"{len(knoten.args) - 1} Stellungsargumente")
    assert not schlimm, ("Routenfunktionen mit Namen aufrufen: "
                         + "; ".join(schlimm))


def test_ein_kontext_der_eine_form_nennt_wird_gemeldet(klient):
    """»Falscher Wortstamm? Hat mich jedenfalls verwirrt.«

    Die Frage lautete »gegessen — Partizip φαγωμένος«, erwartet war
    τρώω. Sie hat φαγωμένο getippt, also das, was in der Frage stand.

    Jedes Stück für sich ist richtig: Deutsch → Griechisch fragt nach
    der Grundform, und ein Kontext soll erläutern. Zusammen zeigt die
    Frage ein griechisches Wort und verlangt ein anderes.
    """
    b = klient.post("/api/benutzer", json={"name": "Lernende 1"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": "τρώω", "wortart": "verb",
            "bedeutungen": [
                {"uebersetzungen": ["essen"]},
                {"uebersetzungen": ["gegessen"],
                 "kontext": "Partizip φαγωμένος"}],
            "formen": [{"text": "φαγωμένος", "merkmale": {
                "nonfinit": "partizip_perfekt", "genus_verbi": "passiv"}}]}]})

    lexem = klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()["lexeme"][0]
    bericht = klient.get(f"/api/lexeme/{lexem['id']}/pruefung").json()
    arten = [x["art"] for x in bericht["befunde"]]
    assert "kontext_nennt_form" in arten, bericht["befunde"]
    treffer = [x for x in bericht["befunde"]
               if x["art"] == "kontext_nennt_form"][0]
    assert "φαγωμένος" in treffer["text"]
    # Eine Notiz, kein Fehler: manchmal ist es gewollt.
    assert treffer["schwere"] == "notiz"


def test_ein_kontext_ohne_eigene_form_wird_nicht_gemeldet(klient):
    """Die Gegenprobe. »klein, Körpergröße« nennt keine Form — das ist
    genau der Kontext, den es geben soll."""
    b = klient.post("/api/benutzer", json={"name": "Lernende 2"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "μικρός", "wortart": "adjektiv",
                       "bedeutungen": [{"uebersetzungen": ["klein"],
                                        "kontext": "Körpergröße"}]}]})
    lexem = klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()["lexeme"][0]
    bericht = klient.get(f"/api/lexeme/{lexem['id']}/pruefung").json()
    assert "kontext_nennt_form" not in [x["art"] for x in bericht["befunde"]]


def test_die_pruefung_laesst_sich_auf_eine_befundart_eingrenzen(klient):
    """Ohne das ist die Antwort für den griechischen Bestand 744 KB
    groß — 1363 Einträge mit 1808 Befunden. Zu viel, um sie einer KI
    zu geben, und zu viel, um darin etwas zu finden.

    Der Zähler zählt trotzdem ALLES: sonst sähe eine gefilterte
    Prüfung aus wie ein sauberer Bestand.
    """
    b = klient.post("/api/benutzer", json={"name": "Lernende 3"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [
            {"lemma": "τρώω", "wortart": "verb",
             "bedeutungen": [{"uebersetzungen": ["essen"]},
                             {"uebersetzungen": ["gegessen"],
                              "kontext": "Partizip φαγωμένος"}],
             "formen": [{"text": "φαγωμένος", "merkmale": {
                 "nonfinit": "partizip_perfekt", "genus_verbi": "passiv"}}]},
            {"lemma": "μικρός", "wortart": "adjektiv",
             "bedeutungen": [{"uebersetzungen": ["klein"]}]}]})

    alles = klient.get(f"/api/sammlungen/{s['id']}/pruefung").json()
    eng = klient.get(f"/api/sammlungen/{s['id']}/pruefung",
                     params={"art": "kontext_nennt_form"}).json()

    assert eng["geprueft"] == 1, eng["eintraege"]
    assert all(x["art"] == "kontext_nennt_form"
               for e in eng["eintraege"] for x in e["befunde"])
    assert eng["zaehler"] == alles["zaehler"], \
        "der Zähler zählt alles, auch das Ausgeblendete"
    assert eng["nach_art"]["kontext_nennt_form"] == 1


def test_keine_zwei_routenfunktionen_heissen_gleich():
    """Der zweite `def` überschreibt den ersten im Modul.

    Am 18.11.2026 bekam app.py eine zweite Funktion namens
    `bedeutung_loeschen`. Über HTTP ging weiterhin alles — FastAPI
    merkt sich die Route und nicht den Namen. Der MCP-Dienst ruft die
    Routenfunktionen aber ÜBER DEN NAMEN auf (`_app().bedeutung_...`)
    und bekam damit stillschweigend die andere: eine, die nichts
    zurückgibt. Der Fehler sah aus wie ein Tippfehler in den
    Argumenten (»'NoneType' object is not subscriptable«) und stand
    zwei Stockwerke von seiner Ursache entfernt.

    Dabei fiel ein zweiter Fall auf, der schon länger so war: zwei
    verschiedene Dinge hießen `text_deckung`.
    """
    import ast
    import collections
    import pathlib

    baum = ast.parse(pathlib.Path("backend/app.py").read_text())
    namen = collections.defaultdict(list)
    for knoten in baum.body:
        if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
            namen[knoten.name].append(knoten.lineno)
    doppelt = {n: z for n, z in namen.items() if len(z) > 1}
    assert not doppelt, f"Doppelt vergebene Namen in app.py: {doppelt}"
