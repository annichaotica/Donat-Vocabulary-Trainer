"""Datensätze berichtigen statt wegwerfen.

»Wir müssen die Datensätze natürlich auch mal überarbeiten können.
Dafür fehlt ein Knopf!«

Es gab Löschen und Bestätigen, aber kein Ändern. Bei einem Bestand,
den zum großen Teil eine KI gefüllt hat, ist das die falsche Richtung:
berichtigen wird häufiger gebraucht als wegwerfen, und Löschen und
Neuanlegen kostet den Lernstand.

Die Schnittstelle konnte es längst — nur war sie von nirgends benutzt
und darum auch von keinem Test berührt. Das hier holt das nach, denn
jetzt hängt ein Knopf daran.
"""


def _aufbau(klient):
    b = klient.post("/api/benutzer", json={"name": "Berichtigende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Griechisch", "sprache": "el"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{
            "lemma": "γράφω", "wortart": "verb",
            "bedeutungen": [{"uebersetzungen": ["schreiben"]}],
            "formen": [{"text": "γράφεις", "merkmale": {
                "modus": "indikativ", "tempus": "praesens",
                "person": "2", "numerus": "sg"}}]}]})
    klient.post(f"/api/sammlungen/{s['id']}/freigabe", json={"lexem_ids": [1]})
    lexem = klient.get("/api/lexeme/1").json()
    form = next(f for f in lexem["formen"] if not f["ist_grundform"])
    return b, s, lexem, form


def _aufgaben(klient, lexem_id=1):
    return {a["typ"]: a for a in klient.get(f"/api/lexeme/{lexem_id}")
            .json().get("aufgaben", [])}


def test_schreibung_berichtigen(klient):
    _b, _s, _l, f = _aufbau(klient)
    a = klient.patch(f"/api/formen/{f['id']}/teil", json={"text": "γράφεισ"})
    assert a.status_code == 200, a.text
    assert a.json()["text"] == "γράφεισ"


def test_berichtigtes_faellt_auf_ungeprueft_zurueck(klient):
    """Was geändert wurde, ist nicht mehr das, was jemand freigegeben
    hat. Eine erfundene Form, die unbemerkt gepaukt wird, ist schlimmer
    als eine fehlende."""
    _b, _s, _l, f = _aufbau(klient)
    assert f["geprueft"], "Vorbedingung: die Form war freigegeben"
    neu = klient.patch(f"/api/formen/{f['id']}/teil",
                       json={"text": "γράφεισ"}).json()
    assert neu["geprueft"] == 0


def test_dieselbe_schreibung_noch_einmal_aendert_nichts(klient):
    """Sonst fiele eine Form auf ungeprüft zurück, weil jemand das
    Feld geöffnet und wieder gespeichert hat."""
    _b, _s, _l, f = _aufbau(klient)
    neu = klient.patch(f"/api/formen/{f['id']}/teil",
                       json={"text": f["text"]}).json()
    assert neu["geprueft"] == 1


def test_schreibung_behaelt_den_lernstand(klient):
    """Der Aufgabenschlüssel nennt das Merkmalsbündel, nicht die
    Form-ID. Ein Tippfehler in der Schreibung lässt die Zelle also,
    wo sie ist — und mit ihr den Lernstand. Genau deshalb muss man
    berichtigen können, statt zu löschen und neu anzulegen."""
    _b, _s, _l, f = _aufbau(klient)
    vorher = {a["id"] for a in klient.get("/api/lexeme/1").json()["aufgaben"]
              if a["typ"] == "form_bilden"}
    assert vorher
    klient.patch(f"/api/formen/{f['id']}/teil", json={"text": "γράφεισ"})
    nachher = {a["id"] for a in klient.get("/api/lexeme/1").json()["aufgaben"]
               if a["typ"] == "form_bilden"}
    assert nachher == vorher, "die Aufgabe wurde ausgetauscht"


def test_andere_bestimmung_haengt_die_form_um(klient):
    """Eine falsch eingeordnete Form gehört umgehängt, nicht gelöscht.
    Der Lernstand bleibt dabei NICHT an ihr hängen: er gehört der
    Zelle. Was man unter »du schreibst« gelernt hat, hat man nicht
    unter »er schreibt« gelernt — und wenn die Zuordnung falsch war,
    war auch das Gelernte falsch."""
    def aktive():
        return {a["id"] for a in klient.get("/api/lexeme/1").json()["aufgaben"]
                if a["typ"] == "form_bilden" and a["aktiv"]}

    _b, _s, _l, f = _aufbau(klient)
    vorher = aktive()
    assert vorher
    a = klient.patch(f"/api/formen/{f['id']}/teil", json={
        "merkmale": {"modus": "indikativ", "tempus": "praesens",
                     "person": "3", "numerus": "sg"}})
    assert a.status_code == 200, a.text

    # Erst einmal gar keine: die umgehängte Form ist ungeprüft, und
    # Ungeprüftes wird nicht abgefragt. Das ist richtig so — eine
    # gerade erst umsortierte Form ist der Fall, bei dem man am
    # ehesten danebengegriffen hat.
    assert not aktive()

    klient.post(f"/api/formen/{f['id']}/bestaetigen")
    nachher = aktive()
    assert nachher and nachher.isdisjoint(vorher), \
        "die Zelle hat gewechselt, die Aufgabe nicht"


def test_lexemmerkmal_berichtigen(klient):
    """Die Ablautreihe steht am Wort, nicht an einer Form. Falsch
    eingetragen macht sie die Klassenabfrage unbemerkt falsch — die
    Frage sieht ja richtig aus."""
    b = klient.post("/api/benutzer", json={"name": "Berichtigende"}).json()
    s = klient.post("/api/sammlungen", json={
        "besitzer_id": b["id"], "name": "Mhd", "sprache": "gmh"}).json()
    klient.post(f"/api/sammlungen/{s['id']}/import/vokabeln", json={
        "eintraege": [{"lemma": "rîten", "wortart": "verb",
                       "merkmale": {"klasse": "stark II"},
                       "bedeutungen": [{"uebersetzungen": ["reiten"]}]}]})
    a = klient.patch("/api/lexeme/1", json={"merkmale": {"klasse": "stark I"}})
    assert a.status_code == 200, a.text
    assert klient.get("/api/lexeme/1").json()["merkmale"]["klasse"] == "stark I"

    # Und Unsinn wird nicht angenommen: die Werteliste steht im Profil.
    schlecht = klient.patch("/api/lexeme/1",
                            json={"merkmale": {"klasse": "stark XI"}})
    assert schlecht.status_code == 400, schlecht.text


def test_uebersetzung_ergaenzen_und_entfernen(klient):
    _b, _s, lexem, _f = _aufbau(klient)
    bed = lexem["bedeutungen"][0]
    a = klient.post(f"/api/bedeutungen/{bed['id']}/uebersetzungen",
                    json={"text": "aufschreiben", "quelle": "manuell",
                          "geprueft": True})
    assert a.status_code == 201, a.text
    jetzt = klient.get("/api/lexeme/1").json()["bedeutungen"][0]
    assert len(jetzt["uebersetzungen"]) == 2
    klient.delete(f"/api/uebersetzungen/{a.json()['id']}")
    assert len(klient.get("/api/lexeme/1").json()
               ["bedeutungen"][0]["uebersetzungen"]) == 1
