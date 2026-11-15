# Zugang von außen

Der Familienserver ist von außen über einen **Cloudflare-Tunnel** erreichbar,
nicht über eine Portweiterleitung. Der Unterschied ist nicht Geschmackssache:

* Im Router bleibt **kein Port offen**. Die Verbindung baut der Server selbst
  nach außen auf.
* Es gibt **keine erreichbare Adresse des Hauses**. Wer den Namen nachschlägt,
  landet bei Cloudflare, nicht bei euch.
* Ein wechselnder Anschluss macht nichts aus — kein DynDNS nötig.

## Was erreichbar ist

Welche Namen das sind, steht in `einrichten.py` unter `DIENSTE` und wird
beim Einrichten über `CF_ZONE` mit der eigenen Domain verbunden:

| Name | Dienst | intern |
|---|---|---|
| `vokabeln.<deine-domain>` | Vokabeltrainer | `127.0.0.1:8030` |
| `rezepte.<deine-domain>` | Mealie | `127.0.0.1:9925` |
| `mcp.<deine-domain>` | MCP-Schnittstelle | `127.0.0.1:8030` |

Alles, was nicht in dieser Liste steht, beantwortet der Tunnel mit 404 — auch
wenn jemand den Namen errät.

## Davor steht Cloudflare Access

**Der Vokabeltrainer hat keinerlei Anmeldung.** Die Profile sind bloße Namen
ohne Passwort — im Heimnetz richtig so, im offenen Netz nicht. Deshalb fragt
Cloudflare Access *vor* dem Durchreichen nach einer Mailadresse und schickt
einen sechsstelligen Einmalcode. Nur hinterlegte Adressen kommen durch.

Wer hinterlegt ist, steht in der Zugriffsregel in der Cloudflare-Verwaltung
unter **Zero Trust → Access → Anwendungen**.

Die **MCP-Schnittstelle** ist anders geschützt: sie wird von einem Programm
gerufen, nicht von einem Menschen, und kann keine Anmeldeseite bedienen.

Hier stand bis zum 15.11.2026, davor stehe zusätzlich ein
**Access-Diensttoken** mit zwei festen Kopfzeilen — »zwei Schlösser«.
**Das stimmt nicht mehr.** Nachgemessen an der öffentlichen Adresse:

```
POST https://mcp.<deine-domain>/mcp     ohne jede Kopfzeile
→ 401 »Kein gültiges Zugangsmerkmal …«
```

Das ist die Antwort des Trainers, nicht die von Cloudflare — die Anfrage
kommt also durch. Der Grund ist bekannt und nicht versehentlich: die
Konnektoren von claude.ai und ChatGPT lassen keine beliebigen Kopfzeilen
zu, und ohne die beiden Access-Kopfzeilen kommt kein Konnektor durch. Das
Diensttoken musste weichen, damit die Anbindung überhaupt geht.

**Es bleibt also ein Schloss, nicht zwei**, und das sollte dastehen statt
einer beruhigenden Angabe, die niemand nachgeprüft hat. Dieses eine
Schloss ist gut: 256 Bit aus `secrets.token_urlsafe(32)`, nur als
Streuwert gespeichert, dazu eine Sperre nach acht Fehlversuchen in fünf
Minuten für eine Viertelstunde. Erraten lässt sich das nicht. Aber wer
das Merkmal hat, ist drin — es gibt nichts dahinter.

Daraus folgt für den Umgang damit:

* Das Merkmal gehört **nicht in eine Adresse** (auch nicht in einen
  Pfad wie `/mcp/<merkmal>`): Adressen landen in Protokollen, bei
  Cloudflare wie auf dem Server, und im Verlauf jedes Programms, das
  sie einmal gesehen hat. In einer Kopfzeile tut es das nicht.
* Wird ein Konnektor abgeschafft oder weitergegeben, gehört das
  zugehörige Merkmal in den Einstellungen gelöscht. Dafür hat jedes
  einen Namen.

## Der Tunnel lässt auf `mcp.` nur `/mcp` durch

Gemessen am 15.11.2026, und nirgends sonst aufgeschrieben:

```
/mcp/irgendwas   404 {"detail":"Not Found"}   ← die Anwendung antwortet
/.well-known/…   404 (leerer Rumpf)           ← Cloudflare antwortet
```

Auf diesem Namen ist also nur der Pfad `/mcp` freigegeben, und er gilt
als **Präfix**. Alles daneben beantwortet Cloudflare selbst, die
Anwendung sieht es nie — man sucht den Fehler sonst stundenlang im
falschen Haus.

Deshalb hängen die OAuth-Endpunkte zusätzlich unter `/mcp`:
`/mcp/oauth/token` und `/mcp/.well-known/oauth-authorization-server`.
An den vorgeschriebenen Stellen stehen sie auch; die werden erreichbar,
sobald `/.well-known/*` und `/oauth/*` in der Tunnelkonfiguration
freigegeben sind. Nötig ist das nicht — angekündigt wird die Adresse,
die durchkommt.

Der Name `vokabeln.` ist **nicht** so beschränkt: dort geht jeder Pfad
durch, und davor steht Access. Genau deshalb liegt der Schritt, in dem
ein Mensch einwilligt, auf diesem Namen.

## Wartung

```sh
cd /srv/cloudflared
docker compose logs -f          # läuft der Tunnel?
docker compose restart          # nach einer Konfigurationsänderung
docker compose pull && docker compose up -d   # Fassung aktualisieren
```

Der Tunnel ist **fassungsfest gebunden** (nicht `:latest`), damit er nicht
eines Nachts von selbst auf eine Fassung springt, die sich anders verhält.
Zum Aktualisieren die Nummer in `docker-compose.yml` ändern.

Die Weiterleitungen selbst stehen nicht hier, sondern bei Cloudflare in der
Tunnelkonfiguration — dieser Tunnel wird von dort aus verwaltet.

## Wenn etwas nicht geht

1. `docker compose logs --tail 50` — der Tunnel meldet jede abgelehnte
   Verbindung mit Grund.
2. Läuft der Dienst dahinter? `curl -s http://127.0.0.1:8030/api/zustand`
3. Zeigt der DNS-Eintrag noch auf den Tunnel? In der Cloudflare-Verwaltung
   muss ein CNAME auf `<Tunnelkennung>.cfargotunnel.com` stehen, orange Wolke.
