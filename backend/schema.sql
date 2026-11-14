-- Vokabeltrainer, Datenbankschema.
-- Grundgedanke: ein Lexem hat FORMEN (mit Merkmalen beschrieben) und
-- BEDEUTUNGEN (mit beliebig vielen gültigen Übersetzungen). Abgefragt und
-- terminiert wird nicht das Lexem, sondern jede einzelne AUFGABE darüber.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_stand (
    version INTEGER NOT NULL
);

-- ---------------------------------------------------------------- Sprachen

CREATE TABLE IF NOT EXISTS sprache (
    code         TEXT PRIMARY KEY,              -- 'fr', 'es', 'en', 'el', 'de'
    name         TEXT NOT NULL,
    schrift      TEXT NOT NULL DEFAULT 'latein',
    stimme       TEXT,                          -- BCP47 für Sprachsynthese
    profil       TEXT NOT NULL DEFAULT '{}'     -- JSON, siehe sprachen.py
);

-- --------------------------------------------------------------- Benutzer

CREATE TABLE IF NOT EXISTS benutzer (
    id             INTEGER PRIMARY KEY,
    name           TEXT NOT NULL UNIQUE,
    -- Von Cloudflare Access geprüfte Mailadresse. Nur gesetzt bei Profilen,
    -- die von außen hereinkommen; im Heimnetz bleibt sie leer und man wählt
    -- sein Profil wie bisher aus der Liste.
    email          TEXT UNIQUE,
    farbe          TEXT NOT NULL DEFAULT '#6b7fd7',
    einstellungen  TEXT NOT NULL DEFAULT '{}',
    -- Darf Sprachprofile ändern und neue Sprachen einrichten. Das wirkt auf
    -- den ganzen Bestand, auch auf fremde Sammlungen — ein eingeladener Gast
    -- soll das nicht können. Die erste angelegte Person bekommt es.
    verwalter      INTEGER NOT NULL DEFAULT 0,
    angelegt       TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Zugangsmerkmale für die MCP-Schnittstelle, je Person eines.
--
-- Ein gemeinsames Geheimnis wäre hier falsch: man könnte nicht sagen, wer
-- etwas eingetragen hat, und man könnte es niemandem einzeln entziehen.
-- Gespeichert wird nur der Streuwert — das Geheimnis selbst sieht der Server
-- nach der Ausgabe nie wieder.
CREATE TABLE IF NOT EXISTS mcp_token (
    id              INTEGER PRIMARY KEY,
    benutzer_id     INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,           -- wofür, z.B. "Claude-App iPad"
    streuwert       TEXT NOT NULL UNIQUE,    -- sha256 des Geheimnisses
    anfang          TEXT NOT NULL,           -- erste Zeichen, zum Wiedererkennen
    angelegt        TEXT NOT NULL DEFAULT (datetime('now')),
    zuletzt_benutzt TEXT,
    aktiv           INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_mcp_token_benutzer ON mcp_token(benutzer_id);

-- --------------------------------------------------------------- Sammlungen

CREATE TABLE IF NOT EXISTS sammlung (
    id            INTEGER PRIMARY KEY,
    besitzer_id   INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    sprache       TEXT NOT NULL REFERENCES sprache(code),
    grundsprache  TEXT NOT NULL DEFAULT 'de' REFERENCES sprache(code),
    beschreibung  TEXT,
    -- JSON. Wichtigster Eintrag: "formgruppen" — welche Zeiten und Tabellen
    -- überhaupt abgefragt werden. Ohne diese Auswahl entstünden pro
    -- französischem Verb an die zweihundert Aufgaben.
    einstellungen TEXT NOT NULL DEFAULT '{}',
    angelegt      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sammlung_besitzer ON sammlung(besitzer_id);

-- Freigabe einer Sammlung an ein anderes Profil. Der Lernstand bleibt
-- trotzdem persönlich: er hängt an (aufgabe, benutzer), nicht an der Sammlung.
CREATE TABLE IF NOT EXISTS freigabe (
    sammlung_id  INTEGER NOT NULL REFERENCES sammlung(id) ON DELETE CASCADE,
    benutzer_id  INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    recht        TEXT NOT NULL CHECK (recht IN ('lesen', 'schreiben')),
    PRIMARY KEY (sammlung_id, benutzer_id)
);

CREATE TABLE IF NOT EXISTS lektion (
    id           INTEGER PRIMARY KEY,
    sammlung_id  INTEGER NOT NULL REFERENCES sammlung(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    reihenfolge  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_lektion_sammlung ON lektion(sammlung_id);

-- ------------------------------------------------------------------ Lexeme

CREATE TABLE IF NOT EXISTS lexem (
    id           INTEGER PRIMARY KEY,
    sammlung_id  INTEGER NOT NULL REFERENCES sammlung(id) ON DELETE CASCADE,
    lektion_id   INTEGER REFERENCES lektion(id) ON DELETE SET NULL,
    lemma        TEXT NOT NULL,
    wortart      TEXT NOT NULL,
    -- lexemfeste Merkmale, z.B. {"genus": "f"} beim Substantiv,
    -- {"klasse": "er", "hilfsverb": "etre"} beim französischen Verb
    merkmale     TEXT NOT NULL DEFAULT '{}',
    notiz        TEXT,
    angelegt     TEXT NOT NULL DEFAULT (datetime('now')),
    geaendert    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_lexem_sammlung ON lexem(sammlung_id);
CREATE INDEX IF NOT EXISTS idx_lexem_lektion  ON lexem(lektion_id);
CREATE INDEX IF NOT EXISTS idx_lexem_lemma    ON lexem(sammlung_id, lemma);

-- Eine Wortform mit ihrem Merkmalsbündel.
-- quelle/geprueft: generierte oder von der KI ergänzte Formen werden erst
-- abgefragt, wenn sie bestätigt sind.
CREATE TABLE IF NOT EXISTS form (
    id            INTEGER PRIMARY KEY,
    lexem_id      INTEGER NOT NULL REFERENCES lexem(id) ON DELETE CASCADE,
    text          TEXT NOT NULL,
    merkmale      TEXT NOT NULL DEFAULT '{}',
    ist_grundform INTEGER NOT NULL DEFAULT 0,
    aussprache    TEXT,                       -- IPA
    audio         TEXT,                       -- Dateipfad eigener Aufnahme
    quelle        TEXT NOT NULL DEFAULT 'manuell'
                  CHECK (quelle IN ('manuell','generiert','wiktionary','ki','import')),
    geprueft      INTEGER NOT NULL DEFAULT 1,
    notiz         TEXT
);
CREATE INDEX IF NOT EXISTS idx_form_lexem ON form(lexem_id);

-- ------------------------------------------------------------- Bedeutungen

CREATE TABLE IF NOT EXISTS bedeutung (
    id           INTEGER PRIMARY KEY,
    lexem_id     INTEGER NOT NULL REFERENCES lexem(id) ON DELETE CASCADE,
    reihenfolge  INTEGER NOT NULL DEFAULT 0,
    kontext      TEXT,            -- Unterscheidung, z.B. "Geldinstitut"
    notiz        TEXT
);
CREATE INDEX IF NOT EXISTS idx_bedeutung_lexem ON bedeutung(lexem_id);

-- Mehrere gültige Übersetzungen je Bedeutung sind der Normalfall.
CREATE TABLE IF NOT EXISTS uebersetzung (
    id            INTEGER PRIMARY KEY,
    bedeutung_id  INTEGER NOT NULL REFERENCES bedeutung(id) ON DELETE CASCADE,
    sprache       TEXT NOT NULL,
    text          TEXT NOT NULL,
    ist_haupt     INTEGER NOT NULL DEFAULT 0,
    quelle        TEXT NOT NULL DEFAULT 'manuell',
    geprueft      INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_uebersetzung_bedeutung ON uebersetzung(bedeutung_id);

CREATE TABLE IF NOT EXISTS beispiel (
    id              INTEGER PRIMARY KEY,
    lexem_id        INTEGER NOT NULL REFERENCES lexem(id) ON DELETE CASCADE,
    bedeutung_id    INTEGER REFERENCES bedeutung(id) ON DELETE SET NULL,
    satz            TEXT NOT NULL,
    uebersetzung    TEXT,
    luecke_form_id  INTEGER REFERENCES form(id) ON DELETE SET NULL,
    quelle          TEXT NOT NULL DEFAULT 'manuell'
);
CREATE INDEX IF NOT EXISTS idx_beispiel_lexem ON beispiel(lexem_id);

-- ----------------------------------------------------------------- Aufgaben

-- Aufgaben werden aus den Daten ERZEUGT, nicht von Hand gepflegt.
-- schluessel ist deterministisch (typ:lexem:zielart:zielid) und verhindert
-- Doppelte bei erneutem Erzeugen.
CREATE TABLE IF NOT EXISTS aufgabe (
    id          INTEGER PRIMARY KEY,
    lexem_id    INTEGER NOT NULL REFERENCES lexem(id) ON DELETE CASCADE,
    typ         TEXT NOT NULL,
    ziel_art    TEXT,                   -- 'bedeutung' | 'form' | 'lexem'
    ziel_id     INTEGER,
    schluessel  TEXT NOT NULL UNIQUE,
    aktiv       INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_aufgabe_lexem ON aufgabe(lexem_id);
CREATE INDEX IF NOT EXISTS idx_aufgabe_typ   ON aufgabe(typ);

-- ---------------------------------------------------------------- Lernstand

CREATE TABLE IF NOT EXISTS lernzustand (
    aufgabe_id           INTEGER NOT NULL REFERENCES aufgabe(id) ON DELETE CASCADE,
    benutzer_id          INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    zustand              TEXT NOT NULL DEFAULT 'neu'
                         CHECK (zustand IN ('neu','lernen','reif','verlernt','ausgesetzt')),
    stabilitaet          REAL,
    schwierigkeit        REAL,
    letzte_wiederholung  TEXT,
    faellig              TEXT,            -- Datum, ISO
    anzahl               INTEGER NOT NULL DEFAULT 0,
    anzahl_fehler        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (aufgabe_id, benutzer_id)
);
CREATE INDEX IF NOT EXISTS idx_lernzustand_faellig
    ON lernzustand(benutzer_id, faellig);
CREATE INDEX IF NOT EXISTS idx_lernzustand_zustand
    ON lernzustand(benutzer_id, zustand);

-- Protokoll. Wird nie gelöscht: erlaubt spätere Optimierung der
-- FSRS-Parameter auf das eigene Lernverhalten.
CREATE TABLE IF NOT EXISTS wiederholung (
    id                 INTEGER PRIMARY KEY,
    aufgabe_id         INTEGER NOT NULL REFERENCES aufgabe(id) ON DELETE CASCADE,
    benutzer_id        INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    zeitpunkt          TEXT NOT NULL,
    bewertung          INTEGER NOT NULL CHECK (bewertung BETWEEN 1 AND 4),
    antwort            TEXT,
    urteil             TEXT,           -- richtig | fast | falsch | aufgedeckt
    dauer_ms           INTEGER,        -- gesamt, inkl. Tippen
    -- Zeit bis zum ERSTEN Tastendruck. Das ist das Abrufmaß; die Gesamtzeit
    -- misst zu großen Teilen Tippgeschwindigkeit und Wortlänge mit.
    denkzeit_ms        INTEGER,
    versuche           INTEGER NOT NULL DEFAULT 1,
    -- Wie kam die Bewertung zustande: automatisch oder von Hand gesetzt?
    bewertung_quelle   TEXT NOT NULL DEFAULT 'automatisch',
    stabilitaet_vor    REAL,
    stabilitaet_nach   REAL,
    schwierigkeit_vor  REAL,
    schwierigkeit_nach REAL,
    intervall_tage     REAL,
    verstrichen_tage   REAL
);
CREATE INDEX IF NOT EXISTS idx_wiederholung_aufgabe
    ON wiederholung(benutzer_id, aufgabe_id, zeitpunkt);
CREATE INDEX IF NOT EXISTS idx_wiederholung_zeit
    ON wiederholung(benutzer_id, zeitpunkt);

-- ======================================================================
-- Textebene: echtes Textverständnis nach dem Pauken.
--
-- Vorbereitet, noch nicht in Betrieb (Stufe 4). Die Tabellen stehen jetzt
-- hier, damit später keine Datenbankwanderung nötig ist.
--
-- Der Gedanke: ein Text wird in Abschnitte zerlegt (meist Sätze) — das ist
-- die Einheit, an der gearbeitet wird. Jeder Abschnitt kann eine
-- Referenzübersetzung haben. Über text_lexem hängt der Text an den Vokabeln,
-- die in ihm vorkommen; damit lässt sich beides beantworten: "übe die
-- Vokabeln zu diesem Text" und "welchen Text kann ich mit meinem
-- Wortschatz schon lesen".
-- ======================================================================

CREATE TABLE IF NOT EXISTS text (
    id            INTEGER PRIMARY KEY,
    sammlung_id   INTEGER NOT NULL REFERENCES sammlung(id) ON DELETE CASCADE,
    lektion_id    INTEGER REFERENCES lektion(id) ON DELETE SET NULL,
    titel         TEXT NOT NULL,
    sprache       TEXT NOT NULL REFERENCES sprache(code),
    inhalt        TEXT NOT NULL,          -- der Text im Ganzen
    uebersetzung  TEXT,                   -- Referenzübersetzung im Ganzen
    niveau        TEXT,                   -- A1 … C2, frei
    quelle        TEXT NOT NULL DEFAULT 'manuell'
                  CHECK (quelle IN ('manuell','import','ki','wiktionary')),
    notiz         TEXT,
    angelegt      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_text_sammlung ON text(sammlung_id);

-- Die Arbeitseinheit: ein Satz oder ein Absatz.
CREATE TABLE IF NOT EXISTS textabschnitt (
    id            INTEGER PRIMARY KEY,
    text_id       INTEGER NOT NULL REFERENCES text(id) ON DELETE CASCADE,
    reihenfolge   INTEGER NOT NULL DEFAULT 0,
    original      TEXT NOT NULL,
    referenz      TEXT,                   -- Referenzübersetzung des Abschnitts
    notiz         TEXT
);
CREATE INDEX IF NOT EXISTS idx_textabschnitt_text ON textabschnitt(text_id, reihenfolge);

-- Welche Vokabeln kommen in diesem Text vor? Wird beim Einpflegen ermittelt
-- (über den MCP-Server oder beim Import) und macht den Text mit dem
-- Wortschatz verrechenbar.
CREATE TABLE IF NOT EXISTS text_lexem (
    text_id     INTEGER NOT NULL REFERENCES text(id) ON DELETE CASCADE,
    lexem_id    INTEGER NOT NULL REFERENCES lexem(id) ON DELETE CASCADE,
    form_id     INTEGER REFERENCES form(id) ON DELETE SET NULL,
    abschnitt_id INTEGER REFERENCES textabschnitt(id) ON DELETE CASCADE,
    PRIMARY KEY (text_id, lexem_id, abschnitt_id)
);
CREATE INDEX IF NOT EXISTS idx_text_lexem_lexem ON text_lexem(lexem_id);

-- Aufgaben zum Text. Getrennt von `aufgabe` gehalten, weil hier nicht eine
-- einzelne Form geprüft wird, sondern freier Text.
--
-- typ:
--   uebersetzung_hin    Abschnitt in die Grundsprache übersetzen
--   uebersetzung_rueck  Abschnitt in die Lernsprache übersetzen
--   verstaendnis        Frage zum Inhalt
--   lueckentext         Lücke im Abschnitt füllen (Antwort prüfbar)
--
-- bewertung_art — der Kern des Problems: eine freie Übersetzung lässt sich
-- nicht per Zeichenkettenvergleich bewerten.
--   selbst    Referenzübersetzung aufdecken, selbst einschätzen
--   ki        Rückmeldung über den MCP-Server einholen
--   genau     prüfbare Antwort (Lückentext, Auswahlfrage)
CREATE TABLE IF NOT EXISTS textaufgabe (
    id             INTEGER PRIMARY KEY,
    text_id        INTEGER NOT NULL REFERENCES text(id) ON DELETE CASCADE,
    abschnitt_id   INTEGER REFERENCES textabschnitt(id) ON DELETE CASCADE,
    typ            TEXT NOT NULL,
    bewertung_art  TEXT NOT NULL DEFAULT 'selbst'
                   CHECK (bewertung_art IN ('selbst','ki','genau')),
    frage          TEXT,
    erwartet       TEXT NOT NULL DEFAULT '[]',   -- JSON-Liste gültiger Antworten
    schluessel     TEXT NOT NULL UNIQUE,
    aktiv          INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_textaufgabe_text ON textaufgabe(text_id);

-- Bearbeitungen von Textaufgaben. Eigenes Protokoll, weil hier die Antwort
-- lang ist und die Rückmeldung der KI mitgeschrieben wird.
CREATE TABLE IF NOT EXISTS textbearbeitung (
    id             INTEGER PRIMARY KEY,
    textaufgabe_id INTEGER NOT NULL REFERENCES textaufgabe(id) ON DELETE CASCADE,
    benutzer_id    INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    zeitpunkt      TEXT NOT NULL,
    antwort        TEXT,
    bewertung      INTEGER,          -- 1..4, wie bei den Vokabeln
    rueckmeldung   TEXT,             -- Text der KI oder eigene Notiz
    dauer_ms       INTEGER
);
CREATE INDEX IF NOT EXISTS idx_textbearbeitung
    ON textbearbeitung(benutzer_id, textaufgabe_id, zeitpunkt);

-- ======================================================================
-- Lernziele und Lernblöcke
--
-- Ein LERNZIEL ist ein Ausschnitt des Bestands mit einem Termin: "Lektion 3
-- bis Freitag", "alle Verben im Passé composé", "die Stammformen aus dem
-- Nibelungenlied". Der Ausschnitt ist ausdrücklich NICHT an eine Lektion
-- gebunden — er darf über Lektionen und sogar über Sammlungen greifen.
--
-- Ein LERNBLOCK wird daraus errechnet und nicht gespeichert: er ist immer
-- der aktuelle Zuschnitt aus Fälligem, Wackligem und Neuem, verschränkt
-- gemischt. Gespeichert wird nur das Ziel; der Block folgt daraus.
-- ======================================================================

CREATE TABLE IF NOT EXISTS lernziel (
    id            INTEGER PRIMARY KEY,
    benutzer_id   INTEGER NOT NULL REFERENCES benutzer(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    -- JSON. Mögliche Einträge: sammlungen, lektionen, wortarten,
    -- formgruppen, typen, lexeme — alles Listen, alles freigestellt.
    -- Was fehlt, schränkt nicht ein.
    umfang        TEXT NOT NULL DEFAULT '{}',
    termin        TEXT,                    -- Datum, bis wann
    -- Was gilt als geschafft: 'reif' (sitzt dauerhaft) oder
    -- 'einmal_richtig' (wenigstens einmal gekonnt).
    ziel          TEXT NOT NULL DEFAULT 'reif'
                  CHECK (ziel IN ('reif', 'einmal_richtig')),
    aktiv         INTEGER NOT NULL DEFAULT 1,
    notiz         TEXT,
    angelegt      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_lernziel_benutzer ON lernziel(benutzer_id, aktiv);
