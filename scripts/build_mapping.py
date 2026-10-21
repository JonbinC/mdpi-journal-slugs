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
EXTRA = {"app": ["applsci"], "bs": ["behavsci"], "c": ["carbon"], "bdcc": ["BDCC"], "pediatric": ["pediatrrep"],
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

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mailto", default="you@example.org")
    ap.add_argument("--until", default="2025-09-30", help="sample articles published before this date (CDN lag)")
    a = ap.parse_args()
    S = requests.Session(); S.headers["User-Agent"] = f"mdpi-journal-slugs (mailto:{a.mailto})"
    facet = S.get("https://api.crossref.org/works", params={"filter": "prefix:10.3390", "facet": "issn:*", "rows": 0, "mailto": a.mailto}, timeout=60).json()
    issns = [k.rsplit("/", 1)[1] for k in facet["message"]["facets"]["issn"]["values"]]

    def sample(issn):
        try:
            r = S.get(f"https://api.crossref.org/journals/{issn}/works", params={"rows": 3, "sort": "published", "order": "desc",
                      "filter": f"type:journal-article,prefix:10.3390,until-pub-date:{a.until}", "mailto": a.mailto}, timeout=30).json()
        except Exception:
            return None
        for it in r["message"]["items"]:
            m = re.match(r"10\.3390/([a-z]+)\d+$", it["DOI"].lower())
            if not m: continue
            art = None
            for l in it.get("link", []):
                x = re.search(r"/(\d+)/pdf", l["URL"]); art = x and x.group(1)
            t = {x["type"]: x["value"] for x in it.get("issn-type", [])}
            return dict(doi_code=m.group(1), example_doi=it["DOI"], vol=it.get("volume"), art=art,
                        journal_title=(it.get("container-title") or [""])[0], issn=t.get("print", ""), eissn=t.get("electronic", ""))
        return None

    with ThreadPoolExecutor(4) as ex: rows = [r for r in ex.map(sample, issns) if r]
    J = {}
    for r in rows: J.setdefault(r["doi_code"], r)

    def verify(r):
        r.update(slug="", verified=False, note="")
        if not (r["vol"] and r["art"] and r["vol"].isdigit()):
            r["note"] = "no volume/article number in Crossref"; return r
        for s in candidates(r["doi_code"], r["journal_title"]):
            b = f"{s}-{int(r['vol']):02d}-{int(r['art']):05d}"
            for ext in (".xml", ".pdf"):
                try: x = S.get(CDN.format(s=s, b=b, ext=ext), timeout=20)
                except Exception: continue
                if x.status_code == 200:
                    m = re.search(rb'journal-id-type="publisher-id">([^<]+)<', x.content) if ext == ".xml" else None
                    r.update(slug=m.group(1).decode() if m else s, verified=True); return r
            time.sleep(0.2)
        r["note"] = "CDN 404 for tried slugs"; return r

    with ThreadPoolExecutor(4) as ex: out = sorted(ex.map(verify, J.values()), key=lambda r: r["doi_code"])
    F = ["doi_code", "slug", "journal_title", "issn", "eissn", "verified", "example_doi", "note"]
    out = [{k: r.get(k, "") for k in F} for r in out]
    json.dump(out, open("mdpi_journals.json", "w"), indent=1, ensure_ascii=False)
    with open("mdpi_journals.csv", "w", newline="") as f:
        w = csv.DictWriter(f, F); w.writeheader(); w.writerows(out)
    print(f"verified {sum(r['verified'] for r in out)}/{len(out)}")

if __name__ == "__main__":
    main()
