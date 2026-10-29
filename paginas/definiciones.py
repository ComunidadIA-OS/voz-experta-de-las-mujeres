"""How the indicators are calculated, for anyone who wants to check or reuse them.

The definitions shown here are read from the code (indicators.py and analysis.py),
so the page and the calculation cannot drift apart.
"""

import os

import pandas as pd
import streamlit as st

from analysis import PROMPT_VERSION
from indicators import INDICATORS_VERSION, LABELS
from navegacion import nav_links

REPO_URL = os.environ.get(
    "REPO_URL",
    "https://github.com/ComunidadIA-OS/voz-experta-de-las-mujeres",
)


def code(path):
    return f"[`{path}`]({REPO_URL}/blob/main/{path})"


nav_links()
st.title("Cómo se calculan los indicadores")
st.write(
    f"Versión de los indicadores: **{INDICATORS_VERSION}** · versión del prompt: **{PROMPT_VERSION}**. "
    "Las dos versiones se guardan en cada archivo descargado. Si cambia una definición, cambia la "
    "versión, y las cifras de versiones distintas no deben compararse."
)

st.header("1. Resumen")
st.markdown(
    "Cada indicador es el **porcentaje de mujeres** entre las personas de un paso de la noticia: "
    "las mencionadas, las citadas, las presentadas como especialistas, las que lideran el trabajo, "
    "las que lo comentan y las que aparecen en el titular o la entradilla. "
    "El denominador son las personas cuyo género **indica el texto**; las demás se cuentan aparte. "
    "Cada porcentaje lleva un intervalo de confianza de Wilson al 95 %."
)

st.header("2. De la noticia a los datos")
st.markdown(
    f"""
1. **Extracción.** Un modelo de lenguaje (por defecto, gpt-oss-120b, con temperatura 0 y salida en JSON) lee el titular, la entradilla y el cuerpo y devuelve una lista de personas. Cada persona agrupa todas las veces que se la nombra en esa noticia. Para cada una devuelve las etiquetas de la tabla siguiente y, para cada etiqueta, la frase exacta de la noticia en la que se basa. Las instrucciones completas están en {code("analysis.py")}.
2. **Quién cuenta como persona.** Se incluyen las personas humanas identificables que participan en la noticia, aunque no hablen ni tengan nombre (por ejemplo, «una portavoz de la agencia»). Se excluyen los animales, los sistemas de IA, las organizaciones, los colectivos sin individuos concretos («el equipo») y los personajes históricos que solo son tema de la noticia.
3. **Verificación automática.** El código comprueba que cada frase de evidencia aparece tal cual en la noticia, tras normalizar los espacios. Una cita marcada como directa debe ir entre comillas en el texto. Si algo no se cumple, la app avisa. La comprobación confirma que la frase existe, no que la interpretación sea correcta.
4. **Capa gramatical de género.** Cuando el modelo deja el género como «no indicado», unas reglas en código buscan concordancia gramatical junto a cada mención del nombre: hasta 6 palabras antes, sin cruzar el final de la frase, y una aposición tras una coma («Ana Ruiz, investigadora…»). Se usan pares de sustantivos con forma femenina y masculina («investigadora / investigador», «autora / autor») y el artículo ante el cargo («la primera autora»). Las palabras con una sola forma, como «portavoz» o «especialista», no cuentan. El género solo se asigna si todas las pistas coinciden, y la regla nunca cambia un género que haya dado el modelo. Código: {code("evaluation/grammar_gender.py")}.
5. **Sin inferencia por el nombre.** La app nunca deduce el género a partir del nombre. En el estudio, una capa opcional basada en el INE y en la OMPI se usó solo como comprobación, porque empeoraba el resultado.
6. **Revisión humana.** Quien usa la app puede corregir cualquier etiqueta, añadir o borrar personas y citas. Los indicadores se calculan con la versión revisada. La columna «Según el modelo» muestra el mismo cálculo con la predicción sin corregir.
"""
)

st.subheader("Etiquetas por persona")
st.dataframe(
    pd.DataFrame([
        ("gender_representation", "woman, man, other_explicit, unknown", "Género que indica el propio texto: pronombres, concordancia, cargos con género. Sin prueba: unknown."),
        ("quotes", "lista de citas (direct / indirect)", "Afirmaciones atribuidas a la persona, entre comillas o en estilo indirecto («según…», «explica que…»). Se omiten las de atribución dudosa."),
        ("technical_expert", "true, false, null", "true si el texto presenta conocimiento técnico explícito: ocupación, especialidad o función técnica. Un cargo directivo por sí solo no basta."),
        ("source_role", "specialist, spokesperson, politician, testimony, other, mentioned_only", "Función de la persona como fuente."),
        ("work_role", "leads, comments, mentioned", "Relación con el trabajo que cuenta la noticia: lo lidera o es coautora, lo comenta sin haberlo hecho, o solo aparece."),
        ("headline_reference", "named, described, absent", "Si aparece en el titular o la entradilla con su nombre, solo descrita («una química catalana») o no aparece."),
    ], columns=["Campo", "Valores", "Definición"]),
    hide_index=True,
)

st.header("3. Definición de cada indicador")
conditions = {
    "Presencia": "toda persona incluida",
    "Voz": "len(quotes) ≥ 1",
    "Autoridad": "technical_expert = true",
    "Protagonismo": "work_role = leads",
    "Voces elegidas": "work_role = comments",
    "Reconocimiento": "headline_reference ∈ {named, described}",
}
st.dataframe(
    pd.DataFrame(
        [(name, question, conditions[name]) for name, question in LABELS.values()],
        columns=["Indicador", "Pregunta", "Personas que entran en el paso"],
    ),
    hide_index=True,
)
st.markdown("Para cada paso *s*, con las personas *P(s)* que cumplen su condición:")
st.latex(r"\%\,\text{mujeres}_s = \frac{\#\{p \in P(s) : \text{género} = \text{woman}\}}{\#\{p \in P(s) : \text{género} \in \{\text{woman}, \text{man}, \text{other\_explicit}\}\}}")
st.markdown(
    """
- **Género no indicado.** Las personas con `unknown` quedan fuera del denominador y se informan en la columna «Sin género indicado». Así no se inventa un género, pero si hay muchas, el porcentaje describe solo a una parte de las personas.
- **Otra identidad indicada.** `other_explicit` entra en el denominador y no en el numerador.
- **Agregación.** Se suman las personas de todas las noticias antes de dividir. No es la media de los porcentajes de cada noticia, así que una noticia con muchas personas pesa más que una con pocas. Si la misma persona aparece en dos noticias, cuenta dos veces: la unidad es la persona en una noticia.
- **Voz.** Cuenta a quién se cita, no cuántas citas tiene cada persona. El recuento de citas por género se guarda aparte en los archivos.
"""
)

st.subheader("Intervalo de confianza")
st.markdown(
    "Se usa el intervalo de Wilson (Wilson, 1927) con *z* = 1,96. Con *k* mujeres entre *n* personas "
    "con género indicado y *p̂ = k / n*:"
)
st.latex(r"\frac{\hat p + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat p(1-\hat p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}")
st.markdown(
    "Se eligió frente al intervalo normal porque se comporta bien con muestras pequeñas y con "
    "proporciones cercanas a 0 o a 1, que es lo habitual al medir pocas noticias. El intervalo solo "
    "recoge el azar del muestreo, no los errores del modelo: por eso conviene revisar a mano. "
    f"Código: {code('indicators.py')}, que usa las mismas funciones que el estudio "
    f"({code('evaluation/metrics.py')})."
)

st.header("4. Cuánto se equivoca el sistema")
st.markdown(
    "Se evaluó con 40 noticias de la Agencia SINC que una persona anotó a mano sin ver la predicción "
    "del modelo (prompt 0.6, gpt-oss-120b). Lo que importa es cuánto se desvía el porcentaje final "
    "del que se obtiene a mano (Rodríguez Fonollosa, 2026), no la precisión de cada etiqueta por separado."
)
st.dataframe(
    pd.DataFrame([
        ("Presencia", "35 % (24–48)", "36 %", "+1"),
        ("Voz", "36 % (25–50)", "38 %", "+1"),
        ("Autoridad", "36 % (25–50)", "33 %", "−4"),
        ("Protagonismo", "37 % (25–51)", "39 %", "+2"),
    ], columns=["Indicador", "Anotación humana (IC 95 %)", "Modelo", "Error (puntos)"]),
    hide_index=True,
)
st.markdown(
    """
- **Voces elegidas y reconocimiento:** en la muestra anotada hay muy pocos casos (5 y 0 personas con género indicado), así que su error no puede estimarse con fiabilidad.
- **Personas:** el modelo encontró a las 65 personas anotadas y añadió 6 que no estaban en la anotación.
- **Coincidencia por etiqueta con la anotación:** género 61 de 65 (con la capa gramatical), cita 65 de 65, especialista 58 de 65, papel como fuente 54 de 65 y relación con el trabajo 48 de 65. La relación con el trabajo es la etiqueta menos fiable: el modelo marca como «lidera» a menos personas que la anotación humana.
- **Acuerdo entre dos anotadoras** (6 noticias, kappa de Cohen): género 0,88, cita 1,00, relación con el trabajo 0,81 y papel como fuente 0,48. El papel como fuente es difícil incluso para las personas.
- **Capa gramatical:** el error en presencia pasa de −4 puntos (solo el modelo) a +1. Añadir la inferencia por el nombre lo empeora (+4), por eso la app no la usa.

Estas cifras valen para noticias de ciencia en español parecidas a las evaluadas. En otros medios o temas el error puede ser distinto: revisa una muestra a mano antes de publicar cifras.
"""
)

st.header("5. Qué contienen los archivos descargados")
st.markdown(
    f"""
- **Análisis completo (.json, formato `voz-experta-analisis/1`):** versión de la app, del prompt y de los indicadores; para cada noticia, el texto, la licencia detectada, la predicción original del modelo, los avisos de verificación, las tablas revisadas y el estado de revisión (`model_only` o `human_reviewed`). Se puede volver a cargar en la app.
- **Indicadores (.csv):** una fila por indicador con `etiqueta`, `fecha`, `noticias`, `noticias_revisadas`, `version_indicadores`, `personas`, `con_genero_indicado`, `mujeres`, `porcentaje_mujeres`, `ic95_inferior`, `ic95_superior` y `sin_genero_indicado`.
- **Personas (.csv):** una fila por persona y noticia, con sus etiquetas revisadas y las frases de evidencia.

Si publicas indicadores, indica el número de noticias, cuántas revisaste a mano y la versión de los indicadores.
"""
)

st.header("Referencias")
st.markdown(
    """
Rodríguez Fonollosa, J. A. (2026, 15 de octubre). *Del audio a las métricas: tecnologías del habla para medir la presencia y el protagonismo de las mujeres en el entorno digital* [Taller]. Reto Mujeres por la IA Abierta, SEDIA.

Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. *Journal of the American Statistical Association, 22*(158), 209–212. https://doi.org/10.1080/01621459.1927.10502953
"""
)
