"""Simple baseline: the people spaCy finds, compared with the human annotation and with the model.

It answers whether a classic, free method finds the same people (and the same women) as the LLM.
Only presence is compared: spaCy finds names but not quotes, roles or gender.

    pip install spacy && python -m spacy download es_core_news_md   (once)
    python evaluation/baseline_spacy.py --annotator Eva --predictions evaluation/data/predictions/gpt-oss-120b --group test
"""

import argparse
import json
import time
from pathlib import Path

import spacy

from metrics import ANNOTATIONS, human_people, match, model_people, name_keys, write
from sinc import load_article


SAMPLE = Path(__file__).resolve().parent / "data" / "sample"


def spacy_people(nlp, text):
    """Person entities, joining repeated references to the same person («Nuria Oliver», «Oliver»)."""
    people = []
    for entity in nlp(text).ents:
        if entity.label_ != "PER":
            continue
        name = " ".join(entity.text.split())
        keys = name_keys(name)
        if not keys:
            continue
        for person in people:
            if keys & person["keys"]:
                if len(name) > len(person["name"]):
                    person["name"] = name
                person["keys"] |= keys
                break
        else:
            people.append({"name": name, "keys": keys})
    return [{"name": person["name"]} for person in people]


def detection_row(human, found):
    pairs, missed, extra = match(human, found)
    women = [p for p in human if p["gender"] == "woman"]
    women_found = sum(1 for h, _ in pairs if h["gender"] == "woman")
    return {"found": len(pairs), "missed": len(missed), "extra": len(extra), "women": len(women), "women_found": women_found}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--annotator", required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--group", default="test")
    parser.add_argument("--spacy-model", default="es_core_news_md")
    args = parser.parse_args()

    nlp = spacy.load(args.spacy_model)
    totals = {"spaCy": {}, "LLM": {}}
    seconds = 0.0
    articles = 0
    for path in sorted((ANNOTATIONS / args.annotator).glob("*.json")):
        annotation = json.loads(path.read_text(encoding="utf-8"))
        if annotation.get("review_status") != "human_reviewed" or annotation.get("group") != args.group:
            continue
        prediction_path = args.predictions / f"{annotation['article_id']}.json"
        if not prediction_path.exists():
            continue
        articles += 1
        human = human_people(annotation)
        article = load_article(SAMPLE / f"{annotation['article_id']}.json")["article"]

        started = time.perf_counter()
        found_spacy = spacy_people(nlp, "\n\n".join(article.values()))
        seconds += time.perf_counter() - started
        found_llm = model_people(json.loads(prediction_path.read_text(encoding="utf-8")))

        for method, found in (("spaCy", found_spacy), ("LLM", found_llm)):
            for key, value in detection_row(human, found).items():
                totals[method][key] = totals[method].get(key, 0) + value

    if not articles:
        raise SystemExit("No finished annotations with a prediction for that group.")

    results = {"annotator": args.annotator, "group": args.group, "articles": articles,
               "spacy_model": args.spacy_model, "spacy_seconds_per_article": round(seconds / articles, 2),
               "detection": totals}
    lines = [
        f"# Baseline: spaCy against the LLM · {args.annotator} · {args.group}", "",
        f"{articles} annotated articles. Reference: the people annotated by hand. "
        f"spaCy ({args.spacy_model}) takes {results['spacy_seconds_per_article']} s per article and costs nothing.", "",
        "| Method | People found | Missed | Extra (not annotated) | Women found |",
        "| --- | --- | --- | --- | --- |",
    ]
    for method, row in totals.items():
        total = row["found"] + row["missed"]
        lines.append(
            f"| {method} | {row['found']} of {total} | {row['missed']} | {row['extra']} "
            f"| {row['women_found']} of {row['women']} |"
        )
    lines += ["", "spaCy only finds names: quotes, roles, work role and gender still need the LLM or the annotation."]
    write(f"baseline_spacy_{args.group}", results, lines)


if __name__ == "__main__":
    main()
