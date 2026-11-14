"""Datenmodelle der Schnittstelle (Pydantic).

Die geschachtelten Modelle sind mit Absicht so gebaut, dass ein ganzes Wort
mit allen Formen und Bedeutungen in einem Aufruf hereinkommt. Genau so wird
der MCP-Server später Vokabeln anlegen: ein Verb mit vollständigem Paradigma
in einem Zug, nicht in vierzig Einzelaufrufen.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

import merkmale as mk

Quelle = Literal["manuell", "generiert", "wiktionary", "ki", "import"]


class BenutzerAnlegen(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    farbe: str = "#6b7fd7"


class BenutzerAendern(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    farbe: str | None = None
    wunschretention: float | None = Field(default=None, ge=0.70, le=0.99)
    neu_je_sitzung: int | None = Field(default=None, ge=0, le=500)


class LegasthenieEinstellungen(BaseModel):
    """Legastheniemodus. Jeder Posten einzeln schaltbar — Legasthenie sieht
    bei jedem anders aus, und eine Voreinstellung, die man nicht ändern kann,
    ist keine Hilfe."""
    aktiv: bool | None = None
    # Darstellung
    zeichenabstand: float | None = Field(default=None, ge=0.0, le=0.5)
    wortabstand: float | None = Field(default=None, ge=0.0, le=1.0)
    zeilenhoehe: float | None = Field(default=None, ge=1.0, le=3.0)
    schriftgroesse: float | None = Field(default=None, ge=0.8, le=2.5)
    schriftart: Literal["grotesk", "opendyslexic", "serifenlos"] | None = None
    hintergrund: Literal["creme", "hell", "dunkel"] | None = None
    silben_faerben: bool | None = None
    stamm_hervorheben: bool | None = None
    # Lernen
    vorlesen_zuerst: bool | None = None
    erkennen_vor_schreiben: bool | None = None
    bausteine: bool | None = None
    maske_stufe: int | None = Field(default=None, ge=0, le=3)
    mehr_wiederholungen: bool | None = None
    weniger_neues: bool | None = None
    fehler_benennen: bool | None = None
    keine_zeitmessung: bool | None = None


class SammlungAnlegen(BaseModel):
    besitzer_id: int
    name: str = Field(min_length=1, max_length=120)
    sprache: str = Field(min_length=2, max_length=8)
    grundsprache: str = "de"
    beschreibung: str | None = None


class SammlungAendern(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    beschreibung: str | None = None


class SammlungEinstellungen(BaseModel):
    """Welche Formgruppen und Aufgabentypen diese Sammlung abfragt.

    Das ist die Antwort auf "180 Aufgaben pro französischem Verb": man wählt
    die Zeiten, die gerade dran sind, und schaltet später weitere zu. Der
    Lernstand abgewählter Aufgaben bleibt erhalten.
    """
    formgruppen: list[str] | None = None
    typen: list[str] | None = None
    ungeprueft_abfragen: bool | None = None


class LektionAnlegen(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    # Die Nummer im Lehrwerk. Sie ist der Schlüssel, unter dem ein Import
    # seine Lektion wiederfindet — Namen ändern sich, Nummern nicht.
    nr: int | None = Field(default=None, ge=0, le=9999)
    beschreibung: str | None = None
    reihenfolge: int = 0


class SammelimportEingabe(BaseModel):
    """Viele Wörter in einem Aufruf.

    `nur_pruefen` schreibt nichts und liefert trotzdem alle Befunde — man
    sieht also vorher, was herauskäme. Wiederholte Läufe bessern nach,
    statt zu verdoppeln; geprüfte Formen werden nie überschrieben.
    """
    eintraege: list[dict[str, Any]] = Field(min_length=1, max_length=2000)
    nur_pruefen: bool = False
    quelle: Quelle = "ki"


class FreigabeEingabe(BaseModel):
    """Was soll freigegeben werden?

    Mindestens eines von form_ids, lexem_ids, lektion_nr muss dastehen.
    Eine ganze Sammlung auf einmal freizugeben wäre keine Prüfung.
    `ausser` ist der Weg für die abgewählten Zellen.
    """
    form_ids: list[int] | None = None
    lexem_ids: list[int] | None = None
    lektion_nr: int | None = None
    ausser: list[int] | None = None
    geprueft: bool = True


class UebungEingabe(BaseModel):
    """Ein Übungssatz oder ein Text.

    Der ganze Eintrag darf als `zielsprache`/`grundsprache` kommen; bei
    mehreren Sätzen ist eine ausdrückliche Liste `abschnitte` genauer,
    weil sich die Zuordnung dann nicht erraten muss.
    """
    typ: Literal["satz", "text", "dialog", "brief", "zeitungsstil"] = "satz"
    titel: str | None = None
    zielsprache: str | None = None
    grundsprache: str | None = None
    alternativen_zielsprache: list[str] = Field(default_factory=list)
    alternativen_grundsprache: list[str] = Field(default_factory=list)
    abschnitte: list[dict[str, Any]] | None = None
    # ["hin", "rueck"] oder in Sprachpaaren: ["el-de", "de-el"]
    richtungen: list[str] | None = None
    lektion_nr: int | None = None
    lektion_titel: str | None = None
    niveau: str | None = None
    reihenfolge: int = 0
    kennung: str | None = None
    notiz: str | None = None
    quelle: dict[str, Any] | None = None
    geprueft: bool = False


class UebungAendern(BaseModel):
    """Teiländerung. Was nicht genannt ist, bleibt wie es war.

    Ändert sich der Inhalt, fällt die Übung auf ungeprüft zurück — wie
    eine geänderte Form.
    """
    typ: Literal["satz", "text", "dialog", "brief", "zeitungsstil"] | None = None
    titel: str | None = None
    zielsprache: str | None = None
    grundsprache: str | None = None
    alternativen_zielsprache: list[str] | None = None
    alternativen_grundsprache: list[str] | None = None
    abschnitte: list[dict[str, Any]] | None = None
    richtungen: list[str] | None = None
    lektion_nr: int | None = None
    niveau: str | None = None
    reihenfolge: int | None = None
    kennung: str | None = None
    notiz: str | None = None
    quelle: dict[str, Any] | None = None
    geprueft: bool | None = None


class UebungenImportEingabe(BaseModel):
    eintraege: list[dict[str, Any]] = Field(min_length=1, max_length=1000)
    nur_pruefen: bool = False


class UebungPruefenEingabe(BaseModel):
    benutzer_id: int
    textaufgabe_id: int
    antwort: str = ""


class UebungBewertenEingabe(BaseModel):
    """Ohne `bewertung` wird sie aus dem Urteil abgeleitet.

    Bei langen Texten schickt die Oberfläche das selbst eingeschätzte
    Urteil — dort stimmt eine freie Übersetzung selten wörtlich, und ein
    Trainer, der sie deshalb als falsch wertet, erzieht zum Auswendiglernen
    der Musterlösung.
    """
    benutzer_id: int
    textaufgabe_id: int
    urteil: Literal["richtig", "fast", "falsch", "aufgedeckt"] | None = None
    bewertung: int | None = Field(default=None, ge=1, le=4)
    antwort: str | None = None
    dauer_ms: int | None = Field(default=None, ge=0)
    versuche: int = Field(default=1, ge=1, le=10)
    aufgedeckt: bool = False
    rueckmeldung: str | None = None


class TextPruefenEingabe(BaseModel):
    """Deckung eines Textes gegen den Bestand."""
    text: str = Field(min_length=1, max_length=20000)
    bis_lektion: int | None = None


class UebungAntwort(BaseModel):
    antwort: str = ""


class FormEingabe(BaseModel):
    text: str = Field(min_length=1, max_length=200)
    merkmale: dict[str, Any] = Field(default_factory=dict)
    ist_grundform: bool = False
    # Nebenformen derselben Zelle: μιλάω neben μιλώ. Beide gelten als
    # richtig; gefragt wird die Hauptform.
    varianten: list[str] = Field(default_factory=list)
    ist_variante: bool = False
    aussprache: str | None = None
    quelle: Quelle = "manuell"
    geprueft: bool = True
    notiz: str | None = None

    @field_validator("merkmale")
    @classmethod
    def merkmale_pruefen(cls, wert: dict) -> dict:
        try:
            return mk.pruefen(wert)
        except mk.MerkmalFehler as fehler:
            raise ValueError(str(fehler)) from fehler


class UebersetzungEingabe(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    sprache: str | None = None          # fehlt sie, gilt die Grundsprache
    ist_haupt: bool = False
    quelle: Quelle = "manuell"
    geprueft: bool = True


class BedeutungEingabe(BaseModel):
    uebersetzungen: list[UebersetzungEingabe] = Field(min_length=1)
    kontext: str | None = Field(default=None, max_length=120)
    reihenfolge: int = 0
    notiz: str | None = None

    @field_validator("uebersetzungen", mode="before")
    @classmethod
    def _kurzform(cls, wert):
        """["schreiben", "reden"] statt [{"text": "schreiben"}, …].

        Der Sammelimport nahm die Kurzform von Anfang an, und so steht sie
        auch in jeder Werkzeugbeschreibung und auf dem Festlegungsblatt.
        Dass sie beim einzelnen Aufruf fehlschlug, war ein Bruch in der
        Schnittstelle, kein Vorsatz.
        """
        if not isinstance(wert, list):
            return wert
        return [{"text": u} if isinstance(u, str) else u for u in wert]


class BeispielEingabe(BaseModel):
    satz: str = Field(min_length=1)
    uebersetzung: str | None = None
    quelle: Quelle = "manuell"


class LexemEingabe(BaseModel):
    """Ein vollständiges Wort in einem Aufruf."""
    sammlung_id: int
    lemma: str = Field(min_length=1, max_length=200)
    wortart: str = "sonstiges"
    merkmale: dict[str, Any] = Field(default_factory=dict)
    lektion_id: int | None = None
    notiz: str | None = None
    formen: list[FormEingabe] = Field(default_factory=list)
    bedeutungen: list[BedeutungEingabe] = Field(default_factory=list)
    beispiele: list[BeispielEingabe] = Field(default_factory=list)
    # Lektion und Lernreihenfolge
    lektion_nr: int | None = Field(default=None, ge=0, le=9999)
    reihenfolge: int = 0
    kennung: str | None = Field(default=None, max_length=120)
    # Merkmalsmuster für Zellen, die es bei diesem Wort nicht gibt.
    # [{}] bedeutet: gar keine Formen (unveränderliche Wörter).
    luecken: list[dict[str, Any]] = Field(default_factory=list)
    # Stamm je Formgruppe, von Hand gesetzt; "*" gilt für alle.
    staemme: dict[str, str] = Field(default_factory=dict)

    @field_validator("luecken")
    @classmethod
    def luecken_pruefen(cls, wert: list) -> list:
        try:
            return mk.luecken_pruefen(wert)
        except mk.MerkmalFehler as fehler:
            raise ValueError(str(fehler)) from fehler

    @field_validator("wortart")
    @classmethod
    def wortart_pruefen(cls, wert: str) -> str:
        if wert not in mk.WORTARTEN:
            erlaubt = ", ".join(mk.WORTARTEN)
            raise ValueError(f"Unbekannte Wortart {wert!r}. Erlaubt: {erlaubt}")
        return wert


class LexemAendern(BaseModel):
    lemma: str | None = Field(default=None, min_length=1, max_length=200)
    wortart: str | None = None
    merkmale: dict[str, Any] | None = None
    lektion_id: int | None = None
    notiz: str | None = None
    reihenfolge: int | None = None
    kennung: str | None = None
    # Angegeben, ersetzt es ALLE Bedeutungen. Eine Teiländerung einzelner
    # Übersetzungen ließe sich nicht ausdrücken — welche gemeint wäre,
    # stünde nirgends.
    bedeutungen: list[BedeutungEingabe] | None = None


class FormAendern(BaseModel):
    """Teiländerung einer Form. Was nicht genannt ist, bleibt."""
    text: str | None = Field(default=None, min_length=1, max_length=200)
    merkmale: dict[str, Any] | None = None
    ist_grundform: bool | None = None
    ist_variante: bool | None = None
    aussprache: str | None = None
    notiz: str | None = None
    geprueft: bool | None = None


class PruefenEingabe(BaseModel):
    benutzer_id: int
    aufgabe_id: int
    # Text bei Eingabefeldern, Objekt bei "Form bestimmen"
    antwort: str | dict[str, Any]
    # Zeit bis zum ERSTEN Tastendruck. Das ist das Abrufmaß — die Gesamtzeit
    # misst zu großen Teilen Tippgeschwindigkeit und Wortlänge mit.
    denkzeit_ms: int | None = Field(default=None, ge=0)
    versuche: int = Field(default=1, ge=1, le=10)
    aufgedeckt: bool = False


class BewertenEingabe(BaseModel):
    """Ohne `bewertung` wird sie aus den Antwortsignalen abgeleitet — das ist
    der Normalfall. Eine mitgegebene Bewertung gilt als Eingriff von Hand."""
    benutzer_id: int
    aufgabe_id: int
    bewertung: int | None = Field(default=None, ge=1, le=4)
    antwort: str | None = None
    urteil: str | None = None
    fehlerart: str | None = None
    dauer_ms: int | None = Field(default=None, ge=0)
    denkzeit_ms: int | None = Field(default=None, ge=0)
    versuche: int = Field(default=1, ge=1, le=10)
    aufgedeckt: bool = False


class EingriffEingabe(BaseModel):
    benutzer_id: int
    aufgabe_id: int
    datum: str | None = None


class SpracheAnlegen(BaseModel):
    """Eine neue Sprache einrichten.

    Gedacht für den Agenten am MCP: er kann eine Sprache anlegen und ihr
    Profil gleich mitgeben, ohne dass jemand Code ändert.
    """
    code: str = Field(min_length=2, max_length=8, pattern=r"^[a-z]{2,3}(-[A-Za-z]+)?$")
    name: str = Field(min_length=1, max_length=60)
    schrift: str = "latein"
    stimme: str | None = None
    profil: dict[str, Any] = Field(default_factory=dict)


class SprachprofilSetzen(BaseModel):
    """Profilteile, die das im Code hinterlegte Profil überschreiben.

    Nur was hier steht, wird überschrieben — der Rest bleibt. Formgruppen
    werden je Wortart gemischt: gleiche Kennung ersetzt, neue kommen hinzu.
    So lässt sich dem Französischen eine Zeit anfügen, ohne alle fünfzehn
    noch einmal hinzuschreiben.
    """
    profil: dict[str, Any]
    neu_rechnen: bool = True        # Aufgaben der betroffenen Sammlungen neu


class EintragPruefen(BaseModel):
    lexem_id: int | None = None
    sammlung_id: int | None = None
    nur_mangelhafte: bool = True


class LernzielAnlegen(BaseModel):
    """Ein Ausschnitt des Bestands mit einem Termin.

    Der Ausschnitt ist ausdrücklich nicht an eine Lektion gebunden: alle
    Angaben in `umfang` sind Listen, alle freigestellt, und was fehlt,
    schränkt nicht ein. "Alle Verben im Passé composé über alle Lektionen"
    ist damit ein genauso gültiges Ziel wie "Lektion 3".
    """
    benutzer_id: int
    name: str = Field(min_length=1, max_length=120)
    umfang: dict[str, Any] = Field(default_factory=dict)
    termin: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    ziel: Literal["reif", "einmal_richtig"] = "reif"
    notiz: str | None = None

    @field_validator("termin")
    @classmethod
    def termin_pruefen(cls, wert: str | None) -> str | None:
        if wert is not None:
            import datetime
            datetime.date.fromisoformat(wert)
        return wert


class LernzielAendern(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    umfang: dict[str, Any] | None = None
    termin: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")

    @field_validator("termin")
    @classmethod
    def termin_pruefen(cls, wert: str | None) -> str | None:
        # Das Muster allein lässt 2026-13-45 durch. Ein solches Lernziel wäre
        # danach dauerhaft unbenutzbar: Fortschritt, Block und die Übersicht
        # würden daran scheitern.
        if wert is not None:
            import datetime
            datetime.date.fromisoformat(wert)
        return wert
    ziel: Literal["reif", "einmal_richtig"] | None = None
    aktiv: bool | None = None
    notiz: str | None = None


class ImportEingabe(BaseModel):
    """Import in zwei Schritten: erst Vorschau, dann Übernahme.

    Ein Import, der ungefragt 800 Zeilen in den Bestand kippt, ist schlimmer
    als keiner — darum sieht man vorher, was herauskäme, und kann die
    Spaltenzuordnung berichtigen.
    """
    text: str = Field(min_length=1, max_length=5_000_000)
    trenner: str | None = Field(default=None, max_length=4)
    # Spaltennummer -> Rolle: lemma, uebersetzung, wortart, lektion, notiz,
    # ignorieren. Fehlt sie, wird geraten.
    zuordnung: dict[str, str] | None = None
    hat_kopfzeile: bool | None = None
    doppelte: Literal["ueberspringen", "ergaenzen", "trotzdem"] = "ueberspringen"


class McpTokenAnlegen(BaseModel):
    """Ein Zugangsmerkmal für die MCP-Schnittstelle, gebunden an ein Profil.

    Je Person und je Gerät eines — dann lässt sich einzeln zurücknehmen,
    was abhandengekommen ist, ohne allen anderen den Zugang zu nehmen.
    """
    name: str = Field(min_length=1, max_length=80,
                      description="wofür, z.B. »Claude-App auf dem iPad«")
