# Voz experta de las mujeres

Herramienta abierta que mide, con indicadores estándar, el papel que las noticias de ciencia en español atribuyen a las mujeres:

- si aparecen;
- si se les da la palabra;
- si se las presenta como especialistas;
- si se reconoce que lideran el trabajo del que trata la noticia.

Un modelo de lenguaje de pesos abiertos propone las etiquetas y muestra la frase de la noticia en la que se basa cada una. Después, una persona revisa y corrige el resultado.

Frente a 40 noticias anotadas a mano, el error de los cuatro indicadores principales no supera los 4 puntos. En una muestra aleatoria de 200 noticias de la Agencia SINC, las mujeres son el 38 % de las personas en todos los pasos.

Proyecto del Equipo 4 en el reto *Mujeres por la IA Abierta* (2026): Maryam Nadhim Edam Edam, Eva del Mar Pérez Fernández y Elena Soria López.

> Las predicciones del modelo siempre requieren revisión humana. La aplicación no almacena textos ni resultados.

---

## Para quién es

| Perfil | Uso |
| --- | --- |
| Organizaciones y medios de comunicación | Seguimiento periódico de sus publicaciones con los mismos indicadores |
| Periodistas | Revisión de una noticia antes de su publicación |
| Ciudadanía, docencia e investigación | Análisis de noticias publicadas con licencia Creative Commons |

---

## La solución

1. **Extracción.** Un modelo de lenguaje abierto (por defecto, gpt-oss-120b) identifica a cada persona de la noticia y propone:
   - su cargo;
   - su género según el texto;
   - su papel como fuente (especialista, portavoz, cargo político, testimonio…);
   - su relación con el trabajo (lo lidera, lo comenta o solo aparece);
   - su presencia en el titular o la entradilla;
   - sus citas directas e indirectas.

   Cada etiqueta lleva la frase exacta del texto en la que se basa.
2. **Verificación.** El código comprueba que cada frase existe en la noticia y que las citas directas van entre comillas.
3. **Revisión humana.** En la aplicación web, una persona corrige las etiquetas y añade o elimina personas y citas. Los avisos y los indicadores se recalculan con la versión revisada. El archivo descargado distingue la predicción del modelo de la revisión.
4. **Indicadores.** Porcentaje de mujeres entre las personas cuyo género indica el texto, con intervalo de confianza de Wilson al 95 %. Las definiciones son las mismas en el estudio ([`evaluation/metrics.py`](evaluation/metrics.py)) y en la app ([`indicators.py`](indicators.py), versión 1.0), para que las cifras de distintas organizaciones sean comparables.

| Indicador | Cálculo |
| --- | --- |
| Presencia | mujeres mencionadas ÷ personas mencionadas |
| Voz | mujeres citadas ÷ personas citadas |
| Autoridad | especialistas mujeres ÷ especialistas |
| Protagonismo | mujeres que lideran el trabajo ÷ personas que lo lideran |
| Voces elegidas | mujeres que comentan el trabajo ÷ personas que lo comentan |
| Reconocimiento | mujeres en el titular o la entradilla ÷ personas en el titular o la entradilla |

El estudio mide también la **pérdida de crédito**: si la persona que lidera el trabajo tiene voz en la noticia, según su género.

### Cómo se asigna el género

1. **Texto:** «la investigadora», «él», «directora». El modelo solo lo asigna con evidencia explícita.
2. **Reglas gramaticales:** completan los casos que el modelo deja sin decidir, a partir de la concordancia junto al nombre («el primer autor», «la coautora»). Nunca cambian lo que asignó el modelo.
3. **«No indicado»:** si nada basta, la persona se cuenta aparte y no entra en el denominador.

La aplicación no infiere el género a partir del nombre. En el estudio se evaluó una capa basada en el INE y en el diccionario de nombres de la OMPI (WGND 2.0). Aumentaba el error de 1 a 4 puntos, así que solo se conserva como comprobación.

---

## Resultados

| | Valor | Base |
| --- | --- | --- |
| Error del indicador frente a la anotación humana | +1, +1, −4 y +2 puntos (presencia, voz, autoridad, protagonismo) | 40 noticias de test |
| Personas encontradas | 65 de 65 anotadas; 6 de más | 40 noticias de test |
| Acuerdo entre anotadoras (κ de Cohen) | género 0,88; cita 1,00; relación con el trabajo 0,81; papel como fuente 0,48 | 6 noticias de calibración |
| Mujeres en presencia, voz, autoridad y protagonismo | 38 %, 39 %, 38 % y 39 % | 200 noticias, 447 personas |
| Mujeres entre quienes comentan el trabajo (voces elegidas) | 37 % (IC 28–46) | 200 noticias |
| Quien lidera el trabajo tiene voz | mujeres 90 %, hombres 89 % | 200 noticias |
| Línea base con spaCy | encuentra 62 de 65 personas, pero añade 61 de más y no identifica citas, papel ni género | 40 noticias de test |
| Coste de operación (consumo medido) | ≈ 1,07 € por un año de noticias de SINC (1.066) | 235 noticias |

Las tablas completas están en [`evaluation/data/results/`](evaluation/data/results/).

---

## Instalación

Se necesita **Python 3.11 o superior** y **Git**.

### macOS / Linux

```bash
git clone https://github.com/ComunidadIA-OS/voz-experta-de-las-mujeres.git
cd voz-experta-de-las-mujeres
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
git clone https://github.com/ComunidadIA-OS/voz-experta-de-las-mujeres.git
cd voz-experta-de-las-mujeres
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Acceso al modelo

Por defecto se usa **gpt-oss-120b** (pesos abiertos, Apache-2.0) a través de **OVHcloud AI Endpoints**, con una API compatible con OpenAI. El token se guarda en una variable de entorno y **nunca debe escribirse en el código ni subirse al repositorio**:

```bash
export OVH_AI_ENDPOINTS_ACCESS_TOKEN=...         # macOS / Linux
$env:OVH_AI_ENDPOINTS_ACCESS_TOKEN="..."         # Windows PowerShell
```

**Independencia del modelo.** La llamada usa el formato estándar `/v1/chat/completions`, así que sirve cualquier modelo compatible. Por ejemplo, un modelo abierto en local con [Ollama](https://ollama.com), sin token y sin enviar textos a terceros:

```bash
ollama pull qwen2.5:7b
# En la barra lateral de la app: URL http://127.0.0.1:11434/v1 y modelo qwen2.5:7b
```

---

## Uso

### Aplicación web

```bash
python -m streamlit run app.py
```

Abre `http://localhost:8501`. Después:

1. **Términos y perfil:** acepta los términos y condiciones y la política de privacidad, y elige el perfil de uso. La fila de enlaces superior lleva a las páginas de indicadores, términos, privacidad y aviso legal.
2. **Incorporación de noticias:** pega el texto de una noticia o hasta 20 enlaces de cualquier medio. En el perfil de ciudadanía, docencia e investigación solo se analizan enlaces cuya página declare una licencia Creative Commons.
3. **Revisión y corrección:** compara las tablas con el texto, corrige lo necesario y pulsa **Guardar correcciones y recalcular**.
4. **Indicadores:** porcentaje de mujeres en cada paso con su intervalo, junto a la cifra del modelo antes de corregir.
5. **Descarga de resultados:** análisis completo (.json), indicadores (.csv) y personas (.csv). El .json permite retomar el análisis en **Análisis anterior** y sumar las noticias de otro periodo.

### Evaluación y métricas

```bash
# Acuerdo entre anotadoras (6 noticias de calibración)
python evaluation/metrics.py agreement --annotators Eva_Mar Elena

# El modelo analiza la muestra anotada y la muestra de 200 noticias
python evaluation/run_batch.py evaluation/data/sample
python evaluation/run_batch.py evaluation/data/corpus_sample

# Error del modelo frente a la anotación humana, y efecto de cada capa de género
P=evaluation/data/predictions/gpt-oss-120b
python evaluation/name_layer.py apply $P
python evaluation/metrics.py compare --annotator Elena --predictions $P --group test
python evaluation/metrics.py layers --annotator Elena --predictions $P --group test

# Línea base con spaCy (requiere: pip install spacy && python -m spacy download es_core_news_md)
python evaluation/baseline_spacy.py --annotator Elena --predictions $P --group test

# Indicadores de la muestra de 200 noticias y coste medido
python evaluation/metrics.py corpus $P --articles evaluation/data/corpus_sample
python evaluation/cost.py $P --input-price 0.08 --output-price 0.4
```

El flujo completo, incluida la descarga de noticias y la anotación a ciegas, está en [`evaluation/README.md`](evaluation/README.md).

---

## Estructura del repositorio

```
app.py                 Punto de entrada de la aplicación web (Streamlit) y su menú
herramienta.py         Página principal: incorporar, revisar, corregir y descargar
navegacion.py          Páginas de la app y enlaces entre ellas
paginas/               Cómo se calculan los indicadores, términos, privacidad y aviso legal
analysis.py            Prompt, llamada al modelo y verificación de evidencias
indicators.py          Indicadores estándar (las mismas definiciones que el estudio)
article_fetch.py       Lectura de noticias desde su enlace y detección de su licencia
TERMINOS_Y_CONDICIONES.md, PRIVACIDAD.md, AVISO_LEGAL.md
                       Textos legales, que la app muestra en sus páginas
docs/plan_difusion.md  Plan de implantación, medios recomendados y financiación
requirements.txt       Dependencias
evaluation/
  sinc.py              Descarga de noticias de SINC y extracción de las muestras
  annotate.py/.html    Anotación manual a ciegas (sin ver la predicción del modelo)
  run_batch.py         Ejecuta el modelo sobre muchas noticias
  grammar_gender.py    Reglas gramaticales de género
  name_layer.py        Capa de nombres INE + OMPI (solo evaluación)
  metrics.py           Acuerdo entre anotadoras, error del modelo e indicadores de la muestra
  baseline_spacy.py    Línea base con spaCy
  cost.py              Coste a partir de los tokens medidos
  export_dataset.py    Exporta el conjunto de datos abierto
  data/                Noticias, muestras, anotaciones, predicciones, resultados y tablas de nombres
```

---

## Datos

- **Noticias de la Agencia SINC** (FECYT), de octubre de 2025 a septiembre de 2026. Solo se guardan, analizan y publican noticias con licencia **CC BY 4.0**; el resto se descarta al leer su licencia, sin guardarlo. En total, 1.066 noticias del periodo. Cada noticia se guarda con su enlace, su fuente y su huella SHA-256, sin modificar el texto.
- **Muestra de evaluación:** 46 noticias elegidas al azar con semilla fija (2026), 6 de calibración y 40 de test, la mitad de la redacción de SINC y la mitad notas de prensa de instituciones.
- **Muestra de resultados:** 200 noticias elegidas al azar con semilla fija (2026), etiquetadas por el modelo.
- **Anotación manual a ciegas:** quien anota nunca ve la predicción del modelo. Dos anotadoras anotaron las 6 noticias de calibración para medir el acuerdo.

Las personas que aparecen son las citadas en noticias publicadas, en su papel público.

---

## Componentes de terceros y licencias

| Componente | Uso | Licencia |
|---|---|---|
| [gpt-oss-120b](https://huggingface.co/openai/gpt-oss-120b) | Modelo de lenguaje por defecto | Apache-2.0 |
| [Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | Modelo local alternativo (opcional) | Apache-2.0 |
| [OVHcloud AI Endpoints](https://www.ovhcloud.com/es/public-cloud/ai-endpoints/) | Servicio de inferencia | Servicio de terceros; condiciones de OVHcloud |
| [Streamlit](https://streamlit.io) | Aplicación web | Apache-2.0 |
| [pandas](https://pandas.pydata.org) | Tablas | BSD-3-Clause |
| [requests](https://requests.readthedocs.io) | Llamadas HTTP | Apache-2.0 |
| [trafilatura](https://trafilatura.readthedocs.io) | Lectura de noticias desde su enlace | Apache-2.0 |
| [spaCy](https://spacy.io) | Línea base (opcional) | MIT |
| [es_core_news_md](https://spacy.io/models/es) | Modelo español de spaCy (opcional, no se distribuye) | GPL-3.0 |
| Noticias de [Agencia SINC](https://www.agenciasinc.es) | Corpus | CC BY 4.0 |
| [INE, nombres por frecuencia](https://www.ine.es/daco/daco42/nombyapel/nombyapel2.htm) | Capa de nombres (solo evaluación) | Reutilización con cita de la fuente (aviso legal del INE) |
| [WGND 2.0](https://doi.org/10.7910/DVN/MSEGSJ) (Raffo, 2021) | Capa de nombres (solo evaluación) | CC0 1.0 |

El resto de dependencias de Python están en `requirements.txt`, con sus propias licencias de código abierto.

---

## Ética y cumplimiento normativo

Los textos legales están en [`TERMINOS_Y_CONDICIONES.md`](TERMINOS_Y_CONDICIONES.md), [`PRIVACIDAD.md`](PRIVACIDAD.md) y [`AVISO_LEGAL.md`](AVISO_LEGAL.md). La app los muestra en sus páginas y pide aceptar los términos y la política de privacidad antes de analizar.

- **Sin almacenamiento:** la app no guarda textos, enlaces ni resultados en ningún servidor ni en el repositorio. Las estadísticas de uso de Streamlit están desactivadas (`.streamlit/config.toml`).
- **Supervisión humana:** el sistema propone y una persona decide. Los resultados sirven para la autoevaluación del propio contenido, no para señalar a medios ni a personas.
- **Género:** solo el que indica el texto. No se infiere a partir del nombre.
- **Datos personales:**
  - El repositorio publica nombres de personas reales tal como aparecen en noticias publicadas con licencia abierta, junto con el papel público que les da la noticia y las frases que se les atribuyen.
  - No se añaden datos externos ni se hacen perfiles.
  - El tratamiento se apoya en el interés legítimo de la investigación y en la libertad de información sobre personas en su papel público (RGPD, art. 6.1.f y art. 85).
  - Conforme al apartado 12.3 de las bases del reto, se ha solicitado a la organización la autorización para tratar datos personales reales.
- **Retirada:** cualquier persona que aparezca en los datos puede pedir que se retire su nombre abriendo una incidencia en el repositorio.
- **Derechos:** solo textos con licencia CC BY 4.0, citados y enlazados a su original. El texto no se modifica; las etiquetas se añaden aparte.
- **Marco:**
  - Reglamento (UE) 2024/1689 de IA (no es un sistema de alto riesgo);
  - RGPD y LOPDGDD;
  - LSSI;
  - Directiva (UE) 2019/790 (minería de textos);
  - LO 3/2007 y Ley 15/2022.

---

## Limitaciones

- El modelo puede pasar por alto personas o citas, o asignar etiquetas sin apoyo en el texto. La verificación comprueba que la frase existe, no que la interpretación sea correcta.
- La relación con el trabajo es la etiqueta en la que el modelo coincide menos con la anotación humana (48 de 65), y el papel como fuente es la de menor acuerdo entre anotadoras (κ = 0,48).
- Los resultados describen las noticias de SINC en ese periodo, no toda la prensa española. Las cifras de la muestra de 200 noticias proceden del modelo sin revisión humana.
- Con 40 noticias de test, los porcentajes tienen márgenes de unos ±12 puntos.
- «Voces elegidas» y «Reconocimiento» tienen muy pocos casos en la muestra anotada (5 y 0 personas con género indicado), así que su error no puede estimarse con fiabilidad. El error de 4 puntos como máximo se refiere a los cuatro indicadores principales.

---

## Hoja de ruta

| Cuándo | Qué |
| --- | --- |
| Noviembre de 2026 – enero de 2027 | Piloto con cuatro organizaciones: Agencia SINC, Science Media Centre España, The Conversation España y una unidad de cultura científica |
| Febrero de 2027 | Mejoras de la aplicación a partir del piloto |
| 11 de febrero de 2027 | Primer informe abierto, en el Día Internacional de la Mujer y la Niña en la Ciencia |
| Marzo – diciembre de 2027 | Adopción a través de AECC, ANIS, AMIT, la red UCC+i y facultades de periodismo |
| Cada trimestre | Informe con noticias de licencia abierta |

Líneas de investigación:
- **Validación más amplia:** más noticias, más anotadoras y cada nueva fuente.
- **Seguimiento de la noticia:** del artículo científico a los medios que la reproducen.

El calendario, los medios recomendados y la financiación están en [`docs/plan_difusion.md`](docs/plan_difusion.md).

---

## Despliegue

- **Actual:** la aplicación se ejecuta en local o en un servidor propio (`python -m streamlit run app.py`). El modelo puede ser gpt-oss-120b en OVHcloud AI Endpoints o cualquier modelo compatible en local.
- **Siguiente paso:** publicar una demo en [Streamlit Community Cloud](https://streamlit.io/cloud), que despliega la app directamente desde este repositorio. Antes hay que resolver dos cuestiones:
  - **Token:** no se guardará el token del equipo en los *secrets* de la demo pública, para que nadie consuma la cuota en nuestro nombre. Cada usuario introducirá el suyo en la barra lateral, como ya permite la app.
  - **Privacidad:** los servidores de Streamlit Community Cloud están fuera de la UE, así que la política de privacidad deberá indicarlo. Para uso profesional se recomienda un servidor propio o un modelo local.

## Licencia

Código publicado bajo la licencia **Apache-2.0** (ver [`LICENSE`](LICENSE)). Los textos de las noticias conservan su licencia CC BY 4.0.
