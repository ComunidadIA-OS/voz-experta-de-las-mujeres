"""Standard indicators of women's role in science news.

The same definitions as the study (evaluation/metrics.py), so an organisation,
a journalist or anyone else gets figures that can be compared with each other
and over time. Each indicator is the share of women among the people of that
stage whose gender the text indicates, with a Wilson 95 % interval. People
whose gender is not indicated are counted apart, never guessed.

Change INDICATORS_VERSION whenever a definition changes.
"""

from evaluation.metrics import STAGES, funnel

INDICATORS_VERSION = "1.0"

# Spanish name and question for each stage, in the order of STAGES.
LABELS = {
    "Presence: mentioned": ("Presencia", "¿Qué parte de las personas mencionadas son mujeres?"),
    "Voice: quoted": ("Voz", "¿A quién se le da la palabra?"),
    "Authority: technical experts": ("Autoridad", "¿A quién se presenta como especialista?"),
    "Protagonism: lead the work": ("Protagonismo", "¿Quién lidera el trabajo del que habla la noticia?"),
    "Chosen voices: comment on the work": ("Voces elegidas", "¿A quién se llama para comentar el trabajo?"),
    "Recognition: named in headline or lead": ("Reconocimiento", "¿Quién aparece en el titular o la entradilla?"),
}


def person_record(person):
    """The fields the funnel needs, from one person in the model's format."""
    return {
        "gender": person.get("gender_representation") or "unknown",
        "quoted": bool(person.get("quotes")),
        "expert": person.get("technical_expert") is True,
        "work_role": person.get("work_role") or "mentioned",
        "recognised": person.get("headline_reference") in ("named", "described"),
    }


def compute(predictions):
    """One row per indicator for a list of predictions (one per article)."""
    people = [person_record(p) for prediction in predictions for p in prediction["people"]]
    stages = funnel(people)
    rows = []
    for stage, _ in STAGES:
        values = stages[stage]
        name, question = LABELS[stage]
        interval = values["ci95"]
        rows.append({
            "indicador": name,
            "pregunta": question,
            "personas": values["people"],
            "con_genero_indicado": values["known_gender"],
            "mujeres": values["women"],
            "porcentaje_mujeres": None if values["share_women"] is None else round(100 * values["share_women"], 1),
            "ic95_inferior": None if interval is None else round(100 * interval[0], 1),
            "ic95_superior": None if interval is None else round(100 * interval[1], 1),
            "sin_genero_indicado": values["people"] - values["known_gender"],
        })
    return rows
