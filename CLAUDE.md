# Hinweise für automatische Läufe

- Lies zuerst README.md (Aufbau und Datenfluss).
- Wertungslogik nie ändern: Punkte kommen ausschließlich aus `src/scores.json` (berechnet aus der Original-Seite).
- Nach jeder Änderung an `src/original.html`: erst `node tools/scores.js …`, dann `node tools/visuals.js`, dann `python3 tools/build.py`. `assets/gen/` mit committen.
- Design liegt in `assets/style.css`, `assets/site.js` und den HTML-Vorlagen in `tools/build.py`. Läufe, die nur Daten pflegen, ändern diese Dateien nicht.
- Vor dem Push prüfen: `python3 tools/build.py` läuft ohne Fehler und meldet rund 970 Seiten.
