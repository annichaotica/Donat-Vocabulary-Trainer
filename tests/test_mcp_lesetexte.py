"""Der Übergabepunkt: markiertes Wort hier, Vokabel von dort.

»… als Allerletztes noch Worte, die ich quasi noch nicht kenne,
markieren kann. Die soll dann die angebundene KI über den MCP auslesen
können, um mir hier die entsprechenden Datensätze einfügen zu können.«

Der ganze Weg in einem Test: Text einwerfen, Lücke markieren, die KI
liest sie, legt die Vokabel an, hakt ab — und das Wort gilt beim
nächsten Blick auf denselben Text nicht mehr als Lücke.

Was dabei nicht passieren darf, und wofür es je eine eigene Prüfung
gibt: dass die KI fremde Wortwünsche sieht, dass sie einen abhaken
kann, der ihr nicht gehört, und dass sie für eine fehlende FORM eine
zweite Vokabel anlegt statt die Form zu ergänzen.
"""

import pytest

from test_mcp import mcp, person_mit_token, werkzeug, _aufbau  # noqa: F401


@pytest.fixture()
def gelesen(mcp):
    b, s = _aufbau(mcp)
    mcp.klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [
            {"lemma": "το μήλο", "wortart": "substantiv", "lektion_nr": 1,
             "bedeutungen": [{"uebersetzungen": ["der Apfel"]}]}]})
    mcp.klient.post(f"/api/sammlungen/{s['id']}/freigabe",
                    json={"lektion_nr": 1})
    t = mcp.klient.post(f"/api/sammlungen/{s['id']}/texte", json={
        "titel": "Zwei Sätze",
        "inhalt": "Το μήλο είναι κόκκινο."}).json()
    return b, s, t


def test_der_ganze_weg(gelesen, mcp):
    """Markieren, auslesen, anlegen, abhaken — und die Lücke ist zu."""
    b, s, t = gelesen

    # 1. Sie markiert, was sie nicht kennt.
    mcp.klient.post(f"/api/texte/{t['id']}/wortwunsch", json={
        "benutzer_id": b["id"], "wort": "κόκκινο",
        "zusammenhang": "Το μήλο είναι κόκκινο."})

    # 2. Die KI liest die Liste — mit dem Satz, in dem das Wort stand.
    offen = werkzeug(mcp, "offene_woerter_lesen")
    assert offen["anzahl"] == 1
    eintrag = offen["woerter"][0]
    assert eintrag["wort"] == "κόκκινο"
    assert eintrag["zusammenhang"] == "Το μήλο είναι κόκκινο."
    assert eintrag["sprache"] == "el"
    assert eintrag["aus_text"] == "Zwei Sätze"

    # 3. Sie legt die Vokabel an …
    neu = werkzeug(mcp, "vokabel_anlegen", sammlung_id=s["id"],
                   lemma="κόκκινος", wortart="adjektiv",
                   bedeutungen=[{"uebersetzungen": ["rot"]}],
                   formen=[{"text": "κόκκινο", "merkmale": {
                       "genus": "n", "numerus": "sg", "kasus": "nom"}}])
    assert "lexem_id" in neu, neu

    # 4. … und hakt ab.
    werkzeug(mcp, "offenes_wort_erledigen",
             wunsch_id=eintrag["wunsch_id"], lexem_id=neu["lexem_id"])
    assert werkzeug(mcp, "offene_woerter_lesen")["anzahl"] == 0

    # 5. Die Lücke ist zu — sobald die Form freigegeben ist.
    mcp.klient.post(f"/api/sammlungen/{s['id']}/freigabe",
                    json={"lektion_nr": 1})
    d = mcp.klient.get(f"/api/texte/{t['id']}/deckung",
                       params={"benutzer_id": b["id"]}).json()
    fehlt = {w["wort"] for w in d["woerter"] if not w["lexem_id"]}
    assert "κόκκινο" not in fehlt, (
        f"die angelegte Vokabel schließt die Lücke nicht: {sorted(fehlt)}")
    # Die Form, nicht das Lemma: im Text steht »κόκκινο«, angelegt wurde
    # »κόκκινος«. Ohne die mitgelieferte Form bliebe die Lücke offen —
    # und genau davor warnt die Beschreibung des MCP-Werkzeugs.
    treffer = next(w for w in d["woerter"] if w["wort"] == "κόκκινο")
    assert treffer["lexem_id"] == neu["lexem_id"]


def test_die_deckung_nennt_die_luecken_ohne_markieren(gelesen, mcp):
    """Der bequemere Weg: die KI sieht selbst nach, was fehlt — dann
    muss sie nicht warten, bis jedes Wort einzeln angetippt ist."""
    b, s, t = gelesen
    d = werkzeug(mcp, "text_deckung_lesen", text_id=t["id"])
    assert "κόκκινο" in d["fehlende_woerter"]
    assert "Το μήλο" not in d["fehlende_woerter"]
    assert d["abdeckung"] < 100


def test_die_ki_kann_einen_text_hinterlegen(mcp):
    """Die andere Richtung: »schreib mir einen Text auf meinem Niveau«."""
    b, s = _aufbau(mcp)
    neu = werkzeug(mcp, "text_anlegen", sammlung_id=s["id"],
                   titel="Im Garten",
                   inhalt="Πρώτος παράγραφος.\n\nΔεύτερος παράγραφος.",
                   niveau="A1")
    assert neu["abschnitte"] == 2
    liste = werkzeug(mcp, "texte_auflisten", sammlung_id=s["id"])
    assert [x["titel"] for x in liste["texte"]] == ["Im Garten"]


def test_fremde_wortwuensche_sind_nicht_zu_sehen(gelesen, mcp, klient):
    """Der Wortwunsch sagt, was jemand nicht kann. Das geht niemanden
    sonst etwas an — und die Liste ist der Ort, an dem es stünde."""
    b, s, t = gelesen
    mcp.klient.post(f"/api/texte/{t['id']}/wortwunsch", json={
        "benutzer_id": b["id"], "wort": "κόκκινο"})

    zweite = person_mit_token(klient, "Zweite")
    assert werkzeug(zweite, "offene_woerter_lesen")["anzahl"] == 0


def test_ein_fremder_wortwunsch_laesst_sich_nicht_abhaken(gelesen, mcp, klient):
    b, s, t = gelesen
    mcp.klient.post(f"/api/texte/{t['id']}/wortwunsch", json={
        "benutzer_id": b["id"], "wort": "κόκκινο"})
    wunsch_id = werkzeug(mcp, "offene_woerter_lesen")["woerter"][0]["wunsch_id"]

    zweite = person_mit_token(klient, "Zweite")
    antwort = werkzeug(zweite, "offenes_wort_erledigen", wunsch_id=wunsch_id)
    assert antwort.get("_werkzeugfehler") or antwort.get("_protokollfehler"), \
        antwort
    # Und er steht noch offen.
    assert werkzeug(mcp, "offene_woerter_lesen")["anzahl"] == 1


def test_ein_fremder_text_ist_nicht_lesbar(gelesen, mcp, klient):
    b, s, t = gelesen
    zweite = person_mit_token(klient, "Zweite")
    antwort = werkzeug(zweite, "text_deckung_lesen", text_id=t["id"])
    assert antwort.get("_werkzeugfehler") or antwort.get("_protokollfehler"), \
        antwort


# ------------------------------------------- Lehrgang über die Schnittstelle

def test_die_ki_kann_die_lektionszuordnung_lesen_und_setzen(mcp):
    """»Kann anhand der Vokabelstruktur vielleicht der angeschlossene
    Chat besser die Zuordnung machen?«

    Die Struktur nicht — nachgemessen erschien jede Formgruppe ab
    Lektion 1, weil zu fast jedem Wort das volle Paradigma eingetragen
    ist. Der Chat schon, aber wegen seines Wissens über Lehrwerke, und
    dafür braucht er diese beiden Werkzeuge.
    """
    b, s = _aufbau(mcp)
    for nr, name in ((1, "Erste Wörter"), (2, "Verben im Präsens"),
                     (3, "Aorist I")):
        mcp.klient.post(f"/api/sammlungen/{s['id']}/lektionen",
                        json={"nr": nr, "name": name})

    d = werkzeug(mcp, "lehrgang_lesen", sammlung_id=s["id"])
    assert [l["nr"] for l in d["lektionen"]] == [1, 2, 3]
    kennungen = {g["formgruppe"] for g in d["formgruppen"]}
    assert {"enestotas", "aoristos"} <= kennungen
    # Noch nichts eingetragen, aber ein Vorschlag liegt bei.
    assert all(g["ab_lektion"] is None for g in d["formgruppen"])
    nach = {g["formgruppe"]: g for g in d["formgruppen"]}
    assert nach["aoristos"]["namensvorschlag"] == 3
    # Und der Hinweis sagt, worauf man sich NICHT stützen soll.
    assert "Paradigma" in d["hinweis"]

    werkzeug(mcp, "lehrgang_zuordnen", sammlung_id=s["id"],
             zuordnung={"enestotas": 2, "aoristos": 3})
    wieder = werkzeug(mcp, "lehrgang_lesen", sammlung_id=s["id"])
    nach = {g["formgruppe"]: g["ab_lektion"] for g in wieder["formgruppen"]}
    assert nach["enestotas"] == 2 and nach["aoristos"] == 3


def test_die_zuordnung_wird_als_ganzes_ersetzt(mcp):
    """Sonst bliebe eine Gruppe stehen, die die KI bewusst weggelassen
    hat — »gilt von Anfang an« ließe sich dann nicht ausdrücken."""
    b, s = _aufbau(mcp)
    mcp.klient.post(f"/api/sammlungen/{s['id']}/lektionen",
                    json={"nr": 3, "name": "Aorist I"})
    werkzeug(mcp, "lehrgang_zuordnen", sammlung_id=s["id"],
             zuordnung={"enestotas": 2, "aoristos": 3})
    werkzeug(mcp, "lehrgang_zuordnen", sammlung_id=s["id"],
             zuordnung={"aoristos": 3})
    d = werkzeug(mcp, "lehrgang_lesen", sammlung_id=s["id"])
    nach = {g["formgruppe"]: g["ab_lektion"] for g in d["formgruppen"]}
    assert nach["enestotas"] is None
    assert nach["aoristos"] == 3


def test_eine_fremde_sammlung_laesst_sich_nicht_zuordnen(gelesen, mcp, klient):
    b, s, _t = gelesen
    zweite = person_mit_token(klient, "Zweite")
    antwort = werkzeug(zweite, "lehrgang_zuordnen", sammlung_id=s["id"],
                       zuordnung={"aoristos": 3})
    assert antwort.get("_werkzeugfehler") or antwort.get("_protokollfehler"), \
        antwort
