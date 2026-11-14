"""Wer ist das, der da anfragt?

Im **Heimnetz** niemand Bestimmtes: man wählt sein Profil aus einer Liste,
ohne Passwort. Das ist Absicht und reicht dort völlig.

Von **außen** steht Cloudflare Access davor. Es prüft die Mailadresse, bevor
die Anfrage überhaupt hier ankommt, und hängt sie als Kopfzeile an. Die
nehmen wir als Identität — dann braucht der Trainer keine eigenen Passwörter,
keine Registrierung, kein Zurücksetzen vergessener Kennwörter. Eingeladene
Leute bekommen ein eigenes Profil und sehen nur, was ihnen gehört oder was
ihnen freigegeben wurde.

**Zur Vertrauenswürdigkeit der Kopfzeile, ehrlich gesagt:** Cloudflare
überschreibt alle `Cf-Access-*`-Kopfzeilen, die ein Client selbst mitschickt
— von außen ist sie also belastbar. Im Heimnetz ließe sie sich fälschen; dort
kann man aber ohnehin jedes Profil anklicken, es wird also nichts schlechter.
Wer das enger haben will, muss zusätzlich das mitgelieferte Wertpapier
(`Cf-Access-Jwt-Assertion`) gegen die Schlüssel des Teams prüfen — dafür
bräuchte es eine Kryptobibliothek, die dieses Projekt bisher nicht hat.
"""

from __future__ import annotations

import os
import re
import sqlite3

import datenbank as dbm

KOPFZEILE = "cf-access-authenticated-user-email"
# Ohne gesetzte Teamkennung wird die Kopfzeile gar nicht erst angesehen.
TEAM = os.environ.get("VOKABEL_ACCESS_TEAM", "").strip()

_MAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,}$")


def mail_aus_anfrage(kopfzeilen) -> str | None:
    """Die geprüfte Mailadresse, falls die Anfrage durch Access kam."""
    if not TEAM:
        return None
    wert = (kopfzeilen.get(KOPFZEILE) or "").strip().lower()
    return wert if _MAIL.match(wert) else None


def _name_aus_mail(mail: str) -> str:
    vorn = mail.split("@", 1)[0]
    teile = [t for t in re.split(r"[._\-+]", vorn) if t]
    return " ".join(t.capitalize() for t in teile) or vorn


def profil_fuer_mail(db: sqlite3.Connection, mail: str,
                     anlegen: bool = True) -> dict | None:
    """Findet das Profil zu einer Mailadresse — oder legt eines an.

    Selbsttätiges Anlegen ist hier richtig: durch Access kommt nur, wer in
    der Zugriffsregel steht. Wer also bis hierher gelangt, ist bereits
    eingeladen worden; ihn dann noch einmal um eine Anmeldung zu bitten,
    wäre eine Hürde ohne Gewinn.
    """
    person = dbm.zeile(db, "SELECT * FROM benutzer WHERE email = ?", (mail,))
    if person:
        return person
    if not anlegen:
        return None

    # Ein Profil ohne Mailadresse, das zufällig so heißt, wird NICHT
    # übernommen — sonst könnte eine Einladung an »anna@...« das
    # Familienprofil »Anna« an sich ziehen.
    grundname = _name_aus_mail(mail)
    name, zaehler = grundname, 1
    while dbm.wert(db, "SELECT 1 FROM benutzer WHERE name = ?", (name,)):
        zaehler += 1
        name = f"{grundname} {zaehler}"

    farben = ["#6b7fd7", "#4f9e74", "#c27a3e", "#9b5fa8", "#3e8fa3", "#b05b6a"]
    anzahl = dbm.wert(db, "SELECT COUNT(*) FROM benutzer") or 0
    # Die erste Person überhaupt wird Verwalterin — egal, ob sie über die
    # Oberfläche oder über Access entsteht. Sonst stünde ein Bestand, der
    # ausschließlich von außen angelegt wurde, ohne jemanden da, der
    # Sprachprofile pflegen darf.
    cur = db.execute("""INSERT INTO benutzer (name, email, farbe, verwalter)
                        VALUES (?, ?, ?, ?)""",
                     (name, mail, farben[anzahl % len(farben)], int(anzahl == 0)))
    return dbm.zeile(db, "SELECT * FROM benutzer WHERE id = ?", (cur.lastrowid,))


def wer_bin_ich(db: sqlite3.Connection, kopfzeilen) -> dict:
    """Antwort für die Oberfläche.

    gebunden = True heißt: die Identität steht fest, der Profilwähler
    entfällt. gebunden = False heißt Heimnetz — bitte auswählen.
    """
    mail = mail_aus_anfrage(kopfzeilen)
    if not mail:
        return {"gebunden": False, "benutzer": None, "email": None,
                "hinweis": "Im Heimnetz: bitte Profil wählen."}
    person = profil_fuer_mail(db, mail)
    return {
        "gebunden": True,
        "email": mail,
        "benutzer": {"id": person["id"], "name": person["name"],
                     "farbe": person["farbe"]},
        "hinweis": None,
    }
