"""OAuth für Konnektoren ohne eigene Kopfzeile.

Der Anlass: der Dialog »Benutzerdefinierten MCP-Server hinzufügen« in
ChatGPT kennt unter Authentifizierung nur OAuth, keine Authentifizierung
oder beides. Kein Feld für einen API-Schlüssel. Ohne OAuth bliebe nur,
das Zugangsmerkmal in die Adresse zu schreiben.

Hier wird vor allem geprüft, was NICHT gehen darf. Bei einem
Anmeldeverfahren ist der glückliche Fall der leichte; die Fälle, die
zählen, sind die, in denen jemand etwas versucht.
"""

import base64
import hashlib
import os

import pytest

PRUEFER = "s" * 64          # code_verifier
RUECK = "https://chatgpt.com/connector/oauth/5PDdWevX"
MAIL = "kathi@example.org"


def pruefwert(pruefer=PRUEFER):
    roh = hashlib.sha256(pruefer.encode()).digest()
    return base64.urlsafe_b64encode(roh).decode().rstrip("=")


@pytest.fixture
def eingerichtet(monkeypatch):
    """OAuth bietet der Trainer nur an, wenn beide Adressen bekannt sind —
    die mit Access davor und die der Schnittstelle."""
    import app
    import identitaet
    monkeypatch.setattr(app, "WEB_URL", "https://vokabeln.example.org")
    monkeypatch.setattr(app, "MCP_URL", "https://mcp.example.org/mcp")
    # Ohne gesetzte Team-Kennung sieht der Trainer die Access-Kopfzeile
    # gar nicht erst an. Genau diese Zeile hat am 15.11. gefehlt, weil
    # rsync die .env mitgenommen hatte.
    monkeypatch.setattr(identitaet, "TEAM", "test-team")


def _profil(klient, name="Lernende 2", mail=MAIL):
    b = klient.post("/api/benutzer", json={"name": name}).json()
    klient.patch(f"/api/benutzer/{b['id']}", json={"email": mail})
    return b


def _client(klient, name="ChatGPT", rueck=RUECK):
    a = klient.post("/api/oauth/clients", json={"name": name,
                                                "rueckadresse": rueck})
    assert a.status_code == 201, a.text
    return a.json()


def _angemeldet(mail=MAIL):
    return {"cf-access-authenticated-user-email": mail}


def _autorisieren(klient, c, mail=MAIL, **abweichend):
    frage = {"client_id": c["client_id"], "redirect_uri": RUECK,
             "response_type": "code", "code_challenge": pruefwert(),
             "code_challenge_method": "S256", "state": "xyz"}
    frage.update(abweichend)
    return klient.get("/oauth/authorize", params=frage,
                      headers=_angemeldet(mail))


def _code_holen(klient, c, mail=MAIL):
    seite = _autorisieren(klient, c, mail)
    assert seite.status_code == 200, seite.text
    handgriff = seite.text.split('name="vorgang" value="')[1].split('"')[0]
    antwort = klient.post("/oauth/authorize", headers=_angemeldet(mail),
                          data={"vorgang": handgriff, "antwort": "ja"},
                          follow_redirects=False)
    assert antwort.status_code == 303, antwort.text
    ziel = antwort.headers["location"]
    return dict(p.split("=", 1) for p in ziel.split("?", 1)[1].split("&"))


def _tauschen(klient, c, code, **abweichend):
    daten = {"grant_type": "authorization_code", "code": code,
             "client_id": c["client_id"], "redirect_uri": RUECK,
             "code_verifier": PRUEFER}
    daten.update(abweichend)
    return klient.post("/oauth/token", data=daten)


# --------------------------------------------------------- Der gute Fall

def test_der_ganze_weg(klient, eingerichtet):
    """Vom Konnektor bis zum Bearer, der an /mcp wirklich angenommen
    wird. Das ist der Punkt des ganzen Umbaus: am Ende steht ein ganz
    gewöhnliches Zugangsmerkmal, und /mcp bleibt unverändert."""
    _profil(klient)
    c = _client(klient)
    felder = _code_holen(klient, c)
    assert felder["state"] == "xyz"

    antwort = _tauschen(klient, c, felder["code"])
    assert antwort.status_code == 200, antwort.text
    merkmal = antwort.json()["access_token"]
    assert antwort.json()["token_type"] == "Bearer"

    # Und jetzt der eigentliche Beweis.
    mcp = klient.post("/mcp", headers={"Authorization": f"Bearer {merkmal}"},
                      json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                            "params": {}})
    assert mcp.status_code == 200, mcp.text


def test_der_herausgeber_passt_zur_adresse(klient, eingerichtet):
    """RFC 8414 §3.3: der genannte Herausgeber muss genau zu der
    Adresse passen, unter der das Blatt liegt. Tut er es nicht,
    verwirft ein prüfender Client das Blatt und sucht weiter — ChatGPT
    hat es geholt, verworfen und die Suche von vorn begonnen, in einer
    Schleife alle fünf Sekunden."""
    d = klient.get("/.well-known/oauth-authorization-server").json()
    assert d["issuer"] == "https://mcp.example.org"
    # Und der Endpunkt liegt auf DEMSELBEN Namen. Dass er vorher auf
    # einen anderen zeigte, war erlaubt, aber ungewöhnlich.
    assert d["authorization_endpoint"] == \
        "https://mcp.example.org/mcp/oauth/authorize"
    assert d["token_endpoint"] == "https://mcp.example.org/mcp/oauth/token"
    # plain wäre kein Schutz und steht darum nicht drin.
    assert d["code_challenge_methods_supported"] == ["S256"]


def test_der_umweg_fuehrt_hinter_die_anmeldung(klient, eingerichtet):
    """Der Endpunkt auf dem MCP-Namen leitet dorthin weiter, wo Access
    davorsteht — angemeldet wird weiterhin dort und nirgends sonst."""
    antwort = klient.get("/mcp/oauth/authorize",
                         params={"client_id": "x", "state": "abc"},
                         follow_redirects=False)
    assert antwort.status_code == 302
    ziel = antwort.headers["location"]
    assert ziel.startswith("https://vokabeln.example.org/oauth/authorize?")
    assert "client_id=x" in ziel and "state=abc" in ziel


def test_der_401_sagt_wo_die_angaben_stehen(klient, eingerichtet):
    """RFC 9728 sieht die Kopfzeile vor, die MCP-Spezifikation verlangt
    sie — und hier ist sie der einzige Weg: die vorgeschriebenen
    Stellen unter /.well-known sind auf diesem Namen vom Tunnel
    gesperrt. Ohne diese Kopfzeile muss ein Client raten, und ChatGPT
    hat die Einrichtung genau deshalb abgelehnt, ohne den Server auch
    nur einmal anzufragen."""
    # Irgendein Merkmal muss es geben, sonst meldet die Schnittstelle
    # »noch nicht eingerichtet« (503) statt »abgewiesen« (401) — und
    # dann gibt es nichts zu verweisen.
    b = _profil(klient)
    klient.post(f"/api/benutzer/{b['id']}/mcp-token", json={"name": "Claude"})

    antwort = klient.post("/mcp", json={"jsonrpc": "2.0", "id": 1,
                                        "method": "initialize", "params": {}})
    assert antwort.status_code == 401
    kopf = antwort.headers.get("www-authenticate", "")
    assert kopf.startswith("Bearer ")
    # Und zwar auf die Adresse, die durch den Tunnel kommt — unter /mcp.
    assert 'resource_metadata="https://mcp.example.org/mcp/.well-known/' \
           'oauth-protected-resource"' in kopf


def test_ressource_und_herausgeber_sind_zweierlei(klient, eingerichtet):
    """Die Ressource ist die Schnittstelle MIT Pfad, der Herausgeber
    der Name OHNE.

    Hier stand erst beides auf »…/mcp«, weil nur dieser Pfad durch den
    Tunnel kam. Das war ein Umweg um ein Transportproblem auf Kosten
    der Richtigkeit, und es hat sich gerächt: unter der Adresse ohne
    Pfad nannte das Blatt einen Herausgeber mit Pfad, und das ist nach
    RFC 8414 §3.3 ungültig. Seit die Tunnelroute steht, braucht es den
    Umweg nicht mehr.
    """
    d = klient.get("/.well-known/oauth-authorization-server").json()
    r = klient.get("/.well-known/oauth-protected-resource/mcp").json()
    assert r["resource"] == "https://mcp.example.org/mcp"
    assert r["authorization_servers"] == [d["issuer"]]
    assert d["issuer"] == "https://mcp.example.org"


def test_die_blaetter_liegen_an_den_passenden_stellen(klient, eingerichtet):
    """Ein Client sucht je nach Auslegung an verschiedenen Stellen.

    Hat der Herausgeber einen Pfad — hier /mcp —, schiebt RFC 8414 ihn
    HINTER den .well-known-Teil; daneben gibt es die schlichte Form
    und die angehängte. Alle drei zu bedienen kostet drei Zeilen und
    spart die Suche nach dem Grund, warum ein Konnektor die
    Einrichtung ablehnt, ohne den Server je zu fragen.
    """
    for pfad in ("/.well-known/oauth-authorization-server",
                 "/mcp/.well-known/oauth-authorization-server"):
        a = klient.get(pfad)
        assert a.status_code == 200, pfad
        assert a.json()["issuer"] == "https://mcp.example.org", pfad
    for pfad in ("/.well-known/oauth-protected-resource/mcp",
                 "/mcp/.well-known/oauth-protected-resource"):
        a = klient.get(pfad)
        assert a.status_code == 200, pfad
        assert a.json()["resource"] == "https://mcp.example.org/mcp", pfad
        assert a.json()["authorization_servers"] == ["https://mcp.example.org"]

    # Und NICHT dort, wo der Herausgeber nicht zur Adresse passte: ein
    # Blatt an falscher Stelle ist schlimmer als keines.
    assert klient.get(
        "/.well-known/oauth-authorization-server/mcp").status_code == 404


def test_ohne_anlage_kein_oauth(klient):
    """Ohne die beiden Adressen bietet der Trainer gar nichts an, statt
    einen Endpunkt zu nennen, der ungeschützt wäre."""
    assert klient.get("/.well-known/oauth-authorization-server"
                      ).status_code == 503


# ------------------------------------------------- Was nicht gehen darf

def test_ohne_gepruefte_anmeldung_keine_einwilligung(klient, eingerichtet):
    """Die eigentliche Absicherung, und sie ist eine einzige Bedingung.
    Wer den Endpunkt ohne Access erreicht, könnte sich sonst selbst
    einen Zugang zu fremden Vokabeln ausstellen."""
    _profil(klient)
    c = _client(klient)
    antwort = klient.get("/oauth/authorize", params={
        "client_id": c["client_id"], "redirect_uri": RUECK,
        "response_type": "code", "code_challenge": pruefwert(),
        "code_challenge_method": "S256"})
    assert antwort.status_code == 403


def test_fremde_rueckadresse_wird_nicht_weitergeleitet(klient, eingerichtet):
    """Ein nachsichtiger Vergleich machte aus dem Endpunkt eine offene
    Weiterleitung, mit der sich Codes abholen lassen. Und die Absage
    geht NICHT an die fremde Adresse — dorthin darf gar nichts."""
    _profil(klient)
    c = _client(klient)
    antwort = _autorisieren(klient, c, redirect_uri="https://boese.example/x")
    assert antwort.status_code == 400
    assert "Rückadresse" in antwort.text


def test_ein_schraegstrich_zuviel_ist_eine_andere_adresse(klient, eingerichtet):
    _profil(klient)
    c = _client(klient)
    assert _autorisieren(klient, c, redirect_uri=RUECK + "/").status_code == 400


def test_ohne_pkce_geht_nichts(klient, eingerichtet):
    _profil(klient)
    c = _client(klient)
    assert _autorisieren(klient, c, code_challenge="",
                         code_challenge_method="").status_code == 400
    # plain wird abgewiesen, auch wenn ein Prüfwert dabeisteht.
    assert _autorisieren(klient, c, code_challenge_method="plain"
                         ).status_code == 400


def test_falscher_pkce_nachweis(klient, eingerichtet):
    """Der Code allein reicht nicht. Wer ihn mitliest, hat den Prüfer
    nicht — das ist der ganze Sinn von PKCE."""
    _profil(klient)
    c = _client(klient)
    felder = _code_holen(klient, c)
    antwort = _tauschen(klient, c, felder["code"], code_verifier="x" * 64)
    assert antwort.status_code == 400
    assert antwort.json()["error"] == "invalid_grant"


def test_zweite_einloesung_nimmt_die_token_mit(klient, eingerichtet):
    """Eine zweite Einlösung heißt, dass jemand den Code mitgelesen hat.
    Dann ist auch das zuerst ausgegebene Merkmal nicht mehr
    vertrauenswürdig."""
    _profil(klient)
    # Noch jemand mit einem eigenen Merkmal, damit die Schnittstelle
    # eingeschaltet BLEIBT, wenn das andere zurückgenommen wird. Ohne
    # das antwortet sie mit »noch nicht eingerichtet« statt mit
    # »abgewiesen«, und der Test prüfte dann die falsche Sache.
    anderer = _profil(klient, "Max", "max@example.org")
    klient.post(f"/api/benutzer/{anderer['id']}/mcp-token",
                json={"name": "Max am iPad"})

    c = _client(klient)
    felder = _code_holen(klient, c)
    erstes = _tauschen(klient, c, felder["code"]).json()["access_token"]
    assert klient.post("/mcp", headers={"Authorization": f"Bearer {erstes}"},
                       json={"jsonrpc": "2.0", "id": 1,
                             "method": "initialize", "params": {}}
                       ).status_code == 200

    zweite = _tauschen(klient, c, felder["code"])
    assert zweite.status_code == 400
    assert zweite.json()["error"] == "invalid_grant"

    # Und das zuerst ausgegebene Merkmal gilt nicht mehr.
    assert klient.post("/mcp", headers={"Authorization": f"Bearer {erstes}"},
                       json={"jsonrpc": "2.0", "id": 1,
                             "method": "initialize", "params": {}}
                       ).status_code == 401


def test_code_eines_anderen_konnektors(klient, eingerichtet):
    _profil(klient)
    einer = _client(klient, "ChatGPT")
    anderer = _client(klient, "Sonstwas", "https://example.org/zurueck")
    felder = _code_holen(klient, einer)
    antwort = _tauschen(klient, anderer, felder["code"])
    assert antwort.status_code == 400


def test_falscher_clientschluessel_wird_nicht_durchgewunken(klient,
                                                            eingerichtet):
    """Der Schlüssel ist freiwillig — ChatGPT stellt den Tokenendpunkt
    auf »none«. Wird aber einer mitgeschickt, muss er stimmen."""
    _profil(klient)
    c = _client(klient)
    felder = _code_holen(klient, c)
    assert _tauschen(klient, c, felder["code"],
                     client_secret="voks_falsch").status_code == 400


def test_fremde_anmeldung_kann_den_vorgang_nicht_abschliessen(klient,
                                                              eingerichtet):
    """Zwischen dem Aufruf der Seite und dem Klick kann jemand anderes am
    Gerät angemeldet sein. Eine Einwilligung gilt für einen Menschen."""
    _profil(klient)
    _profil(klient, "Max", "max@example.org")
    c = _client(klient)
    seite = _autorisieren(klient, c)
    handgriff = seite.text.split('name="vorgang" value="')[1].split('"')[0]
    antwort = klient.post("/oauth/authorize",
                          headers=_angemeldet("max@example.org"),
                          data={"vorgang": handgriff, "antwort": "ja"},
                          follow_redirects=False)
    assert antwort.status_code == 400


def test_abbrechen_gibt_keinen_code(klient, eingerichtet):
    _profil(klient)
    c = _client(klient)
    seite = _autorisieren(klient, c)
    handgriff = seite.text.split('name="vorgang" value="')[1].split('"')[0]
    antwort = klient.post("/oauth/authorize", headers=_angemeldet(),
                          data={"vorgang": handgriff, "antwort": "nein"},
                          follow_redirects=False)
    assert antwort.status_code == 303
    ziel = antwort.headers["location"]
    assert "error=access_denied" in ziel and "code=" not in ziel


def test_ohne_profil_zur_mailadresse(klient, eingerichtet):
    """Access lässt durch, wer in der Zugriffsregel steht. Steht im
    Trainer kein Profil zu der Adresse, wird hier KEINES angelegt — ein
    dauerhaftes Zugangsmerkmal ist etwas anderes als ein Blick auf die
    Oberfläche."""
    c = _client(klient)
    antwort = _autorisieren(klient, c, mail="fremde@example.org")
    assert antwort.status_code == 403


def test_rueckadresse_ohne_tls_wird_nicht_angelegt(klient, eingerichtet):
    antwort = klient.post("/api/oauth/clients",
                          json={"name": "Unsicher",
                                "rueckadresse": "http://example.org/x"})
    assert antwort.status_code == 400


def test_zuruecknehmen_macht_den_konnektor_tot(klient, eingerichtet):
    _profil(klient)
    c = _client(klient)
    klient.delete(f"/api/oauth/clients/{c['client_id']}")
    assert _autorisieren(klient, c).status_code == 400
