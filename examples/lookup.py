#!/usr/bin/env python3
"""DOI -> mdpi-res.com CDN URLs (xml / epub / pdf). Usage: python examples/lookup.py 10.3390/en19204993"""
import json, re, sys, pathlib, requests

MAP = {r["doi_code"]: r for r in json.load(open(pathlib.Path(__file__).parents[1] / "mdpi_journals.json"))}

def cdn_urls(doi):
    code = re.match(r"10\.3390/([a-z]+)\d+$", doi.lower()).group(1)
    slug = MAP[code]["slug"]
    link = requests.get(f"https://api.crossref.org/works/{doi}", timeout=20).json()["message"]["link"][0]["URL"]
    # e.g. https://www.mdpi.com/1996-1073/19/20/4993/pdf  (Molbank: /1422-8599/2026/5/M2246/pdf)
    vol, art = link.rstrip("/").split("/")[-4], link.rstrip("/").split("/")[-2]
    base = f"{slug}-{vol}-{art}" if art.startswith("M") else f"{slug}-{int(vol):02d}-{int(art):05d}"
    return {e: f"https://mdpi-res.com/d_attachment/{slug}/{base}/article_deploy/{base}.{e}" for e in ("xml", "epub", "pdf")}

if __name__ == "__main__":
    print(json.dumps(cdn_urls(sys.argv[1]), indent=1))
