"""Kurspakete einspielen — ganz oder gar nicht.

Fünf Aufrufe nacheinander können nach dem dritten abbrechen, und dann
steht im Bestand ein halbes Paket: Vokabeln ohne die Regeln, die sie
erklären, Texte ohne die Wörter, die sie decken. Genau dagegen gibt es
diesen Weg.
"""

import base64
import io
import json
import zipfile

import pytest


def _zip(dateien: dict) -> bytes:
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w") as z:
        for name, inhalt in dateien.items():
            z.writestr(name, inhalt if isinstance(inhalt, str)
                       else json.dumps(inhalt, ensure_ascii=False))
    return puffer.getvalue()


def _beschreibung(**rest) -> dict:
    grund = {
        "format": 1, "kennung": "probe", "name": "Probepaket",
        "fassung": "1.0.0", "sprache": "en", "grundsprache": "de",
        "herkunft": {"art": "selbst verfasst", "lizenz": "CC-BY-SA-4.0"},
        "geprueft": [],
    }
    grund.update(rest)
    return grund


VOKABELN = [
    {"lemma": "the house", "wortart": "substantiv",
     "bedeutungen": [{"uebersetzungen": ["das Haus", "das Gebäude"]}],
     "formen": [{"text": "house", "merkmale": {"numerus": "sg"},
                 "ist_grundform": True},
                {"text": "houses", "merkmale": {"numerus": "pl"}}]},
    {"lemma": "to walk", "wortart": "verb",
     "bedeutungen": [{"uebersetzungen": ["gehen", "laufen"]}],
     "formen": [{"text": "to walk", "merkmale": {"nonfinit": "infinitiv"},
                 "ist_grundform": True},
                {"text": "walked", "merkmale": {"modus": "indikativ",
                                                "tempus": "praeteritum"}}]},
]

VOLLES_PAKET = {
    "paket.json": _beschreibung(),
    "vokabeln.json": VOKABELN,
    "texte.json": [{"titel": "A walk", "inhalt": "The house is big."}],
    "regeln.json": [{"titel": "Plural mit -s", "text": "house → houses.",
                     "kennung": "probe-plural"}],
}


def _sammlung(klient, sprache="en"):
    b = klient.post("/api/benutzer", json={"name": "Einspielende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Englisch", "sprache": sprache}).json()
    return b, s


def _einspielen(klient, sammlung_id, dateien, nur_pruefen=False):
    return klient.post(f"/api/sammlungen/{sammlung_id}/paket", json={
        "zip_base64": base64.b64encode(_zip(dateien)).decode(),
        "nur_pruefen": nur_pruefen})


# ------------------------------------------------------------ Einspielen

def test_ein_paket_bringt_alles_auf_einmal(klient):
    _b, s = _sammlung(klient)
    a = _einspielen(klient, s["id"], VOLLES_PAKET)
    assert a.status_code == 200, a.text
    bericht = a.json()

    assert bericht["paket"]["kennung"] == "probe"
    assert bericht["teile"]["vokabeln"]["angelegt"] == 2
    assert bericht["teile"]["texte"]["angelegt"] == 1
    assert bericht["teile"]["regeln"]["angelegt"] == 1
    assert bericht["aufgaben"] > 0

    lexeme = klient.get(f"/api/sammlungen/{s['id']}/lexeme").json()["lexeme"]
    assert {l["lemma"] for l in lexeme} == {"the house", "to walk"}
    texte = klient.get("/api/texte", params={"benutzer_id": _b["id"]}).json()
    assert len(texte if isinstance(texte, list) else texte["texte"]) == 1


def test_ohne_pruefvermerk_bleiben_die_formen_ungeprueft(klient):
    """Der Trainer fragt nichts ab, was kein Mensch bestätigt hat.

    Ein leeres `geprueft` ist kein »im Zweifel in Ordnung«, sondern
    sichtbar ungeprüft — und genau so verhält sich das Einspielen.
    """
    _b, s = _sammlung(klient)
    bericht = _einspielen(klient, s["id"], VOLLES_PAKET).json()
    assert bericht["freigegeben"] is False
    assert any("ungeprüft" in w for w in bericht["warnungen"])

    offen = klient.get(f"/api/sammlungen/{s['id']}/freigabe").json()
    assert offen["offen_gesamt"] > 0


def test_mit_pruefvermerk_sind_die_formen_abfragbar(klient):
    _b, s = _sammlung(klient)
    paket = dict(VOLLES_PAKET)
    paket["paket.json"] = _beschreibung(geprueft=[{
        "wer": "Lernende 1", "wann": "2026-11-20", "was": "vokabeln",
        "wie": "Stichprobe gegen das Wörterbuch", "ergebnis": "in Ordnung"}])
    bericht = _einspielen(klient, s["id"], paket).json()

    assert bericht["freigegeben"] is True
    assert bericht["freigabe_durch"]["wer"] == "Lernende 1"
    assert bericht["formen_freigegeben"] > 0
    assert klient.get(f"/api/sammlungen/{s['id']}/freigabe"
                      ).json()["offen_gesamt"] == 0


@pytest.mark.parametrize("vermerk", [
    {"wer": "", "wann": "2026-11-20", "was": "vokabeln", "ergebnis": "in Ordnung"},
    {"wer": "A", "wann": "", "was": "vokabeln", "ergebnis": "in Ordnung"},
    {"wer": "A", "wann": "2026-11-20", "was": "texte", "ergebnis": "in Ordnung"},
    {"wer": "A", "wann": "2026-11-20", "was": "vokabeln", "ergebnis": "mit Vorbehalt"},
])
def test_ein_halber_pruefvermerk_gibt_nichts_frei(klient, vermerk):
    """Ohne Namen, ohne Datum, für etwas anderes oder mit Vorbehalt.

    Ein Vermerk ohne Namen sagt nicht, wen man fragen kann, wenn sich
    später etwas als falsch herausstellt.
    """
    _b, s = _sammlung(klient)
    paket = dict(VOLLES_PAKET)
    paket["paket.json"] = _beschreibung(geprueft=[vermerk])
    assert _einspielen(klient, s["id"], paket).json()["freigegeben"] is False


# -------------------------------------------------------- Ganz oder gar nicht

def test_ein_fehler_im_letzten_teil_laesst_nichts_zurueck(klient):
    """Das ist der Grund, warum es diesen Weg gibt.

    Die Vokabeln sind schon eingetragen, wenn der Text scheitert. Ohne
    die Klammer stünden sie danach im Bestand — ein halbes Paket, das
    niemand bestellt hat.
    """
    _b, s = _sammlung(klient)
    kaputt = dict(VOLLES_PAKET)
    kaputt["texte.json"] = [{"titel": "ohne Inhalt"}]      # inhalt fehlt
    a = _einspielen(klient, s["id"], kaputt)
    assert a.status_code == 400
    assert "inhalt" in a.text

    assert klient.get(f"/api/sammlungen/{s['id']}/lexeme"
                      ).json()["lexeme"] == []
    assert klient.get(f"/api/sammlungen/{s['id']}/regeln").json() == []


def test_probelauf_schreibt_nichts_und_berichtet_trotzdem(klient):
    _b, s = _sammlung(klient)
    bericht = _einspielen(klient, s["id"], VOLLES_PAKET, nur_pruefen=True).json()
    assert bericht["nur_pruefen"] is True
    assert bericht["teile"]["vokabeln"]["angelegt"] == 2      # als ob
    assert klient.get(f"/api/sammlungen/{s['id']}/lexeme"
                      ).json()["lexeme"] == []                # aber nichts da


def test_zweimal_einspielen_legt_nichts_doppelt_an(klient):
    _b, s = _sammlung(klient)
    _einspielen(klient, s["id"], VOLLES_PAKET)
    vorher = len(klient.get(f"/api/sammlungen/{s['id']}/lexeme"
                            ).json()["lexeme"])
    _einspielen(klient, s["id"], VOLLES_PAKET)
    assert len(klient.get(f"/api/sammlungen/{s['id']}/lexeme"
                          ).json()["lexeme"]) == vorher


# ------------------------------------------------------------ Abweisen

def test_kein_zip_wird_abgewiesen(klient):
    _b, s = _sammlung(klient)
    a = klient.post(f"/api/sammlungen/{s['id']}/paket", json={
        "zip_base64": base64.b64encode(b"das ist kein zip").decode()})
    assert a.status_code == 400 and "ZIP" in a.text


def test_kein_base64_wird_abgewiesen(klient):
    _b, s = _sammlung(klient)
    a = klient.post(f"/api/sammlungen/{s['id']}/paket",
                    json={"zip_base64": "!!! kein base64 !!!"})
    assert a.status_code == 400


def test_ohne_paket_json_wird_abgewiesen(klient):
    _b, s = _sammlung(klient)
    a = _einspielen(klient, s["id"], {"vokabeln.json": VOKABELN})
    assert a.status_code == 400 and "paket.json" in a.text


@pytest.mark.parametrize("weg", ["kennung", "name", "fassung", "sprache"])
def test_eine_unvollstaendige_beschreibung_wird_abgewiesen(klient, weg):
    _b, s = _sammlung(klient)
    p = _beschreibung()
    del p[weg]
    a = _einspielen(klient, s["id"], {"paket.json": p, "vokabeln.json": VOKABELN})
    assert a.status_code == 400 and weg in a.text


def test_ein_falsches_format_wird_abgewiesen(klient):
    _b, s = _sammlung(klient)
    a = _einspielen(klient, s["id"],
                    {"paket.json": _beschreibung(format=99)})
    assert a.status_code == 400 and "format" in a.text


def test_herkunft_muss_dastehen(klient):
    """»Selbst verfasst« ist eine Angabe, keine Lücke."""
    _b, s = _sammlung(klient)
    p = _beschreibung()
    del p["herkunft"]
    a = _einspielen(klient, s["id"], {"paket.json": p})
    assert a.status_code == 400 and "herkunft" in a.text


def test_eine_andere_sprache_wird_gemeldet_aber_nicht_verweigert(klient):
    _b, s = _sammlung(klient, sprache="fr")
    bericht = _einspielen(klient, s["id"], VOLLES_PAKET).json()
    assert any("'en'" in w and "'fr'" in w for w in bericht["warnungen"])


def test_zuviele_eintraege_werden_abgewiesen(klient):
    """Eine stumpfe Grenze gegen Packbomben."""
    _b, s = _sammlung(klient)
    viele = {"paket.json": _beschreibung()}
    viele.update({f"beiwerk/{i}.txt": "x" for i in range(250)})
    a = _einspielen(klient, s["id"], viele)
    assert a.status_code == 400 and "Einträge" in a.text


def test_fremde_dateien_im_paket_stoeren_nicht(klient):
    """Eine LIESMICH oder eine Lizenz darf mitkommen."""
    _b, s = _sammlung(klient)
    paket = dict(VOLLES_PAKET)
    paket["LIESMICH.md"] = "# Probepaket\n"
    paket["LICENSE"] = "CC-BY-SA-4.0\n"
    assert _einspielen(klient, s["id"], paket).status_code == 200
