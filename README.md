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
| `assets/gen/` | Gerätebilder, mit `tools/visuals.js` aus der Original-Seite erzeugt (nicht von Hand ändern) |
| `assets/style.css`, `assets/site.js` | Design und kleine Helfer (3D-Drehen, Suche, Sortieren) |
| `tools/visuals.js` | Erzeugt `assets/gen/` (braucht Playwright mit Chromium) |
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
4. Bilder neu erzeugen: `node tools/visuals.js` (braucht Playwright, dauert ein paar Minuten). Das legt `assets/gen/` neu an und muss mit committet werden.
5. `python3 tools/build.py`

## Gerätebilder (`assets/gen/`)

`tools/visuals.js` öffnet `src/original.html` in Chromium und nutzt deren eigene Zeichnungen:

- **Handys**: Standbild (`p/<gruppe>-<name>.webp`) und Dreh-Sprite mit 30 Bildern (`p/<gruppe>-<name>-3d.webp`) aus dem WebGL-3D-Renderer (`window.TK3D`). Auf der Geräteseite lässt sich das Modell mit Maus oder Finger drehen.
- **alle anderen Geräte**: SVG-Zeichnung aus der Funktion `art()` (`p/<gruppe>-<name>.svg`).
- **Kategorien**: Titelbild aus `window.TKArt` (`s/<bereich>.webp`).
- `manifest.json` verknüpft „Gruppen-ID|Gerätename“ mit den Dateien. `build.py` liest nur dieses Manifest. Fehlt ein Gerät darin (z. B. neu hinzugekommen, Bilder noch nicht erzeugt), zeigt die Seite einen neutralen Platzhalter statt abzubrechen.

Nur Änderungen an Gerätedaten (Preise, Teilnoten) brauchen keinen neuen Bilderlauf. Neue Geräte, neue Farben oder geänderte 3D-Datenblätter (`d3`) schon.

## Partner-Links einschalten

In `config.json` den Amazon-Tag eintragen (z. B. `technikkompa-21`). Dann bekommt jedes Gerät einen Button „Bei Amazon ansehen*“, und der Werbehinweis erscheint automatisch auf allen Seiten.
