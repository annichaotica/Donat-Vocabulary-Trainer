import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

import pytest
import sprachen
from pruefung import pruefen, varianten, abstand, ohne_diakritika

FR = sprachen.profil("fr")
ES = sprachen.profil("es")
EN = sprachen.profil("en")
EL = sprachen.profil("el")
DE = sprachen.profil("de")


def u(eingabe, erwartet, profil=FR, **kw):
    return pruefen(eingabe, erwartet if isinstance(erwartet, list) else [erwartet],
                   profil, **kw)


# ---------------------------------------------------- mehrere gültige Antworten

@pytest.mark.parametrize("eingabe", ["gehen", "laufen", "zu Fuß gehen", "  GEHEN  "])
def test_jede_hinterlegte_uebersetzung_gilt(eingabe):
    assert u(eingabe, ["gehen", "laufen", "zu Fuß gehen"], DE).urteil == "richtig"


def test_falsche_uebersetzung_bleibt_falsch():
    assert u("fliegen", ["gehen", "laufen"], DE).urteil == "falsch"


def test_leere_eingabe():
    assert u("", ["gehen"], DE).urteil == "falsch"
    assert u("   ", ["gehen"], DE).urteil == "falsch"


# ------------------------------------------------------------------ Diakritika

def test_fehlender_akzent_ist_fast_richtig_nicht_falsch():
    urteil = u("eleve", "élève")
    assert urteil.urteil == "fast"
    assert "diakritika" in urteil.abweichungen
    assert "élève" in urteil.hinweis


def test_richtiger_akzent_ist_richtig():
    assert u("élève", "élève").urteil == "richtig"


def test_akzent_streng_zaehlt_als_falsch():
    streng = dict(FR)
    streng["pruefung"] = dict(FR["pruefung"], diakritika="streng")
    assert u("eleve", "élève", streng).urteil == "falsch"


def test_akzent_ignorieren_zaehlt_als_richtig():
    locker = dict(FR)
    locker["pruefung"] = dict(FR["pruefung"], diakritika="ignorieren")
    assert u("eleve", "élève", locker).urteil == "richtig"


def test_spanische_tilde():
    assert u("anos", "años", ES).urteil == "fast"
    assert u("años", "años", ES).urteil == "richtig"


# --------------------------------------------------------------- Tippfehler

def test_tippfehler_bei_langem_wort_ist_fast_richtig():
    urteil = u("travailer", "travailler")
    assert urteil.urteil == "fast"
    assert urteil.abweichungen == ["tippfehler"]


def test_kurzes_wort_ohne_toleranz():
    # "pan" und "pen" sind zwei Wörter, kein Vertipper.
    assert u("pan", "pen", EN).urteil == "falsch"


def test_zu_viele_tippfehler_sind_falsch():
    assert u("travxilxer", "travailler").urteil == "falsch"   # 2 von 10 Zeichen


def test_abstand_bricht_bei_grenze_ab():
    assert abstand("abc", "abc") == 0
    assert abstand("abc", "abd") == 1
    assert abstand("kurz", "vielvielanders", grenze=2) > 2


# -------------------------------------------------------------------- Artikel

def test_artikel_darf_fehlen():
    assert u("table", "la table").urteil == "richtig"


def test_artikel_darf_dastehen():
    assert u("la table", "la table").urteil == "richtig"


def test_falscher_artikel_ist_falsch_und_wird_benannt():
    urteil = u("le table", "la table")
    assert urteil.urteil == "falsch"
    assert "artikel_falsch" in urteil.abweichungen
    assert "la" in urteil.hinweis


def test_elidierter_artikel():
    assert u("école", "l'école").urteil == "richtig"
    assert u("l'école", "l'école").urteil == "richtig"


def test_artikel_im_englischen_ist_gleichgueltig():
    assert u("the table", "table", EN).urteil == "richtig"
    assert u("table", "the table", EN).urteil == "richtig"


def test_verlangter_artikel_fehlt():
    streng = dict(DE)
    streng["artikel"] = dict(DE["artikel"], regel="verlangt")
    urteil = u("Tisch", "der Tisch", streng)
    assert urteil.urteil == "fast"
    assert "artikel_fehlt" in urteil.abweichungen


# ------------------------------------------------------------------ Varianten

def test_klammerteil_ist_optional():
    assert u("waschen", "(sich) waschen", DE).urteil == "richtig"
    assert u("sich waschen", "(sich) waschen", DE).urteil == "richtig"


def test_mehrere_klammern():
    gefunden = set(varianten("(sich) etwas (gut) merken"))
    assert "sich etwas gut merken" in gefunden
    assert "etwas merken" in gefunden
    assert "sich etwas merken" in gefunden


# -------------------------------------------------------------- Verwechslung

VERWECHSLUNGEN = [("vas", "die 2. Person Singular Présent"),
                  ("va", "die 3. Person Singular Présent"),
                  ("allons", "die 1. Person Plural Présent")]


def test_andere_form_desselben_wortes_ist_keine_tippfehlertoleranz():
    # "vas" liegt einen Buchstaben von "vais" entfernt. Als Tippfehler
    # durchgewinkt wäre das genau der Fehler, den der Trainer aufdecken soll.
    urteil = u("vas", "vais", verwechslungen=VERWECHSLUNGEN)
    assert urteil.urteil == "falsch"
    assert urteil.abweichungen == ["verwechslung"]
    assert "2. Person Singular" in urteil.hinweis


def test_richtige_form_bleibt_richtig_trotz_verwechslungsliste():
    assert u("vais", "vais", verwechslungen=VERWECHSLUNGEN).urteil == "richtig"


def test_verwechslung_schlaegt_nicht_auf_fremde_eingabe_durch():
    urteil = u("xyz", "vais", verwechslungen=VERWECHSLUNGEN)
    assert urteil.urteil == "falsch"
    assert urteil.abweichungen == []


# ------------------------------------------------------------------ Griechisch

def test_schluss_sigma_gilt_als_dasselbe_zeichen():
    assert u("άνθρωποσ", "άνθρωπος", EL).urteil == "richtig"


def test_fehlender_tonos_ist_fast_richtig():
    urteil = u("ανθρωπος", "άνθρωπος", EL)
    assert urteil.urteil == "fast"
    assert "diakritika" in urteil.abweichungen


def test_rueckmeldung_zeigt_das_wort_richtig_geschrieben():
    # Die Unicode-Kleinschreibung wandelt ς in σ um. Was dem Lernenden
    # angezeigt wird, muss die Originalschreibung sein.
    urteil = u("ανθρωπος", "άνθρωπος", EL)
    assert "άνθρωπος" in urteil.hinweis
    assert "άνθρωποσ" not in urteil.hinweis


def test_griechischer_artikel():
    assert u("σπίτι", "το σπίτι", EL).urteil == "richtig"
    assert u("η σπίτι", "το σπίτι", EL).urteil == "falsch"


def test_ohne_diakritika_wirkt_auch_griechisch():
    assert ohne_diakritika("άνθρωπος") == "ανθρωπος"
    assert ohne_diakritika("élève") == "eleve"


# --------------------------------------------------------------------- Deutsch

def test_scharfes_s_und_umlautumschrift():
    assert u("Fuss", "Fuß", DE).urteil == "richtig"
    assert u("Fuß", "Fuß", DE).urteil == "richtig"


def test_umlaut_ohne_punkte_ist_fast_richtig():
    assert u("schon", "schön", DE).urteil == "fast"


def test_umschrift_mit_e_gilt():
    assert u("schoen", "schön", DE).urteil in ("richtig", "fast")
