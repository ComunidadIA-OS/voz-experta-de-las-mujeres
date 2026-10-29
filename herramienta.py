import json
import os
import re
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

from analysis import (
    APP_VERSION,
    PEOPLE_COLUMNS,
    PROMPT_VERSION,
    QUOTE_COLUMNS,
    gender_summary,
    make_review_tables,
    prediction_warnings,
    run_model,
    safe_error,
    tables_to_prediction,
    validate_prediction,
)
from article_fetch import ArticleNotFound, fetch_article
from evaluation.grammar_gender import fill as fill_grammar_gender
from indicators import INDICATORS_VERSION, compute
from navegacion import PAGES, nav_links

# Format of the exported file, so a later session can load it and add more articles.
EXPORT_FORMAT = "voz-experta-analisis/1"
MAX_LINKS = 20

PROFILES = {
    "organization": "Organización o medio de comunicación: seguimiento periódico de las propias publicaciones",
    "journalist": "Periodista: revisión de una noticia antes de su publicación",
    "public": "Ciudadanía, docencia e investigación: análisis de noticias publicadas con licencia abierta",
}


st.title("Voz experta de las mujeres")
st.caption(
    "Herramienta de código abierto que mide, con indicadores estándar, el papel de las mujeres "
    "en las noticias de ciencia: quién aparece, a quién se cita, a quién se presenta como "
    "especialista y quién lidera el trabajo."
)
nav_links()

json_mode = True

# Las etiquetas y los avisos se guardan en inglés para compararlos con la anotación;
# aquí solo se traducen para mostrarlos.
WARNING_TRANSLATIONS = [
    (r"^Unnamed person (\d+)", r"Persona sin nombre \1"),
    (r": invalid gender label\.$", ": etiqueta de género no válida."),
    (r": expertise evidence is missing or does not match the article\.$",
     ": falta la evidencia de especialidad o no aparece en la noticia."),
    (r": gender evidence is missing or does not match the article\.$",
     ": falta la evidencia de género o no aparece en la noticia."),
    (r": headline reference evidence is missing or does not match the article\.$",
     ": falta la evidencia del titular o la entradilla o no aparece en la noticia."),
    (r": work role evidence is missing or does not match the article\.$",
     ": falta la evidencia de su relación con el trabajo o no aparece en la noticia."),
    (r", quotation (\d+): text is missing or does not match\.$",
     r", cita \1: el texto de la cita falta o no aparece en la noticia."),
    (r", quotation (\d+): attribution_evidence is missing or does not match\.$",
     r", cita \1: la frase de atribución falta o no aparece en la noticia."),
    (r", quotation (\d+): marked as direct but it has no quotation marks in the article\.$",
     r", cita \1: está marcada como directa, pero en la noticia no va entre comillas."),
]

ERROR_TRANSLATIONS = {
    "Check the API token.": "El token de la API no es válido.",
    "Check the token permissions and model access.": "El token no tiene permisos o acceso al modelo.",
    "Check the API base URL and exact model ID.": "La URL de la API o el nombre del modelo no son correctos.",
    "Check model parameters. Try disabling JSON mode if unsupported.": "Los parámetros del modelo no son válidos.",
    "The service limit was reached. Wait before retrying.": "Se ha alcanzado el límite del servicio; conviene esperar antes de reintentarlo.",
    "Check service availability.": "El servicio del modelo no está disponible en este momento.",
    "Analysis timed out. Try a shorter article or retry later.": "El análisis ha superado el tiempo máximo; puede reintentarse más tarde o con una noticia más breve.",
    "Connection failed. Check that the selected service is running and reachable.": "No ha sido posible conectar con el servicio del modelo.",
    "The model returned an incomplete or invalid response. No new analysis was saved.": "El modelo ha devuelto una respuesta incompleta o no válida.",
}


def translate_warning(text):
    for pattern, replacement in WARNING_TRANSLATIONS:
        text = re.sub(pattern, replacement, text)
    return text


def translate_error(text):
    text = text.replace("Analysis failed:", "El análisis ha fallado:")
    for english, spanish in ERROR_TRANSLATIONS.items():
        text = text.replace(english, spanish)
    return text


def describe_provider(url):
    if url.startswith(("http://localhost", "http://127.0.0.1")):
        return "Modelo local"
    if "ovh.net" in url:
        return "OVHcloud AI Endpoints"
    return "API compatible con OpenAI"


with st.sidebar:
    st.header("Modelo")
    model_name = st.text_input("Nombre del modelo", value="gpt-oss-120b").strip()
    base_url = st.text_input(
        "URL base de la API (acaba en /v1)",
        value=os.environ.get(
            "OVH_AI_BASE_URL",
            "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1",
        ),
    ).strip()
    api_token = os.environ.get("OVH_AI_ENDPOINTS_ACCESS_TOKEN", "").strip()
    if not api_token:
        api_token = st.text_input("Token de la API", type="password").strip()
    else:
        st.caption("Token cargado desde el entorno.")
    st.caption(
        "Compatible con cualquier modelo que ofrezca la API de OpenAI. Con un modelo local "
        "(http://localhost) el texto no sale del equipo y no se requiere token. "
        "El token no se incluye en los resultados descargados."
    )

local = base_url.startswith(("http://localhost", "http://127.0.0.1"))
model_ready = bool(model_name and base_url and (api_token or local))

# Who the tool is for and what may be analysed: the conditions of use, in short.
st.info(
    "**Finalidad.** Esta herramienta ofrece a organizaciones, medios de comunicación, periodistas "
    "y ciudadanía una medición estándar y verificable de la representación de las mujeres en las "
    "noticias de ciencia. Está concebida como apoyo a la autoevaluación del propio contenido.\n\n"
    "**Textos admitidos.** Textos propios o de la propia organización, y noticias publicadas con "
    "licencia Creative Commons. En el perfil de ciudadanía, docencia e investigación solo se "
    "analizan enlaces cuya página declare dicha licencia.\n\n"
    "**Confidencialidad.** La aplicación no almacena textos, enlaces ni resultados. El texto se "
    "transmite al modelo de lenguaje únicamente para su análisis, y los resultados pueden "
    "descargarse al finalizar. Para textos no publicados se recomienda un modelo local.\n\n"
    "**Uso de los resultados.** Las etiquetas son propuestas automáticas que la persona usuaria "
    "revisa y puede corregir. Las cifras describen el conjunto del contenido y su evolución; no "
    "constituyen una valoración de personas ni de medios."
)
# Widgets lose their state when another page is shown, so the choices are kept apart.
accepted = st.checkbox(
    "He leído y acepto los términos y condiciones y la política de privacidad.",
    value=st.session_state.get("accepted_terms", False),
)
st.session_state["accepted_terms"] = accepted

profile = st.radio(
    "Perfil de uso",
    list(PROFILES),
    index=list(PROFILES).index(st.session_state.get("profile", "organization")),
    format_func=PROFILES.get,
    disabled=not accepted,
)
st.session_state["profile"] = profile

if "articles" not in st.session_state:
    st.session_state["articles"] = []
    st.session_state["next_id"] = 1


def add_article(article_fields, source, licence):
    """Analyse one article with the model and keep it in this session only."""
    result, run_metadata = run_model(
        describe_provider(base_url), model_name, base_url, api_token,
        article_fields, json_mode,
    )
    validate_prediction(result)
    source_text = "\n\n".join(article_fields.values())
    # The evidence checks judge the model's own answer, before the grammar layer.
    warnings = prediction_warnings(result, source_text)
    # Gender from grammatical agreement when the model left it unknown.
    fill_grammar_gender(result, source_text)
    people_table, quote_table = make_review_tables(result)
    st.session_state["articles"].append({
        "id": f"a{st.session_state['next_id']}",
        "source": source,
        "licence": licence,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        **run_metadata,
        "prompt_version": PROMPT_VERSION,
        "article": article_fields,
        "original_prediction": result,
        "validation_warnings": warnings,
        "review_status": "model_only",
        "revision": 0,
        "reviewed_people": people_table.to_dict("records"),
        "reviewed_quotes": quote_table.to_dict("records"),
    })
    st.session_state["next_id"] += 1


st.header("1. Incorporación de noticias")
paste_tab, links_tab, upload_tab = st.tabs([
    "Texto de una noticia",
    f"Enlaces (hasta {MAX_LINKS})",
    "Análisis anterior",
])

with paste_tab:
    if profile == "public":
        st.write(
            "En este perfil, las noticias se incorporan mediante su enlace, lo que permite "
            "comprobar que la página declara una licencia abierta."
        )
    else:
        with st.form("article_form", clear_on_submit=True):
            title = st.text_input("Titular")
            introduction = st.text_area("Entradilla", height=100)
            body = st.text_area("Cuerpo de la noticia", height=250)
            analyse = st.form_submit_button("Analizar noticia", type="primary", disabled=not accepted)
        if analyse:
            if not model_ready:
                st.warning("Falta configurar el modelo en el panel lateral: URL de la API, nombre del modelo y token.")
            elif not body.strip():
                st.warning("Falta el cuerpo de la noticia.")
            else:
                with st.spinner(f"Análisis en curso con {model_name}…"):
                    try:
                        add_article(
                            {"headline": title, "introduction": introduction, "body": body},
                            "Texto pegado", None,
                        )
                    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError) as error:
                        st.error(translate_error(safe_error(error)))

with links_tab:
    links_text = st.text_area(
        "Enlaces, uno por línea",
        height=150,
        key="links",
        placeholder="https://www.ejemplo.es/noticia-de-ciencia",
    )
    if st.button("Analizar enlaces", type="primary", disabled=not accepted):
        links = [line.strip() for line in links_text.splitlines() if line.strip()]
        if not links:
            st.warning("Es necesario indicar al menos un enlace.")
        elif len(links) > MAX_LINKS:
            st.warning(f"Se admiten hasta {MAX_LINKS} enlaces por análisis; pueden añadirse más a continuación.")
        elif not model_ready:
            st.warning("Falta configurar el modelo en el panel lateral: URL de la API, nombre del modelo y token.")
        else:
            progress = st.progress(0.0, text="Analizando...")
            for number, link in enumerate(links, start=1):
                try:
                    article_fields, licence = fetch_article(link)
                    if profile == "public" and not licence:
                        st.warning(
                            f"{link}: la página no declara una licencia Creative Commons "
                            "y no se ha analizado."
                        )
                    else:
                        add_article(article_fields, link, licence)
                except ArticleNotFound as error:
                    st.warning(f"{link}: {error}")
                except (requests.RequestException, ValueError, KeyError, TypeError, IndexError) as error:
                    st.warning(f"{link}: {translate_error(safe_error(error))}")
                progress.progress(number / len(links), text=f"Analizadas {number} de {len(links)}")

with upload_tab:
    st.write(
        "Permite retomar un análisis descargado previamente con esta herramienta, para "
        "continuar su revisión o incorporar noticias de un nuevo periodo."
    )
    uploaded = st.file_uploader("Archivo de análisis (.json)", type="json")
    if uploaded is not None and st.button("Cargar el análisis", disabled=not accepted):
        try:
            previous = json.load(uploaded)
            if previous.get("format") != EXPORT_FORMAT:
                raise ValueError
            for entry in previous["articles"]:
                entry["id"] = f"a{st.session_state['next_id']}"
                entry["revision"] = 0
                st.session_state["next_id"] += 1
                st.session_state["articles"].append(entry)
            st.success(f"Se han incorporado {len(previous['articles'])} noticias.")
        except (ValueError, KeyError, TypeError):
            st.error("El archivo no corresponde a un análisis exportado con esta herramienta.")

articles = st.session_state["articles"]
if not articles:
    st.stop()

st.header("2. Revisión y corrección")
st.write(
    "Las etiquetas son propuestas del modelo y pueden contener errores. En cada noticia es posible "
    "comparar las tablas con el texto, modificar etiquetas, añadir personas o citas omitidas y "
    "eliminar filas incorrectas. Al pulsar «Guardar correcciones y recalcular», los avisos y los "
    "indicadores se actualizan con la versión revisada."
)
with st.expander("Significado de las etiquetas"):
    st.markdown(
        "Los valores se registran en inglés para que los archivos sean comparables entre organizaciones.\n\n"
        "- **Género según el texto:** woman = mujer, man = hombre, other_explicit = otra identidad indicada, unknown = no indicado. Se toma exclusivamente del texto («la investigadora», «él»), nunca del nombre.\n"
        "- **Papel como fuente:** specialist = especialista, spokesperson = portavoz, politician = cargo político, testimony = testimonio, other = otro, mentioned_only = solo mencionada/o.\n"
        "- **Relación con el trabajo:** leads = lo lidera o es autora, comments = lo comenta sin haberlo hecho, mentioned = solo aparece.\n"
        "- **En titular o entradilla:** named = con su nombre, described = solo descrita/o, absent = no aparece.\n"
        "- **Especialista técnica/o:** yes = sí, no = no, unclear = dudoso.\n"
        "- **Tipo de cita:** direct = directa (entre comillas), indirect = indirecta."
    )

people_columns = {
    "person_id": st.column_config.TextColumn("ID"),
    "name": st.column_config.TextColumn("Nombre"),
    "professional_role": st.column_config.TextColumn("Cargo o profesión"),
    "technical_expert": st.column_config.SelectboxColumn(
        "Especialista técnica/o", options=["yes", "no", "unclear"], required=True,
    ),
    "source_role": st.column_config.SelectboxColumn(
        "Papel como fuente",
        options=["specialist", "spokesperson", "politician", "testimony", "other", "mentioned_only"],
        required=True,
    ),
    "expert_evidence": st.column_config.TextColumn("Evidencia de especialidad"),
    "gender_representation": st.column_config.SelectboxColumn(
        "Género según el texto", options=["woman", "man", "other_explicit", "unknown"], required=True,
    ),
    "gender_evidence": st.column_config.TextColumn("Evidencia de género"),
    "work_role": st.column_config.SelectboxColumn(
        "Relación con el trabajo", options=["leads", "comments", "mentioned"], required=True,
    ),
    "work_role_evidence": st.column_config.TextColumn("Evidencia de la relación con el trabajo"),
    "headline_reference": st.column_config.SelectboxColumn(
        "En titular o entradilla", options=["named", "described", "absent"], required=True,
    ),
    "headline_reference_evidence": st.column_config.TextColumn("Evidencia en titular o entradilla"),
    "review_notes": st.column_config.TextColumn("Notas de revisión"),
}
quote_columns = {
    "speaker_id": st.column_config.TextColumn("ID de quien habla"),
    "type": st.column_config.SelectboxColumn("Tipo de cita", options=["direct", "indirect"], required=True),
    "text": st.column_config.TextColumn("Texto de la cita"),
    "attribution_evidence": st.column_config.TextColumn("Frase de atribución"),
    "review_notes": st.column_config.TextColumn("Notas de revisión"),
}

reviewed_predictions = []
for entry in articles:
    people_table = pd.DataFrame(entry["reviewed_people"], columns=PEOPLE_COLUMNS)
    quote_table = pd.DataFrame(entry["reviewed_quotes"], columns=QUOTE_COLUMNS)
    reviewed = tables_to_prediction(people_table, quote_table)
    reviewed_predictions.append(reviewed)
    source_text = "\n\n".join(entry["article"].values())

    status = "revisada" if entry["review_status"] == "human_reviewed" else "sin revisar"
    with st.expander(f"{entry['article'].get('headline') or entry['source']} · {status}"):
        details = [entry["source"], f"Licencia: {entry.get('licence') or 'no declarada'}"]
        st.caption(" · ".join(details))
        with st.popover("Ver la noticia"):
            for label, field in (("Titular", "headline"), ("Entradilla", "introduction"), ("Cuerpo", "body")):
                st.markdown(f"**{label}**")
                st.text(entry["article"].get(field) or "(Sin texto)")

        for alert in gender_summary(reviewed):
            st.warning(alert)
        checks = prediction_warnings(reviewed, source_text)
        if checks:
            st.caption("Las siguientes frases no figuran literalmente en la noticia; conviene comprobarlas.")
            for warning in checks:
                st.info(translate_warning(warning))

        with st.form(f"review_{entry['id']}"):
            st.markdown("**Personas.** Cada persona requiere un identificador distinto (p1, p2…).")
            edited_people = st.data_editor(
                people_table, column_config=people_columns, num_rows="dynamic", hide_index=True,
                key=f"people_{entry['id']}_{entry['revision']}",
            )
            st.markdown("**Citas.** El identificador de quien habla debe coincidir con el de la tabla de personas.")
            edited_quotes = st.data_editor(
                quote_table, column_config=quote_columns, num_rows="dynamic", hide_index=True,
                key=f"quotes_{entry['id']}_{entry['revision']}",
            )
            if st.form_submit_button("Guardar correcciones y recalcular"):
                entry["reviewed_people"] = edited_people.fillna("").to_dict("records")
                entry["reviewed_quotes"] = edited_quotes.fillna("").to_dict("records")
                entry["review_status"] = "human_reviewed"
                # A new key gives the editors the saved tables as their starting point.
                entry["revision"] += 1
                st.rerun()

        if st.button("Retirar esta noticia del análisis", key=f"remove_{entry['id']}"):
            articles.remove(entry)
            st.rerun()

st.header("3. Indicadores")
label = st.text_input(
    "Etiqueta del análisis",
    placeholder="Por ejemplo: sección de ciencia, octubre de 2026",
    help="Se guarda en los archivos descargados para comparar periodos.",
)
pending = sum(entry["review_status"] != "human_reviewed" for entry in articles)
st.write(
    f"{len(articles)} {'noticia' if len(articles) == 1 else 'noticias'}; "
    f"revisadas manualmente: {len(articles) - pending}. "
    "Cada indicador expresa el porcentaje de mujeres entre las personas cuyo género indica el texto, "
    "con su intervalo de confianza del 95 %. La columna «Según el modelo» recoge el valor previo a las correcciones."
)
if pending:
    st.warning(f"Noticias pendientes de revisión: {pending}. Sus cifras corresponden a la propuesta del modelo.")

indicator_rows = compute(reviewed_predictions)
model_rows = compute([entry["original_prediction"] for entry in articles])
table = pd.DataFrame([
    {
        "Indicador": row["indicador"],
        "Pregunta": row["pregunta"],
        "Mujeres": f"{row['mujeres']} de {row['con_genero_indicado']}",
        "% mujeres": "—" if row["porcentaje_mujeres"] is None else f"{row['porcentaje_mujeres']:.1f}",
        "IC 95 %": "—" if row["ic95_inferior"] is None else f"{row['ic95_inferior']}–{row['ic95_superior']}",
        "Según el modelo (%)": "—" if model["porcentaje_mujeres"] is None else f"{model['porcentaje_mujeres']:.1f}",
        "Sin género indicado": row["sin_genero_indicado"],
    }
    for row, model in zip(indicator_rows, model_rows)
])
st.dataframe(table, hide_index=True, width="stretch")
st.caption(
    "Con pocas noticias, los intervalos son amplios. Los indicadores están pensados para el "
    "seguimiento del propio contenido a lo largo del tiempo, y no para valorar a personas concretas."
)
st.page_link(PAGES["definiciones"], label="Definiciones, fórmulas y error medido de cada indicador")

st.header("4. Descarga de resultados")
st.write(
    "La aplicación no conserva ningún dato al cerrar la sesión. El archivo completo (.json) "
    "permite retomar el análisis más adelante desde «Análisis anterior»."
)
created_at = datetime.now(timezone.utc).isoformat()
export_data = {
    "format": EXPORT_FORMAT,
    "label": label,
    "created_at": created_at,
    "app_version": APP_VERSION,
    "prompt_version": PROMPT_VERSION,
    "indicators_version": INDICATORS_VERSION,
    "indicators": indicator_rows,
    "articles": [{key: value for key, value in entry.items() if key != "revision"} for entry in articles],
}
indicators_csv = pd.DataFrame([
    {"etiqueta": label, "fecha": created_at[:10], "noticias": len(articles),
     "noticias_revisadas": len(articles) - pending, "version_indicadores": INDICATORS_VERSION, **row}
    for row in indicator_rows
]).to_csv(index=False)
people_csv = pd.DataFrame([
    {"noticia": entry["source"], "titular": entry["article"].get("headline", ""),
     "estado": entry["review_status"], **person}
    for entry in articles
    for person in entry["reviewed_people"]
]).to_csv(index=False)

columns = st.columns(3)
columns[0].download_button(
    "Análisis completo (.json)",
    data=json.dumps(export_data, ensure_ascii=False, indent=2),
    file_name="voz_experta_analisis.json",
    mime="application/json",
    help="Noticias, predicción original del modelo, correcciones e indicadores. Se puede volver a cargar.",
)
columns[1].download_button(
    "Indicadores (.csv)",
    data=indicators_csv,
    file_name="voz_experta_indicadores.csv",
    mime="text/csv",
    help="Una fila por indicador, lista para un cuadro de mando o una hoja de cálculo.",
)
columns[2].download_button(
    "Personas (.csv)",
    data=people_csv,
    file_name="voz_experta_personas.csv",
    mime="text/csv",
    help="Una fila por persona, con sus etiquetas revisadas y la frase que las justifica.",
)

if st.button("Iniciar un análisis nuevo"):
    st.session_state["articles"] = []
    st.rerun()
