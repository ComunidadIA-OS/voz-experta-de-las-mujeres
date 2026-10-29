"""Blind human annotation of the sampled articles, selecting passages directly on the text.

    python evaluation/annotate.py

Opens http://127.0.0.1:8765 (in a Codespace, open port 8765 from the Ports tab).
The page never shows the model prediction. Each annotation is saved at once to
evaluation/data/annotations/<annotator>/<article id>.json in the app's review format
(reviewed_people and reviewed_quotes), so metrics.py can compare it with the model.
"""

import csv
import io
import json
import re
import sys
import threading
import unicodedata
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sinc import load_article


HERE = Path(__file__).resolve().parent
SAMPLE = HERE / "data" / "sample"
ANNOTATIONS = HERE / "data" / "annotations"
PAGE = HERE / "annotate.html"
GUIDE_VERSION = "0.4"
PORT = 8765

GENDER = {"mujer": "woman", "hombre": "man", "otro": "other_explicit", "desconocido": "unknown"}
WORK_ROLE = {"protagoniza": "leads", "comenta": "comments", "aparece": "mentioned"}
QUOTE_TYPE = {"directa": "direct", "indirecta": "indirect"}
SOURCE_ROLE = {
    "especialista": "specialist",
    "portavoz_institucional": "spokesperson",
    "cargo_politico": "politician",
    "testimonio": "testimony",
    "solo_mencion": "mentioned_only",
    "otro": "other",
}


def safe_name(text):
    return re.sub(r"[^\w-]", "_", (text or "").strip())[:40] or None


def valid_id(text):
    return bool(re.fullmatch(r"[0-9a-f]{12}", text or ""))


def page_article(record):
    """The page was written for the first prototype and reads these field names."""
    article = record["article"]
    return {
        "id": record["id"],
        "url": record["url"],
        "fecha_publicacion": record.get("published"),
        "grupo": record.get("group", "practice"),
        "campos": {
            "titular": article["headline"],
            "entradilla": article["introduction"],
            "cuerpo": article["body"],
        },
    }


def load_record(article_id):
    return load_article(SAMPLE / f"{article_id}.json")


def annotation_path(annotator, article_id):
    return ANNOTATIONS / annotator / f"{article_id}.json"


def load_saved(annotator, article_id):
    path = annotation_path(annotator, article_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def status(annotator, article_id):
    saved = load_saved(annotator, article_id)
    if saved is None:
        return "pendiente"
    return "terminada" if saved.get("review_status") == "human_reviewed" else "en curso"


def list_articles(annotator):
    order = {"calibration": 0, "test": 1}
    items = []
    for path in sorted(SAMPLE.glob("*.json")):
        record = load_article(path)
        items.append({
            "id": record["id"],
            "titular": record["article"]["headline"],
            "fecha": (record.get("published") or "")[:10],
            "grupo": record.get("group", "practice"),
            "estado": status(annotator, record["id"]) if annotator else "pendiente",
        })
    return sorted(items, key=lambda item: (order.get(item["grupo"], 2), item["id"]))


def from_utf16(text, position):
    """The browser counts UTF-16 units; Python counts characters."""
    return len(text.encode("utf-16-le")[: position * 2].decode("utf-16-le", errors="ignore"))


def fix_positions(page_annotation, fields):
    """Turn browser positions into character positions and check every passage matches the text."""
    warnings = []

    def fix(passage):
        if not passage:
            return
        text = fields.get(passage.get("campo"), "")
        start, end = from_utf16(text, passage["inicio16"]), from_utf16(text, passage["fin16"])
        passage["inicio"], passage["fin"] = start, end
        if text[start:end] != passage.get("texto"):
            warnings.append(f"The passage «{passage.get('texto', '')[:40]}» does not match the text")

    for person in page_annotation.get("personas", []):
        for passage in person.get("menciones", []) + person.get("citas", []):
            fix(passage)
        fix(person.get("indicio_genero"))
        fix(person.get("evidencia_rol"))
    return warnings


def headline_reference(person):
    """named if a mention in the headline or lead contains the person's name; described if it does not."""
    plain = lambda text: "".join(c for c in unicodedata.normalize("NFD", (text or "").lower()) if unicodedata.category(c) != "Mn")
    keys = [t for t in re.findall(r"\w+", plain(person.get("nombre"))) if len(t) >= 3 and t not in {"del", "las", "los"}]
    up_front = [m for m in person.get("menciones", []) if m.get("campo") in ("titular", "entradilla")]
    if not up_front:
        return "absent", ""
    for mention in up_front:
        if any(re.search(rf"\b{re.escape(k)}\b", plain(mention.get("texto"))) for k in keys):
            return "named", mention.get("texto", "")
    return "described", up_front[0].get("texto", "")


def review_tables(page_annotation):
    """Convert the page's annotation into the app's review tables."""
    people, quotes = [], []
    for index, person in enumerate(page_annotation.get("personas", []), start=1):
        person_id = f"p{index}"
        role = person.get("rol")
        mentioned_in = {mention.get("campo") for mention in person.get("menciones", [])}
        reference, reference_evidence = headline_reference(person)
        people.append({
            "person_id": person_id,
            "name": person.get("nombre") or "",
            "professional_role": role or "",
            "technical_expert": "yes" if role == "especialista" else "no",
            "source_role": SOURCE_ROLE.get(role, "other"),
            "in_headline": "titular" in mentioned_in,
            "in_introduction": "entradilla" in mentioned_in,
            "expert_evidence": (person.get("evidencia_rol") or {}).get("texto", ""),
            "gender_representation": GENDER.get(person.get("genero"), "unknown"),
            "gender_evidence": (person.get("indicio_genero") or {}).get("texto", ""),
            "work_role": WORK_ROLE.get(person.get("participacion"), "mentioned"),
            "work_role_evidence": "",
            "headline_reference": reference,
            "headline_reference_evidence": reference_evidence,
            "review_notes": "",
        })
        for quote in person.get("citas", []):
            quotes.append({
                "speaker_id": person_id,
                "type": QUOTE_TYPE.get(quote.get("tipo"), ""),
                "text": quote.get("texto", ""),
                "attribution_evidence": "",
                "review_notes": "",
            })
    return people, quotes


def export_csv(annotator):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["article_id", "url", "review_status", "person_id", "name", "technical_expert",
                     "gender_representation", "gender_evidence", "work_role", "direct_quotes", "indirect_quotes"])
    for path in sorted((ANNOTATIONS / annotator).glob("*.json")):
        saved = json.loads(path.read_text(encoding="utf-8"))
        for person in saved.get("reviewed_people", []):
            types = [q["type"] for q in saved.get("reviewed_quotes", []) if q["speaker_id"] == person["person_id"]]
            writer.writerow([
                saved["article_id"], saved["url"], saved["review_status"], person["person_id"], person["name"],
                person["technical_expert"], person["gender_representation"], person["gender_evidence"],
                person["work_role"], types.count("direct"), types.count("indirect"),
            ])
    return output.getvalue()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def reply(self, code, body, content_type="application/json; charset=utf-8", extra=None):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlparse(self.path)
        annotator = safe_name(parse_qs(url.query).get("anotadora", [""])[0])
        if url.path == "/":
            return self.reply(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if url.path == "/api/noticias":
            return self.reply(200, list_articles(annotator))
        if url.path.startswith("/api/noticia/"):
            article_id = url.path.rsplit("/", 1)[-1]
            if not valid_id(article_id) or not (SAMPLE / f"{article_id}.json").exists():
                return self.reply(404, {"error": "article not found"})
            saved = load_saved(annotator, article_id) if annotator else None
            return self.reply(200, {
                "noticia": page_article(load_record(article_id)),
                "anotacion": saved.get("page_annotation") if saved else None,
            })
        if url.path == "/api/exportar.csv" and annotator:
            return self.reply(200, ("﻿" + export_csv(annotator)).encode("utf-8"), "text/csv; charset=utf-8",
                              {"Content-Disposition": f'attachment; filename="annotations_{annotator}.csv"'})
        self.reply(404, {"error": "unknown path"})

    def do_PUT(self):
        url = urlparse(self.path)
        annotator = safe_name(parse_qs(url.query).get("anotadora", [""])[0])
        article_id = url.path.rsplit("/", 1)[-1]
        if not url.path.startswith("/api/anotacion/") or not annotator or not valid_id(article_id):
            return self.reply(400, {"error": "invalid request"})
        page_annotation = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
        record = load_record(article_id)
        warnings = fix_positions(page_annotation, page_article(record)["campos"])
        people, quotes = review_tables(page_annotation)
        path = annotation_path(annotator, article_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "article_id": article_id,
            "url": record["url"],
            "group": record.get("group"),
            "source_type": record.get("source_type"),
            "annotator": annotator,
            "guide_version": GUIDE_VERSION,
            "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "article_sha256": record.get("sha256"),
            "review_status": "human_reviewed" if page_annotation.get("terminada") else "draft_review",
            "reviewed_people": people,
            "reviewed_quotes": quotes,
            "page_annotation": page_annotation,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        self.reply(200, {"ok": True, "avisos": warnings})


def main():
    if not any(SAMPLE.glob("*.json")):
        sys.exit("No sampled articles yet. Run «python evaluation/sinc.py sample ...» first.")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    address = f"http://127.0.0.1:{PORT}"
    print(f"Annotation page at {address}  (Ctrl+C to stop)", flush=True)
    if "--no-browser" not in sys.argv:
        threading.Timer(0.5, lambda: webbrowser.open(address)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
