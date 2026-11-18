"""Bücher — die Klammer über den Texten.

»Es gibt noch keine Bücher, das wäre noch gut. Und tatsächlich würde
ich behaupten, die Texte gehören dem Konto und nicht der Sammlung.«

Sie hat recht, und zwar in der Ordnung der Dinge: der Iwein gehört
nicht zu »Mittelhochdeutsch, Stammformen«. Er ist Literatur, die man
MIT diesem Wortschatz liest.

Was daraus folgt und hier festgehalten wird:

  Die Bücherliste fragt nicht nach einer Sammlung. Wer drei Sprachen
  lernt, hat EIN Regal.

  Die Sammlung hängt trotzdem am Buch — an ihr hängt die Deckung. Ein
  Buch wird gegen einen Wortschatz gelesen; das ist etwas anderes, als
  ihm zu gehören. Darum darf ein Text aus einem anderen Wortschatz
  auch nicht hinein.

  Ein Buch zu löschen löscht keine Texte. Es ist eine Klammer, kein
  Behälter.
"""

import pytest


@pytest.fixture()
def regal(klient):
    """Eine Person mit zwei Sammlungen und Texten in beiden."""
    b = klient.post("/api/benutzer", json={"name": "Lernender 1"}).json()
    mhd = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Mittelhochdeutsch",
        "sprache": "gmh"}).json()
    el = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    texte = []
    for titel in ["Verse 1–38", "Verse 39–86", "Verse 4818–4865"]:
        texte.append(klient.post(f"/api/sammlungen/{mhd['id']}/texte", json={
            "titel": f"Iwein – {titel}", "typ": "text",
            "inhalt": f"ein vers aus {titel}."}).json())
    fremd = klient.post(f"/api/sammlungen/{el['id']}/texte", json={
        "titel": "Το σπίτι", "typ": "text", "inhalt": "Το σπίτι."}).json()
    return b, mhd, el, texte, fremd


def test_das_regal_fragt_nicht_nach_einer_sammlung(klient, regal):
    """Der Kern der Umstellung: Bücher hängen am Konto, nicht an der
    Sammlungskarte. Wer drei Sprachen lernt, hat ein Regal."""
    b, mhd, el, texte, fremd = regal
    klient.post("/api/buecher", json={
        "benutzer_id": b["id"], "sammlung_id": mhd["id"], "titel": "Iwein",
        "verfasser": "Hartmann von Aue"})
    klient.post("/api/buecher", json={
        "benutzer_id": b["id"], "sammlung_id": el["id"], "titel": "Odyssee"})

    liste = klient.get("/api/buecher", params={"benutzer_id": b["id"]}).json()
    assert [x["titel"] for x in liste] == ["Iwein", "Odyssee"]
    # Und jedes nennt, gegen welchen Wortschatz es gelesen wird.
    assert {x["sammlung"] for x in liste} == {"Mittelhochdeutsch", "Griechisch"}


def test_buch_kapitel_text(klient, regal):
    """Drei Ebenen. Beim Iwein sind es 173 Stücke; ohne die mittlere
    wäre das eine Liste, die niemand durchsieht."""
    b, mhd, el, texte, fremd = regal
    buch = klient.post("/api/buecher", json={
        "benutzer_id": b["id"], "sammlung_id": mhd["id"],
        "titel": "Iwein"}).json()

    klient.put("/api/texte/zuordnen", json={
        "benutzer_id": b["id"], "buch_id": buch["id"],
        "text_ids": [texte[0]["id"], texte[1]["id"]],
        "kapitel": "Prolog und Pfingstfest"})
    klient.put("/api/texte/zuordnen", json={
        "benutzer_id": b["id"], "buch_id": buch["id"],
        "text_ids": [texte[2]["id"]], "kapitel": "Kalogreants Erzählung"})

    inhalt = klient.get(f"/api/buecher/{buch['id']}").json()
    assert [k["titel"] for k in inhalt["kapitel"]] == \
        ["Prolog und Pfingstfest", "Kalogreants Erzählung"]
    assert [len(k["texte"]) for k in inhalt["kapitel"]] == [2, 1]
    assert inhalt["texte"] == 3


def test_ein_text_ohne_kapitel_steht_trotzdem_im_buch(klient, regal):
    """Das Kapitel ist freigestellt. Wer ein Buch hat, das keine
    Kapitel braucht, soll keine erfinden müssen."""
    b, mhd, el, texte, fremd = regal
    buch = klient.post("/api/buecher", json={
        "benutzer_id": b["id"], "sammlung_id": mhd["id"],
        "titel": "Iwein"}).json()
    klient.put("/api/texte/zuordnen", json={
        "benutzer_id": b["id"], "buch_id": buch["id"],
        "text_ids": [texte[0]["id"]]})
    inhalt = klient.get(f"/api/buecher/{buch['id']}").json()
    assert inhalt["kapitel"][0]["titel"] is None
    assert len(inhalt["kapitel"][0]["texte"]) == 1


def test_fremder_wortschatz_kommt_nicht_ins_buch(klient, regal):
    """Ein Buch wird gegen EINEN Wortschatz gelesen.

    Ein griechischer Text in einem mittelhochdeutschen Buch hieße, die
    Deckung gegen den falschen Bestand zu rechnen — und die Auskunft
    »kannst du schon lesen« wäre erfunden.
    """
    b, mhd, el, texte, fremd = regal
    buch = klient.post("/api/buecher", json={
        "benutzer_id": b["id"], "sammlung_id": mhd["id"],
        "titel": "Iwein"}).json()
    a = klient.put("/api/texte/zuordnen", json={
        "benutzer_id": b["id"], "buch_id": buch["id"],
        "text_ids": [fremd["id"]]})
    assert a.status_code == 400, a.text
    assert "Wortschatz" in a.json()["detail"]


def test_ein_geloeschtes_buch_nimmt_keine_texte_mit(klient, regal):
    """Ein Buch ist eine Klammer, kein Behälter. Wer sie entfernt,
    will nicht 173 Texte und ihre Übersetzungen verlieren."""
    b, mhd, el, texte, fremd = regal
    buch = klient.post("/api/buecher", json={
        "benutzer_id": b["id"], "sammlung_id": mhd["id"],
        "titel": "Iwein"}).json()
    klient.put("/api/texte/zuordnen", json={
        "benutzer_id": b["id"], "buch_id": buch["id"],
        "text_ids": [t["id"] for t in texte], "kapitel": "Prolog"})

    klient.delete(f"/api/buecher/{buch['id']}")

    liste = klient.get(f"/api/sammlungen/{mhd['id']}/texte").json()
    assert len(liste) == 3, "die Texte bleiben"
    assert all(t["buch_id"] is None for t in liste)
    assert all(t["kapitel"] is None for t in liste), \
        "und hängen an keinem Kapitel mehr"


def test_texte_lassen_sich_aus_dem_buch_nehmen(klient, regal):
    b, mhd, el, texte, fremd = regal
    buch = klient.post("/api/buecher", json={
        "benutzer_id": b["id"], "sammlung_id": mhd["id"],
        "titel": "Iwein"}).json()
    klient.put("/api/texte/zuordnen", json={
        "benutzer_id": b["id"], "buch_id": buch["id"],
        "text_ids": [t["id"] for t in texte], "kapitel": "Prolog"})
    klient.put("/api/texte/zuordnen", json={
        "benutzer_id": b["id"], "text_ids": [texte[0]["id"]]})

    inhalt = klient.get(f"/api/buecher/{buch['id']}").json()
    assert inhalt["texte"] == 2


def test_das_buch_sagt_wie_weit_die_uebersetzung_ist(klient, regal):
    """Dieselbe Auskunft wie beim einzelnen Text, nur eine Ebene
    höher: wer 8912 Abschnitte übersetzen lässt, will wissen, wo er
    steht."""
    b, mhd, el, texte, fremd = regal
    buch = klient.post("/api/buecher", json={
        "benutzer_id": b["id"], "sammlung_id": mhd["id"],
        "titel": "Iwein"}).json()
    klient.put("/api/texte/zuordnen", json={
        "benutzer_id": b["id"], "buch_id": buch["id"],
        "text_ids": [t["id"] for t in texte]})

    erste = klient.get(f"/api/texte/{texte[0]['id']}").json()
    klient.put(f"/api/texte/{texte[0]['id']}/referenz", json={
        "fassungen": {str(erste["abschnitte"][0]["id"]): "Ein Vers daraus."}})

    liste = klient.get("/api/buecher", params={"benutzer_id": b["id"]}).json()
    assert liste[0]["texte"] == 3
    assert liste[0]["abschnitte"] == 3
    assert liste[0]["uebersetzt"] == 1


def test_fremde_texte_werden_abgewiesen(klient, regal):
    """Still zu übergehen sähe aus, als wäre zugeordnet worden."""
    b, mhd, el, texte, fremd = regal
    fremder = klient.post("/api/benutzer", json={"name": "Lernende 2"}).json()
    s2 = klient.post("/api/sammlungen", json={
        "besitzer_id": fremder["id"], "name": "Französisch",
        "sprache": "fr"}).json()
    t2 = klient.post(f"/api/sammlungen/{s2['id']}/texte", json={
        "titel": "La maison", "typ": "text",
        "inhalt": "La maison est grande."}).json()
    buch = klient.post("/api/buecher", json={
        "benutzer_id": b["id"], "sammlung_id": mhd["id"],
        "titel": "Iwein"}).json()

    a = klient.put("/api/texte/zuordnen", json={
        "benutzer_id": b["id"], "buch_id": buch["id"],
        "text_ids": [t2["id"]]})
    assert a.status_code == 403, a.text


def test_die_textliste_fragt_auch_nicht_nach_einer_sammlung(klient, regal):
    """Dasselbe eine Ebene tiefer: wer einen Text sucht, soll nicht
    erst raten müssen, in welcher Sammlung er liegt."""
    b, mhd, el, texte, fremd = regal
    alle = klient.get("/api/texte", params={"benutzer_id": b["id"]}).json()
    assert len(alle) == 4
    assert {t["sammlung"] for t in alle} == {"Mittelhochdeutsch", "Griechisch"}


def test_buecher_ordnen_die_textliste(klient, regal):
    """Texte eines Buchs stehen beieinander, der Rest dahinter."""
    b, mhd, el, texte, fremd = regal
    buch = klient.post("/api/buecher", json={
        "benutzer_id": b["id"], "sammlung_id": mhd["id"],
        "titel": "Iwein"}).json()
    klient.put("/api/texte/zuordnen", json={
        "benutzer_id": b["id"], "buch_id": buch["id"],
        "text_ids": [t["id"] for t in texte], "kapitel": "Prolog"})

    alle = klient.get("/api/texte", params={"benutzer_id": b["id"]}).json()
    assert [t["buch_titel"] for t in alle[:3]] == ["Iwein"] * 3
    assert alle[3]["buch_titel"] is None
    assert alle[0]["kapitel"] == "Prolog"
