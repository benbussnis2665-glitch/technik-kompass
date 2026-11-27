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
    if a: out.append(f'<a class="{cls}" href="{e(a)}" rel="sponsored nofollow noopener" target="_blank">Bei Amazon ansehen*</a>')
    out.append(f'<a class="{cls} ghost" href="{e(idealo_url(p))}" rel="nofollow noopener" target="_blank">Preise vergleichen</a>')
    return '<div class="actions">' + "".join(out) + "</div>"

DISCLOSURE = ('<p class="disc">* Werbung: Partner-Link. Kaufst du darüber, bekommt der Technik Kompass eine kleine Provision. '
              'Für dich ändert sich am Preis nichts, und die Wertung hängt nie davon ab. '
              + ('Als Amazon-Partner verdiene ich an qualifizierten Verkäufen. ' if TAG else '')
              + '<a href="/werbung/">Mehr dazu</a></p>') if TAG else ''

def price_line(p):
    if p.get("mp") is None:
        return '<span class="muted">derzeit nicht regulär im Handel</span>'
    return f'<span>ca. <b class="num">{eur(p["mp"])}</b></span>'

# ---------- Layout ----------
CSS_V = "1"
def page(path, title, desc, body, crumbs=None, jsonld=None, noindex=False):
    canon = DOMAIN + path
    ld = []
    if crumbs:
        ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": DOMAIN + u} for i, (n, u) in enumerate(crumbs)]})
    if jsonld: ld.append(jsonld)
    ldh = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    bc = ""
    if crumbs:
        bc = '<nav class="crumbs" aria-label="Brotkrumen">' + " › ".join(
            f'<a href="{e(u)}">{e(n)}</a>' if i < len(crumbs) - 1 else f'<span>{e(n)}</span>' for i, (n, u) in enumerate(crumbs)) + "</nav>"
    nav = "".join(f'<a href="/{s["id"]}/">{e(s["n"])}</a>' for s in DATA["sections"])
    doc = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canon)}">{'<meta name="robots" content="noindex">' if noindex else ''}
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{e(canon)}">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#0c0c0e" media="(prefers-color-scheme: dark)">
<link rel="icon" href="/assets/icon.svg" type="image/svg+xml"><link rel="stylesheet" href="/assets/style.css?v={CSS_V}">{ldh}
</head><body>
<header class="bar"><div class="bar-in"><a class="logo" href="/"><img src="/assets/icon.svg" width="22" height="22" alt="">{e(CFG['site_name'])}</a>
<a class="tool" href="/app/">Berater &amp; Test</a></div><nav class="nav" aria-label="Kategorien">{nav}</nav></header>
<main class="wrap">{bc}{body}</main>
<footer class="wrap foot"><div><b>{e(CFG['site_name'])}</b>: unabhängige Geräte-Ranglisten mit offener Formel. Stand {e(CFG['updated'])}.</div>
<div class="flinks"><a href="/methode/">So wird bewertet</a><a href="/vergleich/">Vergleiche</a><a href="/tiktok/">Aus den Videos</a><a href="/werbung/">Werbung &amp; Partner-Links</a><a href="/impressum/">Impressum</a><a href="/datenschutz/">Datenschutz</a></div>
<div class="muted small">Preise sind Richtwerte und können sich ändern. Links mit * sind Partner-Links.</div></footer>
</body></html>"""
    out = os.path.join(DIST, path.strip("/"), "index.html") if path != "/404.html" else os.path.join(DIST, "404.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(doc)
    if not noindex: SITEMAP.append(canon)

SITEMAP = []

def bar(v, mx=10):
    pct = max(0, min(100, v / mx * 100))
    tier = 1 if pct >= 85 else 2 if pct >= 70 else 3 if pct >= 55 else 4
    return f'<i class="sbar"><u class="b{tier}" style="width:{pct:.0f}%"></u></i>'

def score_badge(p):
    return f'<span class="score"><b class="num">{round(p["_tot"])}</b><small>/100</small></span>'

# ---------- Seiten ----------
def product_card(g, p, big=False):
    return (f'<a class="pod{" p1" if p["_rank"]==1 else ""}" href="{p["_url"]}"><span class="r">Platz {p["_rank"]}</span>'
            f'<b>{e(p["_full"])}</b>{score_badge(p)}<span class="pr">{price_line(p)}</span></a>')

def build_group(g):
    s = SECT[g["sect"]]
    order = g["_order"]
    t = gtitle(g)
    h1 = f"Die besten {t} {YEAR}"
    top = order[:3]
    lead = (f"{len(order)} {t} im Vergleich, bewertet nach fester Formel aus Messwerten und Tests. "
            f"Testsieger ist {top[0]['_full']} mit {round(top[0]['_tot'])} von 100 Punkten.")
    cats = g["_cats"]
    rows = []
    for p in order:
        cells = "".join(f'<td class="n" data-l="{e(c)}">{num(p["_ca"][ci])}</td>' for ci, c in enumerate(cats))
        rows.append(f'<tr><td class="n rk">{p["_rank"]}</td><th scope="row"><a href="{p["_url"]}">{e(p["_full"])}</a>'
                    f'<small>{e(p.get("s",""))}</small></th><td class="n tot">{round(p["_tot"])}</td>{cells}'
                    f'<td class="n">{eur(p.get("mp")) or "–"}</td></tr>')
    table = (f'<div class="tbox"><table class="rank"><thead><tr><th class="n">#</th><th>Gerät</th><th class="n">Punkte</th>'
             + "".join(f'<th class="n">{e(c)}</th>' for c in cats) + '<th class="n">Preis</th></tr></thead><tbody>'
             + "".join(rows) + "</tbody></table></div>")
    uses = ""
    if g.get("uses"):
        items = []
        for u in g["uses"]:
            if len(u) >= 3:
                pm = next((p for p in g["products"] if u[1] in (p["n"], p["_full"])), None)
                nm = f'<a href="{pm["_url"]}">{e(pm["_full"])}</a>' if pm else e(u[1])
                items.append(f'<div class="use"><span class="k">{e(u[0])}</span><span class="v">{nm}</span><span class="d">{e(u[2])}</span></div>')
        uses = f'<section><h2>Am besten für …</h2><div class="uses">{"".join(items)}</div></section>'
    pf = g["profiles"][0]
    sw = sum(pf["w"]) or 1
    method = "".join(f'<li><b>{e(c["n"])}</b> ({round(w / sw * 100)} %): {e(c.get("m",""))}</li>' for c, w in zip(g["cats"], pf["w"]))
    notes = "".join(f"<li>{e(n)}</li>" for n in g.get("notes", []))
    srcs = "".join(f'<li><a href="{e(u)}" rel="nofollow noopener" target="_blank">{e(n)}</a></li>' for n, u in g.get("sources", [])[:40])
    duels = [f'<a href="{duel_url(a, b)}">{e(a["_full"])} vs. {e(b["_full"])}</a>' for a, b in duel_pairs(g)]
    others = [x for x in groups_of(g["sect"]) if x is not g]
    body = f"""<div class="hero"><p class="eyebrow">{e(s['n'])}</p><h1>{e(h1)}</h1><p class="lead">{e(lead)}</p></div>
<section class="top3">{''.join(product_card(g, p) for p in top)}</section>
<section class="buy1"><div><b>Testsieger: {e(top[0]['_full'])}</b><span>{price_line(top[0])}</span></div>{buy_buttons(top[0])}</section>
{uses}
<section><h2>Komplette Rangliste</h2><p class="muted small">Teilnoten von 1 bis 10. Die Gesamtpunkte gewichten sie so, wie unten unter „So wird gewertet“ steht.</p>{table}</section>
{'<section><h2>Beliebte Vergleiche</h2><div class="chips">' + ''.join(duels) + '</div></section>' if duels else ''}
<section><h2>So wird gewertet</h2><ul class="notes">{method}</ul>{('<h3>Hinweise</h3><ul class="notes">' + notes + '</ul>') if notes else ''}
<p class="small"><a href="/methode/">Wie die Formel funktioniert</a> · <a href="/app/">Gewichtung selbst einstellen</a></p></section>
{('<section><h2>Mehr ' + e(s['n']) + '</h2><div class="chips">' + ''.join(f'<a href="{x["_url"]}">{e(gtitle(x))}</a>' for x in others) + '</div></section>') if others else ''}
{('<details class="src"><summary>Quellen</summary><ul class="srcs">' + srcs + '</ul></details>') if srcs else ''}
{DISCLOSURE}"""
    ld = {"@context": "https://schema.org", "@type": "ItemList", "name": h1, "itemListElement": [
        {"@type": "ListItem", "position": p["_rank"], "url": DOMAIN + p["_url"], "name": p["_full"]} for p in order[:10]]}
    page(g["_url"], f"{h1}: Rangliste & Vergleich | {CFG['site_name']}",
         f"{h1} im Vergleich: {top[0]['_full']} vor {top[1]['_full'] if len(top)>1 else ''}. Offene Formel, aktuelle Preise, Stand {CFG['updated']}."[:158],
         body, crumbs=[("Start", "/"), (s["n"], f"/{s['id']}/"), (t, g["_url"])], jsonld=ld)

def build_product(g, p):
    s = SECT[g["sect"]]
    t = gtitle(g)
    order = g["_order"]
    cats = "".join(f'<div class="mrow"><span class="l">{e(c)}</span>{bar(p["_ca"][ci])}<span class="v num">{num(p["_ca"][ci])}</span></div>'
                   for ci, c in enumerate(g["_cats"]))
    spec = "".join(f'<div><span>{e(k)}</span><span>{e(v)}</span></div>' for k, v in (p.get("sp") or {}).items() if v not in ("–", "", None))
    de = p.get("de")
    tests = []
    sw = (de or {}).get("sw")
    if sw:
        tests.append(f'<li><b>{e(sw.get("src","Stiftung Warentest"))}: {e(sw.get("w",""))} {(" (" + num(sw["n"]) + ")") if sw.get("n") is not None else ""}</b> · {e(sw.get("h",""))} · '
                     f'<a href="{e(sw["u"])}" rel="nofollow noopener" target="_blank">Quelle</a></li>')
    if de and "n" in de:
        tests.append(f'<li><b>Deutsche Testnote {num(de.get("n"))}</b> ({e(de.get("w",""))}, Schnitt aus {de.get("c","?")} Tests) · '
                     f'<a href="{e(de["u"])}" rel="nofollow noopener" target="_blank">testberichte.de</a></li>')
        for m in de.get("m", [])[:5]: tests.append(f"<li>{e(m[0])}: {e(m[1])}</li>")
    for x in (p.get("ext") or [])[:6]:
        tests.append(f'<li>{e(x[0])}: {e(x[1])} · <a href="{e(x[2])}" rel="nofollow noopener" target="_blank">Test lesen</a></li>')
    vids = "".join(f'<li><a href="{e(u)}" rel="nofollow noopener" target="_blank">{e(n)}</a></li>' for n, u in (p.get("vid") or [])[:3])
    dq = p.get("dq")
    idx = order.index(p)
    neigh = order[max(0, idx - 2): idx] + order[idx + 1: idx + 3]
    duels = [(a, b) for a, b in duel_pairs(g) if p in (a, b)]
    rivals = "".join(f'<a href="{x["_url"]}">{e(x["_full"])} <span class="num">{round(x["_tot"])}</span></a>' for x in neigh)
    vs = "".join(f'<a href="{duel_url(a, b)}">{e(a["_full"])} vs. {e(b["_full"])}</a>' for a, b in duels)
    var = ", ".join(p.get("var") or [])
    pn = p.get("pn", "")
    h1 = p["_full"]
    body = f"""<div class="hero pd"><div><p class="eyebrow">{e(t)} · Platz {p['_rank']} von {len(order)}</p><h1>{e(h1)}</h1>
<p class="lead">{e(p.get('s',''))}{(' · ' + str(p['y'])) if p.get('y') else ''}</p></div>
<div class="bigscore"><b class="num">{round(p['_tot'])}</b><span>von 100 Punkten</span></div></div>
<section class="buy"><div class="pricebox"><div class="r"><span>Preis</span>{price_line(p)}</div>
{f'<div class="r"><span>UVP</span><b class="num">{eur(p["uvp"])}</b></div>' if p.get('uvp') else ''}
{f'<div class="r"><span>Varianten</span><span>{e(var)}</span></div>' if var else ''}
<p class="muted small">{e(pn)}</p></div>{buy_buttons(p)}</section>
<section><h2>Bewertung im Detail</h2><div class="metric">{cats}</div>
{f'<p class="muted small">Grundlage: {e(dq.get("basis",""))}. {e(dq.get("note",""))}</p>' if dq else ''}
<p class="small"><a href="{g['_url']}">Ganze Rangliste: {e(t)}</a></p></section>
{('<section><h2>Was Tests sagen</h2><ul class="notes">' + ''.join(tests) + '</ul></section>') if tests else ''}
{('<section><h2>Technische Daten</h2><div class="spec">' + spec + '</div></section>') if spec else ''}
{('<section><h2>Videos</h2><ul class="notes">' + vids + '</ul></section>') if vids else ''}
<section><h2>Direkt daneben in der Rangliste</h2><div class="chips">{rivals}</div>{('<h3>Vergleiche</h3><div class="chips">' + vs + '</div>') if vs else ''}</section>
{DISCLOSURE}"""
    desc = (f"{h1} im Test-Vergleich: {round(p['_tot'])} von 100 Punkten, Platz {p['_rank']} von {len(order)} {t}. "
            + (f"Preis ca. {eur(p['mp'])}. " if p.get('mp') else "") + "Stärken, Daten und Testnoten.")[:158]
    page(p["_url"], f"{h1}: Test, Wertung & Preis | {CFG['site_name']}", desc, body,
         crumbs=[("Start", "/"), (s["n"], f"/{s['id']}/"), (t, g["_url"]), (h1, p["_url"])])

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
    srows = "".join(f'<tr class="sp"><th scope="row">{e(k)}</th><td>{e(a["sp"][k])}</td><td>{e(b["sp"][k])}</td></tr>' for k in keys)
    better_a = [c for ci, c in enumerate(g["_cats"]) if a["_ca"][ci] - b["_ca"][ci] >= 0.5]
    better_b = [c for ci, c in enumerate(g["_cats"]) if b["_ca"][ci] - a["_ca"][ci] >= 0.5]
    def why(x, lst): return f"<li><b>{e(x['_full'])}</b> ist klar besser bei: {e(', '.join(lst))}.</li>" if lst else ""
    verdict = ("Beide liegen fast gleichauf, entscheide nach Preis und dem, was dir wichtig ist." if diff < 1.5
               else f"{win['_full']} gewinnt mit {round(win['_tot'])} zu {round(lose['_tot'])} Punkten.")
    h1 = f"{a['_full']} vs. {b['_full']}"
    body = f"""<div class="hero"><p class="eyebrow">Vergleich · {e(t)}</p><h1>{e(h1)}</h1><p class="lead">{e(verdict)}</p></div>
<section class="duel">{''.join(f'<div class="dcard{" win" if x is win and diff>=1.5 else ""}"><a href="{x["_url"]}"><b>{e(x["_full"])}</b></a>{score_badge(x)}<span>Platz {x["_rank"]} · {price_line(x)}</span>{buy_buttons(x, True)}</div>' for x in (a, b))}</section>
<section><ul class="notes">{why(a, better_a)}{why(b, better_b)}</ul></section>
<section><h2>Teilnoten</h2><div class="tbox"><table class="cmp"><thead><tr><th></th><th class="n">{e(a['_full'])}</th><th class="n">{e(b['_full'])}</th></tr></thead><tbody>
<tr class="tt"><th scope="row">Gesamt</th><td class="n"><b>{round(a['_tot'])}</b></td><td class="n"><b>{round(b['_tot'])}</b></td></tr>{rows}
<tr><th scope="row">Preis</th><td class="n">{eur(a.get('mp')) or '–'}</td><td class="n">{eur(b.get('mp')) or '–'}</td></tr></tbody></table></div></section>
{('<section><h2>Daten nebeneinander</h2><div class="tbox"><table class="cmp"><tbody>' + srows + '</tbody></table></div></section>') if srows else ''}
<p class="small"><a href="{g['_url']}">Alle {e(t)} in der Rangliste</a></p>{DISCLOSURE}"""
    url = duel_url(a, b)
    DUELS.append((g, a, b, url))
    page(url, f"{h1}: Welches ist besser? | {CFG['site_name']}",
         f"{h1} im direkten Vergleich: {verdict} Teilnoten, Preise und Daten nebeneinander."[:158], body,
         crumbs=[("Start", "/"), ("Vergleiche", "/vergleich/"), (h1, url)])

def build_duel_index():
    by = {}
    for g, a, b, u in DUELS: by.setdefault(g["id"], []).append((a, b, u))
    secs = "".join(f'<section><h2>{e(gtitle(GBYID[gid]))}</h2><div class="chips">' + "".join(
        f'<a href="{u}">{e(a["_full"])} vs. {e(b["_full"])}</a>' for a, b, u in lst) + "</div></section>" for gid, lst in by.items())
    page("/vergleich/", f"Geräte-Vergleiche: Welches ist besser? | {CFG['site_name']}",
         "Direkte Duelle der besten Handys, Kopfhörer, Laptops, Fernseher und mehr. Teilnoten, Preise und Daten nebeneinander.",
         f'<div class="hero"><h1>Vergleiche</h1><p class="lead">Die Top-Geräte jeder Rangliste im direkten Duell.</p></div>{secs}',
         crumbs=[("Start", "/"), ("Vergleiche", "/vergleich/")])

# ---------- Kategorie- und Startseite ----------
def build_section(s):
    gs = groups_of(s["id"])
    blocks = []
    for g in gs:
        blocks.append(f'<section><div class="sec-h"><h2><a href="{g["_url"]}">{e(gtitle(g))}</a></h2><a class="small" href="{g["_url"]}">Alle {len(g["products"])} ansehen</a></div>'
                      f'<div class="top3">{"".join(product_card(g, p) for p in g["_order"][:3])}</div></section>')
    page(f"/{s['id']}/", f"{s['n']} {YEAR}: die besten Geräte im Vergleich | {CFG['site_name']}",
         f"{s['n']}: {s.get('d','')}. Ranglisten mit offener Formel, aktuelle Preise und Vergleiche.",
         f'<div class="hero"><h1>{e(s["n"])}</h1><p class="lead">{e(s.get("d",""))}</p></div>{"".join(blocks)}{DISCLOSURE}',
         crumbs=[("Start", "/"), (s["n"], f"/{s['id']}/")])

def build_home():
    total = sum(len(g["products"]) for g in GROUPS)
    cards = "".join(
        f'<a class="card" href="/{s["id"]}/"><b>{e(s["n"])}</b><span>{e(s.get("d",""))}</span>'
        f'<span class="cnt">{sum(len(g["products"]) for g in groups_of(s["id"]))} Geräte</span></a>' for s in DATA["sections"])
    picks = []
    for gid in ("handys", "in-ear", "over-ear", "laptops", "tablets", "watches", "tvs", "consoles"):
        g = GBYID.get(gid)
        if g: picks.append(f'<a class="pick" href="{g["_url"]}"><span>{e(gtitle(g))}</span><b>{e(g["_order"][0]["_full"])}</b>{score_badge(g["_order"][0])}</a>')
    news = sorted(DATA.get("news", []), key=lambda n: n.get("d") or "", reverse=True)[:4]
    nh = "".join(f'<div class="nx"><span class="muted small">{e(n.get("d",""))} · {e(n.get("cat",""))}</span><b>{e(n["t"])}</b></div>' for n in news)
    body = f"""<div class="hero home"><h1>Welches Gerät ist wirklich das beste?</h1>
<p class="lead">{total} Handys, Kopfhörer, Laptops, Fernseher und mehr. Jede Wertung kommt aus einer festen Formel mit offenem Rechenweg, nicht aus Bauchgefühl und nicht aus Provisionen.</p>
<div class="actions"><a class="btn" href="/app/">Persönliche Empfehlung holen</a><a class="btn ghost" href="/methode/">So wird bewertet</a></div></div>
<section><h2>Testsieger</h2><div class="picks">{''.join(picks)}</div></section>
<section><h2>Alle Kategorien</h2><div class="cards">{cards}</div></section>
{('<section><h2>Neu in der Technik-Welt</h2><div class="news">' + nh + '</div></section>') if nh else ''}
{DISCLOSURE}"""
    page("/", f"{CFG['site_name']}: unabhängige Geräte-Ranglisten {YEAR}",
         f"{total} Geräte mit offener Formel bewertet: die besten Handys, Kopfhörer, Laptops, Fernseher und mehr im Vergleich. Aktuelle Preise, ehrliche Wertung.",
         body, jsonld={"@context": "https://schema.org", "@type": "WebSite", "name": CFG["site_name"], "url": DOMAIN + "/"})

# ---------- TikTok ----------
def build_tiktok():
    items = []
    for it in TIKTOK:
        g = GBYID[it["group"]]
        p = next(x for x in g["products"] if x["n"] == it["product"])
        vids = " ".join(f'<span class="vtag" id="{e(v)}">Video {e(v[1:])}</span>' for v in it.get("videos", []))
        vids = f'<div>{vids}</div>' if vids else ""
        use = next((u for u in g.get("uses", []) if len(u) >= 2 and u[1] in (p["n"], p["_full"])), None)
        use_h = f'<p class="note"><b>Tipp im Kompass: {e(use[0])}.</b> {e(use[2]) if len(use) > 2 else ""}</p>' if use else ""
        items.append(f"""<article class="tk" id="{e(it['id'])}">{vids}<p class="eyebrow">{e(it['title'])}</p>
<h2><a href="{p['_url']}">{e(p['_full'])}</a></h2><div class="tkm">{score_badge(p)}<span>Platz {p['_rank']} von {len(g['products'])} {e(gtitle(g))}</span><span>{price_line(p)}</span></div>
<p>{e(it['why'])}</p>{use_h}{f'<p class="note">{e(it["tip"])}</p>' if it.get('tip') else ''}{buy_buttons(p)}</article>""")
    body = f"""<div class="hero"><h1>Aus den Videos</h1><p class="lead">Alles, was in den TikToks vorkommt, an einem Ort. Jedes Produkt steht auch in der Rangliste mit offener Wertung.</p></div>
<div class="tkl">{''.join(items)}</div>{DISCLOSURE}"""
    page("/tiktok/", f"Aus den Videos | {CFG['site_name']}", "Die Produkte aus den Technik-Kompass-Videos mit Wertung, Preis und Link.", body,
         crumbs=[("Start", "/"), ("Aus den Videos", "/tiktok/")])

# ---------- Rechtliches und Methode ----------
def build_legal():
    im = CFG["impressum"]
    page("/impressum/", f"Impressum | {CFG['site_name']}", "Impressum des Technik Kompass.", f"""<div class="prose"><h1>Impressum</h1>
<h2>Angaben gemäß § 5 DDG</h2><p>{e(im['name'])}<br>{e(im['street'])}<br>{e(im['city'])}</p>
<h2>Kontakt</h2><p>E-Mail: {e(im['email'])}{('<br>Telefon: ' + e(im['phone'])) if im.get('phone') else ''}</p>
<h2>Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV</h2><p>{e(im['name'])}, Anschrift wie oben</p>
<h2>Verbraucherstreitbeilegung</h2><p>Ich bin nicht bereit und nicht verpflichtet, an Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle teilzunehmen.</p>
<h2>Haftung für Links</h2><p>Diese Seite enthält Links zu externen Websites. Auf deren Inhalte habe ich keinen Einfluss, dafür ist der jeweilige Anbieter verantwortlich. Werden mir Rechtsverstöße bekannt, entferne ich solche Links umgehend.</p></div>""",
         crumbs=[("Start", "/"), ("Impressum", "/impressum/")])
    page("/datenschutz/", f"Datenschutz | {CFG['site_name']}", "Datenschutzerklärung des Technik Kompass.", f"""<div class="prose"><h1>Datenschutzerklärung</h1>
<p>Kurz gesagt: Diese Seite setzt keine Cookies, nutzt kein Google Analytics und keine Werbe-Tracker. Es gibt keine Anmeldung und kein Kontaktformular.</p>
<h2>1. Verantwortlicher</h2><p>{e(im['name'])}, {e(im['street'])}, {e(im['city'])}, E-Mail: {e(im['email'])}</p>
<h2>2. Hosting</h2><p>Die Seite wird bei [GitHub Pages (GitHub Inc., USA) / Cloudflare Pages (Cloudflare Inc., USA)] gehostet. Beim Aufruf verarbeitet der Anbieter technisch notwendige Daten wie IP-Adresse, Datum und Uhrzeit, aufgerufene Seite und Browser-Typ, um die Seite auszuliefern und vor Angriffen zu schützen. Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an einer sicheren, funktionierenden Website). Der Anbieter ist unter dem EU-US Data Privacy Framework zertifiziert.</p>
<h2>3. Besucherstatistik</h2><p>[Nur falls aktiviert:] Ich nutze Cloudflare Web Analytics. Das Tool setzt keine Cookies und speichert keine IP-Adressen. Es zählt nur, wie oft welche Seite aufgerufen wird. Rechtsgrundlage ist Art. 6 Abs. 1 lit. f DSGVO.</p>
<h2>4. Partner-Links</h2><p>Links mit * führen zu Partnerprogrammen wie dem Amazon-Partnerprogramm oder Awin. Erst wenn du einen solchen Link anklickst, setzt der Shop auf seiner eigenen Seite Cookies, um den Kauf zuzuordnen. Dafür ist der jeweilige Shop verantwortlich, Details stehen in dessen Datenschutzerklärung. Auf dieser Seite selbst werden dafür keine Daten erhoben.</p>
<h2>5. Lokaler Speicher im Berater</h2><p>Der interaktive Berater unter /app/ speichert Einstellungen wie deine Merkliste nur in deinem eigenen Browser (Local Storage). Diese Daten verlassen dein Gerät nicht und lassen sich jederzeit über die Browser-Einstellungen löschen.</p>
<h2>6. Deine Rechte</h2><p>Du hast das Recht auf Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung, Datenübertragbarkeit und Widerspruch (Art. 15 bis 21 DSGVO). Schreib dazu einfach an die oben genannte E-Mail-Adresse. Außerdem kannst du dich bei einer Datenschutz-Aufsichtsbehörde beschweren.</p>
<p class="muted small">Stand: {e(CFG['updated'])}</p></div>""", crumbs=[("Start", "/"), ("Datenschutz", "/datenschutz/")])
    page("/werbung/", f"Werbung & Partner-Links | {CFG['site_name']}", "Wie sich der Technik Kompass finanziert.", f"""<div class="prose"><h1>Werbung &amp; Partner-Links</h1>
<p>Der Technik Kompass ist kostenlos und ohne Werbebanner. Finanziert wird er über Partner-Links. Sie sind mit einem Sternchen (*) markiert.</p>
<p>Kaufst du nach einem Klick auf so einen Link etwas, bekommt der Technik Kompass vom Shop eine kleine Provision. Für dich ändert sich am Preis nichts.</p>
<p><b>Die Wertung hängt nie davon ab.</b> Alle Punkte kommen aus derselben festen Formel, egal ob es für ein Gerät einen Partner-Link gibt oder nicht. Den Rechenweg siehst du bei jedem Gerät.</p>
{'<p>Als Amazon-Partner verdiene ich an qualifizierten Verkäufen.</p>' if TAG else ''}
<p>Die Links „Preise vergleichen“ führen zu idealo und sind keine Partner-Links.</p></div>""", crumbs=[("Start", "/"), ("Werbung", "/werbung/")])
    learn = "".join(f'<section><h2>{e(l["t"])}</h2><p class="lead">{e(l.get("x",""))}</p><ul class="notes">'
                    + "".join(f'<li><b>{e(i["t"])}</b>: {e(i.get("x",""))}</li>' for i in l.get("it", [])) + "</ul></section>"
                    for l in DATA.get("learn", [])[:4])
    page("/methode/", f"So wird bewertet | {CFG['site_name']}", "Wie der Technik Kompass aus Messwerten und Tests Punkte macht: feste Formel, offener Rechenweg.",
         f'<div class="hero"><h1>So wird bewertet</h1><p class="lead">Jede Rangliste hat feste Kategorien mit festen Gewichten. Messwerte werden immer nach derselben Formel in Punkte umgerechnet. Fehlt ein Messwert, zählt ein Testurteil und die Stelle ist als geschätzt markiert.</p></div>{learn}',
         crumbs=[("Start", "/"), ("Methode", "/methode/")])
    page("/404.html", f"Seite nicht gefunden | {CFG['site_name']}", "Diese Seite gibt es nicht.",
         '<div class="hero"><h1>Seite nicht gefunden</h1><p class="lead">Vielleicht wurde das Gerät umbenannt. Hier geht es weiter:</p><div class="actions"><a class="btn" href="/">Zur Startseite</a><a class="btn ghost" href="/vergleich/">Vergleiche</a></div></div>', noindex=True)

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
    build_duel_index(); build_tiktok(); build_legal()
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"<url><loc>{e(u)}</loc></url>\n" for u in SITEMAP) + "</urlset>\n"
    open(os.path.join(DIST, "sitemap.xml"), "w").write(sm)
    open(os.path.join(DIST, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nSitemap: {DOMAIN}/sitemap.xml\n")
    open(os.path.join(DIST, ".nojekyll"), "w").write("")
    if "DEINE-DOMAIN" not in DOMAIN:
        open(os.path.join(DIST, "CNAME"), "w").write(DOMAIN.split("://", 1)[1] + "\n")
    print(f"{len(SITEMAP)} Seiten gebaut, Partner-Tag {'aktiv' if TAG else 'noch leer'}")

if __name__ == "__main__":
    main()
