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


def test_kein_stil_greift_auf_eine_unbekannte_variable_zurueck():
    """»Auf dem Handy sind sie weiß auf weiß.«

    Im Stil stand `background: var(--sanft, #f3f1ec)`. `--sanft` gibt
    es nirgends — also griff IMMER die helle Ersatzfarbe, auch im
    Dunkeln, wo die Schrift hell ist. Der Tipp stand damit weiß auf
    weiß.

    Eine Ersatzfarbe ist genau dafür da, dass etwas sichtbar bleibt,
    wenn die Variable fehlt. Fehlt sie IMMER, ist die Ersatzfarbe die
    Farbe — und eine feste Farbe kennt nur eine Richtung.
    """
    import pathlib
    import re

    erklaert = set()
    benutzt = {}
    for datei in sorted(pathlib.Path("frontend/css").glob("*.css")):
        # OHNE die Kommentare. Dort steht, was einmal falsch war —
        # beim ersten Lauf hat der Test sich an der Erklärung des
        # Fehlers gestört, die direkt über dessen Behebung stand.
        text = re.sub(r"/\*.*?\*/", "", datei.read_text(), flags=re.S)
        erklaert |= set(re.findall(r"(--[a-z0-9-]+)\s*:", text))
        for name in re.findall(r"var\(\s*(--[a-z0-9-]+)", text):
            benutzt.setdefault(name, datei.name)
    # Von der Oberfläche zur Laufzeit gesetzt, nicht im Stilblatt:
    # app.js gibt der Kopfzeile die Farbe der gewählten Sammlung.
    erklaert |= {"--sammlungsfarbe"}
    fehlend = {n: d for n, d in benutzt.items() if n not in erklaert}
    assert not fehlend, f"Unbekannte CSS-Variablen: {fehlend}"


def test_keine_festen_farben_im_stil():
    """Farben gehören in die Palette, nicht in die Regel.

    Der weiße Tipp war nur der auffälligste Fall. Nachgemessen fanden
    sich sechs weitere feste Farben in den neueren Ansichten, mit
    Werten bis hinunter zu 1,03:1 im Dunkeln:

        .wort-unbekannt  background: #fdecea      -> 1,07
        .wort-gewuenscht background: #e8f0fe      -> 1,07
        #meldung.fehler  color: #fff              -> 1,94
        .abtippen-balken rgba(0,0,0,.08)          -> 1,05
        .gezielt-zeile   rgba(0,0,0,.07)          -> 1,03

    Eine feste Farbe kennt nur eine Richtung. Die Palette kennt beide
    — und sie kennt dazu die drei Hintergründe, die sich in den
    Einstellungen wählen lassen.

    Erlaubt bleiben Schwarz und Weiß in Schatten und Schleiern: dort
    ist die Deckkraft die Aussage, nicht der Farbton.
    """
    import pathlib
    import re

    muster = re.compile(
        r"(?:color|background(?:-color)?|border(?:-[a-z]+)?(?:-color)?)\s*:"
        r"[^;{}]*?(#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\))")
    unschuldig = re.compile(
        r"^(?:rgba?\(\s*0\s*,?\s*0\s*,?\s*0\s*[,/]|rgba?\(\s*255\s+255\s+255\s*/|"
        r"rgba?\(\s*255\s*,\s*255\s*,\s*255\s*,)", re.I)
    funde = []
    for datei in sorted(pathlib.Path("frontend/css").glob("*.css")):
        ohne_kommentar = re.sub(r"/\*.*?\*/", "", datei.read_text(), flags=re.S)
        for zeile in ohne_kommentar.splitlines():
            # Die Palette selbst DARF feste Farben nennen — sie ist der
            # eine Ort, an dem sie hingehören.
            if re.match(r"\s*--", zeile.strip()):
                continue
            for treffer in muster.finditer(zeile):
                farbe = treffer.group(1)
                if unschuldig.match(farbe):
                    continue
                funde.append(f"{datei.name}: {zeile.strip()[:72]}")
    assert not funde, "Feste Farben außerhalb der Palette:\n" + "\n".join(funde)


def test_die_abfrage_schickt_die_genommenen_tipps_mit():
    """Der Server kann es, die Oberfläche hat es nie getan.

    `tipps` ist Feld von PruefenEingabe und BewertenEingabe und
    deckelt die Bewertung auf »Schwer«. In ansicht_lernen.js stand es
    in keinem der beiden Aufrufe — das Tippsystem war damit umsonst zu
    haben, und der Kommentar bei `tippHolen` behauptete das Gegenteil.

    Ein Feld, das der Server auswertet und der Aufrufer vergisst,
    fällt niemandem auf: es gibt keine Fehlermeldung, nur eine
    Bewertung, die zu gut ist.
    """
    import pathlib
    import re

    quelle = pathlib.Path("frontend/js/ansicht_lernen.js").read_text()
    for name in ("api.pruefen({", "api.bewerten({"):
        anfang = quelle.index(name)
        # Bis zur schließenden Klammer des Aufrufs.
        ende = quelle.index("});", anfang)
        aufruf = quelle[anfang:ende]
        assert re.search(r"\btipps\s*:", aufruf), \
            f"{name} schickt die genommenen Tipps nicht mit"


def test_jedes_kaestchen_hat_ein_tippziel():
    """17 px trifft auf dem Handy niemand zuverlässig.

    `.eintrag-haken` ist 1,1 rem groß, die Kästchen in »Gezielt
    lernen« tragen die Browservorgabe — und gehakt wird damit beim
    Durchgehen von dreißig Wörtern, also genau dort, wo oft getroffen
    werden muss. Der Dateikopf von stil.css sagt es selbst: »ein
    Tippziel darf nie unter 44 px fallen«.

    Die Lösung ist eine Umhüllung (`.hakenfeld`), nicht ein größeres
    Kästchen: so bleibt die Darstellung, und die Trefferfläche wächst.
    """
    import pathlib
    import re

    for name in ("ansicht_wortschatz.js", "ansicht_texte.js",
                 "ansicht_gezielt.js"):
        quelle = pathlib.Path("frontend/js") .joinpath(name).read_text()
        for stelle in re.finditer(r"type: 'checkbox'", quelle):
            # Das Kästchen muss in einem .hakenfeld landen. Gesucht wird
            # der Name der Variablen und dann ihre Verwendung.
            umgebung = quelle[max(0, stelle.start() - 300):stelle.start() + 2000]
            assert "hakenfeld" in umgebung, (
                f"{name}: ein Kästchen ohne Tippziel bei Zeichen "
                f"{stelle.start()}")


def test_keine_knopfreihe_nimmt_ihre_eigene_ausrichtung_zurueck():
    """»Zur Anordnung der Buttons hat der Agent keine Vorschläge?«

    `.frage-werkzeuge` heißt »eine Reihe Knöpfe« und richtete mittig
    aus, weil die Klasse für die Abfragekarte entstanden ist. Benutzt
    wird sie überall — und an 38 von 50 Stellen stand daneben ein
    `justify-content:flex-start`, das die eigene Vorgabe wieder aufhob.
    Die Vorgabe war damit in vier von fünf Fällen die falsche.

    Wer das Gegengift vergaß, bekam eine zentrierte Reihe unter
    linksbündigem Text; in der Regelfreigabe stand sie so und sah dort
    nach einem anderen Bauteil aus.

    Jetzt gibt die Klasse linksbündig vor, und die beiden Karten mit
    mittigem Inhalt (`.frage`, `.abtippkarte`) zentrieren selbst. Eine
    Angabe im Einzelfall heißt: die Vorgabe stimmt wieder nicht.
    """
    import pathlib
    import re

    funde = []
    for datei in sorted(pathlib.Path("frontend/js").glob("*.js")):
        text = datei.read_text()
        for treffer in re.finditer(
                r"class: '([^']*\bfrage-werkzeuge\b[^']*)',\s*style: '([^']*)'",
                text):
            if "justify-content" in treffer.group(2):
                zeile = text[:treffer.start()].count("\n") + 1
                funde.append(f"{datei.name}:{zeile}: {treffer.group(2)}")
    assert not funde, (
        "Knopfreihen mit eigener Ausrichtung — dann gehört sie in die "
        "Klasse:\n" + "\n".join(funde))


def test_in_den_einstellungen_sagt_jeder_speichern_knopf_wofuer():
    """Vier Karten, vier Knöpfe, drei davon hießen »Speichern«.

    Keiner sagte, wofür er gilt. Auf einer Seite mit vier Karten ist
    »Speichern« keine Beschriftung, sondern eine Frage.
    """
    import pathlib
    import re

    quelle = pathlib.Path("frontend/js/ansicht_einstellungen.js").read_text()
    nackt = re.findall(r"\}, 'Speichern'\)|, 'Speichern'\)\)", quelle)
    assert not nackt, (
        f"{len(nackt)} Knopf/Knöpfe heißen bloß »Speichern« — welche Karte?")


def test_die_einstellungen_zeichnen_nie_die_ganze_seite_neu():
    """Der Fund hinter »die Anordnung der Buttons«.

    Drei der Speichern-Knöpfe riefen nach dem Speichern
    `zeichnen(behaelter)` auf, und drei Zurücknehmen-Knöpfe ebenfalls.
    Das leert den Behälter vollständig: was in einer ANDEREN Karte
    eingetippt und noch nicht gespeichert war, entstand aus dem
    gespeicherten Wert neu und war damit weg. Ohne Nachfrage, ohne
    Meldung.

    Nachzustellen war es so: Tagesziel auf 30 ändern, NICHT speichern,
    dann oben im Lehrwerk eine Lektionsnummer speichern — das Tagesziel
    stand wieder auf 20.

    Ein Neuaufbau bleibt nötig, weil die Karten abgeleitete Angaben
    zeigen. Er gehört aber auf die eigene Karte: `karteErneuern`.
    """
    import pathlib
    import re

    quelle = pathlib.Path("frontend/js/ansicht_einstellungen.js").read_text()
    # Ohne Kommentare — dort steht, was einmal falsch war.
    ohne = re.sub(r"/\*.*?\*/", "", quelle, flags=re.S)
    ohne = re.sub(r"^\s*//.*$", "", ohne, flags=re.M)
    # Die Deklaration selbst ist kein Aufruf.
    aufrufe = re.findall(r"(?<!function )\bzeichnen\(behaelter\)", ohne)
    assert not aufrufe, (
        f"{len(aufrufe)}x Ganzseiten-Neuaufbau in den Einstellungen — "
        "das verwirft ungespeicherte Eingaben in den anderen Karten. "
        "karteErneuern(behaelter, kasten, teilX) benutzen.")


def test_die_dritte_ueberschrift_ist_nicht_kleingedrucktes():
    """h3 war kleiner als der Fließtext und dazu grau.

    .95em bei `--leise` heißt: die dritte Gliederungsebene sieht aus
    wie eine Fußnote. Gegen den Grund gemessen waren das im Hellen
    6,27 — unter dem, was für Schrift gilt, die man lesen soll.

    Die Größe bleibt in em, nicht in rem: `--mass` hängt an body, und
    rem würde den Legastheniemodus übergehen.
    """
    import pathlib
    import re

    stil = pathlib.Path("frontend/css/stil.css").read_text()
    regel = re.search(r"\nh3 \{([^}]*)\}", stil)
    assert regel, "Keine h3-Regel in stil.css gefunden"
    inhalt = regel.group(1)

    groesse = re.search(r"font-size:\s*([\d.]+)em", inhalt)
    assert groesse, f"h3 ohne Größe in em: {inhalt.strip()}"
    assert float(groesse.group(1)) >= 1.0, (
        f"h3 ist mit {groesse.group(1)}em kleiner als der Fließtext")

    farbe = re.search(r"color:\s*var\((--[a-z-]+)\)", inhalt)
    assert farbe and farbe.group(1) != "--leise", (
        f"h3 ist leise gesetzt: {inhalt.strip()}")


def test_kein_filter_brightness_statt_einer_mischung():
    """`filter: brightness()` kennt die Richtung nicht.

    Es rechnet am fertigen Bild statt in der Palette: aufhellen heißt
    im Hellen dasselbe wie im Dunkeln. Ein gedrückter Knopf soll im
    Hellen aber dunkler werden und im Dunkeln heller.

    `color-mix(in oklab, var(--akzent) 86%, var(--text))` macht beides
    mit einer Angabe, weil `--text` im Hellen nahschwarz und im
    Dunkeln nahweiß ist.
    """
    import pathlib
    import re

    funde = []
    for datei in sorted(pathlib.Path("frontend/css").glob("*.css")):
        ohne = re.sub(r"/\*.*?\*/", "", datei.read_text(), flags=re.S)
        for nr, zeile in enumerate(ohne.splitlines(), 1):
            if re.search(r"filter:\s*brightness", zeile):
                funde.append(f"{datei.name}:{nr}: {zeile.strip()}")
    assert not funde, (
        "Helligkeitsfilter statt einer Mischung in der Palette:\n"
        + "\n".join(funde))


def test_der_weitersprung_haelt_ueberall_an_wo_es_weitergeht():
    """Eine Uhr, die nach dem Seitenwechsel noch feuert, bewertet die
    FALSCHE Aufgabe.

    Der Weitersprung nach »richtig« ist ein `setTimeout`, der nach
    1,4 Sekunden `weiter()` aufruft. Jede Stelle, an der die Sitzung
    weitergeht oder endet, muss ihn vorher anhalten — sonst läuft er in
    die nächste Frage hinein und wertet sie ab, ohne dass sie jemand
    gelesen hat.

    Drei Stellen sind es: `weiter` (von Hand weitergeklickt),
    `naechste` (die nächste Aufgabe wird geholt) und `beenden` (die
    Ansicht wird verlassen).
    """
    import pathlib
    import re

    quelle = pathlib.Path("frontend/js/ansicht_lernen.js").read_text()
    for name in ("async weiter(", "async naechste(", "beenden()"):
        anfang = quelle.index(name)
        # Bis zur nächsten Methode auf derselben Einrückungsebene.
        rest = quelle[anfang:]
        ende = rest.index("\n  }\n")
        rumpf = rest[:ende]
        assert re.search(r"\bsprungAbbrechen\(\)", rumpf), \
            f"{name} hält den Weitersprung nicht an"


def test_der_weitersprung_gilt_nur_bei_sauber_richtig():
    """Sonst wäre es ein »Rückmeldung überspringen«.

    Und genau die will man sehen: bei »fast richtig« steht dort die
    richtige Schreibung, bei einem Fehler die Lösung, und wer einen
    Tipp genommen oder das Wort nachgesehen hat, dem ist die Wertung
    auf »Schwer« gedeckelt — auch das gehört gelesen.

    Die vier Ausschlüsse sind nicht Beiwerk, sie sind der Grund, warum
    der Schalter vertretbar ist.
    """
    import pathlib

    quelle = pathlib.Path("frontend/js/ansicht_lernen.js").read_text()
    anfang = quelle.index("  springtGleich()")
    rumpf = quelle[anfang:anfang + quelle[anfang:].index("\n  }\n")]
    for bedingung in ("'richtig'", "this.tipps", "this.aufgedeckt",
                      "this.wertungOffen"):
        assert bedingung in rumpf, \
            f"springtGleich() prüft {bedingung} nicht — der Sprung käme zu oft"


def test_gezieltes_lernen_benutzt_die_zurueckgeschickte_zeile():
    """Sonst wäre der Umbau am Server umsonst.

    »Gezielt lernen« baute nach jedem »ja/nein« die ganze Liste neu
    auf — bis zu 200 Zeilen, und die Seite sprang nach oben. Dass das
    falsch ist, stand in derselben Datei schon beschrieben: das
    Kästchen daneben erneuert seit jeher nur den Stapelkasten, »beim
    Durchhaken von fünfzig Wörtern darf die Seite nicht unter den
    Fingern wegspringen«.

    Der Server schickt die geänderte Zeile jetzt zurück. Ein Aufruf,
    der die Antwort wegwirft, hat den Neuaufbau noch im Gepäck.
    """
    import pathlib
    import re

    quelle = pathlib.Path("frontend/js/ansicht_gezielt.js").read_text()
    weggeworfen = re.findall(r"^\s*await api\.abfrageSetzen", quelle, re.M)
    assert not weggeworfen, (
        f"{len(weggeworfen)}x wird die Antwort von abfrageSetzen verworfen — "
        "dann bleibt nur der Neuaufbau der ganzen Liste")
    assert "zeilenErneuern" in quelle, \
        "Ohne zeilenErneuern wird wieder die ganze Liste gezeichnet"


def test_die_textwerkstatt_baut_nur_fuer_die_lesart_neu():
    """Ein angetipptes Wort baute 85 Verse neu auf.

    »Für die KI merken« rief `zeichnenText`, und das holt Text UND
    Deckung neu und baut jeden Abschnitt wieder auf. Beim Iwein-Prolog
    sind das 85 Verse: man liest bei Vers 70, tippt ein unbekanntes
    Wort an — und steht wieder bei Vers 1. Dabei ändert sich dadurch
    genau eine Farbe.

    Ein Neuaufbau bleibt richtig für »Übersetzung daneben«: dort
    entsteht je Abschnitt ein anderer Aufbau, zwei Spalten statt
    einer. Das ist die EINE Stelle, die ihn braucht.
    """
    import pathlib
    import re

    quelle = pathlib.Path("frontend/js/ansicht_texte.js").read_text()
    ohne = re.sub(r"/\*.*?\*/", "", quelle, flags=re.S)
    ohne = re.sub(r"^\s*//.*$", "", ohne, flags=re.M)
    aufrufe = re.findall(r"(?<!function )\bzeichnenText\(behaelter", ohne)
    assert len(aufrufe) == 1, (
        f"{len(aufrufe)} Neuaufbauten des ganzen Textes — erwartet ist der "
        "eine für »Übersetzung daneben«")

    # Und er steht dort, wo er hingehört.
    anfang = ohne.index("function teilLesart(")
    rumpf = ohne[anfang:anfang + ohne[anfang:].index("\n}\n")]
    assert "zeichnenText(behaelter" in rumpf, \
        "Der verbliebene Neuaufbau steht nicht in teilLesart"


def test_ziele_mit_termin_stehen_vor_dem_allgemeinen():
    """»Die sind ja das, worauf der Fokus liegen sollte.«

    Die Lernziele standen nicht nur unter der Heute-Karte, sondern
    auch noch unter dem Bücherregal — fünfter Block. In einem Profil
    stand dort »heute fällig, 60 offen«.

    Entscheidender als die Reihenfolge ist aber der Knopf: der große
    »Lernen« auf der Heute-Karte kennt die Lernziele NICHT (er schickt
    kein lernziel_id mit, und der Planer fragt keines ab). Eine Zeile,
    die einen Termin anzeigt und dann auf denselben allgemeinen Knopf
    verweist, ließe einen mit dem Termin allein.
    """
    import pathlib

    quelle = pathlib.Path("frontend/js/ansicht_uebersicht.js").read_text()

    # Oben, vor dem Allgemeinen.
    assert (quelle.index("teilTermine(ziele)")
            < quelle.index("h('h1', { text: 'Heute' })")
            + len("h('h1', { text: 'Heute' })")), \
        "Der Terminstreifen gehört unter die Überschrift »Heute«"
    assert quelle.index("anfuegen(el, teilTermine(ziele))") \
        < quelle.index("zahlKasten(gesamt.faellig"), \
        "Der Terminstreifen steht nicht vor der Heute-Karte"

    # Ein Regal ist Stöbern, ein Ziel ist eine Zusage.
    assert quelle.index("h('h2', { text: 'Lernziele' })") \
        < quelle.index("h('h2', { text: 'Bücher und Texte' })"), \
        "Die Lernziele stehen immer noch unter dem Bücherregal"

    # Und der Knopf startet DIESES Ziel.
    anfang = quelle.index("function teilTermine(")
    rumpf = quelle[anfang:anfang + quelle[anfang:].index("\n}\n")]
    assert "z.termin" in rumpf, "Der Streifen filtert nicht auf einen Termin"
    assert "#/lernen/ziel/" in rumpf, \
        "Der Knopf startet nicht das Ziel, sondern irgendetwas anderes"
    assert "'#/lernen'" not in rumpf, \
        "Der Knopf fällt auf die allgemeine Abfrage zurück"


def test_die_abfrage_sagt_in_welchem_lernziel_man_steckt():
    """Der Server schickt es mit, die Oberfläche zeigte es nie.

    Das fiel nicht auf, solange ein Ziel nur über die Lernzielseite zu
    starten war — man kam ja gerade von dort. Seit der Terminstreifen
    auf der Übersicht unmittelbar eine Zielabfrage startet, ist der
    Unterschied zwischen »planmäßig über alles« und »genau dieses
    Ziel« nicht mehr am Weg abzulesen.

    Und der Unterschied ist groß: gemessen am echten Stand lieferte
    »Lernen« Karotte, Minimarkt und Reis, während das Ziel, das in
    zwei Tagen ablief, bei Lektion 2 und 3 stand.
    """
    import pathlib

    quelle = pathlib.Path("frontend/js/ansicht_lernen.js").read_text()
    anfang = quelle.index("  teilFortschritt()")
    rumpf = quelle[anfang:anfang + quelle[anfang:].index("\n  }\n")]
    assert "lernziel" in rumpf, \
        "Die Abfrage verrät nicht, ob sie aus einem Lernziel zieht"
    assert "ziel.name" in rumpf, "Der Name des Lernziels fehlt"


def test_der_ring_im_kopf_startet_keine_abfrage():
    """»Da wurde mir jetzt aber ein spanischer Begriff gezeigt.«

    Der Ring zeigt den Tagesstand und die Strähne — und sprang beim
    Antippen nach #/lernen, ohne vorher die Sammlung zu leeren. Also
    in das, was zuletzt eingestellt war: wer gestern Spanisch
    ausgewählt hatte, bekam Spanisch.

    Der tiefere Grund ist aber nicht der fehlende Zweizeiler: er ist
    eine ANZEIGE, kein Startknopf. Wer auf eine Zahl tippt, will
    wissen, was dahintersteckt — und das steht unter »Dein
    Fortschritt«: Stufe, Punkte, Strähne, überbrückte Fehltage.
    Gestartet wird von der Übersicht, wo auch steht, WAS man lernt.
    """
    import pathlib
    import re

    quelle = pathlib.Path("frontend/js/app.js").read_text()
    anfang = quelle.index("getElementById('kopf-spiel').addEventListener")
    rumpf = quelle[anfang:anfang + quelle[anfang:].index("});")]
    ziele = re.findall(r"location\.hash = '([^']+)'", rumpf)
    assert ziele, "Der Ring führt nirgendwohin"
    assert not any(z.startswith("#/lernen") for z in ziele), \
        f"Der Ring startet eine Abfrage: {ziele}"


def test_ein_kapitel_wird_nur_einmal_beschriftet():
    """»Bei ihr werden die Units zweimal angezeigt.«

    Der Trainer führt je Sammlung eine laufende Nummer — für die
    Reihenfolge und für die Lehrgangsschranke. Angezeigt wurde sie
    ZUSÄTZLICH zum Namen, und bei einem Lehrwerk, dessen Kapitel schon
    »Unit 1.4 Zahlen« heißen, stand da »5. Unit 1.4 Zahlen«: zwei
    Zählungen für dieselbe Sache, die sich auch noch widersprechen.

    Die Regel steht in hilfen.kapitelname(). Wer sie umgeht und Nummer
    und Namen selbst zusammensetzt, baut das Doppelte wieder ein.
    """
    import pathlib
    import re

    muster = re.compile(
        r"\$\{[a-z_.]*(?:nr|lektion_nr)\}\.?\s*[`'\"]?\s*\+?\s*"
        r"[^;\n]*(?:name|lektion_name)")
    funde = []
    for datei in sorted(pathlib.Path("frontend/js").glob("*.js")):
        if datei.name == "hilfen.js":
            continue          # dort steht die Regel selbst
        text = datei.read_text()
        for nr, zeile in enumerate(text.splitlines(), 1):
            if muster.search(zeile):
                funde.append(f"{datei.name}:{nr}: {zeile.strip()[:72]}")
    assert not funde, (
        "Nummer und Name zusammengesetzt — kapitelname() benutzen:\n"
        + "\n".join(funde))


def test_die_kapitelbeschriftung_steht_an_einer_stelle():
    """Sonst läuft sie wieder auseinander.

    In der Freigabe stand ein eigener Riegel: »Lektion 5 — Lektion 5 zu
    schreiben wäre albern«. Er verglich auf Gleichheit und griff damit
    nur beim Einlesen ohne Namen — wessen Kapitel anders heißen, las
    weiter beides.
    """
    import pathlib

    hilfen = pathlib.Path("frontend/js/hilfen.js").read_text()
    assert "export function kapitelname(" in hilfen

    for datei in ("ansicht_wortschatz.js", "ansicht_freigabe.js"):
        quelle = pathlib.Path("frontend/js") / datei
        text = quelle.read_text()
        assert "kapitelname" in text, f"{datei} beschriftet Kapitel selbst"
