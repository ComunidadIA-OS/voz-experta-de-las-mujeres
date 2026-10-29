"""Build the open dataset: every analysed article with its labels and the passage behind each one.

    python evaluation/export_dataset.py evaluation/data/predictions/gpt-oss-120b
    python evaluation/export_dataset.py evaluation/data/predictions/gpt-oss-120b --annotators Eva_Mar Elena

Writes to evaluation/data/release/:
- people.csv: one row per person and article, with the model labels and their evidence passages
- annotations.csv: the same for the human annotation, if annotators are given
- sections.csv: number of articles by SINC section and source type

Only articles with a Creative Commons licence are exported; each row links to the article on SINC.
The gender suggested by the name layer is never exported: it is only used in aggregate figures.
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


DATA = Path(__file__).resolve().parent / "data"
RELEASE = DATA / "release"
ANNOTATIONS = DATA / "annotations"
PEOPLE_COLUMNS = [
    "article_id", "url", "published", "source_type", "sections",
    "name", "gender_representation", "gender_evidence",
    "technical_expert", "source_role", "expert_evidence",
    "work_role", "work_role_evidence",
    "headline_reference", "headline_reference_evidence",
    "direct_quotes", "indirect_quotes", "quote_passages",
    "model", "prompt_version",
]
ANNOTATION_COLUMNS = [
    "article_id", "url", "group", "annotator", "person_id", "name",
    "gender_representation", "gender_evidence", "technical_expert", "source_role",
    "work_role", "headline_reference", "direct_quotes", "indirect_quotes",
]


def write_csv(path, columns, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("predictions", type=Path, help="folder written by run_batch.py")
    parser.add_argument("--annotators", nargs="*", default=[])
    args = parser.parse_args()

    RELEASE.mkdir(parents=True, exist_ok=True)
    people_rows, sections = [], Counter()
    analyses = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(args.predictions.glob("*.json"))]
    analyses = [a for a in analyses if a.get("cc_licence")]
    for analysis in analyses:
        for section in analysis.get("sections") or ["(none)"]:
            sections[(section, analysis.get("source_type"))] += 1
        for person in analysis["original_prediction"]["people"]:
            quotes = person.get("quotes") or []
            people_rows.append({
                "article_id": analysis["article_id"],
                "url": analysis["url"],
                "published": (analysis.get("published") or "")[:10],
                "source_type": analysis.get("source_type"),
                "sections": "; ".join(analysis.get("sections") or []),
                "name": person.get("name") or "",
                "gender_representation": person.get("gender_representation") or "unknown",
                "gender_evidence": person.get("gender_evidence") or "",
                "technical_expert": person.get("technical_expert"),
                "source_role": person.get("source_role") or "",
                "expert_evidence": person.get("expert_evidence") or "",
                "work_role": person.get("work_role") or "",
                "work_role_evidence": person.get("work_role_evidence") or "",
                "headline_reference": person.get("headline_reference") or "",
                "headline_reference_evidence": person.get("headline_reference_evidence") or "",
                "direct_quotes": sum(q.get("type") == "direct" for q in quotes),
                "indirect_quotes": sum(q.get("type") == "indirect" for q in quotes),
                "quote_passages": " | ".join(q.get("text") or "" for q in quotes),
                "model": analysis.get("model"),
                "prompt_version": analysis.get("prompt_version"),
            })
    write_csv(RELEASE / "people.csv", PEOPLE_COLUMNS, people_rows)

    with open(RELEASE / "sections.csv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["section", "source_type", "articles"])
        for (section, source), count in sorted(sections.items(), key=lambda item: -item[1]):
            writer.writerow([section, source, count])

    annotation_rows = []
    for annotator in args.annotators:
        for path in sorted((ANNOTATIONS / annotator).glob("*.json")):
            annotation = json.loads(path.read_text(encoding="utf-8"))
            if annotation.get("review_status") != "human_reviewed":
                continue
            quotes = annotation.get("reviewed_quotes", [])
            for person in annotation.get("reviewed_people", []):
                types = [q.get("type") for q in quotes if q.get("speaker_id") == person.get("person_id")]
                annotation_rows.append({
                    **{k: annotation.get(k) for k in ("article_id", "url", "group", "annotator")},
                    **{k: person.get(k) for k in ANNOTATION_COLUMNS if k in person},
                    "direct_quotes": types.count("direct"),
                    "indirect_quotes": types.count("indirect"),
                })
    if args.annotators:
        write_csv(RELEASE / "annotations.csv", ANNOTATION_COLUMNS, annotation_rows)

    print(f"{len(analyses)} articles · {len(people_rows)} people · {len(annotation_rows)} annotated people → {RELEASE}")
    print("Articles by section:")
    by_section = Counter()
    for (section, _), count in sections.items():
        by_section[section] += count
    for section, count in by_section.most_common():
        print(f"  {section}: {count}")


if __name__ == "__main__":
    main()
