# mdpi-journal-slugs

An unofficial mapping from MDPI DOI codes (the `en` in `10.3390/en19204993`) to the journal slugs used on MDPI's file CDN `mdpi-res.com` (`energies`). Each row also has the journal title and ISSN/eISSN.

With the slug you can fetch an article's official JATS XML, EPUB or PDF directly from the CDN.

## URL template

```
https://mdpi-res.com/d_attachment/{slug}/{slug}-{vol:02d}-{art:05d}/article_deploy/{slug}-{vol:02d}-{art:05d}.{xml|epub|pdf}
```

Example: `10.3390/en19204993` (Energies vol 19, article 4993) becomes
`https://mdpi-res.com/d_attachment/energies/energies-19-04993/article_deploy/energies-19-04993.xml`

- **Padding:** the volume is zero-padded to 2 digits (`acoustics-06-00001`) and the article number to 5 digits.
- **Version suffix:** the file without a suffix is the current version. `-v2` etc. exist only for revised articles.
- **Volume and article number:** get them from Crossref. The article number is in the `link` URL `/{issn}/{vol}/{issue}/{art}/pdf`.
- **Molbank (`m`):** the volume is the 4-digit year and the article id is a capital `M` plus the number, unpadded:
  `https://mdpi-res.com/d_attachment/molbank/molbank-{year}-M{num}/article_deploy/molbank-{year}-M{num}.{xml|pdf}`
  The Crossref link looks like `/1422-8599/2026/5/M2244/pdf`. Verified: `molbank-2026-M2244` (xml and pdf), `molbank-2023-M1692` (xml).
- **Case-sensitive slugs:** a few slugs must keep their case, e.g. `BDCC`, `IoT`, `J`, `IJNS`, `ChemEngineering`.

See `examples/lookup.py`.

## Files

- `mdpi_journals.json` / `mdpi_journals.csv`. Fields: `doi_code, slug, journal_title, issn, eissn, other_issns, verified, example_doi, note`.
- `scripts/build_mapping.py`: regenerates the mapping (`--mailto you@example.org`).

## How it was verified (2026-10-21)

1. Took the list of journals and ISSNs under DOI prefix `10.3390` from the Crossref REST API.
2. For each journal, took one sample article.
3. Requested candidate slugs on `mdpi-res.com`.
4. A slug counts as verified when the CDN returns the article. Where the XML was returned, the slug was read from `<journal-id journal-id-type="publisher-id">`.

Result: 551 of 551 DOI codes verified.

## Known gaps

- `ht` (High-Throughput): no CDN files under `ht` or `highthroughput` (vols 1, 5, 8, 9 tested). The journal ceased around 2020, so use Europe PMC instead.
- `fossils` (Fossil Studies): slug `fossils` is verified on older articles, but the newest ones (e.g. `10.3390/fossils4040029`) are not on the CDN yet.
- Very new articles may not be on the CDN yet. A 404 does not necessarily mean the slug is wrong.
- Article numbers of 100000 or more have not been tested.
- MDPI launches new journals regularly. Re-run the generator to pick them up.

## Caveats

This project is unofficial and not affiliated with or endorsed by MDPI. MDPI content is open access, but respect MDPI's terms of use and rate limits: identify your client, throttle requests, and do not bulk-mirror.

## License

Data (`*.json`, `*.csv`) is CC0 1.0. Code is MIT.

## 中文简介

这是 MDPI 期刊 DOI 代码到 `mdpi-res.com` CDN 目录名（slug）的非官方对照表，另含期刊名和 ISSN，可以用它直接拉取官方 JATS XML、EPUB 或 PDF。

- 模板见上文。卷号补零到 2 位，文章号补零到 5 位。
- 部分 slug 区分大小写。
- Molbank 例外：用 `molbank-{年份}-M{编号}`，不补零。
- 验证方法：用 Crossref 取样文章，再在 CDN 上读 XML 里的 `journal-id`。
- 验证日期 2026-10-21，551 个期刊中验证通过 550 个。
- 本项目与 MDPI 无关，请遵守 MDPI 的使用条款并控制请求频率。
- 数据采用 CC0，代码采用 MIT。


## Note: hyphenated slug

High-Throughput (`ht`) uses the hyphenated slug `high-throughput`. Lineage: Microarrays (`microarrays`, vols 1-5) -> High-Throughput (`high-throughput`, vols 6-9) -> BioTech (`biotech`, vol 10+). 高通量期刊的代号带连字符：`high-throughput`。
