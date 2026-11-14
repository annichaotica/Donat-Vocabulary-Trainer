# Festlegung für die KI-gestützte Befüllung

Stand 2026-11-14. Dieses Blatt richtet sich an eine KI, die Vokabeln samt
vollständigen Paradigmen für den Vokabeltrainer erzeugt — derzeit von Hand
hinübergetragen, später unmittelbar über den MCP-Server.

**Ja, vollständige Tabellen erzeugen** — alle Personen, alle verlangten Zeiten.
Der Trainer braucht sie vollständig, weil er daraus die Aufgaben ERZEUGT: jede
Form wird eine eigene Abfrage, und aus dem gemeinsamen Anfang aller Formen
leitet er den Wortstamm ab (für die Zerlegung "γράφ|ουμε"). Fehlende Zellen
bedeuten fehlende Aufgaben, und ein unvollständiges Paradigma verdirbt die
Stammerkennung.

## Das Format

Ein Wort ist **ein** Datensatz mit allem darin — Lemma, alle Formen, alle
Bedeutungen. Nicht vierzig Einzelsätze. Gesendet wird er an
`POST /api/lexeme`.

Jede Form besteht aus `text` und einem **Merkmalsbündel**. Das Bündel ist der
Kern des Ganzen: nicht `praesens_1sg` als Spaltenname, sondern
`{"modus": "indikativ", "tempus": "praesens", "person": "1", "numerus": "sg"}`.

### Verbindliche Regeln

1. `quelle` ist **`"ki"`** und `geprueft` ist **`false`**. Ungeprüfte Formen
   werden nicht abgefragt, bis ein Mensch sie bestätigt. Das ist Absicht:
   eine erfundene Form, die unbemerkt gepaukt wird, ist schlimmer als eine
   fehlende.
2. `person` ist eine **Zeichenkette**: `"1"`, nicht `1`.
3. Genau **eine** Form trägt `ist_grundform: true` — die Zitierform, unter der
   das Wort im Wörterbuch steht. Für sie entsteht keine eigene Formaufgabe.
4. Unbekannte Merkmale oder Werte werden **abgelehnt** (HTTP 422). Nur was
   unten steht, ist erlaubt. Eigene Zusätze gehen mit dem Vorsatz `x_`,
   etwa `"x_lehrbuchseite": "42"`.
5. Mehrere gültige Übersetzungen sind der **Normalfall** — bitte alle angeben,
   nicht die beste auswählen. Der Trainer nimmt jede davon als richtig an.
6. Verschiedene **Bedeutungen** sind etwas anderes als verschiedene
   Übersetzungen derselben Bedeutung. „Bank" als Geldinstitut und als Sitzbank
   sind zwei Einträge in `bedeutungen`, jeder mit `kontext`; „schreiben" und
   „aufschreiben" sind zwei `uebersetzungen` derselben Bedeutung.

## Vollständiges Beispiel

Griechisch, `γράφω` mit Präsens, Aorist und Futur — genau das, wonach gefragt
war. So sieht der fertige Datensatz aus:

```json
{
  "sammlung_id": 1,
  "lemma": "γράφω",
  "wortart": "verb",
  "merkmale": {"klasse": "Α-Konjugation"},
  "bedeutungen": [
    {"uebersetzungen": [{"text": "schreiben"}, {"text": "aufschreiben"}],
     "quelle": "ki"}
  ],
  "formen": [
    {"text": "γράφω",     "merkmale": {"modus": "indikativ", "tempus": "praesens", "person": "1", "numerus": "sg"},
     "ist_grundform": true, "quelle": "ki", "geprueft": false},
    {"text": "γράφεις", "merkmale": {"modus": "indikativ", "tempus": "praesens", "person": "2", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "γράφει", "merkmale": {"modus": "indikativ", "tempus": "praesens", "person": "3", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "γράφουμε", "merkmale": {"modus": "indikativ", "tempus": "praesens", "person": "1", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "γράφετε", "merkmale": {"modus": "indikativ", "tempus": "praesens", "person": "2", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "γράφουν", "merkmale": {"modus": "indikativ", "tempus": "praesens", "person": "3", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "έγραψα", "merkmale": {"modus": "indikativ", "tempus": "aorist", "person": "1", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "έγραψες", "merkmale": {"modus": "indikativ", "tempus": "aorist", "person": "2", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "έγραψε", "merkmale": {"modus": "indikativ", "tempus": "aorist", "person": "3", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "γράψαμε", "merkmale": {"modus": "indikativ", "tempus": "aorist", "person": "1", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "γράψατε", "merkmale": {"modus": "indikativ", "tempus": "aorist", "person": "2", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "έγραψαν", "merkmale": {"modus": "indikativ", "tempus": "aorist", "person": "3", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "θα γράψω", "merkmale": {"modus": "indikativ", "tempus": "futur", "aspekt": "perfektiv", "person": "1", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "θα γράψεις", "merkmale": {"modus": "indikativ", "tempus": "futur", "aspekt": "perfektiv", "person": "2", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "θα γράψει", "merkmale": {"modus": "indikativ", "tempus": "futur", "aspekt": "perfektiv", "person": "3", "numerus": "sg"}, "quelle": "ki", "geprueft": false},
    {"text": "θα γράψουμε", "merkmale": {"modus": "indikativ", "tempus": "futur", "aspekt": "perfektiv", "person": "1", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "θα γράψετε", "merkmale": {"modus": "indikativ", "tempus": "futur", "aspekt": "perfektiv", "person": "2", "numerus": "pl"}, "quelle": "ki", "geprueft": false},
    {"text": "θα γράψουν", "merkmale": {"modus": "indikativ", "tempus": "futur", "aspekt": "perfektiv", "person": "3", "numerus": "pl"}, "quelle": "ki", "geprueft": false}
  ]
}
```bash
curl -X POST http://<dein-server>:8030/api/lexeme \
     -H 'Content-Type: application/json' \
     -d @wort.json
```

`sammlung_id` erfragt man mit `GET /api/sammlungen?benutzer_id=1`.

## Das Merkmalsvokabular

Nur diese Dimensionen und Werte sind erlaubt.

- **nonfinit** — `infinitiv`, `partizip_praesens`, `partizip_perfekt`, `gerundium`, `supinum`
- **person** — `1`, `2`, `3`
- **kasus** — `nom`, `gen`, `dat`, `akk`, `vok`, `abl`
- **numerus** — `sg`, `pl`
- **genus** — `m`, `f`, `n`
- **stufe** — `grund`, `komparativ`, `superlativ`
- **tempus** — `praesens`, `imperfekt`, `praeteritum`, `aorist`, `perfekt`, `plusquamperfekt`, `futur`, `futur_perfekt`, `verlaufsform`
- **aspekt** — `perfektiv`, `imperfektiv`
- **modus** — `indikativ`, `konjunktiv`, `imperativ`, `konditional`
- **genus_verbi** — `aktiv`, `passiv`, `medium`
- **flexion** — `stark`, `schwach`

Dazu `genus` nur bei Substantiven und Adjektiven, `flexion` (stark/schwach)
im Deutschen und Mittelhochdeutschen, `aspekt` im Neugriechischen.

## Die Formgruppen je Sprache

Eine **Formgruppe** ist eine Tabelle, die gemeinsam gelernt wird — eine Zeit
mit ihren sechs Personen, oder eine einzelne Form wie das Partizip. Die Spalte
*Merkmale* nennt, was alle Zellen der Gruppe gemeinsam haben; bei mehrzelligen
Gruppen kommen `person` und `numerus` hinzu.

Die mit **(Standard)** bezeichneten Gruppen fragt eine neue Sammlung von
Anfang an ab. Die übrigen lassen sich jederzeit zuschalten — es ist also kein
Schaden, mehr zu liefern als voreingestellt ist.

### Griechisch (`el`)

Stammformen, das Kernpensum: **Ενεστώτας (Präsens) – Αόριστος (Aorist) – Μέλλοντας στιγμιαίος (Futur, punktuell)**

*Verb*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `enestotas` | Ενεστώτας (Präsens) (Standard) | 6 | `{"modus": "indikativ", "tempus": "praesens"}` |
| `paratatikos` | Παρατατικός (Imperfekt) | 6 | `{"modus": "indikativ", "tempus": "imperfekt"}` |
| `aoristos` | Αόριστος (Aorist) (Standard) | 6 | `{"modus": "indikativ", "tempus": "aorist"}` |
| `mellontas_stigmiaios` | Μέλλοντας στιγμιαίος (Futur, punktuell) (Standard) | 6 | `{"aspekt": "perfektiv", "modus": "indikativ", "tempus": "futur"}` |
| `mellontas_exakolouthitikos` | Μέλλοντας εξακολουθητικός (Futur, fortgesetzt) | 6 | `{"aspekt": "imperfektiv", "modus": "indikativ", "tempus": "futur"}` |
| `parakeimenos` | Παρακείμενος (Perfekt) | 6 | `{"modus": "indikativ", "tempus": "perfekt"}` |
| `ypotaktiki` | Υποτακτική (Konjunktiv) | 6 | `{"modus": "konjunktiv", "tempus": "praesens"}` |
| `prostaktiki` | Προστακτική (Imperativ) | 2 | `{"modus": "imperativ"}` |

*Substantiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `subst_nom_sg` | Nominativ Singular (Standard) | 1 | `{"kasus": "nom", "numerus": "sg"}` |
| `subst_gen_sg` | Genitiv Singular (Standard) | 1 | `{"kasus": "gen", "numerus": "sg"}` |
| `subst_akk_sg` | Akkusativ Singular (Standard) | 1 | `{"kasus": "akk", "numerus": "sg"}` |
| `subst_vok_sg` | Vokativ Singular | 1 | `{"kasus": "vok", "numerus": "sg"}` |
| `subst_nom_pl` | Nominativ Plural (Standard) | 1 | `{"kasus": "nom", "numerus": "pl"}` |
| `subst_gen_pl` | Genitiv Plural (Standard) | 1 | `{"kasus": "gen", "numerus": "pl"}` |
| `subst_akk_pl` | Akkusativ Plural (Standard) | 1 | `{"kasus": "akk", "numerus": "pl"}` |
| `subst_vok_pl` | Vokativ Plural | 1 | `{"kasus": "vok", "numerus": "pl"}` |

*Adjektiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `adj_m` | maskulin Nominativ Singular (Standard) | 1 | `{"genus": "m", "kasus": "nom", "numerus": "sg"}` |
| `adj_f` | feminin Nominativ Singular (Standard) | 1 | `{"genus": "f", "kasus": "nom", "numerus": "sg"}` |
| `adj_n` | neutrum Nominativ Singular (Standard) | 1 | `{"genus": "n", "kasus": "nom", "numerus": "sg"}` |

*Lexemmerkmale* — beschreiben das Wort, nicht eine Form:

- Substantiv, `genus`: `m`, `f`, `n`
- Verb, `klasse`: `Α-Konjugation`, `Β1`, `Β2`, `unregelmäßig`


### Französisch (`fr`)

Stammformen, das Kernpensum: **Infinitif – Participe passé**

*Verb*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `praesens` | Présent (Standard) | 6 | `{"modus": "indikativ", "tempus": "praesens"}` |
| `imparfait` | Imparfait (Standard) | 6 | `{"modus": "indikativ", "tempus": "imperfekt"}` |
| `passe_compose` | Passé composé (Standard) | 6 | `{"modus": "indikativ", "tempus": "perfekt"}` |
| `plus_que_parfait` | Plus-que-parfait | 6 | `{"modus": "indikativ", "tempus": "plusquamperfekt"}` |
| `passe_simple` | Passé simple | 6 | `{"modus": "indikativ", "tempus": "praeteritum"}` |
| `futur_simple` | Futur simple (Standard) | 6 | `{"modus": "indikativ", "tempus": "futur"}` |
| `futur_anterieur` | Futur antérieur | 6 | `{"modus": "indikativ", "tempus": "futur_perfekt"}` |
| `conditionnel` | Conditionnel présent | 6 | `{"modus": "konditional", "tempus": "praesens"}` |
| `conditionnel_passe` | Conditionnel passé | 6 | `{"modus": "konditional", "tempus": "perfekt"}` |
| `subjonctif` | Subjonctif présent | 6 | `{"modus": "konjunktiv", "tempus": "praesens"}` |
| `subjonctif_passe` | Subjonctif passé | 6 | `{"modus": "konjunktiv", "tempus": "perfekt"}` |
| `imperatif` | Impératif | 3 | `{"modus": "imperativ"}` |
| `infinitif` | Infinitif (Standard) | 1 | `{"nonfinit": "infinitiv"}` |
| `participe_passe` | Participe passé (Standard) | 1 | `{"nonfinit": "partizip_perfekt"}` |
| `participe_present` | Participe présent | 1 | `{"nonfinit": "partizip_praesens"}` |

*Substantiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `sg` | Singular (Standard) | 1 | `{"numerus": "sg"}` |
| `pl` | Plural (Standard) | 1 | `{"numerus": "pl"}` |

*Adjektiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `m_sg` | maskulin Singular (Standard) | 1 | `{"genus": "m", "numerus": "sg"}` |
| `f_sg` | feminin Singular (Standard) | 1 | `{"genus": "f", "numerus": "sg"}` |
| `m_pl` | maskulin Plural (Standard) | 1 | `{"genus": "m", "numerus": "pl"}` |
| `f_pl` | feminin Plural (Standard) | 1 | `{"genus": "f", "numerus": "pl"}` |

*Lexemmerkmale* — beschreiben das Wort, nicht eine Form:

- Verb, `hilfsverb`: `avoir`, `être`
- Verb, `klasse`: `er`, `ir`, `re`, `unregelmäßig`
- Substantiv, `genus`: `m`, `f`


### Spanisch (`es`)

Stammformen, das Kernpensum: **Infinitivo – Participio – Gerundio**

*Verb*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `presente` | Presente (Standard) | 6 | `{"modus": "indikativ", "tempus": "praesens"}` |
| `imperfecto` | Pretérito imperfecto (Standard) | 6 | `{"modus": "indikativ", "tempus": "imperfekt"}` |
| `indefinido` | Pretérito indefinido (Standard) | 6 | `{"modus": "indikativ", "tempus": "praeteritum"}` |
| `perfecto` | Pretérito perfecto | 6 | `{"modus": "indikativ", "tempus": "perfekt"}` |
| `pluscuamperfecto` | Pretérito pluscuamperfecto | 6 | `{"modus": "indikativ", "tempus": "plusquamperfekt"}` |
| `futuro` | Futuro simple (Standard) | 6 | `{"modus": "indikativ", "tempus": "futur"}` |
| `condicional` | Condicional simple | 6 | `{"modus": "konditional", "tempus": "praesens"}` |
| `subjuntivo` | Presente de subjuntivo | 6 | `{"modus": "konjunktiv", "tempus": "praesens"}` |
| `subjuntivo_imperfecto` | Imperfecto de subjuntivo | 6 | `{"modus": "konjunktiv", "tempus": "imperfekt"}` |
| `imperativo` | Imperativo | 5 | `{"modus": "imperativ"}` |
| `infinitivo` | Infinitivo (Standard) | 1 | `{"nonfinit": "infinitiv"}` |
| `participio` | Participio (Standard) | 1 | `{"nonfinit": "partizip_perfekt"}` |
| `gerundio` | Gerundio | 1 | `{"nonfinit": "gerundium"}` |

*Substantiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `sg` | Singular (Standard) | 1 | `{"numerus": "sg"}` |
| `pl` | Plural (Standard) | 1 | `{"numerus": "pl"}` |

*Adjektiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `m_sg` | maskulin Singular (Standard) | 1 | `{"genus": "m", "numerus": "sg"}` |
| `f_sg` | feminin Singular (Standard) | 1 | `{"genus": "f", "numerus": "sg"}` |
| `m_pl` | maskulin Plural (Standard) | 1 | `{"genus": "m", "numerus": "pl"}` |
| `f_pl` | feminin Plural (Standard) | 1 | `{"genus": "f", "numerus": "pl"}` |

*Lexemmerkmale* — beschreiben das Wort, nicht eine Form:

- Verb, `klasse`: `ar`, `er`, `ir`, `unregelmäßig`
- Substantiv, `genus`: `m`, `f`


### Englisch (`en`)

Stammformen, das Kernpensum: **Infinitiv – Simple past – Past participle**

*Verb*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `infinitive` | Infinitiv (Standard) | 1 | `{"nonfinit": "infinitiv"}` |
| `present_3sg` | 3. Person Singular Präsens (Standard) | 1 | `{"modus": "indikativ", "numerus": "sg", "person": "3", "tempus": "praesens"}` |
| `past` | Simple past (Standard) | 1 | `{"modus": "indikativ", "tempus": "praeteritum"}` |
| `past_participle` | Past participle (Standard) | 1 | `{"nonfinit": "partizip_perfekt"}` |
| `present_participle` | Present participle (-ing) (Standard) | 1 | `{"nonfinit": "partizip_praesens"}` |

*Substantiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `sg` | Singular (Standard) | 1 | `{"numerus": "sg"}` |
| `pl` | Plural (Standard) | 1 | `{"numerus": "pl"}` |

*Adjektiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `grund` | Grundstufe (Standard) | 1 | `{"stufe": "grund"}` |
| `komparativ` | Comparative (Standard) | 1 | `{"stufe": "komparativ"}` |
| `superlativ` | Superlative (Standard) | 1 | `{"stufe": "superlativ"}` |

*Lexemmerkmale* — beschreiben das Wort, nicht eine Form:

- Verb, `klasse`: `regelmäßig`, `unregelmäßig`


### Mittelhochdeutsch (`gmh`)

Stammformen, das Kernpensum: **Infinitiv – 1./3. Singular Präteritum – 1./3. Plural Präteritum – Partizip Präteritum**

*Verb*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `infinitiv` | Infinitiv (Standard) | 1 | `{"nonfinit": "infinitiv"}` |
| `stamm_praet_sg` | 1./3. Singular Präteritum (Standard) | 1 | `{"modus": "indikativ", "numerus": "sg", "person": "1", "tempus": "praeteritum"}` |
| `stamm_praet_pl` | 1./3. Plural Präteritum (Standard) | 1 | `{"modus": "indikativ", "numerus": "pl", "person": "1", "tempus": "praeteritum"}` |
| `partizip_praet` | Partizip Präteritum (Standard) | 1 | `{"nonfinit": "partizip_perfekt"}` |
| `praesens` | Präsens Indikativ | 6 | `{"modus": "indikativ", "tempus": "praesens"}` |
| `praeteritum` | Präteritum Indikativ | 6 | `{"modus": "indikativ", "tempus": "praeteritum"}` |
| `konj_praesens` | Konjunktiv Präsens | 6 | `{"modus": "konjunktiv", "tempus": "praesens"}` |
| `konj_praeteritum` | Konjunktiv Präteritum | 6 | `{"modus": "konjunktiv", "tempus": "praeteritum"}` |
| `imperativ` | Imperativ | 2 | `{"modus": "imperativ"}` |
| `partizip_praes` | Partizip Präsens | 1 | `{"nonfinit": "partizip_praesens"}` |

*Substantiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `subst_nom_sg` | Nominativ Singular (Standard) | 1 | `{"kasus": "nom", "numerus": "sg"}` |
| `subst_gen_sg` | Genitiv Singular (Standard) | 1 | `{"kasus": "gen", "numerus": "sg"}` |
| `subst_dat_sg` | Dativ Singular (Standard) | 1 | `{"kasus": "dat", "numerus": "sg"}` |
| `subst_akk_sg` | Akkusativ Singular (Standard) | 1 | `{"kasus": "akk", "numerus": "sg"}` |
| `subst_nom_pl` | Nominativ Plural (Standard) | 1 | `{"kasus": "nom", "numerus": "pl"}` |
| `subst_gen_pl` | Genitiv Plural (Standard) | 1 | `{"kasus": "gen", "numerus": "pl"}` |
| `subst_dat_pl` | Dativ Plural | 1 | `{"kasus": "dat", "numerus": "pl"}` |
| `subst_akk_pl` | Akkusativ Plural | 1 | `{"kasus": "akk", "numerus": "pl"}` |

*Adjektiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `stark` | starke Flexion, Nominativ Singular (Standard) | 1 | `{"flexion": "stark", "kasus": "nom", "numerus": "sg"}` |
| `schwach` | schwache Flexion, Nominativ Singular (Standard) | 1 | `{"flexion": "schwach", "kasus": "nom", "numerus": "sg"}` |
| `komparativ` | Komparativ (Standard) | 1 | `{"stufe": "komparativ"}` |
| `superlativ` | Superlativ (Standard) | 1 | `{"stufe": "superlativ"}` |

*Lexemmerkmale* — beschreiben das Wort, nicht eine Form:

- Verb, `klasse`: `stark I`, `stark II`, `stark III`, `stark IV`, `stark V`, `stark VI`, `stark VII`, `schwach`, `Präteritopräsens`, `Wurzelverb`
- Substantiv, `genus`: `m`, `f`, `n`
- Substantiv, `klasse`: `stark a`, `stark i`, `stark u`, `schwach n`, `Wurzelnomen`


### Deutsch (`de`)

Stammformen, das Kernpensum: **Infinitiv – Präteritum – Partizip II**

*Verb*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `praesens` | Präsens (Standard) | 6 | `{"modus": "indikativ", "tempus": "praesens"}` |
| `praeteritum` | Präteritum (Standard) | 6 | `{"modus": "indikativ", "tempus": "praeteritum"}` |
| `infinitiv` | Infinitiv (Standard) | 1 | `{"nonfinit": "infinitiv"}` |
| `partizip_ii` | Partizip II (Standard) | 1 | `{"nonfinit": "partizip_perfekt"}` |

*Substantiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `sg` | Singular (Standard) | 1 | `{"numerus": "sg"}` |
| `pl` | Plural (Standard) | 1 | `{"numerus": "pl"}` |

*Adjektiv*

| Kennung | Name | Zellen | Merkmale |
|---|---|---|---|
| `grund` | Grundstufe (Standard) | 1 | `{"stufe": "grund"}` |
| `komparativ` | Komparativ (Standard) | 1 | `{"stufe": "komparativ"}` |
| `superlativ` | Superlativ (Standard) | 1 | `{"stufe": "superlativ"}` |

*Lexemmerkmale* — beschreiben das Wort, nicht eine Form:

- Substantiv, `genus`: `m`, `f`, `n`


## Was später der MCP-Server übernimmt

Alles davon. Der Server bekommt Werkzeuge wie `vokabel_anlegen`,
`formen_ergaenzen` und `paradigma_pruefen`; dann entfällt das Erzeugen von
JSON-Dateien und das Hinübertragen von Hand. Die Regeln auf diesem Blatt
bleiben dieselben — der MCP-Server ist nur ein anderer Weg zur gleichen
Schnittstelle, und er wird dieselben Merkmale prüfen.
