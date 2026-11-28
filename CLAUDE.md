# Hinweise für automatische Läufe

- Lies zuerst README.md (Aufbau und Datenfluss).
- Wertungslogik nie ändern: Punkte kommen ausschließlich aus `src/scores.json` (berechnet aus der Original-Seite).
- Nach jeder Änderung an `src/original.html`: erst `node tools/scores.js …`, dann `node tools/visuals.js`, dann `python3 tools/build.py`. `assets/gen/` mit committen.
- Design liegt in `assets/style.css`, `assets/site.js` und den HTML-Vorlagen in `tools/build.py`. Läufe, die nur Daten pflegen, ändern diese Dateien nicht.
- Vor dem Push prüfen: `python3 tools/build.py` läuft ohne Fehler und meldet rund 970 Seiten.

## Sparsam arbeiten (Caveman-Regeln, gelten für jeden Lauf)

- Erst suchen (`grep -n`, `jq`), dann nur die nötigen Zeilen lesen. `src/data.json`, `src/original.html` und `assets/gen/` nie komplett ausgeben.
- Gezielt ändern statt ganze Dateien neu schreiben. Nichts doppelt lesen.
- Lange Ausgaben filtern: Build und Skripte mit `2>&1 | tail -20` laufen lassen, nur Fehler und das Ende zeigen.
- Keine Subagenten für Kleinigkeiten. Größere Änderung: erst Plan in höchstens 5 Zeilen, dann bauen, dann einmal testen.
- Antworten, PR-Texte und Commit-Nachrichten knapp: was geändert, mit welcher Quelle, Build-Ergebnis. Keine Einleitung, keine Wiederholung.
- Nie kürzen: Quellen und Datum bei Preisen, Warnungen, Annahmen, Fehlermeldungen (exakt zitieren) und Rückfragen vor unumkehrbaren Schritten.
- Keine Ersparnis in Prozent behaupten, die nicht gemessen wurde.
