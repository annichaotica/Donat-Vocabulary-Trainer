# Ein Behälter, ein Dienst, keine Bauschritte.
#
# Auf den Digest festgenagelt, nicht nur auf den Tag: `python:3.13-slim`
# zeigt jeden Monat auf ein anderes Abbild, und dann baut dieselbe Zeile
# im Verzeichnis zwei verschiedene Behälter. Mit Digest ist der Bau
# wiederholbar, und ein Wechsel steht im Diff statt still zu geschehen.
# Dependabot zieht den Digest nach; der Tag davor bleibt als Lesehilfe.
#
# Neu holen:
#   docker pull python:3.15-slim
#   docker image inspect --format '{{index .RepoDigests 0}}' python:3.15-slim
FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

# Kein Schreibrecht auf den Code, nur auf das Datenverzeichnis.
RUN useradd --create-home --uid 10001 vokabel

WORKDIR /app

# Aus der Lock-Datei, nicht aus requirements.txt: dort stehen nur die
# drei obersten Pakete, im Abbild landen zwanzig. --require-hashes ist
# der Teil, der wirkt — ohne ihn sieht pip die Prüfsummen gar nicht an.
COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY werkzeuge/ ./werkzeuge/

# Die Datenbank liegt außerhalb des Abbilds, damit sie Aktualisierungen
# überlebt und von der /srv-Sicherung mitgenommen wird.
ENV VOKABEL_DB=/daten/vokabeltrainer.db
# Gruppenschreibrecht, damit der Behälter auch unter der Kennung des Wirts
# laufen kann (siehe `user:` in docker-compose.yml) — ein eingehängtes
# Verzeichnis bringt die Rechte des Wirts mit, nicht die des Abbilds.
RUN mkdir -p /daten && chown vokabel:vokabel /daten && chmod 775 /daten
VOLUME ["/daten"]

USER vokabel
EXPOSE 8030

HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; \
      sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8030/api/zustand', \
      timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app:app", "--app-dir", "backend", \
     "--host", "0.0.0.0", "--port", "8030"]
