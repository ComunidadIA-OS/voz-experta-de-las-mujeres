"""Download SINC news and draw the random sample for human annotation.

Step 1 (about one article per second; it resumes if interrupted):
    python evaluation/sinc.py candidates --start 2025-10-01 --end 2026-09-30
Step 2 (reproducible with the seed; without --section all sections are used):
    python evaluation/sinc.py sample --start 2025-10-01 --end 2026-09-30 --calibration 3 3 --test 20 20 --seed 2026
Step 3 (simple random subsample of the corpus, when the whole year is too long to run):
    python evaluation/sinc.py corpus --start 2025-10-01 --end 2026-09-30 --size 200 --seed 2026
"""

import argparse
import hashlib
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

import requests


DATA = Path(__file__).resolve().parent / "data"
CANDIDATES = DATA / "candidates"
SAMPLE = DATA / "sample"
CORPUS = DATA / "corpus_sample"
SITEMAP = "https://www.agenciasinc.es/sitemap.xml"
USER_AGENT = "Mozilla/5.0 (academic project, Reto Mujeres IA Abierta)"
# Articles used to practise the annotation guide; they never enter the sample.
PRACTICE_IDS = ["07ea4f0ba41b", "7fb7df971599", "db2ea6c0ccae"]


class SincArticle(HTMLParser):
    """Keep the paragraphs that belong to the article body.

    Highlighted quotes and related links sit in nested blocks;
    they repeat the body or are not part of it, so they are skipped.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.divs = []
        self.buffer = []
        self.in_paragraph = False
        self.in_headline = False
        self.in_tag = False
        self.in_rights = False
        self.headline = ""
        self.introduction = []
        self.body = []
        self.rights = []
        self.tags = []
        self.sections = []

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class", "") or ""
        if tag == "div":
            self.divs.append(classes)
            if classes.strip() == "fuente":
                self.in_rights = True
                self.buffer = []
        elif tag == "p":
            self.in_paragraph = True
            self.buffer = []
        elif tag == "h1":
            self.in_headline = True
            self.buffer = []
        elif tag == "a" and self.divs and "tag_link" in self.divs[-1]:
            self.in_tag = True
            self.buffer = []
            href = dict(attrs).get("href") or ""
            if href.startswith("/"):
                self.sections.append(href.strip("/").split("/")[0])
        elif tag == "br" and self.in_paragraph:
            self.buffer.append(" ")

    def handle_endtag(self, tag):
        text = " ".join("".join(self.buffer).split())
        if tag == "p" and self.in_paragraph:
            self.in_paragraph = False
            parent = self.divs[-1] if self.divs else ""
            if not text:
                return
            if "bm-article_body" in parent:
                self.body.append(text)
            elif parent == "ezxmltext-field" and len(self.divs) >= 2 and self.divs[-2] == "lead":
                self.introduction.append(text)
        elif tag == "h1" and self.in_headline:
            self.in_headline = False
            self.headline = self.headline or text
        elif tag == "a" and self.in_tag:
            self.in_tag = False
            if text:
                self.tags.append(text)
        elif tag == "div" and self.divs:
            if self.in_rights and self.divs[-1].strip() == "fuente":
                self.in_rights = False
                if text:
                    self.rights.append(text)
            self.divs.pop()

    def handle_data(self, data):
        if self.in_paragraph or self.in_headline or self.in_tag or self.in_rights:
            self.buffer.append(data)


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get(url):
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    return response.text


def json_ld_field(html, pattern):
    match = re.search(pattern, html, re.S)
    return unescape(match.group(1)).strip() if match else None


def download_article(url):
    html = get(url)
    parser = SincArticle()
    parser.feed(html)
    article = {
        "headline": parser.headline,
        "introduction": "\n".join(parser.introduction),
        "body": "\n".join(parser.body),
    }
    rights = " | ".join(parser.rights)
    return {
        "id": fingerprint(url)[:12],
        "url": url,
        "author": json_ld_field(html, r'"author":\s*\{[^}]*"name":\s*"([^"]+)"'),
        "published": json_ld_field(html, r'"datePublished":\s*"([^"]+)"'),
        "rights": rights,
        "cc_licence": "Creative Commons" in rights,
        "source_type": "sinc_newsroom" if "Fuente: SINC" in rights else "institution",
        "tags": parser.tags,
        "sections": sorted(set(parser.sections)),
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "article": article,
        "sha256": {field: fingerprint(text) for field, text in article.items()},
    }


def load_article(path):
    """Read an article file. Also accepts files from the first Spanish prototype."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "article" not in data and "campos" in data:
        fields = data["campos"]
        data["article"] = {
            "headline": fields.get("titular", ""),
            "introduction": fields.get("entradilla", ""),
            "body": fields.get("cuerpo", ""),
        }
        data["published"] = data.get("fecha_publicacion")
        data["cc_licence"] = data.get("licencia_cc", False)
        data["source_type"] = "sinc_newsroom" if data.get("fuente_sinc") else "institution"
        data["sections"] = data.get("secciones", [])
    return data


def sitemap_urls(start):
    xml = get(SITEMAP)
    for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
        url = re.search(r"<loc>([^<]+)</loc>", block).group(1).strip()
        # Recent news carry the publication date; older ones only the last modification,
        # which is never earlier. The real date is checked when sampling.
        date = re.search(r"<(?:news:publication_date|lastmod)>(\d{4}-\d{2}-\d{2})", block)
        if "/Noticias/" in url and date and date.group(1) >= start:
            yield url


def candidates(args):
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    urls = list(sitemap_urls(args.start))
    print(f"{len(urls)} news URLs since {args.start}", flush=True)
    for number, url in enumerate(urls, start=1):
        path = CANDIDATES / f"{fingerprint(url)[:12]}.json"
        if path.exists():
            continue
        try:
            record = download_article(url)
        except requests.RequestException as error:
            print(f"  failed {url}: {error}", file=sys.stderr, flush=True)
            continue
        if not record["cc_licence"]:
            # Only Creative Commons articles are stored, because the dataset is published.
            print(f"  skipped, no Creative Commons licence: {url}", flush=True)
            time.sleep(1)
            continue
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        if number % 25 == 0:
            print(f"  {number}/{len(urls)}", flush=True)
        time.sleep(1)  # be polite to the server
    print("done", flush=True)


def in_period(record, start, end):
    return start <= (record.get("published") or "")[:10] <= end


def sample(args):
    records = [load_article(path) for path in sorted(CANDIDATES.glob("*.json"))]
    valid = [
        r for r in records
        if r["cc_licence"] and r["article"]["body"] and in_period(r, args.start, args.end)
        and (not args.section or args.section in r.get("sections", []))
        and r["id"] not in set(args.exclude or [])
    ]
    groups = {
        kind: sorted((r for r in valid if r["source_type"] == kind), key=lambda r: r["id"])
        for kind in ("sinc_newsroom", "institution")
    }
    needed = {
        "sinc_newsroom": args.calibration[0] + args.test[0],
        "institution": args.calibration[1] + args.test[1],
    }
    print(
        f"{len(records)} candidates · {len(valid)} with a CC licence in the period "
        f"({len(groups['sinc_newsroom'])} SINC newsroom, {len(groups['institution'])} institutions)"
    )
    for kind, count in needed.items():
        if len(groups[kind]) < count:
            sys.exit(f"Not enough {kind} articles for the requested sample.")

    rng = random.Random(args.seed)
    chosen = {kind: rng.sample(groups[kind], needed[kind]) for kind in groups}
    split = {
        "calibration": chosen["sinc_newsroom"][:args.calibration[0]] + chosen["institution"][:args.calibration[1]],
        "test": chosen["sinc_newsroom"][args.calibration[0]:] + chosen["institution"][args.calibration[1]:],
    }

    SAMPLE.mkdir(parents=True, exist_ok=True)
    for old in SAMPLE.glob("*.json"):
        old.unlink()  # a new sample replaces the previous one
    log = {
        "seed": args.seed,
        "period": [args.start, args.end],
        "section": args.section,
        "excluded": args.exclude,
        "candidates": len(records),
        "valid": {kind: len(items) for kind, items in groups.items()},
        "groups": {},
    }
    for group, items in split.items():
        log["groups"][group] = []
        for record in items:
            record["group"] = group
            (SAMPLE / f"{record['id']}.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            log["groups"][group].append({"id": record["id"], "source_type": record["source_type"], "url": record["url"]})
    (DATA / "sample_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Sample: {len(split['calibration'])} calibration and {len(split['test'])} test articles → {SAMPLE}")


def corpus(args):
    """Simple random sample of all valid articles, with no stratification, to estimate the corpus metrics."""
    records = [load_article(path) for path in sorted(CANDIDATES.glob("*.json"))]
    valid = sorted(
        (r for r in records if r["cc_licence"] and r["article"]["body"] and in_period(r, args.start, args.end)),
        key=lambda r: r["id"],
    )
    if len(valid) < args.size:
        sys.exit(f"Only {len(valid)} valid articles; ask for fewer.")
    chosen = random.Random(args.seed).sample(valid, args.size)
    CORPUS.mkdir(parents=True, exist_ok=True)
    for old in CORPUS.glob("*.json"):
        old.unlink()
    for record in chosen:
        (CORPUS / f"{record['id']}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    kinds = {kind: sum(r["source_type"] == kind for r in chosen) for kind in ("sinc_newsroom", "institution")}
    (DATA / "corpus_sample_log.json").write_text(json.dumps({
        "seed": args.seed, "period": [args.start, args.end], "valid": len(valid), "size": args.size,
        "source_types": kinds, "ids": sorted(r["id"] for r in chosen),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{args.size} of {len(valid)} valid articles ({kinds['sinc_newsroom']} SINC newsroom, "
          f"{kinds['institution']} institutions) → {CORPUS}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    steps = parser.add_subparsers(dest="step", required=True)
    step_1 = steps.add_parser("candidates")
    step_1.add_argument("--start", required=True)
    step_1.add_argument("--end", required=True)
    step_2 = steps.add_parser("sample")
    step_2.add_argument("--start", required=True)
    step_2.add_argument("--end", required=True)
    step_2.add_argument("--section", default=None, help="for example Tecnologia; all sections by default")
    step_2.add_argument("--calibration", nargs=2, type=int, default=[3, 3], metavar=("SINC", "INSTITUTIONS"))
    step_2.add_argument("--test", nargs=2, type=int, default=[20, 20], metavar=("SINC", "INSTITUTIONS"))
    step_2.add_argument("--seed", type=int, default=2026)
    step_2.add_argument("--exclude", nargs="*", default=PRACTICE_IDS, help="article ids to leave out; the practice articles by default")
    step_3 = steps.add_parser("corpus")
    step_3.add_argument("--start", required=True)
    step_3.add_argument("--end", required=True)
    step_3.add_argument("--size", type=int, default=200)
    step_3.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    {"candidates": candidates, "sample": sample, "corpus": corpus}[args.step](args)


if __name__ == "__main__":
    main()
