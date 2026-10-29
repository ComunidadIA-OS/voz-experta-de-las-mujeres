"""Gender from Spanish grammatical agreement around each person's name.

The model sometimes leaves gender as unknown even when the article says
"la investigadora" or "el primer autor". This layer reads the article itself:
it looks at the words just before and after each mention of the person and
looks for gendered role nouns and articles. It only fills genders that the
model left as unknown, never changes a gender the model assigned, and only
when every cue found points the same way.

Grammatical agreement is evidence in the text, so the result is written in
gender_representation (the text gender). The model's own answer is kept in
gender_model and the change is marked in gender_from. Run it before the name
layer, so names are only used when neither the model nor the grammar decide.

run_batch.py and app.py apply it automatically after each model call.
For predictions saved before that, and to measure it against the annotation:

    python evaluation/grammar_gender.py apply evaluation/data/predictions/gpt-oss-120b
    python evaluation/grammar_gender.py check --annotator Elena
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sinc import load_article  # noqa: E402

# Pairs of feminine / masculine forms. Epicene words (portavoz, genetista,
# especialista, responsable, miembro...) are left out on purpose.
PAIRS = [
    ("investigadora", "investigador"), ("coordinadora", "coordinador"),
    ("directora", "director"), ("subdirectora", "subdirector"),
    ("profesora", "profesor"), ("catedrática", "catedrático"),
    ("autora", "autor"), ("coautora", "coautor"), ("doctora", "doctor"),
    ("científica", "científico"), ("experta", "experto"),
    ("astrónoma", "astrónomo"), ("astrofísica", "astrofísico"),
    ("física", "físico"), ("química", "químico"), ("bióloga", "biólogo"),
    ("ecóloga", "ecólogo"), ("arqueóloga", "arqueólogo"),
    ("paleontóloga", "paleontólogo"), ("antropóloga", "antropólogo"),
    ("geóloga", "geólogo"), ("psicóloga", "psicólogo"),
    ("neurocientífica", "neurocientífico"), ("epidemióloga", "epidemiólogo"),
    ("ingeniera", "ingeniero"), ("médica", "médico"),
    ("veterinaria", "veterinario"), ("enfermera", "enfermero"),
    ("técnica", "técnico"), ("becaria", "becario"),
    ("presidenta", "presidente"), ("vicepresidenta", "vicepresidente"),
    ("jefa", "jefe"), ("rectora", "rector"), ("vicerrectora", "vicerrector"),
    ("decana", "decano"), ("ministra", "ministro"),
    ("consejera", "consejero"), ("secretaria", "secretario"),
    ("fundadora", "fundador"), ("cofundadora", "cofundador"),
    ("compañera", "compañero"), ("colega", None), ("divulgadora", "divulgador"),
    ("gerente", None), ("asesora", "asesor"), ("analista", None),
    ("estudiante", None), ("doctoranda", "doctorando"),
    ("afiliada", "afiliado"), ("responsable", None),
]
FEMININE = {f for f, m in PAIRS}
MASCULINE = {m for f, m in PAIRS if m}
ARTICLES = {"la": "woman", "el": "man", "una": "woman", "un": "man"}
BEFORE, AFTER = 6, 4


def fold(text):
    return unicodedata.normalize("NFC", text or "").lower()


def tokens(text):
    return re.findall(r"[\wáéíóúüñ-]+|[,.;:()«»“”\"']", fold(text))


def name_variants(name):
    parts = [p for p in re.split(r"\s+", (name or "").strip()) if p]
    variants = {" ".join(parts)}
    if len(parts) >= 2:
        variants.add(" ".join(parts[1:]))          # surname(s)
        variants.add(parts[-1])                     # last surname
        if len(parts) >= 3:
            variants.add(" ".join(parts[1:-1]))     # first surname
    return [tokens(v) for v in variants if len(v) > 2]


def cues_around(article_tokens, start, end):
    """Gender cues in the words around one mention."""
    found = []
    window_before = article_tokens[max(0, start - BEFORE):start]
    # Stop at a sentence boundary so a cue from the previous sentence is not used.
    for i in range(len(window_before) - 1, -1, -1):
        if window_before[i] in {".", ";", ":", "“", "”", "«", "»", '"'}:
            window_before = window_before[i + 1:]
            break
    window_after = article_tokens[end:end + AFTER]
    # After the name, only an apposition counts: "Ana Ruiz, investigadora de..."
    if window_after[:1] == [","]:
        window_after = window_after[1:AFTER]
    else:
        window_after = []
    for word in window_before + window_after:
        if word in FEMININE:
            found.append("woman")
        elif word in MASCULINE:
            found.append("man")
    # An article right before the role noun: "la investigadora", "el primer autor".
    for i, word in enumerate(window_before[:-1]):
        nxt = window_before[i + 1]
        if word in ARTICLES and (nxt in FEMININE or nxt in MASCULINE or nxt in {"primer", "primera"}):
            found.append(ARTICLES[word])
    return found


def grammar_gender(name, article_text):
    article_tokens = tokens(article_text)
    cues = []
    for variant in name_variants(name):
        n = len(variant)
        for i in range(len(article_tokens) - n + 1):
            if article_tokens[i:i + n] == variant:
                cues += cues_around(article_tokens, i, i + n)
    if cues and len(set(cues)) == 1:
        return cues[0]
    return None


def article_text(record):
    article = record.get("article", {})
    return "\n\n".join(v for v in article.values() if v)


def fill(result, text):
    """Fill unknown genders in one model result. Returns how many were filled."""
    changed = 0
    for person in result.get("people", []):
        if person.get("gender_representation") != "unknown" or not person.get("name"):
            continue
        gender = grammar_gender(person["name"], text)
        if gender:
            person["gender_model"] = "unknown"
            person["gender_representation"] = gender
            person["gender_from"] = "grammar_layer"
            changed += 1
    return changed


def apply(folder):
    """Apply the layer to predictions saved before it was part of run_batch."""
    changed = files = 0
    for path in sorted(Path(folder).glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        n = fill(record.get("original_prediction", {}), article_text(record))
        if n:
            changed += n
            files += 1
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{changed} people with unknown gender got a grammatical gender, in {files} articles.")


def check(annotator, sample):
    """Accuracy of the rule on the human annotation, ignoring the model."""
    root = Path(__file__).resolve().parent / "data"
    right = wrong = none = 0
    errors = []
    for path in sorted((root / "annotations" / annotator).glob("*.json")):
        ann = json.loads(path.read_text(encoding="utf-8"))
        text = article_text(load_article(root / sample / path.name))
        for person in ann.get("reviewed_people", []):
            truth = person.get("gender_representation")
            if truth not in {"woman", "man"} or not person.get("name"):
                continue
            guess = grammar_gender(person["name"], text)
            if guess is None:
                none += 1
            elif guess == truth:
                right += 1
            else:
                wrong += 1
                errors.append(f"{path.stem} {person['name']}: {guess} (annotation: {truth})")
    total = right + wrong + none
    print(f"{total} people with gender in the annotation: right {right}, wrong {wrong}, no cue {none}.")
    for e in errors:
        print("  ", e)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    steps = parser.add_subparsers(dest="step", required=True)
    a = steps.add_parser("apply")
    a.add_argument("predictions", type=Path)
    c = steps.add_parser("check")
    c.add_argument("--annotator", required=True)
    c.add_argument("--sample", default="sample")
    args = parser.parse_args()
    if args.step == "apply":
        apply(args.predictions)
    else:
        check(args.annotator, args.sample)


if __name__ == "__main__":
    main()
