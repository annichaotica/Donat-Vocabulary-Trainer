# Ein Behälter, ein Dienst, keine Bauschritte.
FROM python:3.13-slim

# Kein Schreibrecht auf den Code, nur auf das Datenverzeichnis.
RUN useradd --create-home --uid 10001 vokabel

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY werkzeuge/ ./werkzeuge/

# Die Datenbank liegt außerhalb des Abbilds, damit sie Aktualisierungen
# überlebt und von der /srv-Sicherung mitgenommen wird.
ENV VOKABEL_DB=/daten/vokabeltrainer.db
RUN mkdir -p /daten && chown vokabel:vokabel /daten
VOLUME ["/daten"]

USER vokabel
EXPOSE 8020

HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; \
      sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8020/api/zustand', \
      timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app:app", "--app-dir", "backend", \
     "--host", "0.0.0.0", "--port", "8020"]
