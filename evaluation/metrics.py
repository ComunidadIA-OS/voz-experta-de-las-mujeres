"""Team metrics: the women's funnel, recognition, credit loss and model error against human annotation.

Model error on the annotated test articles:
    python evaluation/metrics.py compare --annotator Eva --predictions evaluation/data/predictions/gpt-oss-120b --group test [--with-name]
Agreement between two annotators on the calibration articles (Cohen's kappa):
    python evaluation/metrics.py agreement --annotators Eva Elena
Metrics for the whole corpus (only articles with a Creative Commons licence by default):
    python evaluation/metrics.py corpus evaluation/data/predictions/gpt-oss-120b --articles evaluation/data/corpus_sample

Percentages of women are over people whose gender is known; intervals are Wilson 95 %.
Results are written to evaluation/data/results/.
"""

import argparse
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


DATA = Path(__file__).resolve().parent / "data"
ANNOTATIONS = DATA / "annotations"
RESULTS = DATA / "results"
KNOWN = {"woman", "man", "other_explicit"}
STAGES = [
    ("Presence: mentioned", lambda p: True),
    ("Voice: quoted", lambda p: p["quoted"]),
    ("Authority: technical experts", lambda p: p["expert"]),
    ("Protagonism: lead the work", lambda p: p["work_role"] == "leads"),
    # The voices a newsroom chooses (BBC 50:50 lesson): who is called to comment on the work.
    ("Chosen voices: comment on the work", lambda p: p["work_role"] == "comments"),
    ("Recognition: named in headline or lead", lambda p: p["recognised"]),
]
ROLES = ["specialist", "spokesperson", "politician", "testimony", "other", "mentioned_only"]


def plain(text):
    return "".join(
        c for c in unicodedata.normalize("NFD", (text or "").lower())
        if unicodedata.category(c) != "Mn"
    )


def name_hits(name, text):
    """How many times the person's surname (or only name) appears in a text."""
    parts = [t for t in re.findall(r"\w+", plain(name)) if len(t) >= 3 and t not in {"del", "las", "los"}]
    keys = parts[1:] or parts
    return max((len(re.findall(rf"\b{re.escape(k)}\b", plain(text))) for k in keys), default=0)


def model_people(analysis, with_name=False, llm_only=False):
    article = analysis.get("article", {})
    full_text = "\n".join(article.values())
    people = []
    for person in analysis["original_prediction"]["people"]:
        name = person.get("name") or ""
        gender = person.get("gender_representation") or "unknown"
        if llm_only and person.get("gender_from") == "grammar_layer":
            gender = person.get("gender_model") or "unknown"
        reference = person.get("headline_reference")
        if reference not in ("named", "described", "absent"):
            # Older predictions have no headline_reference: the name is searched in the text.
            up_front = name_hits(name, article.get("headline", "")) or name_hits(name, article.get("introduction", ""))
            reference = "named" if up_front else "absent"
        if with_name and person.get("gender_with_name"):
            gender = person["gender_with_name"]
        people.append({
            "name": name,
            "gender": gender,
            "expert": person.get("technical_expert") is True,
            "role": person.get("source_role") or ("specialist" if person.get("technical_expert") is True else "other"),
            "quoted": bool(person.get("quotes")),
            "quotes": len(person.get("quotes") or []),
            "work_role": person.get("work_role") or "mentioned",
            "headline_reference": reference,
            "recognised": reference in ("named", "described"),
            "name_mentions": max(name_hits(name, full_text), 1),
            "gender_source": person.get("gender_source"),
            "unrecognised_name": "name_layer" in person and not person["name_layer"].get("source"),
        })
    return people


def human_people(annotation, article=None):
    quotes = Counter(quote.get("speaker_id") for quote in annotation.get("reviewed_quotes", []))
    full_text = "\n".join((article or {}).values())
    people = []
    for person in annotation.get("reviewed_people", []):
        expert = person.get("technical_expert") == "yes"
        reference = person.get("headline_reference") or (
            "named" if person.get("in_headline") or person.get("in_introduction") else "absent"
        )
        people.append({
            "name": person.get("name") or "",
            "gender": person.get("gender_representation") or "unknown",
            "expert": expert,
            "role": person.get("source_role") or ("specialist" if expert else "other"),
            "quoted": quotes[person.get("person_id")] > 0,
            "quotes": quotes[person.get("person_id")],
            "work_role": person.get("work_role") or "mentioned",
            "headline_reference": reference,
            "recognised": reference in ("named", "described"),
            "name_mentions": max(name_hits(person.get("name") or "", full_text), 1),
        })
    return people


def counts(people):
    """Presence and voice as counts: unique people, times named and quotations, by gender."""
    rows = {}
    for gender in ("woman", "man", "other_explicit", "unknown"):
        group = [p for p in people if p["gender"] == gender]
        rows[gender] = {
            "people": len(group),
            "name_mentions": sum(p["name_mentions"] for p in group),
            "quotes": sum(p["quotes"] for p in group),
        }
    return rows


def roles(people):
    """Authority: how many women and men are presented in each role."""
    return {role: {g: sum(p["role"] == role and p["gender"] == g for p in people) for g in ("woman", "man")} for role in ROLES}


def naming(people):
    """Recognition: of the people in the headline or lead, how many appear with their name and how many only described."""
    rows = {}
    for gender in ("woman", "man"):
        up_front = [p for p in people if p["gender"] == gender and p["recognised"]]
        named = sum(p["headline_reference"] == "named" for p in up_front)
        rows[gender] = {
            "in_headline_or_lead": len(up_front),
            "named": named,
            "described_only": len(up_front) - named,
            "share_named": named / len(up_front) if up_front else None,
            "ci95": wilson(named, len(up_front)),
        }
    return rows


def naming_table(rows):
    lines = [
        "| Gender | In headline or lead | With their name | Only described | Named share | 95 % CI |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for gender, row in rows.items():
        lines.append(
            f"| {gender} | {row['in_headline_or_lead']} | {row['named']} | {row['described_only']} "
            f"| {pct(row['share_named'])} | {ci(row['ci95'])} |"
        )
    return lines + [""]


def counts_table(rows):
    known = [g for g in ("woman", "man", "other_explicit")]
    total = {k: sum(rows[g][k] for g in known) for k in ("people", "name_mentions", "quotes")}
    lines = ["| Gender | People | Times named | Quotations |", "| --- | --- | --- | --- |"]
    for gender, row in rows.items():
        lines.append(f"| {gender} | {row['people']} | {row['name_mentions']} | {row['quotes']} |")
    share = lambda k: pct(rows["woman"][k] / total[k] if total[k] else None)
    lines += ["", f"Women among known genders: {share('people')} of people, "
              f"{share('name_mentions')} of the times someone is named, {share('quotes')} of quotations.", ""]
    return lines


def roles_table(rows):
    lines = ["| Role | Women | Men | Women's share |", "| --- | --- | --- | --- |"]
    for role, row in rows.items():
        total = row["woman"] + row["man"]
        lines.append(f"| {role} | {row['woman']} | {row['man']} | {pct(row['woman'] / total if total else None)} |")
    return lines + [""]


def wilson(successes, n, z=1.96):
    if n == 0:
        return None
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [max(0.0, centre - margin), min(1.0, centre + margin)]


def funnel(people):
    rows = {}
    for stage, condition in STAGES:
        group = [p for p in people if condition(p)]
        known = [p for p in group if p["gender"] in KNOWN]
        women = sum(p["gender"] == "woman" for p in known)
        rows[stage] = {
            "people": len(group),
            "known_gender": len(known),
            "women": women,
            "share_women": women / len(known) if known else None,
            "ci95": wilson(women, len(known)),
        }
    return rows


def credit_loss(people):
    """Of the people who lead the work, how many are quoted, by gender."""
    rows = {}
    for gender in ("woman", "man"):
        leaders = [p for p in people if p["work_role"] == "leads" and p["gender"] == gender]
        quoted = sum(p["quoted"] for p in leaders)
        rows[gender] = {
            "lead": len(leaders),
            "quoted": quoted,
            "share_quoted": quoted / len(leaders) if leaders else None,
            "ci95": wilson(quoted, len(leaders)),
        }
    return rows


def pct(value):
    return "no cases" if value is None else f"{100 * value:.0f} %"


def ci(value):
    return "—" if not value else f"{100 * value[0]:.0f}–{100 * value[1]:.0f} %"


def funnel_table(title, rows):
    lines = [f"### {title}", "", "| Stage | People | Known gender | Women | 95 % CI |", "| --- | --- | --- | --- | --- |"]
    for stage, row in rows.items():
        lines.append(
            f"| {stage} | {row['people']} | {row['known_gender']} | "
            f"{pct(row['share_women'])} ({row['women']}) | {ci(row['ci95'])} |"
        )
    return lines + [""]


def credit_table(rows_text, rows_name):
    lines = [
        "| Who leads | Text only: quoted | 95 % CI | With name layer: quoted | 95 % CI |",
        "| --- | --- | --- | --- | --- |",
    ]
    for gender in ("woman", "man"):
        a, b = rows_text[gender], rows_name[gender]
        lines.append(
            f"| {gender} | {pct(a['share_quoted'])} ({a['quoted']} of {a['lead']}) | {ci(a['ci95'])} "
            f"| {pct(b['share_quoted'])} ({b['quoted']} of {b['lead']}) | {ci(b['ci95'])} |"
        )
    return lines + [""]


def write(name, results, lines):
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{name}.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def corpus(args):
    analyses = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(args.predictions.glob("*.json"))]
    if args.articles:
        # Only the articles of one sample, e.g. the random corpus sample, not the annotated one.
        wanted = {path.stem for path in args.articles.glob("*.json")}
        analyses = [a for a in analyses if a.get("article_id") in wanted]
    excluded = [a for a in analyses if args.cc_only and not a.get("cc_licence")]
    analyses = [a for a in analyses if not args.cc_only or a.get("cc_licence")]
    if not analyses:
        raise SystemExit(f"No predictions in {args.predictions}")

    text_only = [p for a in analyses for p in model_people(a)]
    with_name = [p for a in analyses for p in model_people(a, with_name=True)]
    by_source = defaultdict(list)
    for analysis in analyses:
        by_source[analysis.get("source_type") or "unknown"] += model_people(analysis)
    sources = Counter(p["gender_source"] or "no name layer" for p in with_name)
    unrecognised = sum(p["unrecognised_name"] for p in with_name)
    unknown_text = sum(p["gender"] not in KNOWN for p in text_only)
    unknown_name = sum(p["gender"] not in KNOWN for p in with_name)

    results = {
        "predictions": args.predictions.name,
        "articles": len(analyses),
        "excluded_without_cc_licence": len(excluded),
        "people": len(text_only),
        "funnel_text_only": funnel(text_only),
        "funnel_with_name": funnel(with_name),
        "unknown_text_only": unknown_text,
        "unknown_with_name": unknown_name,
        "gender_source": dict(sources),
        "unrecognised_names": unrecognised,
        "credit_loss_text_only": credit_loss(text_only),
        "credit_loss_with_name": credit_loss(with_name),
        "funnel_by_source_type": {source: funnel(people) for source, people in by_source.items()},
        "counts_text_only": counts(text_only),
        "roles_text_only": roles(text_only),
        "naming_text_only": naming(text_only),
        "credit_loss_by_source_type": {source: credit_loss(people) for source, people in by_source.items()},
    }

    lines = [
        f"# Corpus metrics · {args.predictions.name}", "",
        f"{len(analyses)} articles ({len(excluded)} left out without a Creative Commons licence), "
        f"{len(text_only)} people. Model predictions without human review: their error is measured with "
        "`metrics.py compare`.", "",
        "## Funnel", "",
    ]
    lines += funnel_table("Text only", results["funnel_text_only"])
    lines += funnel_table("Text plus name layer (INE and WIPO)", results["funnel_with_name"])
    lines += [
        f"Unknown gender: {unknown_text} of {len(text_only)} people with the text only; "
        f"{unknown_name} with the name layer.",
        "Where the gender comes from: " + ", ".join(f"{k} {v}" for k, v in sources.most_common()) + ". "
        f"Names neither the INE nor WIPO recognise: {unrecognised}.", "",
        "## Presence and voice in counts (text only)", "",
        "Unique people, times each is named in the text, and quotations attributed to them.", "",
    ]
    lines += counts_table(results["counts_text_only"])
    lines += ["## Recognition: named or only described in the headline or lead (text only)", ""]
    lines += naming_table(results["naming_text_only"])
    lines += ["## Authority: role given to each person (text only)", ""]
    lines += roles_table(results["roles_text_only"])
    lines += ["## Credit loss: is the person who leads the work quoted?", ""]
    lines += credit_table(results["credit_loss_text_only"], results["credit_loss_with_name"])
    lines += ["## Credit loss by source type (text only)", "",
              "| Source | Women who lead: quoted | Men who lead: quoted |", "| --- | --- | --- |"]
    for source, rows in results["credit_loss_by_source_type"].items():
        w, m = rows["woman"], rows["man"]
        lines.append(f"| {source} | {pct(w['share_quoted'])} ({w['quoted']} of {w['lead']}) "
                     f"| {pct(m['share_quoted'])} ({m['quoted']} of {m['lead']}) |")
    lines += ["", "## SINC newsroom compared with institutions' press releases (text only)", ""]
    for source, rows in results["funnel_by_source_type"].items():
        lines += funnel_table(source, rows)
    suffix = f"_{args.articles.name}" if args.articles else ""
    write(f"corpus_{args.predictions.name}{suffix}", results, lines)


def name_keys(name):
    """Surnames (or the only name), without accents, to match people across annotations."""
    plain = "".join(
        c for c in unicodedata.normalize("NFD", (name or "").lower())
        if unicodedata.category(c) != "Mn"
    )
    parts = [t for t in re.findall(r"\w+", plain) if len(t) >= 3 and t not in {"del", "las", "los"}]
    return set(parts[1:] or parts)


def match(human, model):
    pairs, free, missed = [], list(range(len(model))), []
    for person in human:
        best, overlap = None, 0
        for j in free:
            shared = len(name_keys(person["name"]) & name_keys(model[j]["name"]))
            if shared > overlap:
                best, overlap = j, shared
        if best is None:
            missed.append(person)
        else:
            pairs.append((person, model[best]))
            free.remove(best)
    return pairs, missed, [model[j] for j in free]


def annotation_minutes(annotation):
    seconds = (annotation.get("page_annotation") or {}).get("segundos")
    return seconds / 60 if seconds else None


def mean_minutes(values):
    values = [v for v in values if v]
    return round(sum(values) / len(values), 1) if values else None


def cohen_kappa(pairs):
    """Agreement beyond chance between two annotators' labels."""
    if not pairs:
        return None
    observed = sum(a == b for a, b in pairs) / len(pairs)
    first, second = Counter(a for a, _ in pairs), Counter(b for _, b in pairs)
    expected = sum(first[label] * second[label] for label in first) / len(pairs) ** 2
    return None if expected == 1 else (observed - expected) / (1 - expected)


def agreement(args):
    first, second = args.annotators
    labels = defaultdict(list)
    found = Counter()
    minutes = {first: [], second: []}
    articles = 0
    for path in sorted((ANNOTATIONS / first).glob("*.json")):
        a = json.loads(path.read_text(encoding="utf-8"))
        other = ANNOTATIONS / second / path.name
        if a.get("group") != args.group or a.get("review_status") != "human_reviewed" or not other.exists():
            continue
        b = json.loads(other.read_text(encoding="utf-8"))
        if b.get("review_status") != "human_reviewed":
            continue
        articles += 1
        minutes[first].append(annotation_minutes(a))
        minutes[second].append(annotation_minutes(b))
        people_a, people_b = human_people(a), human_people(b)
        pairs, only_a, only_b = match(people_a, people_b)
        found.update(both=len(pairs), only_first=len(only_a), only_second=len(only_b))
        for pa, pb in pairs:
            for field in ("gender", "role", "quoted", "work_role", "headline_reference"):
                labels[field].append((pa[field], pb[field]))
    if not articles:
        raise SystemExit(f"No {args.group} article finished by both {first} and {second}.")

    results = {
        "annotators": [first, second],
        "group": args.group,
        "articles": articles,
        "people": dict(found),
        "kappa": {field: cohen_kappa(pairs) for field, pairs in labels.items()},
        "observed": {field: sum(x == y for x, y in pairs) / len(pairs) for field, pairs in labels.items()},
        "minutes_mean": {name: mean_minutes(values) for name, values in minutes.items()},
    }
    lines = [
        f"# Agreement between {first} and {second} · {args.group}", "",
        f"{articles} articles annotated by both. People found by both: {found['both']}; "
        f"only by {first}: {found['only_first']}; only by {second}: {found['only_second']}.",
        f"Mean annotation time: {first} {results['minutes_mean'][first] or '—'} min, "
        f"{second} {results['minutes_mean'][second] or '—'} min per article.", "",
        "| Label | Same label | Cohen's kappa |", "| --- | --- | --- |",
    ]
    for field in labels:
        kappa = results["kappa"][field]
        lines.append(f"| {field} | {pct(results['observed'][field])} | {'—' if kappa is None else f'{kappa:.2f}'} |")
    lines += ["", "Kappa above 0.6 is usually read as substantial agreement, and above 0.8 as almost perfect."]
    write(f"agreement_{first}_{second}_{args.group}", results, lines)


def layers(args):
    """Gender layers one by one: the LLM alone, plus grammar rules, plus the name layer (INE and WIPO)."""
    settings = [
        ("LLM only", {"llm_only": True}),
        ("LLM + grammar rules", {}),
        ("LLM + grammar + name (INE, WIPO)", {"with_name": True}),
    ]
    pairs_by_setting = {name: [] for name, _ in settings}
    human_all, model_all = [], {name: [] for name, _ in settings}
    articles = 0
    for path in sorted((ANNOTATIONS / args.annotator).glob("*.json")):
        annotation = json.loads(path.read_text(encoding="utf-8"))
        if annotation.get("review_status") != "human_reviewed" or (args.group and annotation.get("group") != args.group):
            continue
        prediction_path = args.predictions / f"{annotation['article_id']}.json"
        if not prediction_path.exists():
            continue
        articles += 1
        analysis = json.loads(prediction_path.read_text(encoding="utf-8"))
        human = human_people(annotation, analysis.get("article"))
        human_all += human
        for name, options in settings:
            model = model_people(analysis, **options)
            model_all[name] += model
            pairs_by_setting[name] += match(human, model)[0]

    human_share = funnel(human_all)["Presence: mentioned"]["share_women"]
    rows = {}
    for name, _ in settings:
        pairs = pairs_by_setting[name]
        presence = funnel(model_all[name])["Presence: mentioned"]
        rows[name] = {
            "people_matched": len(pairs),
            "same_gender": sum(h["gender"] == m["gender"] for h, m in pairs),
            "unknown_gender": sum(m["gender"] not in KNOWN for m in model_all[name]),
            "people_found": len(model_all[name]),
            "share_women": presence["share_women"],
            "error_points": None if presence["share_women"] is None or human_share is None
            else 100 * (presence["share_women"] - human_share),
        }
    results = {"annotator": args.annotator, "group": args.group, "articles": articles,
               "human_share_women": human_share, "layers": rows}
    lines = [
        f"# Gender layers against {args.annotator} · {args.group}", "",
        f"{articles} annotated articles. Women among people mentioned, human annotation: {pct(human_share)}.", "",
        "| Setting | Same gender as human | Gender unknown | Women mentioned | Error |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, row in rows.items():
        error = "—" if row["error_points"] is None else f"{row['error_points']:+.0f} points"
        lines.append(f"| {name} | {row['same_gender']} of {row['people_matched']} | {row['unknown_gender']} of {row['people_found']} "
                     f"| {pct(row['share_women'])} | {error} |")
    lines += ["", "Each layer only fills genders the previous ones left unknown; the text always wins."]
    write(f"layers_{args.predictions.name}_{args.group}", results, lines)


def compare(args):
    human_all, model_all = [], []
    detection, missed_by_gender, total_by_gender = Counter(), Counter(), Counter()
    agreement = defaultdict(Counter)
    articles = 0
    minutes = []
    for path in sorted((ANNOTATIONS / args.annotator).glob("*.json")):
        annotation = json.loads(path.read_text(encoding="utf-8"))
        if annotation.get("review_status") != "human_reviewed":
            continue
        if args.group and annotation.get("group") != args.group:
            continue
        prediction_path = args.predictions / f"{annotation['article_id']}.json"
        if not prediction_path.exists():
            continue
        articles += 1
        minutes.append(annotation_minutes(annotation))
        analysis = json.loads(prediction_path.read_text(encoding="utf-8"))
        human = human_people(annotation, analysis.get("article"))
        model = model_people(analysis, args.with_name)
        human_all += human
        model_all += model

        pairs, missed, extra = match(human, model)
        detection.update(found=len(pairs), missed=len(missed), extra=len(extra))
        total_by_gender.update(p["gender"] for p in human)
        missed_by_gender.update(p["gender"] for p in missed)
        for h, m in pairs:
            for field in ("gender", "expert", "role", "quoted", "work_role", "headline_reference"):
                agreement[field]["total"] += 1
                agreement[field]["same"] += h[field] == m[field]

    human_funnel, model_funnel = funnel(human_all), funnel(model_all)
    results = {
        "annotator": args.annotator,
        "predictions": args.predictions.name,
        "group": args.group or "all",
        "with_name_layer": args.with_name,
        "articles": articles,
        "detection": dict(detection),
        "missed_by_gender": {g: [missed_by_gender[g], total_by_gender[g]] for g in total_by_gender},
        "agreement": {field: dict(tally) for field, tally in agreement.items()},
        "funnel_human": human_funnel,
        "funnel_model": model_funnel,
        "counts_human": counts(human_all),
        "counts_model": counts(model_all),
        "annotation_minutes_mean": mean_minutes(minutes),
        "naming_human": naming(human_all),
        "naming_model": naming(model_all),
    }

    lines = [
        f"# Model error · {args.predictions.name} against {args.annotator} · {results['group']}"
        + (" · with name layer" if args.with_name else ""), "",
        f"{articles} finished annotations with a prediction. "
        f"Mean annotation time: {results['annotation_minutes_mean'] or '—'} minutes per article.", "",
        "| Stage | Women (human) | 95 % CI | Women (model) | Difference |", "| --- | --- | --- | --- | --- |",
    ]
    for stage in human_funnel:
        h, m = human_funnel[stage], model_funnel[stage]
        difference = (
            "—" if h["share_women"] is None or m["share_women"] is None
            else f"{100 * (m['share_women'] - h['share_women']):+.0f} points"
        )
        lines.append(f"| {stage} | {pct(h['share_women'])} ({h['women']}) | {ci(h['ci95'])} | {pct(m['share_women'])} | {difference} |")
    lines += [
        "", "The difference is the error of the final indicator, which is what matters for the results.", "",
        f"People found by the model: {detection['found']} of {detection['found'] + detection['missed']}; "
        f"extra people not in the annotation: {detection['extra']}.", "",
        "| Gender (human) | Missed by the model |", "| --- | --- |",
    ]
    for gender, (missed, total) in results["missed_by_gender"].items():
        lines.append(f"| {gender} | {missed} of {total} |")
    lines += ["", "| Label | Same in human and model |", "| --- | --- |"]
    for field, tally in results["agreement"].items():
        lines.append(f"| {field} | {tally['same']} of {tally['total']} |")
    lines += ["", "### Counts in the human annotation", ""] + counts_table(results["counts_human"])
    lines += ["### Counts in the model prediction", ""] + counts_table(results["counts_model"])
    lines += ["### Named or only described in the headline or lead: human", ""] + naming_table(results["naming_human"])
    lines += ["### Named or only described in the headline or lead: model", ""] + naming_table(results["naming_model"])
    suffix = "_with_name" if args.with_name else ""
    write(f"compare_{args.predictions.name}_{results['group']}{suffix}", results, lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    steps = parser.add_subparsers(dest="step", required=True)
    step_compare = steps.add_parser("compare")
    step_compare.add_argument("--annotator", required=True)
    step_compare.add_argument("--predictions", type=Path, required=True)
    step_compare.add_argument("--group", default=None, help="calibration or test; all by default")
    step_compare.add_argument("--with-name", action="store_true", help="use the gender with the name layer")
    step_layers = steps.add_parser("layers")
    step_layers.add_argument("--annotator", required=True)
    step_layers.add_argument("--predictions", type=Path, required=True)
    step_layers.add_argument("--group", default="test")
    step_agreement = steps.add_parser("agreement")
    step_agreement.add_argument("--annotators", nargs=2, required=True)
    step_agreement.add_argument("--group", default="calibration")
    step_corpus = steps.add_parser("corpus")
    step_corpus.add_argument("predictions", type=Path)
    step_corpus.add_argument("--articles", type=Path, default=None,
                             help="folder of articles to keep, e.g. evaluation/data/corpus_sample")
    step_corpus.add_argument("--all-licences", dest="cc_only", action="store_false",
                             help="also include articles without a Creative Commons licence")
    args = parser.parse_args()
    {"compare": compare, "agreement": agreement, "corpus": corpus, "layers": layers}[args.step](args)


if __name__ == "__main__":
    main()
