# Technik Kompass – Website

Statische Website aus den Daten des Technik Kompass. Jede Rangliste, jedes Gerät und die wichtigsten Duelle bekommen eine eigene Seite, damit Google sie findet.

## Aufbau

| Datei | Wofür |
|---|---|
| `config.json` | Domain, Amazon-Partner-Tag, Impressum-Angaben |
| `links.json` | Optional: feste Amazon-ASIN oder fertiger Partner-Link pro Gerät |
| `tiktok.json` | Produkte für die Seite „Aus den Videos“ (`/tiktok/`) |
| `src/data.json` | Gerätedaten aus der Original-Seite |
| `src/scores.json` | Wertungen, mit `tools/scores.js` aus der Original-Seite berechnet |
| `src/original.html` | Die interaktive Original-Seite, läuft unter `/app/` |
| `tools/build.py` | Baut alles nach `dist/` |

## Bauen

```
python3 tools/build.py          # nur Python 3, keine Pakete nötig
python3 -m http.server -d dist  # Vorschau auf http://localhost:8000
```

Nach jedem Push auf `main` baut GitHub die Seite automatisch und veröffentlicht sie über GitHub Pages.

## Neue Daten aus der Original-Seite übernehmen

1. Neue Original-HTML als `src/original.html` speichern.
2. Daten herausziehen: Zeile mit `<script type="application/json" id="ranking-data">` als `src/data.json` speichern.
3. Wertungen neu berechnen: `node tools/scores.js $PWD/src/original.html $PWD/src/scores.json` (braucht Playwright).
4. `python3 tools/build.py`

## Partner-Links einschalten

In `config.json` den Amazon-Tag eintragen (z. B. `technikkompa-21`). Dann bekommt jedes Gerät einen Button „Bei Amazon ansehen*“, und der Werbehinweis erscheint automatisch auf allen Seiten.
