"""Durchlauf durch die ganze Kette: anlegen, Aufgaben erzeugen, lernen."""


# --------------------------------------------------------------- Hilfsdaten

# aller, mit Présent und Participe passé — das klassische unregelmäßige Verb.
ALLER = {
    "lemma": "aller",
    "wortart": "verb",
    "merkmale": {"hilfsverb": "être", "klasse": "unregelmäßig"},
    "formen": [
        {"text": "aller", "merkmale": {"nonfinit": "infinitiv"}, "ist_grundform": True},
        {"text": "vais", "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                      "person": "1", "numerus": "sg"}},
        {"text": "vas", "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                     "person": "2", "numerus": "sg"}},
        {"text": "va", "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                    "person": "3", "numerus": "sg"}},
        {"text": "allons", "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                        "person": "1", "numerus": "pl"}},
        {"text": "allez", "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                       "person": "2", "numerus": "pl"}},
        {"text": "vont", "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                      "person": "3", "numerus": "pl"}},
        {"text": "allé", "merkmale": {"nonfinit": "partizip_perfekt"}},
    ],
    "bedeutungen": [
        {"uebersetzungen": [{"text": "gehen"}, {"text": "laufen"},
                            {"text": "zu Fuß gehen"}]},
        {"uebersetzungen": [{"text": "fahren"}], "kontext": "mit Fahrzeug",
         "reihenfolge": 1},
    ],
}


def _aufbau(klient, sprache="fr", name="Französisch 1"):
    b = klient.post("/api/benutzer", json={"name": "Annuschka"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": name, "sprache": sprache}).json()
    return b, s


# ------------------------------------------------------------------ Stammdaten

def test_sprachen_sind_eingetragen(klient):
    codes = {s["code"] for s in klient.get("/api/sprachen").json()}
    assert {"de", "en", "fr", "es", "el", "gmh"} <= codes


def test_mittelhochdeutsch_hat_stammformen(klient):
    antwort = klient.get("/api/sprachen/gmh/formgruppen").json()
    assert antwort["sprache"] == "Mittelhochdeutsch"
    assert "stamm_praet_sg" in antwort["stammformen"]
    klassen = antwort["lexemmerkmale"]["verb"]["klasse"]
    assert "stark IV" in klassen and "schwach" in klassen


def test_doppelter_benutzername_wird_abgelehnt(klient):
    klient.post("/api/benutzer", json={"name": "Anni"})
    assert klient.post("/api/benutzer", json={"name": "Anni"}).status_code == 409


def test_unbekanntes_lexemmerkmal_wird_abgelehnt(klient):
    _b, s = _aufbau(klient)
    antwort = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "aller", "wortart": "verb",
        "merkmale": {"ablautreihe": "IV"}})          # gibt es im Französischen nicht
    assert antwort.status_code == 400
    assert "Lexemmerkmal" in antwort.json()["detail"]


def test_eigenes_lexemmerkmal_mit_x_ist_erlaubt(klient):
    _b, s = _aufbau(klient)
    antwort = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "aller", "wortart": "verb",
        "merkmale": {"x_lehrbuchseite": "42"}})
    assert antwort.status_code == 201
    assert antwort.json()["merkmale"]["x_lehrbuchseite"] == "42"


def test_unbekannte_wortart_wird_abgelehnt(klient):
    _b, s = _aufbau(klient)
    antwort = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "x", "wortart": "quatsch"})
    assert antwort.status_code == 422


def test_unbekanntes_merkmal_wird_abgelehnt(klient):
    _b, s = _aufbau(klient)
    antwort = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "x", "wortart": "verb",
        "formen": [{"text": "y", "merkmale": {"tempus": "unfug"}}]})
    assert antwort.status_code == 422


# ------------------------------------------------------- Anlegen und Aufgaben

def test_wort_mit_paradigma_in_einem_aufruf(klient):
    _b, s = _aufbau(klient)
    lexem = klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]}).json()
    assert len(lexem["formen"]) == 8
    assert len(lexem["bedeutungen"]) == 2
    # Die Formen tragen ihre Beschriftung aus dem Sprachprofil.
    beschriftungen = {f["text"]: f["beschriftung"] for f in lexem["formen"]}
    assert beschriftungen["vais"] == "Présent, 1. Person Singular"
    assert beschriftungen["allé"] == "Participe passé"


def test_aufgaben_werden_selbsttaetig_erzeugt(klient):
    _b, s = _aufbau(klient)
    lexem = klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]}).json()
    typen = [a["typ"] for a in lexem["aufgaben"] if a["aktiv"]]
    # Bedeutung erkennen: EINE Aufgabe für das ganze Lexem
    assert typen.count("bedeutung_fremd_deutsch") == 1
    # Wort bilden: eine je Bedeutung, denn die Richtung braucht die Bedeutung
    assert typen.count("bedeutung_deutsch_fremd") == 2
    # Form bilden: je Form außer der Grundform
    assert typen.count("form_bilden") == 7
    # "Form bestimmen" ist nicht voreingestellt
    assert typen.count("form_bestimmen") == 0


def test_abgewaehlte_formgruppe_schaltet_aufgaben_ab_statt_zu_loeschen(klient):
    _b, s = _aufbau(klient)
    lexem = klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]}).json()
    vorher = len([a for a in lexem["aufgaben"] if a["aktiv"]])

    klient.put(f"/api/sammlungen/{s['id']}/einstellungen",
               json={"formgruppen": ["participe_passe", "infinitif"]})
    nachher = klient.get(f"/api/lexeme/{lexem['id']}").json()["aufgaben"]
    assert len([a for a in nachher if a["aktiv"]]) < vorher
    assert len(nachher) == len(lexem["aufgaben"])        # nichts gelöscht

    # Wieder zuschalten bringt dieselben Aufgaben zurück
    klient.put(f"/api/sammlungen/{s['id']}/einstellungen",
               json={"formgruppen": ["praesens", "participe_passe", "infinitif"]})
    zurueck = klient.get(f"/api/lexeme/{lexem['id']}").json()["aufgaben"]
    assert len([a for a in zurueck if a["aktiv"]]) == vorher


def test_form_bestimmen_laesst_sich_zuschalten(klient):
    _b, s = _aufbau(klient)
    klient.put(f"/api/sammlungen/{s['id']}/einstellungen",
               json={"typen": ["form_bilden", "form_bestimmen"]})
    lexem = klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]}).json()
    typen = [a["typ"] for a in lexem["aufgaben"] if a["aktiv"]]
    assert typen.count("form_bestimmen") == 7
    assert typen.count("bedeutung_fremd_deutsch") == 0


def test_ungepruefte_formen_werden_nicht_abgefragt(klient):
    _b, s = _aufbau(klient)
    lexem = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "parler", "wortart": "verb",
        "formen": [
            {"text": "parler", "merkmale": {"nonfinit": "infinitiv"},
             "ist_grundform": True},
            {"text": "parle", "merkmale": {"modus": "indikativ",
                                           "tempus": "praesens",
                                           "person": "1", "numerus": "sg"},
             "quelle": "ki", "geprueft": False},
        ]}).json()
    assert [a for a in lexem["aufgaben"] if a["aktiv"]] == []

    form = next(f for f in lexem["formen"] if f["text"] == "parle")
    klient.post(f"/api/formen/{form['id']}/bestaetigen")
    nachher = klient.get(f"/api/lexeme/{lexem['id']}").json()
    assert len([a for a in nachher["aufgaben"] if a["aktiv"]]) == 1


# ------------------------------------------------------------------- Lernen

def _naechste(klient, benutzer_id, **kw):
    return klient.get("/api/lernen/naechste",
                      params={"benutzer_id": benutzer_id, "anzahl": 1, **kw}).json()


def test_stand_zaehlt_neue_aufgaben(klient):
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    stand = klient.get("/api/lernen/stand", params={"benutzer_id": b["id"]}).json()
    assert stand["neu"] == 10 and stand["faellig"] == 0


def test_aufgabe_bringt_begruendung_und_terminvorschau_mit(klient):
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    aufgabe = _naechste(klient, b["id"])[0]
    assert aufgabe["warum"]["neu"] is True
    # Jeder der vier Knöpfe sagt vorher, welchen Termin er ergibt.
    assert set(aufgabe["vorschau"]) == {"1", "2", "3", "4"}
    assert aufgabe["vorschau"]["3"]["text"]
    assert aufgabe["vorschau"]["4"]["tage"] > aufgabe["vorschau"]["2"]["tage"]


def test_jede_hinterlegte_bedeutung_gilt(klient):
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    aufgabe = _naechste(klient, b["id"], typ="bedeutung_fremd_deutsch")[0]
    assert aufgabe["frage_text"] == "aller"
    for antwort in ("gehen", "laufen", "zu Fuß gehen", "fahren"):
        ergebnis = klient.post("/api/lernen/pruefen", json={
            "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
            "antwort": antwort}).json()
        assert ergebnis["urteil"]["urteil"] == "richtig", antwort


def test_formaufgabe_fragt_die_beschriftete_form(klient):
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    for _ in range(40):
        aufgabe = _naechste(klient, b["id"], typ="form_bilden")[0]
        if aufgabe["frage_zusatz"] == "Présent, 1. Person Singular":
            break
        klient.post("/api/lernen/bewerten", json={
            "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
            "bewertung": 3})
    else:
        raise AssertionError("1. Person Singular kam nicht dran")

    assert aufgabe["frage_text"] == "aller"
    richtig = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "antwort": "vais"}).json()
    assert richtig["urteil"]["urteil"] == "richtig"

    # Und jetzt der Kern: eine ANDERE Form desselben Verbs.
    verwechselt = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "antwort": "vas"}).json()
    assert verwechselt["urteil"]["urteil"] == "falsch"
    assert verwechselt["urteil"]["abweichungen"] == ["verwechslung"]
    assert "2. Person Singular" in verwechselt["urteil"]["hinweis"]


def test_bewerten_setzt_termin_und_schreibt_protokoll(klient):
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    aufgabe = _naechste(klient, b["id"])[0]
    ergebnis = klient.post("/api/lernen/bewerten", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "bewertung": 3, "antwort": "gehen", "urteil": "richtig"}).json()
    assert ergebnis["stabilitaet"] > 0
    assert ergebnis["faellig"] and ergebnis["termin_text"]

    verlauf = klient.get("/api/lernen/verlauf",
                         params={"benutzer_id": b["id"]}).json()
    assert len(verlauf) == 1
    assert verlauf[0]["antwort"] == "gehen"
    # Vor- und Nachzustand stehen im Protokoll — Grundlage dafür, die
    # FSRS-Parameter später aufs eigene Lernverhalten zu rechnen.
    assert verlauf[0]["stabilitaet_vor"] is None
    assert verlauf[0]["stabilitaet_nach"] > 0


def test_nochmal_bleibt_heute_faellig(klient):
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    aufgabe = _naechste(klient, b["id"])[0]
    ergebnis = klient.post("/api/lernen/bewerten", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "bewertung": 1}).json()
    assert ergebnis["intervall_tage"] == 0.0
    import datetime as dt
    assert ergebnis["faellig"] == dt.date.today().isoformat()


def test_eingriffe_von_hand(klient):
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    aufgabe = _naechste(klient, b["id"])[0]
    kennung = {"benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"]}

    klient.post("/api/lernen/bewerten", json={**kennung, "bewertung": 3})
    klient.post("/api/lernen/termin", json={**kennung, "datum": "2027-01-01"})
    klient.post("/api/lernen/aussetzen", json=kennung)
    stand = klient.get("/api/lernen/stand", params={"benutzer_id": b["id"]}).json()
    assert stand["ausgesetzt"] == 1

    klient.post("/api/lernen/fortsetzen", json=kennung)
    klient.post("/api/lernen/zuruecksetzen", json=kennung)
    stand = klient.get("/api/lernen/stand", params={"benutzer_id": b["id"]}).json()
    assert stand["ausgesetzt"] == 0


# ------------------------------------------------------------- Weitere Sprachen

def test_griechisches_substantiv_mit_artikel(klient):
    b, s = _aufbau(klient, "el", "Griechisch")
    lexem = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "σπίτι", "wortart": "substantiv",
        "merkmale": {"genus": "n"},
        "formen": [
            {"text": "σπίτι", "merkmale": {"kasus": "nom", "numerus": "sg"},
             "ist_grundform": True},
            {"text": "σπιτιού", "merkmale": {"kasus": "gen", "numerus": "sg"}},
            {"text": "σπίτια", "merkmale": {"kasus": "nom", "numerus": "pl"}},
        ],
        "bedeutungen": [{"uebersetzungen": [{"text": "Haus"},
                                            {"text": "Wohnung"}]}]}).json()
    typen = [a["typ"] for a in lexem["aufgaben"] if a["aktiv"]]
    assert "genus" in typen                       # Artikelaufgabe entsteht

    artikelaufgabe = next(a for a in lexem["aufgaben"] if a["typ"] == "genus")
    richtig = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": artikelaufgabe["id"],
        "antwort": "το"}).json()
    assert richtig["urteil"]["urteil"] == "richtig"
    falsch = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": artikelaufgabe["id"],
        "antwort": "η"}).json()
    assert falsch["urteil"]["urteil"] == "falsch"


def test_mittelhochdeutsches_verb_fragt_die_stammformen(klient):
    b, s = _aufbau(klient, "gmh", "Mittelhochdeutsch")
    lexem = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "nëmen", "wortart": "verb",
        "merkmale": {"klasse": "stark IV"},
        "formen": [
            {"text": "nëmen", "merkmale": {"nonfinit": "infinitiv"},
             "ist_grundform": True},
            {"text": "nam", "merkmale": {"modus": "indikativ",
                                         "tempus": "praeteritum",
                                         "person": "1", "numerus": "sg"}},
            {"text": "nâmen", "merkmale": {"modus": "indikativ",
                                           "tempus": "praeteritum",
                                           "person": "1", "numerus": "pl"}},
            {"text": "genomen", "merkmale": {"nonfinit": "partizip_perfekt"}},
        ],
        "bedeutungen": [{"uebersetzungen": [{"text": "nehmen"}]}]}).json()
    beschriftungen = {f["text"]: f["beschriftung"] for f in lexem["formen"]}
    assert beschriftungen["nam"] == "1./3. Singular Präteritum"
    assert beschriftungen["nâmen"] == "1./3. Plural Präteritum"
    assert len([a for a in lexem["aufgaben"] if a["aktiv"]]) == 5

    # Singular statt Plural: das soll als Verwechslung dastehen, nicht als
    # Längenzeichenfehler.
    pl = next(a for a in lexem["aufgaben"]
              if a["typ"] == "form_bilden" and a["ziel_id"] ==
              next(f["id"] for f in lexem["formen"] if f["text"] == "nâmen"))
    ergebnis = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": pl["id"], "antwort": "nam"}).json()
    assert ergebnis["urteil"]["urteil"] == "falsch"
    assert ergebnis["urteil"]["abweichungen"] == ["verwechslung"]


# ------------------------------------------------------------- Legasthenie

def test_legastheniemodus_aendert_die_lernvorgaben(klient):
    b, _s = _aufbau(klient)
    vorher = klient.get(f"/api/benutzer/{b['id']}/einstellungen").json()
    assert vorher["wunschretention"] == 0.9 and vorher["neu_je_sitzung"] == 20

    klient.put(f"/api/benutzer/{b['id']}/legasthenie", json={"aktiv": True})
    nachher = klient.get(f"/api/benutzer/{b['id']}/einstellungen").json()
    assert nachher["wunschretention"] == 0.95      # häufiger wiederholen
    assert nachher["neu_je_sitzung"] == 8          # weniger Neues auf einmal
    assert nachher["legasthenie"]["zeichenabstand"] > 0


def test_eigene_vorgabe_schlaegt_den_modus(klient):
    b, _s = _aufbau(klient)
    klient.patch(f"/api/benutzer/{b['id']}", json={"wunschretention": 0.85})
    klient.put(f"/api/benutzer/{b['id']}/legasthenie", json={"aktiv": True})
    assert klient.get(f"/api/benutzer/{b['id']}/einstellungen"
                      ).json()["wunschretention"] == 0.85


def test_fehlerart_wird_benannt(klient):
    b, s = _aufbau(klient)
    lexem = klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "travailler", "wortart": "verb",
        "bedeutungen": [{"uebersetzungen": [{"text": "arbeiten"}]}]}).json()
    aufgabe = next(a for a in lexem["aufgaben"]
                   if a["typ"] == "bedeutung_deutsch_fremd")
    ergebnis = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["id"],
        "antwort": "travailer"}).json()
    assert ergebnis["urteil"]["fehlerart"] == "doppelung_zuwenig"
    assert "ll" in ergebnis["urteil"]["fehlertext"]


def test_zerlegung_nur_im_legastheniemodus(klient):
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={
        "sammlung_id": s["id"], "lemma": "parler", "wortart": "verb",
        "formen": [
            {"text": "parler", "merkmale": {"nonfinit": "infinitiv"},
             "ist_grundform": True},
            {"text": "parlons", "merkmale": {"modus": "indikativ",
                                             "tempus": "praesens",
                                             "person": "1", "numerus": "pl"}},
            {"text": "parlez", "merkmale": {"modus": "indikativ",
                                            "tempus": "praesens",
                                            "person": "2", "numerus": "pl"}},
        ],
        "bedeutungen": [{"uebersetzungen": [{"text": "sprechen"}]}]})
    aufgabe = _naechste(klient, b["id"], typ="form_bilden")[0]
    ohne = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "antwort": "falsch"}).json()
    assert ohne["zerlegung"] is None

    klient.put(f"/api/benutzer/{b['id']}/legasthenie", json={"aktiv": True})
    mit = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "antwort": "falsch"}).json()
    # Der Stamm wird aus dem Paradigma abgeleitet, nicht geraten.
    assert mit["zerlegung"]["stamm"] == "parl"
    assert mit["zerlegung"]["teile"][0] == "parl"
    assert mit["zerlegung"]["maske"]


def test_aufdecken_zeigt_loesung_ohne_zu_bewerten(klient):
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    aufgabe = _naechste(klient, b["id"], typ="form_bilden")[0]
    kennung = {"benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"]}

    gezeigt = klient.post("/api/lernen/aufdecken", json=kennung).json()
    assert gezeigt["erwartet"]
    assert gezeigt["zerlegung"]["maske"]
    # Der Lernstand darf sich davon nicht verändern.
    assert klient.get("/api/lernen/verlauf",
                      params={"benutzer_id": b["id"]}).json() == []
    stand = klient.get("/api/lernen/stand", params={"benutzer_id": b["id"]}).json()
    assert stand["faellig"] == 0


GRAFO = {
    "lemma": "γράφω", "wortart": "verb", "merkmale": {"klasse": "Α-Konjugation"},
    "bedeutungen": [{"uebersetzungen": [{"text": "schreiben"},
                                        {"text": "aufschreiben"}]}],
    "formen": (
        [{"text": t, "merkmale": {"modus": "indikativ", "tempus": "praesens",
                                  "person": p, "numerus": n},
          "ist_grundform": t == "γράφω"}
         for t, (p, n) in zip(["γράφω", "γράφεις", "γράφει", "γράφουμε",
                               "γράφετε", "γράφουν"],
                              [("1", "sg"), ("2", "sg"), ("3", "sg"),
                               ("1", "pl"), ("2", "pl"), ("3", "pl")])]
        + [{"text": t, "merkmale": {"modus": "indikativ", "tempus": "aorist",
                                    "person": p, "numerus": n}}
           for t, (p, n) in zip(["έγραψα", "έγραψες", "έγραψε", "γράψαμε",
                                 "γράψατε", "έγραψαν"],
                                [("1", "sg"), ("2", "sg"), ("3", "sg"),
                                 ("1", "pl"), ("2", "pl"), ("3", "pl")])]
        + [{"text": t, "merkmale": {"modus": "indikativ", "tempus": "futur",
                                    "aspekt": "perfektiv",
                                    "person": p, "numerus": n}}
           for t, (p, n) in zip(["θα γράψω", "θα γράψεις", "θα γράψει",
                                 "θα γράψουμε", "θα γράψετε", "θα γράψουν"],
                                [("1", "sg"), ("2", "sg"), ("3", "sg"),
                                 ("1", "pl"), ("2", "pl"), ("3", "pl")])]
    ),
}


def test_stamm_wird_je_zeit_abgeleitet_nicht_ueber_alle_formen(klient):
    """Über alle Formen hinweg scheitert der gemeinsame Anfang: "γράφω",
    "έγραψα" und "θα γράψω" haben keinen. Innerhalb einer Zeit ist der Stamm
    dagegen konstant — und nur der hilft beim Lernen."""
    b, s = _aufbau(klient, "el", "Griechisch")
    klient.put(f"/api/benutzer/{b['id']}/legasthenie", json={"aktiv": True})
    lexem = klient.post("/api/lexeme", json={**GRAFO, "sammlung_id": s["id"]}).json()
    assert len(lexem["formen"]) == 18

    def stamm_fuer(wort):
        form = next(f for f in lexem["formen"] if f["text"] == wort)
        aufgabe = next(a for a in lexem["aufgaben"]
                       if a["typ"] == "form_bilden" and a["ziel_id"] == form["id"])
        gezeigt = klient.post("/api/lernen/aufdecken", json={
            "benutzer_id": b["id"], "aufgabe_id": aufgabe["id"]}).json()
        return gezeigt["zerlegung"]["stamm"]

    assert stamm_fuer("γράφουμε") == "γράφ"
    assert stamm_fuer("θα γράψουμε") == "θα γράψ"
    # Im Aorist wandert das Augment (έγραψα, aber γράψαμε) und mit ihm der
    # Akzent. Der Stamm ist trotzdem auffindbar.
    assert stamm_fuer("γράψαμε") == "γραψ"


def test_zerlegung_zeigt_stamm_und_endung(klient):
    b, s = _aufbau(klient, "el", "Griechisch")
    klient.put(f"/api/benutzer/{b['id']}/legasthenie", json={"aktiv": True})
    lexem = klient.post("/api/lexeme", json={**GRAFO, "sammlung_id": s["id"]}).json()
    form = next(f for f in lexem["formen"] if f["text"] == "γράφουμε")
    aufgabe = next(a for a in lexem["aufgaben"]
                   if a["typ"] == "form_bilden" and a["ziel_id"] == form["id"])
    gezeigt = klient.post("/api/lernen/aufdecken", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["id"]}).json()
    assert gezeigt["zerlegung"]["teile"] == ["γράφ", "ουμε"]


def test_griechischer_aspekt_wird_beschriftet(klient):
    _b, s = _aufbau(klient, "el", "Griechisch")
    lexem = klient.post("/api/lexeme", json={**GRAFO, "sammlung_id": s["id"]}).json()
    beschriftungen = {f["text"]: f["beschriftung"] for f in lexem["formen"]}
    assert beschriftungen["θα γράψω"] == \
        "Μέλλοντας στιγμιαίος (Futur, punktuell), 1. Person Singular"


def test_zellen_einer_formgruppe_tragen_ihre_beschriftung(klient):
    zellen = klient.get("/api/sprachen/fr/formgruppen/praesens/zellen").json()
    assert len(zellen) == 6
    assert zellen[0]["beschriftung"] == "Présent, 1. Person Singular"
    assert zellen[0]["merkmale"]["tempus"] == "praesens"
    einzeln = klient.get("/api/sprachen/fr/formgruppen/participe_passe/zellen").json()
    assert len(einzeln) == 1 and einzeln[0]["beschriftung"] == "Participe passé"
    assert klient.get("/api/sprachen/fr/formgruppen/quatsch/zellen").status_code == 404


def test_zellen_bei_griechischer_deklination(klient):
    zellen = klient.get("/api/sprachen/el/formgruppen/subst_gen_sg/zellen").json()
    assert zellen[0]["beschriftung"] == "Genitiv Singular"
    assert zellen[0]["kurz"] == "Gen. Sg."


# ------------------------------------------- Automatische Bewertung über die API

def test_pruefen_liefert_die_bewertung_mit_begruendung(klient):
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    aufgabe = _naechste(klient, b["id"], typ="bedeutung_fremd_deutsch")[0]
    ergebnis = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "antwort": "gehen", "denkzeit_ms": 900}).json()
    assert ergebnis["bewertung"]["bewertung"] in (3, 4)
    assert ergebnis["bewertung"]["automatisch"] is True
    assert "richtig" in ergebnis["bewertung"]["begruendung"]
    assert ergebnis["bewertung"]["signale"]["denkzeit_ms"] == 900


def test_bewerten_ohne_note_leitet_sie_ab(klient):
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    aufgabe = _naechste(klient, b["id"])[0]
    ergebnis = klient.post("/api/lernen/bewerten", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "urteil": "richtig", "antwort": "gehen", "denkzeit_ms": 700}).json()
    assert ergebnis["bewertung_quelle"] == "automatisch"
    assert ergebnis["einschaetzung"]["begruendung"]
    verlauf = klient.get("/api/lernen/verlauf",
                         params={"benutzer_id": b["id"]}).json()
    assert verlauf[0]["denkzeit_ms"] == 700
    assert verlauf[0]["bewertung_quelle"] == "automatisch"


def test_eigene_note_gilt_als_eingriff_von_hand(klient):
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    aufgabe = _naechste(klient, b["id"])[0]
    ergebnis = klient.post("/api/lernen/bewerten", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "bewertung": 4, "urteil": "falsch"}).json()
    assert ergebnis["bewertung"] == 4
    assert ergebnis["bewertung_quelle"] == "von_hand"


def test_bewerten_ohne_note_und_ohne_urteil_wird_abgelehnt(klient):
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    aufgabe = _naechste(klient, b["id"])[0]
    antwort = klient.post("/api/lernen/bewerten", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"]})
    assert antwort.status_code == 400


def test_zweiter_versuch_wird_schwaecher_gewertet(klient):
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    aufgabe = _naechste(klient, b["id"], typ="bedeutung_fremd_deutsch")[0]
    daten = {"benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
             "antwort": "gehen", "denkzeit_ms": 900}
    erster = klient.post("/api/lernen/pruefen", json=daten).json()
    zweiter = klient.post("/api/lernen/pruefen",
                          json={**daten, "versuche": 2}).json()
    assert zweiter["bewertung"]["bewertung"] < erster["bewertung"]["bewertung"]


def test_legastheniemodus_schaltet_die_zeitwertung_ab(klient):
    b, s = _aufbau(klient)
    klient.put(f"/api/benutzer/{b['id']}/legasthenie", json={"aktiv": True})
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    aufgabe = _naechste(klient, b["id"], typ="bedeutung_fremd_deutsch")[0]
    ergebnis = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "antwort": "gehen", "denkzeit_ms": 20000}).json()
    assert ergebnis["bewertung"]["signale"]["zeit_gewertet"] is False
    assert ergebnis["bewertung"]["bewertung"] == 3      # nicht abgewertet


def test_zeit_wird_ohne_legastheniemodus_gewertet(klient):
    """Die Legasthenie-Voreinstellungen stehen immer im Datensatz, gelten aber
    nur bei eingeschaltetem Modus. Sonst wäre die Zeitwertung für alle
    abgeschaltet — dort steht ja »nicht messen«."""
    b, s = _aufbau(klient)
    klient.post("/api/lexeme", json={**ALLER, "sammlung_id": s["id"]})
    aufgabe = _naechste(klient, b["id"], typ="bedeutung_fremd_deutsch")[0]
    ergebnis = klient.post("/api/lernen/pruefen", json={
        "benutzer_id": b["id"], "aufgabe_id": aufgabe["aufgabe_id"],
        "antwort": "gehen", "denkzeit_ms": 500}).json()
    assert ergebnis["bewertung"]["signale"]["zeit_gewertet"] is True
    assert ergebnis["bewertung"]["bewertung"] == 4        # sofort da
