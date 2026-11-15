"""Zugangsmerkmale und Berechtigungen.

Zwei Dinge, die zusammengehören, sobald nicht mehr nur die Familie im
Heimnetz zugreift:

**Wer ist das?** Über die MCP-Schnittstelle meldet sich ein Programm, kein
Mensch. Jede Person bekommt darum ein eigenes Token, an ihr Profil gebunden.
Ein gemeinsames Geheimnis könnte man weder zuordnen noch einzeln entziehen.

**Was darf die Person?** Dass die Oberfläche nur die eigenen Sammlungen
anzeigt, ist keine Absicherung — die Schnittstelle muss es durchsetzen.
Solange nur die Familie im Heimnetz zugriff, war das verschmerzbar. Sobald
Eingeladene hereinkommen, ist es das nicht mehr.
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3

import datenbank as dbm

VORSATZ = "vok_"          # damit man das Token in einer Zwischenablage erkennt


def _streuwert(geheimnis: str) -> str:
    return hashlib.sha256(geheimnis.encode()).hexdigest()


# ------------------------------------------------------------ Token

def token_anlegen(db: sqlite3.Connection, benutzer_id: int, name: str) -> dict:
    """Legt ein Token an und gibt es EINMAL im Klartext zurück."""
    geheimnis = VORSATZ + secrets.token_urlsafe(32)
    cur = db.execute("""INSERT INTO mcp_token
                          (benutzer_id, name, streuwert, anfang)
                        VALUES (?, ?, ?, ?)""",
                     (benutzer_id, name.strip() or "ohne Namen",
                      _streuwert(geheimnis), geheimnis[:len(VORSATZ) + 6]))
    eintrag = dbm.zeile(db, "SELECT * FROM mcp_token WHERE id = ?", (cur.lastrowid,))
    eintrag.pop("streuwert", None)
    return {**eintrag, "token": geheimnis,
            "hinweis": "Das Token wird nur dieses eine Mal angezeigt. "
                       "Es steht nirgends gespeichert, nur sein Streuwert."}


def token_auflisten(db: sqlite3.Connection, benutzer_id: int) -> list[dict]:
    reihe = dbm.zeilen(db, """SELECT id, benutzer_id, name, anfang, angelegt,
                                     zuletzt_benutzt, aktiv
                                FROM mcp_token WHERE benutzer_id = ?
                                ORDER BY angelegt DESC""", (benutzer_id,))
    return reihe


def token_zuruecknehmen(db: sqlite3.Connection, token_id: int) -> None:
    db.execute("UPDATE mcp_token SET aktiv = 0 WHERE id = ?", (token_id,))


def person_zu_token(db: sqlite3.Connection, geheimnis: str) -> dict | None:
    """Welche Person gehört zu diesem Token? None heißt: keine."""
    if not geheimnis:
        return None
    eintrag = dbm.zeile(db, """SELECT * FROM mcp_token
                                WHERE streuwert = ? AND aktiv = 1""",
                        (_streuwert(geheimnis),))
    if eintrag is None:
        return None
    db.execute("UPDATE mcp_token SET zuletzt_benutzt = datetime('now') WHERE id = ?",
               (eintrag["id"],))
    person = dbm.zeile(db, "SELECT * FROM benutzer WHERE id = ?",
                       (eintrag["benutzer_id"],))
    if person is None:
        return None
    return {"benutzer": person, "token_id": eintrag["id"],
            "token_name": eintrag["name"]}


def mcp_eingeschaltet(db: sqlite3.Connection) -> bool:
    """Die Schnittstelle schaltet sich selbst frei, sobald es ein Token gibt.
    Kein Token heißt: niemand kann hinein, auch nicht versehentlich."""
    return bool(dbm.wert(db, "SELECT 1 FROM mcp_token WHERE aktiv = 1 LIMIT 1"))


# ------------------------------------------------------- Berechtigungen

class NichtErlaubt(PermissionError):
    """Die Person darf das nicht. Der Text geht an sie zurück."""


def verwalter_pruefen(person: dict) -> None:
    """Nur Verwalter dürfen Sprachprofile ändern — das wirkt auf den ganzen
    Bestand, auch auf fremde Sammlungen."""
    if not person.get("verwalter"):
        raise NichtErlaubt(
            "Sprachprofile zu ändern wirkt auf alle Sammlungen dieser Sprache, "
            "auch auf fremde. Das dürfen nur Verwalter. Bitte die Besitzerin "
            "des Trainers fragen.")


def darf_sammlung(db: sqlite3.Connection, benutzer_id: int, sammlung_id: int,
                  schreiben: bool = False) -> bool:
    s = dbm.zeile(db, "SELECT besitzer_id FROM sammlung WHERE id = ?",
                  (sammlung_id,))
    if s is None:
        return False
    if s["besitzer_id"] == benutzer_id:
        return True
    recht = dbm.wert(db, """SELECT recht FROM freigabe
                             WHERE sammlung_id = ? AND benutzer_id = ?""",
                     (sammlung_id, benutzer_id))
    if recht is None:
        return False
    return recht == "schreiben" if schreiben else True


def beschreibbare_sammlungen(db: sqlite3.Connection,
                             benutzer_id: int) -> list[int]:
    """Sammlungen, in die diese Person eintragen darf.

    Eigene und fremde mit Schreibrecht. Gebraucht wird das dort, wo es
    nicht um Sichtbarkeit geht, sondern um die Frage »kann ich das
    erledigen?« — etwa bei den Wortwünschen: wer in Max' Sammlung
    schreiben darf, kann auch Max' Wünsche erfüllen, und soll sie
    darum zu sehen bekommen.
    """
    return [z["id"] for z in dbm.zeilen(db, """
        SELECT s.id FROM sammlung s WHERE s.besitzer_id = ?
        UNION
        SELECT f.sammlung_id FROM freigabe f
         WHERE f.benutzer_id = ? AND f.recht = 'schreiben'""",
        (benutzer_id, benutzer_id))]


def sammlung_pruefen(db: sqlite3.Connection, benutzer_id: int, sammlung_id: int,
                     schreiben: bool = False) -> None:
    if not darf_sammlung(db, benutzer_id, sammlung_id, schreiben):
        raise NichtErlaubt(
            f"Sammlung {sammlung_id} gehört dir nicht und ist dir nicht "
            f"{'zum Schreiben ' if schreiben else ''}freigegeben.")


def lexem_pruefen(db: sqlite3.Connection, benutzer_id: int, lexem_id: int,
                  schreiben: bool = False) -> None:
    sammlung_id = dbm.wert(db, "SELECT sammlung_id FROM lexem WHERE id = ?",
                           (lexem_id,))
    if sammlung_id is None:
        raise NichtErlaubt(f"Lexem {lexem_id} gibt es nicht")
    sammlung_pruefen(db, benutzer_id, sammlung_id, schreiben)


def form_pruefen(db: sqlite3.Connection, benutzer_id: int, form_id: int,
                 schreiben: bool = True) -> None:
    lexem_id = dbm.wert(db, "SELECT lexem_id FROM form WHERE id = ?", (form_id,))
    if lexem_id is None:
        raise NichtErlaubt(f"Form {form_id} gibt es nicht")
    lexem_pruefen(db, benutzer_id, lexem_id, schreiben)
