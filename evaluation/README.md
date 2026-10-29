# Evaluación

Scripts que convierten la aplicación en los resultados del equipo: descargan las noticias de SINC, permiten anotar a mano una muestra sin ver el modelo, ejecutan el análisis de la aplicación sobre muchas noticias y calculan las métricas.

Reutilizan el propio código de la aplicación en `analysis.py`: el mismo prompt, la misma llamada al modelo, las mismas comprobaciones de evidencias y las mismas tablas de revisión, y también las mismas definiciones de los indicadores (`indicators.py` usa `metrics.py`).

Los datos se guardan en `evaluation/data/` y se publican junto con el código, para que cualquier cifra pueda comprobarse: las noticias de SINC (CC BY 4.0), las anotaciones manuales, las predicciones del modelo y los resultados. Los nombres son los de personas citadas en noticias publicadas, en su papel público. El token de la API nunca se guarda ahí.

## Preparación

Todo se ejecuta desde la raíz del repositorio, con el mismo entorno que la aplicación.

```bash
pip install -r requirements.txt
export OVH_AI_ENDPOINTS_ACCESS_TOKEN=...   # token del equipo; nunca lo escribas en un archivo
```

## 1. Descargar las noticias de SINC

```bash
python evaluation/sinc.py candidates --start 2025-10-01 --end 2026-09-30
```

Descarga una noticia por segundo, aproximadamente. Si se interrumpe, basta con volver a lanzarlo: continúa donde lo dejó.

## 2. Extraer la muestra para la anotación manual

```bash
python evaluation/sinc.py sample --start 2025-10-01 --end 2026-09-30 --calibration 3 3 --test 20 20 --seed 2026
```

6 noticias de calibración y 40 de test, la mitad de la redacción de SINC y la mitad notas de prensa de instituciones, elegidas al azar con una semilla fija. Solo se usan noticias con licencia Creative Commons, y las tres noticias de práctica siempre quedan fuera. Si se vuelve a ejecutar, sustituye la muestra anterior.

## 3. Anotación a ciegas

```bash
python evaluation/annotate.py
```

Abre la página de anotación en http://127.0.0.1:8765 (en un Codespace, abre el puerto 8765 desde la pestaña *Ports*). Los fragmentos se seleccionan directamente sobre el texto y se colorean por persona: N nueva persona, M mención, G evidencia de género, R evidencia de papel, D cita directa, I cita indirecta. La predicción del modelo nunca se muestra.

Cada anotadora escribe su nombre. Las anotaciones se guardan al momento en `evaluation/data/annotations/<nombre>/`, en el formato de revisión de la aplicación (`reviewed_people`, `reviewed_quotes`), para que `metrics.py` pueda compararlas con el modelo. Todas las anotadoras hacen las 6 noticias de calibración, así se puede medir el acuerdo entre ellas:

```bash
python evaluation/metrics.py agreement --annotators Eva_Mar Elena
```

Muestra el kappa de Cohen de cada etiqueta, las personas que encontraron ambas y el tiempo medio de anotación.

## 4. Ejecutar el modelo sobre muchas noticias

```bash
python evaluation/run_batch.py evaluation/data/sample
```

Llama a `run_model` para cada noticia y guarda el resultado en el formato de exportación de la aplicación. Las noticias ya analizadas se saltan. Para probarlo sin token, con Ollama en local como en la v1:

```bash
python evaluation/run_batch.py evaluation/data/sample --model qwen2.5:7b --base-url http://127.0.0.1:11434/v1
```

## 5. Capa de nombres: INE y OMPI

Coloca ambos archivos en `evaluation/data/`:

- `nombres_por_edad_media.xlsx` (INE): nombres de las personas residentes en España con frecuencia igual o mayor a 20, con una hoja de hombres y otra de mujeres. Censo a 1 de enero de 2025. Procede de [Apellidos y nombres más frecuentes](https://www.ine.es/daco/daco42/nombyapel/nombyapel2.htm).
- `wgnd_2_0_name-gender_nocode.csv` (World Gender Name Dictionary 2.0 de la OMPI, CC0 1.0): nombres de otros países. Solo se incluyen los nombres asociados a un único género.

```bash
python evaluation/name_layer.py prepare --excel evaluation/data/nombres_por_edad_media.xlsx
python evaluation/name_layer.py apply evaluation/data/predictions/gpt-oss-120b
```

Esta capa es una comprobación que solo se usa en la evaluación: frente a la anotación, aumentó el error de 1 a 4 puntos, así que los resultados principales y la aplicación usan únicamente el texto y las reglas gramaticales. El género que indica el texto nunca se cambia. Se usa el primer nombre de pila. El INE decide cuando conoce el nombre y solo sugiere un género si al menos el 95 % de las personas con ese nombre son mujeres u hombres; si no, se consulta la OMPI. Las sugerencias quedan marcadas con su fuente, y el script cuenta los nombres que contradicen el texto o que ninguna de las dos fuentes reconoce.

## 6. Error del modelo frente a la anotación

```bash
python evaluation/metrics.py compare --annotator Elena --predictions evaluation/data/predictions/gpt-oss-120b --group test
python evaluation/metrics.py compare --annotator Elena --predictions evaluation/data/predictions/gpt-oss-120b --group test --with-name
python evaluation/metrics.py layers --annotator Elena --predictions evaluation/data/predictions/gpt-oss-120b --group test
```

Muestra el embudo humano y el del modelo, la diferencia en puntos, las personas que el modelo pierde según su género y el acuerdo en cada etiqueta. `layers` muestra el error con el modelo solo, con las reglas gramaticales y con la capa de nombres. Elena anotó las 40 noticias de test.

Línea base: ¿encuentra un método clásico y gratuito las mismas personas que el LLM? Se compara el reconocimiento de entidades de spaCy con la anotación y con el modelo. Solo se compara la presencia, porque spaCy encuentra nombres, pero no citas, papeles ni género.

```bash
pip install spacy && python -m spacy download es_core_news_md   # una sola vez
python evaluation/baseline_spacy.py --annotator Elena --predictions evaluation/data/predictions/gpt-oss-120b --group test
```

## 7. Métricas del corpus

Con hasta 1,5 minutos por noticia (0,7 de media con el prompt 0.6), el año completo (1.066 noticias) llevaría más de un día, así que se extrae una muestra aleatoria simple de 200 noticias con una semilla fija. Sus métricas estiman las del año, con intervalos más amplios. Las noticias que ya están en la muestra anotada no se ejecutan dos veces.

```bash
python evaluation/sinc.py corpus --start 2025-10-01 --end 2026-09-30 --size 200 --seed 2026
python evaluation/run_batch.py evaluation/data/corpus_sample
python evaluation/name_layer.py apply evaluation/data/predictions/gpt-oss-120b
python evaluation/metrics.py corpus evaluation/data/predictions/gpt-oss-120b --articles evaluation/data/corpus_sample
```

Calcula el embudo (presencia, voz, autoridad y protagonismo) con intervalos de confianza del 95 %, con y sin la capa de nombres; los géneros no indicados; la pérdida de crédito (si la persona que lidera el trabajo tiene voz, según su género), y la comparación entre la redacción de SINC y las notas de prensa.

## 8. Conjunto de datos abierto

```bash
python evaluation/export_dataset.py evaluation/data/predictions/gpt-oss-120b --annotators Eva_Mar Elena
```

Genera `evaluation/data/release/`: todas las noticias con licencia Creative Commons, las etiquetas de cada persona y los fragmentos en los que se basan, la anotación humana y el número de noticias por sección de SINC. El género sugerido por la capa de nombres no se exporta, porque solo se usa en cifras de conjunto.

## Coste

```bash
python evaluation/cost.py evaluation/data/predictions/gpt-oss-120b --input-price 0.08 --output-price 0.4
```

Calcula la media de tokens por noticia a partir del consumo que el servicio informa en cada llamada, y el coste de un año de SINC con los precios del catálogo de OVHcloud (euros por millón de tokens).

## Resultados

Cada comando guarda sus tablas en `evaluation/data/results/` (en Markdown y JSON). Las cifras del README y de la presentación proceden de esos archivos.

## Fuentes

INE, Censos de población anuales: nombres con frecuencia igual o mayor a 20, 1 de enero de 2025. Raffo, J. (2021). *WGND 2.0*. Harvard Dataverse, CC0 1.0. https://doi.org/10.7910/DVN/MSEGSJ
