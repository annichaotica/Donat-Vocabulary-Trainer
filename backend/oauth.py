"""OAuth für Konnektoren, die keine eigene Kopfzeile mitschicken können.

Der Anlass ist banal und bindend: der Dialog »Benutzerdefinierten
MCP-Server hinzufügen« in ChatGPT kennt unter Authentifizierung nur
**OAuth**, **keine Authentifizierung** oder beides. Ein Feld für einen
API-Schlüssel gibt es nicht. Ohne OAuth bliebe nur, das Zugangsmerkmal
in die Adresse zu schreiben — und Adressen landen in Protokollen, bei
Cloudflare wie auf dem Server.

WAS HIER NICHT GEBAUT WIRD: die Anmeldung des Menschen.

Das ist der Kniff, der das Ganze klein hält. Der Autorisierungsschritt
liegt auf dem Namen, hinter dem **Cloudflare Access** steht. Access
fragt nach Mailadresse und Einmalcode, bevor die Anfrage überhaupt hier
ankommt, und hängt die geprüfte Adresse als Kopfzeile an. Der Trainer
liest sie und weiß, wer da einwilligt. Keine Passwörter, keine
Sitzungen, kein »Kennwort vergessen«.

Daraus folgt eine harte Regel, die weiter unten durchgesetzt wird:
**ohne geprüfte Mailadresse keine Einwilligung.** Wer den
Autorisierungsendpunkt auf dem Namen ohne Access erreicht, bekommt
nichts — sonst könnte sich jeder im Netz selbst einen Zugang
ausstellen.

Was am Ende herauskommt, ist ein ganz gewöhnliches `mcp_token`. Die
Bearer-Prüfung an `/mcp` bleibt unverändert; sie kann das schon lange.

ABSICHTLICH ENG GEHALTEN:

  * PKCE ist Pflicht, und nur S256. »plain« wäre kein Schutz.
  * Die Rückadresse muss zeichengenau der hinterlegten entsprechen.
    Ein unscharfer Vergleich macht aus dem Endpunkt eine
    Weiterleitung, mit der man Codes abholt.
  * Der Code gilt einmal und zwei Minuten. Er steht im Browserverlauf.
  * Ein verbrauchter oder abgelaufener Code nimmt bei Wiedervorlage
    alle Token desselben Konnektors mit: eine zweite Einlösung heißt,
    dass ihn jemand mitgelesen hat.

Was hier NICHT ist: Auffrischungstoken und Ablaufzeiten für den
Zugang. Die ausgegebenen Token laufen nicht ab, genau wie die von Hand
angelegten — zurückgenommen wird in den Einstellungen, wo sie
aufgelistet stehen. Ein Ablauf ohne Auffrischung wäre eine Falle, und
eine Auffrischung ohne Not gebauter Umfang.
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import secrets
import sqlite3

import datenbank as dbm

# Wie lange ein angefangener Vorgang und ein Code gelten.
VORGANG_MINUTEN = 15      # so lange darf die Einwilligungsseite offenstehen
CODE_SEKUNDEN = 120       # der Code selbst: nur der Sprung zurück


class OAuthFehler(Exception):
    """Mit dem Fehlercode, den der Standard dafür vorsieht."""

    def __init__(self, code: str, beschreibung: str):
        super().__init__(beschreibung)
        self.code = code
        self.beschreibung = beschreibung


def _streuwert(geheimnis: str) -> str:
    return hashlib.sha256(geheimnis.encode()).hexdigest()


def _jetzt() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _frist(sekunden: float) -> str:
    return (_jetzt() + dt.timedelta(seconds=sekunden)).isoformat()


def _abgelaufen(wert: str) -> bool:
    try:
        return dt.datetime.fromisoformat(wert) < _jetzt()
    except ValueError:
        return True


# --------------------------------------------------------------- Clients

def client_anlegen(db: sqlite3.Connection, name: str,
                   rueckadresse: str) -> dict:
    """Legt einen Konnektor an. Der Schlüssel wird EINMAL zurückgegeben.

    Die Rückadresse kommt aus dem Dialog des Konnektors und wird
    unverändert übernommen — verglichen wird später zeichengenau.
    """
    rueckadresse = (rueckadresse or "").strip()
    if not rueckadresse.startswith("https://"):
        # Eine Rückadresse ohne TLS gäbe den Code im Klartext weiter.
        # Einzige Ausnahme wäre localhost, und die braucht hier niemand.
        raise OAuthFehler("invalid_request",
                          "Die Rückadresse muss mit https:// beginnen.")
    if "#" in rueckadresse:
        raise OAuthFehler("invalid_request",
                          "Die Rückadresse darf kein Fragment enthalten.")
    client_id = "vokc_" + secrets.token_urlsafe(18)
    geheimnis = "voks_" + secrets.token_urlsafe(24)
    db.execute("""INSERT INTO oauth_client
                    (client_id, name, rueckadresse, streuwert)
                  VALUES (?, ?, ?, ?)""",
               (client_id, name.strip() or "ohne Namen", rueckadresse,
                _streuwert(geheimnis)))
    return {"client_id": client_id, "geheimnis": geheimnis,
            "name": name, "rueckadresse": rueckadresse,
            "hinweis": "Der Clientschlüssel wird nur dieses eine Mal "
                       "angezeigt. Gespeichert ist nur sein Streuwert."}


def client_lesen(db: sqlite3.Connection, client_id: str) -> dict | None:
    return dbm.zeile(db, """SELECT * FROM oauth_client
                             WHERE client_id = ? AND aktiv = 1""",
                     (client_id or "",))


def client_auflisten(db: sqlite3.Connection) -> list[dict]:
    return [{k: v for k, v in z.items() if k != "streuwert"}
            for z in dbm.zeilen(db, """SELECT * FROM oauth_client
                                        WHERE aktiv = 1 ORDER BY id""")]


def client_zuruecknehmen(db: sqlite3.Connection, client_id: str) -> None:
    """Abschalten, nicht löschen — und die zugehörigen Codes mit."""
    db.execute("UPDATE oauth_client SET aktiv = 0 WHERE client_id = ?",
               (client_id,))
    db.execute("DELETE FROM oauth_code WHERE client_id = ?", (client_id,))
    db.execute("DELETE FROM oauth_vorgang WHERE client_id = ?", (client_id,))


# ------------------------------------------------------------- Der Vorgang

def vorgang_anlegen(db: sqlite3.Connection, client_id: str, benutzer_id: int,
                    mail: str, rueckadresse: str, pruefwert: str,
                    verfahren: str, zustand: str | None) -> str:
    """Prüft die Anfrage des Konnektors und merkt sie vor.

    Zurück kommt eine Kennung für das Einwilligungsformular. Erst der
    Klick auf »Erlauben« macht daraus einen Code.
    """
    client = client_lesen(db, client_id)
    if client is None:
        raise OAuthFehler("invalid_client", "Diesen Konnektor gibt es nicht.")
    # ZEICHENGENAU. Ein Vergleich, der Kleinigkeiten durchgehen lässt —
    # ein fehlender Schrägstrich, ein anderer Pfad — macht aus dem
    # Endpunkt eine offene Weiterleitung, mit der sich Codes abholen
    # lassen.
    if rueckadresse != client["rueckadresse"]:
        raise OAuthFehler("invalid_request",
                          "Die Rückadresse gehört nicht zu diesem Konnektor.")
    if verfahren != "S256":
        raise OAuthFehler("invalid_request",
                          "PKCE ist Pflicht, und nur S256 wird angenommen.")
    if not pruefwert or len(pruefwert) < 43:
        raise OAuthFehler("invalid_request", "Der PKCE-Prüfwert fehlt.")

    handgriff = secrets.token_urlsafe(24)
    db.execute("""INSERT INTO oauth_vorgang
                    (streuwert, client_id, benutzer_id, mail, rueckadresse,
                     pruefwert, zustand, ablauf)
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
               (_streuwert(handgriff), client_id, benutzer_id, mail,
                rueckadresse, pruefwert, zustand,
                _frist(VORGANG_MINUTEN * 60)))
    return handgriff


def vorgang_lesen(db: sqlite3.Connection, handgriff: str,
                  mail: str) -> dict:
    """Holt den Vorgang — nur für dieselbe geprüfte Mailadresse.

    Die zweite Prüfung ist nicht überflüssig: zwischen dem Aufruf der
    Seite und dem Klick kann eine andere Person am selben Gerät
    angemeldet sein, und eine Einwilligung gilt für genau einen
    Menschen.
    """
    v = dbm.zeile(db, "SELECT * FROM oauth_vorgang WHERE streuwert = ?",
                  (_streuwert(handgriff or ""),))
    if v is None:
        raise OAuthFehler("invalid_request", "Dieser Vorgang ist unbekannt.")
    if _abgelaufen(v["ablauf"]):
        db.execute("DELETE FROM oauth_vorgang WHERE id = ?", (v["id"],))
        raise OAuthFehler("invalid_request",
                          "Der Vorgang ist abgelaufen. Bitte in ChatGPT noch "
                          "einmal auf Verbinden drücken.")
    if (v["mail"] or "").lower() != (mail or "").lower():
        raise OAuthFehler("access_denied",
                          "Der Vorgang gehört zu einer anderen Anmeldung.")
    return v


def einwilligen(db: sqlite3.Connection, handgriff: str, mail: str) -> dict:
    """Aus dem Vorgang wird ein Code. Der Vorgang ist danach verbraucht."""
    v = vorgang_lesen(db, handgriff, mail)
    db.execute("DELETE FROM oauth_vorgang WHERE id = ?", (v["id"],))
    code = secrets.token_urlsafe(32)
    db.execute("""INSERT INTO oauth_code
                    (streuwert, client_id, benutzer_id, rueckadresse,
                     pruefwert, ablauf)
                  VALUES (?, ?, ?, ?, ?, ?)""",
               (_streuwert(code), v["client_id"], v["benutzer_id"],
                v["rueckadresse"], v["pruefwert"], _frist(CODE_SEKUNDEN)))
    return {"code": code, "zustand": v["zustand"],
            "rueckadresse": v["rueckadresse"]}


def abbrechen(db: sqlite3.Connection, handgriff: str, mail: str) -> dict:
    v = vorgang_lesen(db, handgriff, mail)
    db.execute("DELETE FROM oauth_vorgang WHERE id = ?", (v["id"],))
    return {"zustand": v["zustand"], "rueckadresse": v["rueckadresse"]}


# ---------------------------------------------------------------- Einlösen

def _pkce_passt(pruefer: str, pruefwert: str) -> bool:
    roh = hashlib.sha256((pruefer or "").encode("ascii")).digest()
    eigen = base64.urlsafe_b64encode(roh).decode("ascii").rstrip("=")
    return secrets.compare_digest(eigen, pruefwert)


def code_einloesen(db: sqlite3.Connection, code: str, client_id: str,
                   rueckadresse: str, pruefer: str,
                   geheimnis: str | None) -> dict:
    """Tauscht den Code gegen ein Zugangsmerkmal.

    Gibt das Merkmal im Klartext zurück — einmal, wie überall sonst
    auch. Gespeichert ist nur sein Streuwert.
    """
    import zugang

    client = client_lesen(db, client_id)
    if client is None:
        raise OAuthFehler("invalid_client", "Diesen Konnektor gibt es nicht.")
    # Der Clientschlüssel ist freiwillig — ChatGPT bietet ihn als
    # optional an und stellt den Tokenendpunkt auf »none«. Wenn aber
    # einer mitgeschickt wird, muss er stimmen; stillschweigend einen
    # falschen durchzulassen wäre schlimmer als gar keiner.
    if geheimnis:
        if not client["streuwert"] or not secrets.compare_digest(
                _streuwert(geheimnis), client["streuwert"]):
            raise OAuthFehler("invalid_client",
                              "Der Clientschlüssel stimmt nicht.")

    eintrag = dbm.zeile(db, "SELECT * FROM oauth_code WHERE streuwert = ?",
                        (_streuwert(code or ""),))
    if eintrag is None:
        raise OAuthFehler("invalid_grant", "Diesen Code gibt es nicht.")

    # Zweite Einlösung: der Code wurde mitgelesen. Dann sind auch die
    # Token aus diesem Vorgang nicht mehr vertrauenswürdig — der
    # Standard verlangt genau das, und es ist die einzige Stelle, an
    # der ein Diebstahl überhaupt auffällt.
    if eintrag["eingeloest"]:
        db.execute("""UPDATE mcp_token SET aktiv = 0
                       WHERE benutzer_id = ? AND name LIKE ?""",
                   (eintrag["benutzer_id"], f"{client['name']} (OAuth)%"))
        db.execute("DELETE FROM oauth_code WHERE id = ?", (eintrag["id"],))
        raise OAuthFehler("invalid_grant",
                          "Dieser Code wurde schon eingelöst. Die damit "
                          "ausgegebenen Zugänge sind zurückgenommen.")
    if _abgelaufen(eintrag["ablauf"]):
        db.execute("DELETE FROM oauth_code WHERE id = ?", (eintrag["id"],))
        raise OAuthFehler("invalid_grant", "Der Code ist abgelaufen.")
    if eintrag["client_id"] != client_id:
        raise OAuthFehler("invalid_grant",
                          "Der Code gehört zu einem anderen Konnektor.")
    if rueckadresse and rueckadresse != eintrag["rueckadresse"]:
        raise OAuthFehler("invalid_grant", "Die Rückadresse stimmt nicht.")
    if not _pkce_passt(pruefer, eintrag["pruefwert"]):
        raise OAuthFehler("invalid_grant", "Der PKCE-Nachweis stimmt nicht.")

    db.execute("UPDATE oauth_code SET eingeloest = 1 WHERE id = ?",
               (eintrag["id"],))
    merkmal = zugang.token_anlegen(
        db, eintrag["benutzer_id"],
        f"{client['name']} (OAuth) {_jetzt().date().isoformat()}")
    return {"access_token": merkmal["token"], "token_type": "Bearer",
            "scope": "vokabeln"}


def aufraeumen(db: sqlite3.Connection) -> int:
    """Abgelaufene Vorgänge und Codes wegwerfen.

    Eingelöste Codes bleiben bis zum Ablauf liegen, nicht länger: nur
    solange kann eine zweite Einlösung überhaupt auffallen.
    """
    jetzt = _jetzt().isoformat()
    a = db.execute("DELETE FROM oauth_vorgang WHERE ablauf < ?", (jetzt,))
    b = db.execute("DELETE FROM oauth_code WHERE ablauf < ?", (jetzt,))
    return (a.rowcount or 0) + (b.rowcount or 0)
