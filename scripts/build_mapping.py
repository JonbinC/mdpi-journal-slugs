#!/usr/bin/env python3
"""Rebuild the MDPI DOI-code -> mdpi-res.com CDN slug mapping.

Sources: Crossref REST API (journal list, ISSNs, sample article) and the
mdpi-res.com CDN (JATS <journal-id journal-id-type="publisher-id">).
Usage: python scripts/build_mapping.py --mailto you@example.org
"""
import argparse, csv, json, re, time
from concurrent.futures import ThreadPoolExecutor
import requests

CDN = "https://mdpi-res.com/d_attachment/{s}/{b}/article_deploy/{b}{ext}"
EXTRA = {"m": ["molbank"], "app": ["applsci"], "bs": ["behavsci"], "c": ["carbon"], "bdcc": ["BDCC"], "pediatric": ["pediatrrep"],
         "quantum": ["quantumrep"], "tourhosp": ["tourismhosp"], "ht": ["highthroughput"], "j": ["J"],
         "iot": ["IoT"], "chemengineering": ["ChemEngineering"], "ijns": ["IJNS"], "gidisord": ["gastrointestdisord"]}
STOP = {"and", "of", "the", "in", "for"}

def candidates(code, title):
    w = re.sub(r"[^a-z0-9 ]", "", title.lower().replace("&", " ")).split()
    c = EXTRA.get(code, []) + [code, "".join(w), "".join(x for x in w if x not in STOP | {"journal"})]
    if w: c.append(w[0])
    if len(w) > 1: c.append("".join(x[0] for x in w if x not in STOP))
    if "journal" in w: c.append("j" + "".join(x for x in w if x not in STOP | {"journal"}))
    if w and w[0] == "applied": c.append("appl" + "".join(w[1:]))
    return list(dict.fromkeys(x for x in c if x))

def base_name(slug, vol, art):
    """CDN folder/file base. Normal: volume 2-digit, article 5-digit. Molbank: {year}-M{num}, unpadded."""
    if art.startswith("M"):
        return f"{slug}-{vol}-{art}"
    return f"{slug}-{int(vol):02d}-{int(art):05d}"

KEEP_NOTES = {"ht": "not on CDN; use Europe PMC (journal ceased ~2020)"}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mailto", default="you@example.org")
    ap.add_argument("--until", default="2025-09-30", help="sample articles published before this date (CDN lag)")
    ap.add_argument("--only", default="", help="comma-separated DOI codes to test (prints, does not write files)")
    a = ap.parse_args()
    S = requests.Session(); S.headers["User-Agent"] = f"mdpi-journal-slugs (mailto:{a.mailto})"
    facet = S.get("https://api.crossref.org/works", params={"filter": "prefix:10.3390", "facet": "issn:*", "rows": 0, "mailto": a.mailto}, timeout=60).json()
    issns = [k.rsplit("/", 1)[1] for k in facet["message"]["facets"]["issn"]["values"]]
    only = set(filter(None, a.only.split(",")))
    if only:  # look up ISSNs for the requested codes from the existing table
        known = {r["doi_code"]: r for r in json.load(open("mdpi_journals.json"))}
        issns = [known[c].get("eissn") or known[c].get("issn") for c in only if c in known]

    def sample(issn):
        """Return journal info plus a few sample articles: newest first, then the oldest
        (fallback for journals whose newest articles are not on the CDN yet)."""
        items = []
        for order, extra in (("desc", f",until-pub-date:{a.until}"), ("asc", "")):
            try:
                r = S.get(f"https://api.crossref.org/journals/{issn}/works", params={"rows": 3, "sort": "published", "order": order,
                          "filter": f"type:journal-article,prefix:10.3390{extra}", "mailto": a.mailto}, timeout=30).json()
                items += r["message"]["items"]
            except Exception:
                pass
            time.sleep(0.2)
        info, arts = None, []
        for it in items:
            m = re.match(r"10\.3390/([a-z]+)\d+$", it["DOI"].lower())
            if not m: continue
            art = None
            for l in it.get("link", []):
                x = re.search(r"/(M?\d+)/pdf", l["URL"]); art = x and x.group(1)
            if info is None:
                t = {x["type"]: x["value"] for x in it.get("issn-type", [])}
                info = dict(doi_code=m.group(1), example_doi=it["DOI"], journal_title=(it.get("container-title") or [""])[0],
                            issn=t.get("print", ""), eissn=t.get("electronic", ""))
            if info["doi_code"] == m.group(1) and it.get("volume", "").isdigit() and art:
                arts.append((it["DOI"], it["volume"], art))
        if info: info["arts"] = arts
        return info

    with ThreadPoolExecutor(4) as ex: rows = [r for r in ex.map(sample, issns) if r]
    J = {}
    for r in rows: J.setdefault(r["doi_code"], r)

    def verify(r):
        r.update(slug="", verified=False, note="")
        if not r["arts"]:
            r["note"] = "no volume/article number in Crossref"; return r
        for doi, vol, art in r["arts"]:  # newest first; older ones if the newest are not on the CDN yet
            for s in candidates(r["doi_code"], r["journal_title"]):
                b = base_name(s, vol, art)
                for ext in (".xml", ".pdf"):
                    try: x = S.get(CDN.format(s=s, b=b, ext=ext), timeout=20)
                    except Exception: continue
                    if x.status_code == 200:
                        m = re.search(rb'journal-id-type="publisher-id">([^<]+)<', x.content) if ext == ".xml" else None
                        r.update(slug=m.group(1).decode() if m else s, verified=True, example_doi=doi)
                        if art.startswith("M"): r["note"] = "special filename: {slug}-{year}-M{num} (unpadded)"
                        return r
                time.sleep(0.2)
        r["note"] = "CDN 404 for tried slugs and sample articles"; return r

    with ThreadPoolExecutor(4) as ex: out = sorted(ex.map(verify, J.values()), key=lambda r: r["doi_code"])
    for r in out:
        if r["doi_code"] in KEEP_NOTES and not r["verified"]: r["note"] = KEEP_NOTES[r["doi_code"]]
    if only:
        for r in out: print(r["doi_code"], r["slug"], r["verified"], r["example_doi"], r["note"])
        return
    F = ["doi_code", "slug", "journal_title", "issn", "eissn", "verified", "example_doi", "note"]
    out = [{k: r.get(k, "") for k in F} for r in out]
    json.dump(out, open("mdpi_journals.json", "w"), indent=1, ensure_ascii=False)
    with open("mdpi_journals.csv", "w", newline="") as f:
        w = csv.DictWriter(f, F); w.writeheader(); w.writerows(out)
    print(f"verified {sum(r['verified'] for r in out)}/{len(out)}")

if __name__ == "__main__":
    main()
