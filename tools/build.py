#!/usr/bin/env python3
"""Baut die statische Technik-Kompass-Website nach dist/.

Eingaben: src/data.json (Gerätedaten), src/scores.json (Wertungen, mit tools/scores.js
aus der Original-Seite berechnet), config.json, links.json, tiktok.json.
Aufruf: python3 tools/build.py
"""
import html, json, os, re, shutil, itertools
from urllib.parse import quote_plus

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda p: json.load(open(os.path.join(ROOT, p), encoding="utf-8"))
DATA, SCORES, CFG, LINKS, TIKTOK = J("src/data.json"), J("src/scores.json"), J("config.json"), J("links.json"), J("tiktok.json")
DIST = os.path.join(ROOT, "dist")
DOMAIN = CFG["domain"].rstrip("/")
TAG = CFG.get("amazon_tag", "").strip()
YEAR = 2026
e = lambda s: html.escape(str(s), quote=True)

# ---------- Hilfen ----------
def slug(s):
    s = s.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("+", " plus "), ("&", " und ")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def eur(v):
    if v is None: return ""
    if abs(v - round(v)) < 0.005: s = f"{round(v):,}".replace(",", ".")
    else: s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s + " €"

def num(v, d=1):
    if v is None: return "–"
    return f"{v:.{d}f}".replace(".", ",")

BRAND_GROUPS = {"in-ear", "over-ear", "sport-hp", "studio-hp", "consoles", "watches", "chargers", "cables"}
def full_name(g, p):
    n, s = p["n"], p.get("s", "")
    if g["id"] in BRAND_GROUPS and s:
        b = re.split(r" ·|,", s)[0].strip()
        if b and b[0].isalpha() and not any(c.isdigit() for c in b) and b.split()[0].lower() not in n.lower():
            return f"{b} {n}"
    return n

SECT = {s["id"]: s for s in DATA["sections"]}
GROUPS = DATA["groups"]
GBYID = {g["id"]: g for g in GROUPS}

# Geräte-Liste mit Rang, Wertung, URL
for g in GROUPS:
    sc = SCORES[g["id"]]
    g["_cats"] = sc["cats"]
    used = set()
    for i, p in enumerate(g["products"]):
        p["_i"] = i
        p["_tot"] = sc["items"][i]["tot"]
        p["_ca"] = sc["items"][i]["ca"]
        p["_full"] = full_name(g, p)
        sl = slug(p["_full"]) or f"geraet-{i}"
        while sl in used: sl += "-2"
        used.add(sl)
        p["_slug"] = sl
        p["_key"] = f"{g['id']}/{sl}"
        p["_url"] = f"/{g['sect']}/{g['id']}/{sl}/"
    order = sorted(g["products"], key=lambda p: -p["_tot"])
    for r, p in enumerate(order, 1): p["_rank"] = r
    g["_order"] = order
    g["_url"] = f"/{g['sect']}/{g['id']}/"

def groups_of(sid): return [g for g in GROUPS if g["sect"] == sid]

def gtitle(g):
    """Lesbarer Titel einer Rangliste, z. B. 'In-Ear-Kopfhörer'."""
    return g.get("title") or g.get("variant")

# ---------- Bilder (aus tools/visuals.js) ----------
try:
    VIS = J("assets/gen/manifest.json")
except FileNotFoundError:
    VIS = {"products": {}, "sections": {}}

def vis(g, p): return VIS["products"].get(f"{g['id']}|{p['n']}")

def pic(g, p, size="", lazy=True, cls=""):
    """Gerätebild in einem hellen Rahmen. size: CSS-Klasse für Abmessungen."""
    v = vis(g, p)
    if not v: return f'<span class="ph none {cls}"></span>'
    ld = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
    if v["kind"] == "3d":
        return f'<span class="ph {cls}"><img src="/assets/{v["img"]}" width="640" height="800" alt="{e(p["_full"])}"{ld}></span>'
    return f'<span class="ph svg {cls}"><img src="/assets/{v["img"]}" width="400" height="400" alt="Zeichnung {e(p["_full"])}"{ld}></span>'

def spinner(g, p, lazy=False, loop=False):
    """3D-Modell zum Drehen (Handys) oder großes Bild."""
    v = vis(g, p)
    if not v: return '<span class="ph none"></span>'
    if v["kind"] != "3d":
        return f'<img src="/assets/{v["img"]}" width="400" height="400" alt="Zeichnung {e(p["_full"])}">'
    ld = ' loading="lazy"' if lazy else ' fetchpriority="high"'
    return (f'<div class="spin" data-sprite="/assets/{v["spin"]}" data-frames="{v["frames"]}" data-cols="{v.get("cols", v["frames"])}"{" data-loop=\"1\"" if loop else ""} tabindex="0" role="img" '
            f'aria-label="3D-Modell {e(p["_full"])}, zum Drehen ziehen oder Pfeiltasten nutzen"><img src="/assets/{v["img"]}" width="640" height="800" alt=""{ld}></div>')

DRAG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 12h16M8 8l-4 4 4 4M16 8l4 4-4 4"/></svg>'

# ---------- Partner-Links ----------
def amazon_url(p):
    if not TAG: return None
    ov = LINKS.get(p["_key"], {})
    if ov.get("url"): return ov["url"]
    if ov.get("asin"): return f"https://www.amazon.de/dp/{ov['asin']}?tag={quote_plus(TAG)}"
    return f"https://www.amazon.de/s?k={quote_plus(p['_full'])}&tag={quote_plus(TAG)}"

def idealo_url(p):
    return "https://www.idealo.de/preisvergleich/MainSearchProductCategory.html?q=" + quote_plus(p["_full"])

def buy_buttons(p, small=False):
    cls = "btn sm" if small else "btn"
    out = []
    a = amazon_url(p)
    if a: out.append(f'<a class="{cls} amz" href="{e(a)}" rel="sponsored nofollow noopener" target="_blank">Bei Amazon ansehen*</a>')
    out.append(f'<a class="{cls}{" ghost" if a else ""}" href="{e(idealo_url(p))}" rel="nofollow noopener" target="_blank">Preise vergleichen</a>')
    return '<div class="actions">' + "".join(out) + "</div>"

DISCLOSURE = ('<p class="disc">* Werbung: Partner-Link. Kaufst du darüber, bekommt der Technik Kompass eine kleine Provision. '
              'Für dich ändert sich am Preis nichts, und die Wertung hängt nie davon ab. '
              + ('Als Amazon-Partner verdiene ich an qualifizierten Verkäufen. ' if TAG else '')
              + '<a href="/werbung/">Mehr dazu</a></p>') if TAG else ''

def price_line(p):
    if p.get("mp") is None:
        return '<span class="muted">derzeit nicht im Handel</span>'
    return f'<span>ca. <b class="num">{eur(p["mp"])}</b></span>'

def tier(v): return 1 if v >= 85 else 2 if v >= 70 else 3 if v >= 55 else 4

def note_of(v):
    """Schulnote wie in der Original-Seite (noteOf)."""
    g = round((6 - 5 * v / 100) * 10) / 10
    return num(g), ("sehr gut" if g <= 1.5 else "gut" if g <= 2.5 else "befriedigend" if g <= 3.5 else "ausreichend")

def sc(p, small=True):
    v = p["_tot"]
    return f'<span class="sc{" sm" if small else ""} t{tier(v)}" title="{num(v)} von 100 Punkten">{round(v)}</span>'

def medal(r):
    return f'<span class="medal m{r}">{r}</span>' if r <= 3 else f'<span class="medal">{r}</span>'

# ---------- Layout ----------
CSS_V = "3"
ICON_SEARCH = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg>'

def page(path, title, desc, body, crumbs=None, jsonld=None, noindex=False, sect=None, back=None, after="", img=None):
    canon = DOMAIN + path
    ld = []
    if crumbs:
        ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": DOMAIN + u} for i, (n, u) in enumerate(crumbs)]})
    if jsonld: ld.append(jsonld)
    ldh = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    bc = ""
    if crumbs and len(crumbs) > 1:
        bc = '<nav class="crumbs" aria-label="Brotkrumen">' + '<span class="sep">›</span>'.join(
            f'<a href="{e(u)}">{e(n)}</a>' if i < len(crumbs) - 1 else f'<span aria-current="page">{e(n)}</span>' for i, (n, u) in enumerate(crumbs)) + "</nav>"
    nav = "".join(f'<a href="/{s["id"]}/"{" aria-current=\"page\"" if sect == s["id"] else ""}>{e(s["n"])}</a>' for s in DATA["sections"])
    ogi = f'<meta property="og:image" content="{e(DOMAIN + img)}">' if img else ""
    doc = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canon)}">{'<meta name="robots" content="noindex">' if noindex else ''}
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{e(canon)}">{ogi}
<meta name="theme-color" content="#ffffff">
<link rel="icon" href="/assets/icon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/style.css?v={CSS_V}">{ldh}
</head><body>
<a class="skip" href="#inhalt">Zum Inhalt springen</a>
<header class="top"><div class="top-in"><a class="logo" href="/" aria-label="{e(CFG['site_name'])}, zur Startseite"><i><img src="/assets/icon.svg" width="20" height="20" alt=""></i><span>{e(CFG['site_name'])}</span></a>
<div class="srch" role="search"><label class="sr" for="q">Gerät suchen</label>{ICON_SEARCH}<input id="q" type="search" placeholder="Gerät oder Marke suchen, z. B. iPhone" autocomplete="off" role="combobox" aria-expanded="false" aria-controls="q-res"><div class="srch-res" id="q-res" role="listbox"></div></div>
<button class="s-btn" type="button" aria-label="Suche öffnen">{ICON_SEARCH}</button>
<a class="cta" href="/app/#test" title="Persönliche Empfehlung in 2 Minuten">✦ <span>Berater</span></a></div>
<nav class="cats" aria-label="Kategorien"><div class="cats-in">{nav}<a href="/vergleich/">Vergleiche</a></div></nav></header>
<main id="inhalt"><div class="wrap">{bc}{back or ''}</div>{body}</main>
{after}
<footer class="foot"><div class="foot-in">
<div><a class="logo" href="/"><i><img src="/assets/icon.svg" width="20" height="20" alt=""></i><span>{e(CFG['site_name'])}</span></a><p>Unabhängige Geräte-Ranglisten mit offener Formel. Jede Wertung lässt sich nachrechnen. Stand {e(CFG['updated'])}.</p></div>
<div><h4>Beliebt</h4><a href="/handys/handys/">Beste Handys</a><a href="/kopfhoerer/in-ear/">Beste In-Ear-Kopfhörer</a><a href="/laptops/laptops/">Beste Laptops</a><a href="/tv/tvs/">Beste Fernseher</a></div>
<div><h4>Werkzeuge</h4><a href="/app/#test">Persönlicher Berater</a><a href="/vergleich/">Vergleiche</a><a href="/methode/">So wird bewertet</a><a href="/tiktok/">Aus den Videos</a></div>
<div><h4>Rechtliches</h4><a href="/impressum/">Impressum</a><a href="/datenschutz/">Datenschutz</a><a href="/werbung/">Werbung &amp; Partner-Links</a></div>
</div><div class="foot-b"><span>Preise sind Richtwerte und können sich ändern. Links mit * sind Partner-Links.</span><span>© {YEAR} {e(CFG['site_name'])}</span></div></footer>
<button class="totop" type="button" aria-label="Nach oben"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 15l6-6 6 6"/></svg></button>
<script src="/assets/site.js?v={CSS_V}" defer></script>
</body></html>"""
    out = os.path.join(DIST, path.strip("/"), "index.html") if path != "/404.html" else os.path.join(DIST, "404.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(doc)
    if not noindex: SITEMAP.append(canon)

SITEMAP = []

def bar(v, mx=10):
    pct = max(0, min(100, v / mx * 100))
    t = 1 if pct >= 85 else 2 if pct >= 70 else 3 if pct >= 55 else 4
    return f'<i class="bar"><u class="b{t}" style="width:{pct:.0f}%"></u></i>'

def back_link(url, label):
    return f'<a class="back" href="{url}">← {e(label)}</a>'

# ---------- Karten ----------
def product_card(g, p, cat=False, rank=True, first=False):
    return (f'<a class="pc{" first" if first else ""}" href="{p["_url"]}">{medal(p["_rank"]) if rank else ""}{pic(g, p)}'
            + (f'<span class="cat">{e(gtitle(g))}</span>' if cat else "")
            + f'<b>{e(p["_full"])}</b><span class="row"><span class="pr">{price_line(p)}</span>{sc(p)}</span></a>')

def sec_art(sid, cls="art"):
    src = VIS["sections"].get(sid)
    return f'<div class="{cls}"><img src="/assets/{src}" width="960" height="600" alt=""></div>' if src else ""

# ---------- Rangliste ----------
def build_group(g):
    s = SECT[g["sect"]]
    order = g["_order"]
    t = gtitle(g)
    h1 = f"Die besten {t} {YEAR}"
    top = order[:3]
    lead = (f"{len(order)} {t} im Vergleich, bewertet nach fester Formel aus Messwerten und Tests. "
            f"Testsieger ist {top[0]['_full']} mit {round(top[0]['_tot'])} von 100 Punkten.")
    cats = g["_cats"]
    pf = g["profiles"][0]
    sw = sum(pf["w"]) or 1
    wi = sorted(range(len(cats)), key=lambda i: -pf["w"][i])[:3] if len(pf["w"]) == len(cats) else list(range(min(3, len(cats))))
    prices = sorted(p["mp"] for p in order if p.get("mp"))
    rows = []
    for p in order:
        mini = "".join(f'<div><span>{e(cats[ci])}</span>{bar(p["_ca"][ci])}</div>' for ci in wi)
        mp = p.get("mp")
        val = f'{p["_tot"] / mp * 100:.3f}' if mp else "0"
        rows.append(f'<li class="rr" data-r="{p["_rank"]}" data-p="{mp or ""}" data-v="{val}"><a href="{p["_url"]}"><span class="rk">{p["_rank"]}</span>{pic(g, p)}'
                    f'<span class="nm"><b>{e(p["_full"])}</b><small>{e(p.get("s",""))}{(" · " + str(p["y"])) if p.get("y") else ""}</small></span>'
                    f'<span class="mini">{mini}</span><span class="pr">{eur(mp) if mp else "–"}<small>{"ca. Marktpreis" if mp else "nicht im Handel"}</small></span>{sc(p, False)}</a></li>')
    # Preis-Filter: sinnvolle Stufen aus den vorhandenen Preisen
    steps = []
    if len(prices) >= 5:
        for q in (0.25, 0.5, 0.75):
            v = prices[int(len(prices) * q)]
            mag = 10 ** max(1, len(str(int(v))) - 2)
            v = int((v + mag - 1) // mag * mag)
            if v not in steps: steps.append(v)
    flt = ('<label>Bis <select aria-label="Höchstpreis"><option value="">jeder Preis</option>'
           + "".join(f'<option value="{v}">{eur(v)}</option>' for v in steps) + '</select></label>') if steps else ""
    ranking = f"""<div data-rank><div class="tools"><div class="seg" role="group" aria-label="Sortieren"><button type="button" data-sort="score" aria-pressed="true">Wertung</button><button type="button" data-sort="price" aria-pressed="false">Preis</button><button type="button" data-sort="value" aria-pressed="false">Preis-Leistung</button></div>
{flt}<span class="small muted" data-cnt>{len(order)} von {len(order)}</span></div>
<ol class="rl">{''.join(rows)}</ol><p class="empty" hidden>In dieser Preisklasse gibt es hier kein Gerät.</p></div>"""
    trows = []
    for p in order:
        cells = "".join(f'<td class="n">{num(p["_ca"][ci])}</td>' for ci, c in enumerate(cats))
        trows.append(f'<tr><td class="n">{p["_rank"]}</td><th scope="row"><a href="{p["_url"]}">{e(p["_full"])}</a></th><td class="n tot">{round(p["_tot"])}</td>{cells}<td class="n">{eur(p.get("mp")) or "–"}</td></tr>')
    table = (f'<div class="tbox"><table class="rank"><thead><tr><th class="n">#</th><th>Gerät</th><th class="n">Punkte</th>'
             + "".join(f'<th class="n">{e(c)}</th>' for c in cats) + '<th class="n">Preis</th></tr></thead><tbody>' + "".join(trows) + "</tbody></table></div>")
    uses = ""
    if g.get("uses"):
        items = []
        for u in g["uses"]:
            if len(u) >= 3:
                pm = next((p for p in g["products"] if u[1] in (p["n"], p["_full"])), None)
                if pm:
                    items.append(f'<a class="use" href="{pm["_url"]}">{pic(g, pm)}<span><span class="k">{e(u[0])}</span><b>{e(pm["_full"])}</b><span class="d">{e(u[2])}</span></span></a>')
        if items: uses = f'<section class="sec wrap" id="wofuer"><div class="sec-h"><div><h2>Am besten für …</h2><p>Die Stärksten in einzelnen Disziplinen.</p></div></div><div class="uses">{"".join(items)}</div></section>'
    method = "".join(f'<div class="mth"><b>{e(c["n"])}<span>{round(w / sw * 100)} %</span></b><p>{e(c.get("m",""))}</p></div>' for c, w in zip(g["cats"], pf["w"]))
    notes = "".join(f"<li>{e(n)}</li>" for n in g.get("notes", []))
    srcs = "".join(f'<li><a href="{e(u)}" rel="nofollow noopener" target="_blank">{e(n)}</a></li>' for n, u in g.get("sources", [])[:40])
    duels = [f'<a href="{duel_url(a, b)}">{e(a["_full"])} vs. {e(b["_full"])}</a>' for a, b in duel_pairs(g)]
    others = [x for x in groups_of(g["sect"]) if x is not g]
    w = top[0]
    jump = '<a href="#top3">Top 3</a><a href="#rangliste">Rangliste</a>' + ('<a href="#wofuer">Am besten für</a>' if uses else '') + ('<a href="#vergleiche">Vergleiche</a>' if duels else '') + '<a href="#methode">So wird gewertet</a>'
    body = f"""<div class="wrap"><header class="phead"><div><p class="kicker">{e(s['n'])} · Rangliste {YEAR}</p><h1>{e(h1)}</h1><p class="lead">{e(lead)}</p>
<div class="facts"><span>{len(order)} Geräte</span><span>{len(cats)} Kategorien</span>{f'<span>{eur(prices[0])} bis {eur(prices[-1])}</span>' if prices else ''}<span>Stand {e(CFG['updated'])}</span></div></div>{sec_art(g['sect'])}</header></div>
<nav class="jump" aria-label="Abschnitte"><div class="wrap jump-in">{jump}</div></nav>
<section class="sec wrap" id="top3"><div class="sec-h"><div><h2>Die Top 3</h2><p>Die drei Geräte mit den meisten Punkten.</p></div></div>
<div class="podium">{''.join(product_card(g, p, first=(i == 0)) for i, p in enumerate(top))}</div>
<div class="winner"><span class="tr" aria-hidden="true">🏆</span><div><b>Testsieger: {e(w['_full'])}</b><span>{round(w['_tot'])} von 100 Punkten · {price_line(w)}</span></div>{buy_buttons(w, True)}</div></section>
<section class="sec wrap" id="rangliste"><div class="sec-h"><div><h2>Komplette Rangliste</h2><p>Sortiere nach Wertung, Preis oder Preis-Leistung. Tippe ein Gerät an für alle Details.</p></div></div>{ranking}
<details class="box"><summary>Alle Teilnoten als Tabelle</summary><div><p class="small muted">Teilnoten von 1 bis 10. Die Gesamtpunkte gewichten sie wie unter „So wird gewertet“.</p>{table}</div></details></section>
{uses}
{('<section class="sec wrap" id="vergleiche"><div class="sec-h"><div><h2>Beliebte Vergleiche</h2><p>Die Top-Geräte im direkten Duell.</p></div></div><div class="chips">' + ''.join(duels) + '</div></section>') if duels else ''}
<section class="sec wrap" id="methode"><div class="sec-h"><div><h2>So wird gewertet</h2><p>Feste Kategorien mit festen Gewichten. <a href="/methode/">Mehr zur Formel</a> · <a href="/app/">Gewichtung selbst einstellen</a></p></div></div><div class="method">{method}</div>
{('<details class="box"><summary>Hinweise zur Rangliste</summary><div><ul class="notes">' + notes + '</ul></div></details>') if notes else ''}
{('<details class="box"><summary>Quellen</summary><div><ul class="notes">' + srcs + '</ul></div></details>') if srcs else ''}</section>
{('<section class="sec wrap"><div class="sec-h"><h2>Mehr ' + e(s['n']) + '</h2></div><div class="chips">' + ''.join(f'<a href="{x["_url"]}">{e(gtitle(x))}</a>' for x in others) + '</div></section>') if others else ''}
<div class="wrap">{DISCLOSURE}</div>"""
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": h1, "itemListElement": [
        {"@type": "ListItem", "position": p["_rank"], "url": DOMAIN + p["_url"], "name": p["_full"]} for p in order[:10]]}
    page(g["_url"], f"{h1}: Rangliste & Vergleich | {CFG['site_name']}",
         f"{h1} im Vergleich: {top[0]['_full']} vor {top[1]['_full'] if len(top)>1 else ''}. Offene Formel, aktuelle Preise, Stand {CFG['updated']}."[:158],
         body, crumbs=[("Start", "/"), (s["n"], f"/{s['id']}/"), (t, g["_url"])], jsonld=ld, sect=s["id"],
         img=("/assets/" + VIS["sections"][g["sect"]]) if g["sect"] in VIS["sections"] else None)

# ---------- Preisverlauf ----------
def price_chart(p):
    ph = [x for x in (p.get("ph") or []) if x and x[1]]
    if len(ph) < 2: return ""
    vs = [x[1] for x in ph]
    lo, hi = min(vs), max(vs)
    if hi == lo: hi = lo + 1
    pad = (hi - lo) * 0.25
    lo2, hi2 = lo - pad, hi + pad
    n = len(ph)
    pts = [(i / (n - 1) * 100, 100 - (v - lo2) / (hi2 - lo2) * 100) for i, v in enumerate(vs)]
    line = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
    area = f"0,100 {line} 100,100"
    d0, d1 = ph[0][0], ph[-1][0]
    fd = lambda d: f"{d[8:10]}.{d[5:7]}.{d[0:4]}" if len(d) >= 10 else d
    trend = vs[-1] - vs[0]
    tr = (f'<span class="save">{eur(abs(trend))} günstiger seit {fd(d0)}</span>' if trend < 0 else
          f'<span class="muted small">{eur(trend)} teurer seit {fd(d0)}</span>' if trend > 0 else '<span class="muted small">Preis stabil</span>')
    return f"""<div class="card"><h3>Preisverlauf</h3><svg class="pchart" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="Preisverlauf von {eur(vs[0])} auf {eur(vs[-1])}">
<defs><linearGradient id="pg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1f5eff" stop-opacity=".18"/><stop offset="1" stop-color="#1f5eff" stop-opacity="0"/></linearGradient></defs>
<polygon class="ar" points="{area}"/><polyline class="ln" points="{line}"/></svg>
<div class="pleg"><span>{fd(d0)}: {eur(vs[0])}</span><span>{fd(d1)}: {eur(vs[-1])}</span></div><p class="small" style="margin:10px 0 0">{tr} · Tiefster Wert {eur(lo)}</p></div>"""

# ---------- Geräteseite ----------
def build_product(g, p):
    s = SECT[g["sect"]]
    t = gtitle(g)
    order = g["_order"]
    cats = "".join(f'<div class="mrow"><span class="l">{e(c)}</span><span class="v">{num(p["_ca"][ci])}</span>{bar(p["_ca"][ci])}</div>'
                   for ci, c in enumerate(g["_cats"]))
    spec = "".join(f'<div><span>{e(k)}</span><span>{e(v)}</span></div>' for k, v in (p.get("sp") or {}).items() if v not in ("–", "", None))
    de = p.get("de")
    tests = []
    sw = (de or {}).get("sw")
    if sw:
        tests.append(f'<li><span>{e(sw.get("src","Stiftung Warentest"))}</span><span class="v">{e(sw.get("w",""))}{(" (" + num(sw["n"]) + ")") if sw.get("n") is not None else ""}</span>'
                     f'<small>{e(sw.get("h",""))} · <a href="{e(sw["u"])}" rel="nofollow noopener" target="_blank">Quelle</a></small></li>')
    if de and "n" in de:
        tests.append(f'<li><span>Deutsche Testnote <small style="display:inline">(Schnitt aus {de.get("c","?")} Tests)</small></span><span class="v">{num(de.get("n"))} · {e(de.get("w",""))}</span>'
                     f'<small><a href="{e(de["u"])}" rel="nofollow noopener" target="_blank">testberichte.de</a></small></li>')
        for m in de.get("m", [])[:5]: tests.append(f'<li><span>{e(m[0])}</span><span class="v">{e(m[1])}</span></li>')
    for x in (p.get("ext") or [])[:6]:
        tests.append(f'<li><span>{e(x[0])}</span><span class="v">{e(x[1])}</span><small><a href="{e(x[2])}" rel="nofollow noopener" target="_blank">Test lesen</a></small></li>')
    vids = "".join(f'<li><a href="{e(u)}" rel="nofollow noopener" target="_blank">{e(n)}</a></li>' for n, u in (p.get("vid") or [])[:3])
    dq = p.get("dq")
    idx = order.index(p)
    neigh = sorted((x for x in order if x is not p), key=lambda x: (abs(x["_rank"] - p["_rank"]), x["_rank"]))[:4]
    neigh.sort(key=lambda x: x["_rank"])
    duels = [(a, b) for a, b in duel_pairs(g) if p in (a, b)]
    vs = "".join(f'<a href="{duel_url(a, b)}">{e(a["_full"])} vs. {e(b["_full"])}</a>' for a, b in duels)
    var = ", ".join(p.get("var") or [])
    pn = p.get("pn", "")
    h1 = p["_full"]
    v = p["_tot"]
    ng, nl = note_of(v)
    uv, mp = p.get("uvp"), p.get("mp")
    save = f'<span class="save">{round((1 - mp / uv) * 100)} % unter UVP</span>' if uv and mp and mp < uv * 0.97 else ""
    is3d = (vis(g, p) or {}).get("kind") == "3d"
    stage = (f'<div class="stage"><span class="rk">{medal(p["_rank"])}Platz {p["_rank"]} von {len(order)}</span>{spinner(g, p)}'
             + (f'<span class="hint">{DRAG} Ziehen zum Drehen</span>' if is3d else "") + '</div>')
    chart = price_chart(p)
    jump = '<a href="#wertung">Wertung</a>' + ('<a href="#tests">Tests</a>' if tests else '') + ('<a href="#daten">Daten</a>' if spec else '') + '<a href="#alternativen">Alternativen</a>'
    body = f"""<div class="wrap"><section class="pd">{stage}
<div class="pinfo"><p class="kicker">{e(t)}</p><h1>{e(h1)}</h1><p class="sub">{e(p.get('s',''))}{(' · ' + str(p['y'])) if p.get('y') else ''}</p>
<div class="scorebox"><div class="ring t{tier(v)}" style="--p:{v:.1f}"><div><b class="num">{round(v)}</b><span>von 100</span></div></div>
<p><b>Note {ng} ({nl})</b>Platz {p['_rank']} von {len(order)} {e(t)}. <a href="#wertung">So setzt sich die Wertung zusammen</a></p></div>
<div class="buybox"><div class="pr">{f'<b class="num">{eur(mp)}</b>' if mp else '<b>Nicht im Handel</b>'}{f'<s class="num">UVP {eur(uv)}</s>' if uv and mp and mp < uv else ''}{save}</div>
{f'<p class="src">Varianten: {e(var)}</p>' if var else ''}{buy_buttons(p)}<p class="src">{e(pn)}</p></div></div></section></div>
<nav class="jump" aria-label="Abschnitte"><div class="wrap jump-in">{jump}</div></nav>
<section class="sec wrap" id="wertung"><div class="two"><div class="card"><h3>Bewertung im Detail</h3><div class="metric">{cats}</div>
{f'<p class="muted small" style="margin:16px 0 0">Grundlage: {e(dq.get("basis",""))}. {e(dq.get("note",""))}</p>' if dq else ''}</div>
<div style="display:grid;gap:16px">{chart}<div class="card"><h3>In der Rangliste</h3><p class="small muted" style="margin:0 0 12px">Teilnoten von 1 bis 10, gewichtet wie in der <a href="{g['_url']}#methode">Formel für {e(t)}</a>.</p><a class="btn ghost sm" href="{g['_url']}">Alle {len(order)} {e(t)} ansehen</a></div></div></div></section>
{('<section class="sec wrap" id="tests"><div class="two"><div class="card"><h3>Was Tests sagen</h3><ul class="tests">' + ''.join(tests) + '</ul></div>' + (('<div class="card"><h3>Videos</h3><ul class="vids">' + vids + '</ul></div>') if vids else '') + '</div></section>') if tests else ''}
{('<section class="sec wrap" id="daten"><div class="sec-h"><h2>Technische Daten</h2></div><div class="spec">' + spec + '</div></section>') if spec else ''}
<section class="sec wrap" id="alternativen"><div class="sec-h"><div><h2>Direkt daneben in der Rangliste</h2><p>Ähnlich gute Geräte zum Vergleichen.</p></div><a class="more" href="{g['_url']}">Ganze Rangliste</a></div>
<div class="grid">{''.join(product_card(g, x) for x in neigh)}</div>{('<h3 style="margin:28px 0 12px">Direkte Vergleiche</h3><div class="chips">' + vs + '</div>') if vs else ''}</section>
<div class="wrap">{DISCLOSURE}</div>"""
    after = (f'<div class="sticky-buy"><div><b>{e(h1)}</b><span>{round(v)} Punkte · {eur(mp) if mp else "nicht im Handel"}</span></div>'
             f'<a class="btn sm{" amz" if amazon_url(p) else ""}" href="{e(amazon_url(p) or idealo_url(p))}" rel="{"sponsored " if amazon_url(p) else ""}nofollow noopener" target="_blank">{"Bei Amazon*" if amazon_url(p) else "Preise"}</a></div>')
    desc = (f"{h1} im Test-Vergleich: {round(v)} von 100 Punkten, Platz {p['_rank']} von {len(order)} {t}. "
            + (f"Preis ca. {eur(mp)}. " if mp else "") + "Stärken, Daten und Testnoten.")[:158]
    vv = vis(g, p)
    page(p["_url"], f"{h1}: Test, Wertung & Preis | {CFG['site_name']}", desc, body,
         crumbs=[("Start", "/"), (s["n"], f"/{s['id']}/"), (t, g["_url"]), (h1, p["_url"])], sect=s["id"], after=after,
         img=("/assets/" + vv["img"]) if vv and vv["kind"] == "3d" else None)

# ---------- Duelle ----------
def duel_pairs(g):
    if len(g["products"]) < 4: return []
    return list(itertools.combinations(g["_order"][:5], 2))

def duel_url(a, b): return f"/vergleich/{a['_slug']}-vs-{b['_slug']}/"

DUELS = []
def build_duel(g, a, b):
    t = gtitle(g)
    win = a if a["_tot"] >= b["_tot"] else b
    lose = b if win is a else a
    diff = win["_tot"] - lose["_tot"]
    rows = "".join(
        f'<tr><th scope="row">{e(c)}</th><td class="n{" best" if a["_ca"][ci] > b["_ca"][ci] else ""}">{num(a["_ca"][ci])}</td>'
        f'<td class="n{" best" if b["_ca"][ci] > a["_ca"][ci] else ""}">{num(b["_ca"][ci])}</td></tr>' for ci, c in enumerate(g["_cats"]))
    keys = [k for k in (a.get("sp") or {}) if k in (b.get("sp") or {})][:12]
    srows = "".join(f'<tr><th scope="row">{e(k)}</th><td>{e(a["sp"][k])}</td><td>{e(b["sp"][k])}</td></tr>' for k in keys)
    better_a = [c for ci, c in enumerate(g["_cats"]) if a["_ca"][ci] - b["_ca"][ci] >= 0.5]
    better_b = [c for ci, c in enumerate(g["_cats"]) if b["_ca"][ci] - a["_ca"][ci] >= 0.5]
    def why(x, lst): return f"<li><b>{e(x['_full'])}</b> ist klar besser bei: {e(', '.join(lst))}.</li>" if lst else ""
    verdict = ("Beide liegen fast gleichauf, entscheide nach Preis und dem, was dir wichtig ist." if diff < 1.5
               else f"{win['_full']} gewinnt mit {round(win['_tot'])} zu {round(lose['_tot'])} Punkten.")
    h1 = f"{a['_full']} vs. {b['_full']}"
    def vc(x):
        w = x is win and diff >= 1.5
        return (f'<div class="vc{" win" if w else ""}">{"<span class=wl>Gewinner</span>" if w else ""}<a href="{x["_url"]}">{pic(g, x, lazy=False)}</a><a href="{x["_url"]}"><b>{e(x["_full"])}</b></a>'
                f'{sc(x, False)}<span class="small muted">Platz {x["_rank"]} · {price_line(x)}</span>{buy_buttons(x, True)}</div>')
    body = f"""<div class="wrap"><header class="phead" style="grid-template-columns:1fr"><div><p class="kicker">Vergleich · {e(t)}</p><h1>{e(h1)}</h1><p class="lead">{e(verdict)}</p></div></header>
<section class="vs" style="margin-top:20px">{vc(a)}<div class="mid"><span>vs.</span></div>{vc(b)}</section>
{('<section class="sec"><div class="verdict"><b>Kurz gesagt</b><ul class="notes">' + why(a, better_a) + why(b, better_b) + '</ul></div></section>') if (better_a or better_b) else ''}
<section class="sec"><div class="sec-h"><h2>Teilnoten</h2></div><div class="tbox"><table class="cmp"><thead><tr><th></th><th class="n">{e(a['_full'])}</th><th class="n">{e(b['_full'])}</th></tr></thead><tbody>
<tr><th scope="row">Gesamt</th><td class="n"><b>{round(a['_tot'])}</b></td><td class="n"><b>{round(b['_tot'])}</b></td></tr>{rows}
<tr><th scope="row">Preis</th><td class="n">{eur(a.get('mp')) or '–'}</td><td class="n">{eur(b.get('mp')) or '–'}</td></tr></tbody></table></div></section>
{('<section class="sec"><div class="sec-h"><h2>Daten nebeneinander</h2></div><div class="tbox"><table class="cmp"><tbody>' + srows + '</tbody></table></div></section>') if srows else ''}
<p style="margin-top:28px"><a class="btn ghost" href="{g['_url']}">Alle {e(t)} in der Rangliste</a></p>{DISCLOSURE}</div>"""
    url = duel_url(a, b)
    DUELS.append((g, a, b, url))
    page(url, f"{h1}: Welches ist besser? | {CFG['site_name']}",
         f"{h1} im direkten Vergleich: {verdict} Teilnoten, Preise und Daten nebeneinander."[:158], body,
         crumbs=[("Start", "/"), ("Vergleiche", "/vergleich/"), (h1, url)], back=back_link(g["_url"], f"Zurück zu {t}"))

def build_duel_index():
    by = {}
    for g, a, b, u in DUELS: by.setdefault(g["id"], []).append((a, b, u))
    secs = "".join(f'<section class="sec wrap"><div class="sec-h"><h2>{e(gtitle(GBYID[gid]))}</h2><a class="more" href="{GBYID[gid]["_url"]}">Rangliste</a></div><div class="chips">' + "".join(
        f'<a href="{u}">{e(a["_full"])} vs. {e(b["_full"])}</a>' for a, b, u in lst) + "</div></section>" for gid, lst in by.items())
    page("/vergleich/", f"Geräte-Vergleiche: Welches ist besser? | {CFG['site_name']}",
         "Direkte Duelle der besten Handys, Kopfhörer, Laptops, Fernseher und mehr. Teilnoten, Preise und Daten nebeneinander.",
         f'<div class="wrap"><header class="phead" style="grid-template-columns:1fr"><div><p class="kicker">Vergleiche</p><h1>Welches ist besser?</h1><p class="lead">Die Top-Geräte jeder Rangliste im direkten Duell, mit Teilnoten, Preisen und Daten nebeneinander.</p></div></header></div>{secs}',
         crumbs=[("Start", "/"), ("Vergleiche", "/vergleich/")])

# ---------- Kategorie- und Startseite ----------
def build_section(s):
    gs = groups_of(s["id"])
    n = sum(len(g["products"]) for g in gs)
    blocks = []
    for g in gs:
        blocks.append(f'<section class="sec wrap"><div class="sec-h"><div><h2>{e(gtitle(g))}</h2><p>{len(g["products"])} Geräte in der Rangliste</p></div><a class="more" href="{g["_url"]}">Ganze Rangliste</a></div>'
                      f'<div class="grid g3">{"".join(product_card(g, p, first=(i == 0)) for i, p in enumerate(g["_order"][:3]))}</div></section>')
    chips = "".join(f'<a href="{g["_url"]}">{e(gtitle(g))} <span class="num">{len(g["products"])}</span></a>' for g in gs)
    page(f"/{s['id']}/", f"{s['n']} {YEAR}: die besten Geräte im Vergleich | {CFG['site_name']}",
         f"{s['n']}: {s.get('d','')}. Ranglisten mit offener Formel, aktuelle Preise und Vergleiche.",
         f'<div class="wrap"><header class="phead"><div><p class="kicker">Kategorie</p><h1>{e(s["n"])}</h1><p class="lead">{e(s.get("d",""))}. {n} Geräte, bewertet nach fester Formel.</p>'
         f'{("<div class=facts style=margin-top:22px></div><div class=chips>" + chips + "</div>") if len(gs) > 1 else ""}</div>{sec_art(s["id"])}</header></div>{"".join(blocks)}<div class="wrap">{DISCLOSURE}</div>',
         crumbs=[("Start", "/"), (s["n"], f"/{s['id']}/")], sect=s["id"],
         img=("/assets/" + VIS["sections"][s["id"]]) if s["id"] in VIS["sections"] else None)

def build_home():
    total = sum(len(g["products"]) for g in GROUPS)
    tiles = "".join(
        f'<a class="tile" href="/{s["id"]}/">{sec_art(s["id"])}<span class="tx"><b>{e(s["n"])}</b><span>{e(s.get("d",""))}</span>'
        f'<span class="cnt">{sum(len(g["products"]) for g in groups_of(s["id"]))} Geräte →</span></span></a>' for s in DATA["sections"])
    picks = []
    for gid in ("handys", "in-ear", "over-ear", "laptops", "tablets", "watches", "tvs", "consoles"):
        g = GBYID.get(gid)
        if g: picks.append(product_card(g, g["_order"][0], cat=True, rank=False))
    hg = GBYID["handys"]; hp = hg["_order"][0]
    ng, nl = note_of(hp["_tot"])
    news = sorted(DATA.get("news", []), key=lambda n: (n.get("d") or "")[::-1], reverse=True)
    news = [n for n in DATA.get("news", []) if n.get("t")][:4]
    nh = "".join(f'<article class="nx"><span class="m"><em>{e(n.get("st","News").capitalize())}</em>{e(n.get("d",""))} · {e(n.get("cat",""))}</span><b>{e(n["t"])}</b>'
                 f'{("<p>" + e(n["s"][:180]) + ("…" if len(n["s"]) > 180 else "") + "</p>") if n.get("s") else ""}</article>' for n in news)
    body = f"""<section class="hero-home"><div class="wrap hh"><div><p class="kicker">Unabhängige Ranglisten {YEAR}</p>
<h1>Finde das Gerät, das <em>wirklich</em> zu dir passt.</h1>
<p class="lead">{total} Handys, Kopfhörer, Laptops, Fernseher und mehr, bewertet nach einer festen Formel aus Messwerten und Tests. Nicht nach Bauchgefühl und nicht nach Provision.</p>
<div class="actions"><a class="btn" href="/app/#test">Persönliche Empfehlung holen</a><a class="btn ghost" href="#kategorien">Ranglisten ansehen</a></div>
<ul class="trust"><li>Offener Rechenweg</li><li>Preise regelmäßig aktualisiert</li><li>Ohne Werbebanner</li></ul></div>
<a class="spot" href="{hp['_url']}"><span class="lbl">Platz 1 der Handys</span>{spinner(hg, hp, loop=True)}<span class="spin-hint">{DRAG} Ziehen zum Drehen</span><b>{e(hp['_full'])}</b><span class="meta">{sc(hp)} Note {ng} · {price_line(hp)}</span></a></div></section>
<section class="sec wrap" id="kategorien"><div class="sec-h"><div><h2>Alle Kategorien</h2><p>Wähle aus, was du suchst. Jede Kategorie hat eigene Ranglisten.</p></div></div><div class="tiles">{tiles}</div></section>
<section class="sec wrap"><div class="sec-h"><div><h2>Die Testsieger</h2><p>Platz 1 in den beliebtesten Ranglisten.</p></div><a class="more" href="/vergleich/">Alle Vergleiche</a></div><div class="grid">{''.join(picks)}</div></section>
<section class="sec wrap"><div class="sec-h"><div><h2>So funktioniert der Kompass</h2></div></div><div class="steps">
<div class="step"><i>1</i><h3>Feste Formel</h3><p>Jede Rangliste hat feste Kategorien und Gewichte. Messwerte werden immer gleich in Punkte umgerechnet.</p></div>
<div class="step"><i>2</i><h3>Echte Tests</h3><p>Grundlage sind Labormessungen und Testberichte, mit Quellen bei jedem Gerät.</p></div>
<div class="step"><i>3</i><h3>Deine Wahl</h3><p>Im Berater stellst du ein, was dir wichtig ist, und bekommst deine eigene Rangliste.</p></div></div></section>
{('<section class="sec wrap"><div class="sec-h"><div><h2>Neu in der Technik-Welt</h2><p>Was gerade vorgestellt wurde und bald in die Ranglisten kommt.</p></div></div><div class="news">' + nh + '</div></section>') if nh else ''}
<section class="sec wrap"><div class="band"><div><h2>Unsicher, was du brauchst?</h2><p>Beantworte ein paar kurze Fragen und bekomm drei passende Geräte mit Begründung. Dauert etwa zwei Minuten.</p></div><a class="btn" href="/app/#test">Berater starten</a></div></section>
<div class="wrap">{DISCLOSURE}</div>"""
    page("/", f"{CFG['site_name']}: unabhängige Geräte-Ranglisten {YEAR}",
         f"{total} Geräte mit offener Formel bewertet: die besten Handys, Kopfhörer, Laptops, Fernseher und mehr im Vergleich. Aktuelle Preise, ehrliche Wertung.",
         body, jsonld={"@context": "https://schema.org", "@type": "WebSite", "name": CFG["site_name"], "url": DOMAIN + "/"},
         img=("/assets/" + vis(hg, hp)["img"]) if vis(hg, hp) else None)

# ---------- TikTok ----------
def build_tiktok():
    items = []
    for it in TIKTOK:
        g = GBYID[it["group"]]
        p = next(x for x in g["products"] if x["n"] == it["product"])
        vids = "".join(f'<span class="vtag" id="{e(v)}">Video {e(v[1:])}</span>' for v in it.get("videos", []))
        use = next((u for u in g.get("uses", []) if len(u) >= 2 and u[1] in (p["n"], p["_full"])), None)
        use_h = f'<p class="tip"><b>Tipp im Kompass: {e(use[0])}.</b> {e(use[2]) if len(use) > 2 else ""}</p>' if use else ""
        items.append(f"""<article class="tk" id="{e(it['id'])}"><a href="{p['_url']}">{pic(g, p)}</a><div>{vids}<p class="kicker" style="margin:0 0 6px">{e(it['title'])}</p>
<h2><a href="{p['_url']}">{e(p['_full'])}</a></h2><div class="tkm">{sc(p)}<span>Platz {p['_rank']} von {len(g['products'])} {e(gtitle(g))}</span><span>{price_line(p)}</span></div>
<p>{e(it['why'])}</p>{use_h}{f'<p class="tip">{e(it["tip"])}</p>' if it.get('tip') else ''}{buy_buttons(p)}</div></article>""")
    body = f"""<div class="wrap"><header class="phead" style="grid-template-columns:1fr"><div><p class="kicker">Aus den TikTok-Videos</p><h1>Alles aus den Videos</h1><p class="lead">Jedes Produkt aus den TikToks an einem Ort, mit Wertung und Preis. Jedes steht auch in der Rangliste mit offener Wertung.</p></div></header>
<div class="tkl" style="margin-top:24px">{''.join(items)}</div>{DISCLOSURE}</div>"""
    page("/tiktok/", f"Aus den Videos | {CFG['site_name']}", "Die Produkte aus den Technik-Kompass-Videos mit Wertung, Preis und Link.", body,
         crumbs=[("Start", "/"), ("Aus den Videos", "/tiktok/")])

# ---------- Suchindex ----------
def build_search():
    out = []
    for g in GROUPS:
        for p in g["_order"]:
            v = vis(g, p)
            out.append({"n": p["_full"], "g": gtitle(g), "u": p["_url"], "s": round(p["_tot"], 1), "r": p["_rank"],
                        "b": p.get("s", ""), **({"i": "/assets/" + v["img"]} if v else {})})
    out.sort(key=lambda x: -x["s"])
    os.makedirs(os.path.join(DIST, "assets"), exist_ok=True)
    json.dump(out, open(os.path.join(DIST, "assets/search.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

# ---------- Rechtliches und Methode ----------
def build_legal():
    im = CFG["impressum"]
    page("/impressum/", f"Impressum | {CFG['site_name']}", "Impressum des Technik Kompass.", f"""<div class="wrap prose"><h1>Impressum</h1>
<h2>Angaben gemäß § 5 DDG</h2><p>{e(im['name'])}<br>{e(im['street'])}<br>{e(im['city'])}</p>
<h2>Kontakt</h2><p>E-Mail: {e(im['email'])}{('<br>Telefon: ' + e(im['phone'])) if im.get('phone') else ''}</p>
<h2>Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV</h2><p>{e(im['name'])}, Anschrift wie oben</p>
<h2>Verbraucherstreitbeilegung</h2><p>Ich bin nicht bereit und nicht verpflichtet, an Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle teilzunehmen.</p>
<h2>Haftung für Links</h2><p>Diese Seite enthält Links zu externen Websites. Auf deren Inhalte habe ich keinen Einfluss, dafür ist der jeweilige Anbieter verantwortlich. Werden mir Rechtsverstöße bekannt, entferne ich solche Links umgehend.</p></div>""",
         crumbs=[("Start", "/"), ("Impressum", "/impressum/")])
    page("/datenschutz/", f"Datenschutz | {CFG['site_name']}", "Datenschutzerklärung des Technik Kompass.", f"""<div class="wrap prose"><h1>Datenschutzerklärung</h1>
<p>Kurz gesagt: Diese Seite setzt keine Cookies, nutzt kein Google Analytics und keine Werbe-Tracker. Es gibt keine Anmeldung und kein Kontaktformular.</p>
<h2>1. Verantwortlicher</h2><p>{e(im['name'])}, {e(im['street'])}, {e(im['city'])}, E-Mail: {e(im['email'])}</p>
<h2>2. Hosting</h2><p>Die Seite wird bei [GitHub Pages (GitHub Inc., USA) / Cloudflare Pages (Cloudflare Inc., USA)] gehostet. Beim Aufruf verarbeitet der Anbieter technisch notwendige Daten wie IP-Adresse, Datum und Uhrzeit, aufgerufene Seite und Browser-Typ, um die Seite auszuliefern und vor Angriffen zu schützen. Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an einer sicheren, funktionierenden Website). Der Anbieter ist unter dem EU-US Data Privacy Framework zertifiziert.</p>
<h2>3. Besucherstatistik</h2><p>[Nur falls aktiviert:] Ich nutze Cloudflare Web Analytics. Das Tool setzt keine Cookies und speichert keine IP-Adressen. Es zählt nur, wie oft welche Seite aufgerufen wird. Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO.</p>
<h2>4. Partner-Links</h2><p>Links mit * führen zu Partnerprogrammen wie dem Amazon-Partnerprogramm oder Awin. Erst wenn du einen solchen Link anklickst, setzt der Shop auf seiner eigenen Seite Cookies, um den Kauf zuzuordnen. Dafür ist der jeweilige Shop verantwortlich, Details stehen in dessen Datenschutzerklärung. Auf dieser Seite selbst werden dafür keine Daten erhoben.</p>
<h2>5. Lokaler Speicher im Berater</h2><p>Der interaktive Berater unter /app/ speichert Einstellungen wie deine Merkliste nur in deinem eigenen Browser (Local Storage). Diese Daten verlassen dein Gerät nicht und lassen sich jederzeit über die Browser-Einstellungen löschen.</p>
<h2>6. Deine Rechte</h2><p>Du hast das Recht auf Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung, Datenübertragbarkeit und Widerspruch (Art. 15 bis 21 DSGVO). Schreib dazu einfach an die oben genannte E-Mail-Adresse. Außerdem kannst du dich bei einer Datenschutz-Aufsichtsbehörde beschweren.</p>
<p class="muted small">Stand: {e(CFG['updated'])}</p></div>""", crumbs=[("Start", "/"), ("Datenschutz", "/datenschutz/")])
    page("/werbung/", f"Werbung & Partner-Links | {CFG['site_name']}", "Wie sich der Technik Kompass finanziert.", f"""<div class="wrap prose"><h1>Werbung &amp; Partner-Links</h1>
<p>Der Technik Kompass ist kostenlos und ohne Werbebanner. Finanziert wird er über Partner-Links. Sie sind mit einem Sternchen (*) markiert.</p>
<p>Kaufst du nach einem Klick auf so einen Link etwas, bekommt der Technik Kompass vom Shop eine kleine Provision. Für dich ändert sich am Preis nichts.</p>
<p><b>Die Wertung hängt nie davon ab.</b> Alle Punkte kommen aus derselben festen Formel, egal ob es für ein Gerät einen Partner-Link gibt oder nicht. Den Rechenweg siehst du bei jedem Gerät.</p>
{'<p>Als Amazon-Partner verdiene ich an qualifizierten Verkäufen.</p>' if TAG else ''}
<p>Die Links „Preise vergleichen“ führen zu idealo und sind keine Partner-Links.</p></div>""", crumbs=[("Start", "/"), ("Werbung", "/werbung/")])
    learn = "".join(f'<section class="sec wrap"><h2>{e(l["t"])}</h2><p class="lead">{e(l.get("x",""))}</p><ul class="notes">'
                    + "".join(f'<li><b>{e(i["t"])}</b>: {e(i.get("x",""))}</li>' for i in l.get("it", [])) + "</ul></section>"
                    for l in DATA.get("learn", [])[:4])
    page("/methode/", f"So wird bewertet | {CFG['site_name']}", "Wie der Technik Kompass aus Messwerten und Tests Punkte macht: feste Formel, offener Rechenweg.",
         f'<div class="wrap"><header class="phead" style="grid-template-columns:1fr"><div><p class="kicker">Methode</p><h1>So wird bewertet</h1><p class="lead">Jede Rangliste hat feste Kategorien mit festen Gewichten. Messwerte werden immer nach derselben Formel in Punkte umgerechnet. Fehlt ein Messwert, zählt ein Testurteil und die Stelle ist als geschätzt markiert.</p></div></header></div>{learn}',
         crumbs=[("Start", "/"), ("Methode", "/methode/")])
    page("/404.html", f"Seite nicht gefunden | {CFG['site_name']}", "Diese Seite gibt es nicht.",
         '<div class="wrap"><header class="phead" style="grid-template-columns:1fr"><div><p class="kicker">Fehler 404</p><h1>Seite nicht gefunden</h1><p class="lead">Vielleicht wurde das Gerät umbenannt. Nutze oben die Suche oder geh hier weiter:</p><div class="actions" style="margin-top:20px"><a class="btn" href="/">Zur Startseite</a><a class="btn ghost" href="/vergleich/">Vergleiche</a></div></div></header></div>', noindex=True)

# ---------- Ausgabe ----------
def main():
    if os.path.isdir(DIST): shutil.rmtree(DIST)
    os.makedirs(DIST)
    shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(DIST, "assets"))
    # Interaktive Original-Seite als /app/
    app = open(os.path.join(ROOT, "src/original.html"), encoding="utf-8").read()
    app = app.replace('<meta charset=utf8>', f'<meta charset=utf8><meta name="robots" content="noindex"><link rel="canonical" href="{DOMAIN}/">', 1)
    os.makedirs(os.path.join(DIST, "app"))
    open(os.path.join(DIST, "app/index.html"), "w", encoding="utf-8").write(app)
    build_home()
    for s in DATA["sections"]: build_section(s)
    for g in GROUPS:
        build_group(g)
        for p in g["products"]: build_product(g, p)
        for a, b in duel_pairs(g): build_duel(g, a, b)
    build_duel_index(); build_tiktok(); build_legal(); build_search()
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"<url><loc>{e(u)}</loc></url>\n" for u in SITEMAP) + "</urlset>\n"
    open(os.path.join(DIST, "sitemap.xml"), "w").write(sm)
    open(os.path.join(DIST, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")
    open(os.path.join(DIST, ".nojekyll"), "w").write("")
    if "DEINE-DOMAIN" not in DOMAIN:
        open(os.path.join(DIST, "CNAME"), "w").write(DOMAIN.split("://", 1)[1] + "\n")
    print(f"{len(SITEMAP)} Seiten gebaut, Partner-Tag {'aktiv' if TAG else 'noch leer'}")

if __name__ == "__main__":
    main()
