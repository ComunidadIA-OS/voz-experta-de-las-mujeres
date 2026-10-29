"""Name layer: checks the gender stated in the text against the first name, and suggests one when the text is silent.

The text always wins. The INE list (names of residents in Spain) is used first; if the name is not
there, the WIPO World Gender Name Dictionary 2.0 covers names from other countries. Suggestions are
stored in separate, flagged fields so results can be reported with and without them.

Step 1, once (INE Excel with a Hombres and a Mujeres sheet, names with frequency of 20 or more):
    python evaluation/name_layer.py prepare --excel evaluation/data/nombres_por_edad_media.xlsx
Step 2 (uses evaluation/data/wgnd_2_0_name-gender_nocode.csv if present):
    python evaluation/name_layer.py apply evaluation/data/predictions/gpt-oss-120b
"""

import argparse
import csv
import json
import re
import sys
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree


DATA = Path(__file__).resolve().parent / "data"
INE_TABLE = DATA / "ine_names.json"
WGND_FILE = DATA / "wgnd_2_0_name-gender_nocode.csv"
TITLES = {"DR", "DRA", "PROF", "PROFA", "SR", "SRA", "D", "DNA", "DONA", "DON"}
# The INE stores «María del Carmen» as «MARIA CARMEN», so particles are dropped.
PARTICLES = {"DE", "DEL", "LA", "LAS", "LOS", "Y"}
XLSX = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def name_key(text):
    """Upper case, no accents, single spaces, as in the INE files."""
    plain = "".join(
        c for c in unicodedata.normalize("NFD", text or "")
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(re.sub(r"[^\w\s]", " ", plain.upper()).split())


def xlsx_sheets(path):
    """Read every sheet of an .xlsx file with the standard library: {sheet name: rows}."""
    tag = lambda name: f"{{{XLSX['m']}}}{name}"
    with zipfile.ZipFile(path) as book:
        shared = []
        if "xl/sharedStrings.xml" in book.namelist():
            root = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in item.iter(tag("t"))) for item in root.findall("m:si", XLSX)]
        relations = {
            rel.get("Id"): rel.get("Target").lstrip("/").removeprefix("xl/")
            for rel in ElementTree.fromstring(book.read("xl/_rels/workbook.xml.rels")).findall("rel:Relationship", XLSX)
        }
        sheets = {}
        for sheet in ElementTree.fromstring(book.read("xl/workbook.xml")).iter(tag("sheet")):
            target = "xl/" + relations[sheet.get(f"{{{XLSX['r']}}}id")]
            rows = []
            for row in ElementTree.fromstring(book.read(target)).iter(tag("row")):
                values = []
                for cell in row.findall("m:c", XLSX):
                    value, kind = cell.find("m:v", XLSX), cell.get("t")
                    if kind == "s" and value is not None:
                        values.append(shared[int(value.text)])
                    elif kind == "inlineStr":
                        values.append("".join(t.text or "" for t in cell.iter(tag("t"))))
                    else:
                        values.append(value.text if value is not None else "")
                rows.append(values)
            sheets[sheet.get("name")] = rows
    return sheets


def name_frequencies(rows, label):
    """Find the Nombre and Frecuencia columns by their titles."""
    header = next((i for i, row in enumerate(rows) if any(c.strip().lower() == "nombre" for c in row)), None)
    if header is None:
        sys.exit(f"{label}: column «Nombre» not found")
    columns = [c.strip().lower() for c in rows[header]]
    name_col = columns.index("nombre")
    freq_col = next((i for i, c in enumerate(columns) if "frecuencia" in c), None)
    if freq_col is None:
        sys.exit(f"{label}: column «Frecuencia» not found")
    frequencies = {}
    for row in rows[header + 1:]:
        if len(row) <= max(name_col, freq_col):
            continue
        number = re.sub(r"[.\s,]", "", row[freq_col])
        if number.isdigit() and row[name_col].strip():
            frequencies[name_key(row[name_col])] = int(number)
    return frequencies


def prepare(args):
    sheets = xlsx_sheets(args.excel)
    sheet = lambda prefix: next((rows for name, rows in sheets.items() if name.lower().startswith(prefix)), None)
    if sheet("muj") is None or sheet("hom") is None:
        sys.exit(f"{args.excel}: expected the sheets «Mujeres» and «Hombres», found {list(sheets)}")
    women = name_frequencies(sheet("muj"), "Mujeres")
    men = name_frequencies(sheet("hom"), "Hombres")
    table = {name: [women.get(name, 0), men.get(name, 0)] for name in set(women) | set(men)}
    INE_TABLE.parent.mkdir(parents=True, exist_ok=True)
    INE_TABLE.write_text(json.dumps(table, ensure_ascii=False), encoding="utf-8")
    print(f"{len(table)} names ({len(women)} women's, {len(men)} men's) → {INE_TABLE}")


def first_names(name):
    """The first given name, then the compound one («María José»).

    Trying the compound first mistakes surnames for names («Alex Martín» → «ALEX MARTIN»).
    """
    parts = [p for p in name_key(name).split() if p not in TITLES and p not in PARTICLES]
    return [c for c in (parts[0] if parts else "", " ".join(parts[:2])) if c]


def load_wgnd(path, wanted):
    """Read only the needed names from the WIPO dictionary; drop names listed with both genders."""
    genders = {}
    with open(path, encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.reader(handle):
            if len(row) != 2 or row[1] not in ("F", "M"):
                continue
            key = name_key(row[0])
            if key in wanted:
                gender = "woman" if row[1] == "F" else "man"
                genders[key] = gender if genders.get(key, gender) == gender else None
    return {key: gender for key, gender in genders.items() if gender}


def suggest(name, ine, wgnd, threshold):
    """The INE decides when it knows the name; otherwise WIPO, which only lists single-gender names."""
    for candidate in first_names(name):
        counts = ine.get(candidate)
        if counts and sum(counts):
            share = counts[0] / sum(counts)
            suggestion = "woman" if share >= threshold else "man" if share <= 1 - threshold else None
            return {"source": "INE", "name_checked": candidate, "share_women": round(share, 4), "suggestion": suggestion}
    for candidate in first_names(name):
        if candidate in wgnd:
            return {"source": "WIPO", "name_checked": candidate, "share_women": None, "suggestion": wgnd[candidate]}
    return {"source": None, "name_checked": None, "share_women": None, "suggestion": None}


def apply(args):
    if not INE_TABLE.exists():
        sys.exit("INE table missing: run «python evaluation/name_layer.py prepare ...» first")
    ine = json.loads(INE_TABLE.read_text(encoding="utf-8"))
    files = {path: json.loads(path.read_text(encoding="utf-8")) for path in sorted(args.predictions.glob("*.json"))}

    wgnd = {}
    if args.wgnd.exists():
        wanted = {
            candidate
            for analysis in files.values()
            for person in analysis["original_prediction"]["people"]
            for candidate in first_names(person.get("name") or "")
        }
        wgnd = load_wgnd(args.wgnd, wanted - set(ine))
    else:
        print(f"Note: {args.wgnd} not found; only the INE is used.")

    counts = Counter()
    for path, analysis in files.items():
        for person in analysis["original_prediction"]["people"]:
            layer = suggest(person.get("name") or "", ine, wgnd, args.threshold)
            text_gender = person.get("gender_representation") or "unknown"
            person["name_layer"] = layer
            person["name_contradicts_text"] = bool(
                layer["suggestion"] and text_gender in ("woman", "man") and layer["suggestion"] != text_gender
            )
            if text_gender != "unknown":
                person["gender_with_name"], person["gender_source"] = text_gender, "text"
            elif layer["suggestion"]:
                person["gender_with_name"], person["gender_source"] = layer["suggestion"], layer["source"]
            else:
                person["gender_with_name"], person["gender_source"] = "unknown", "none"
            counts[person["gender_source"]] += 1
            counts["unrecognised_name"] += layer["source"] is None
            counts["contradictions"] += person["name_contradicts_text"]
        analysis["name_layer_sources"] = ["INE"] + (["WIPO"] if wgnd else [])
        analysis["name_layer_threshold"] = args.threshold
        path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"Gender from the text: {counts['text']} · suggested by the INE: {counts['INE']} · "
        f"by WIPO: {counts['WIPO']} · unknown: {counts['none']}"
    )
    print(
        f"Names neither source recognises: {counts['unrecognised_name']} · "
        f"name contradicts the text: {counts['contradictions']}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    steps = parser.add_subparsers(dest="step", required=True)
    step_1 = steps.add_parser("prepare")
    step_1.add_argument("--excel", required=True, help="nombres_por_edad_media.xlsx from the INE")
    step_2 = steps.add_parser("apply")
    step_2.add_argument("predictions", type=Path, help="folder written by run_batch.py")
    step_2.add_argument("--threshold", type=float, default=0.95, help="minimum INE share to suggest a gender")
    step_2.add_argument("--wgnd", type=Path, default=WGND_FILE, help="WIPO name dictionary, for names not in the INE")
    args = parser.parse_args()
    prepare(args) if args.step == "prepare" else apply(args)


if __name__ == "__main__":
    main()
