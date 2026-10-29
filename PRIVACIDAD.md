# Política de privacidad

Última actualización: 29 de octubre de 2026.

**La app no guarda los textos, los enlaces ni los resultados de los análisis.** Solo existen mientras la sesión está abierta. El texto se envía al modelo de lenguaje únicamente para analizarlo. Lo que se quiera conservar hay que descargarlo.

## 1. Responsable del tratamiento

- **Quien opera cada instalación** de la herramienta es responsable de esa instalación, porque el código es abierto y cualquier organización puede instalarlo.
- **La persona u organización que introduce textos** es responsable del tratamiento de los datos personales que esos textos contengan.
- **El equipo del proyecto** es responsable del conjunto de datos del estudio publicado en el repositorio (apartado 7).

## 2. Qué datos se tratan

| Dato | De dónde viene | Qué se hace con él |
| --- | --- | --- |
| Texto de la noticia (titular, entradilla, cuerpo) | Lo pega la persona usuaria o se descarga del enlace | Se envía al modelo para analizarlo y se muestra en la sesión |
| Nombres, cargos y citas de las personas de la noticia | Del propio texto | El modelo los extrae; no se añaden datos externos ni se crean perfiles |
| Enlaces | Los introduce la persona usuaria | El servidor descarga la página. La web enlazada recibe la petición del servidor, no la de la persona usuaria |
| Token de acceso al modelo | Lo introduce quien opera la app o la persona usuaria | Solo en la memoria de la sesión; nunca se incluye en los resultados |
| Datos técnicos de la conexión (dirección IP, navegador) | La conexión con el servidor | Dependen del servicio que aloja la app; la app no los registra |

La app no pide nombre, correo ni ningún otro dato de la persona usuaria.

## 3. Para qué y con qué base jurídica

- **Analizar las noticias que la persona usuaria pide analizar.** Es la finalidad de la herramienta. La base jurídica es la que tenga quien introduce los textos, normalmente el interés legítimo en revisar y mejorar su propio contenido (RGPD, art. 6.1.f).
- **Personas que aparecen en las noticias.** Se tratan solo en su papel público, tal como lo describe la noticia, al amparo de la libertad de información (RGPD, art. 85).
- **Género.** Solo se registra el que indica el texto («la investigadora», «él»). La app nunca lo deduce del nombre ni de otros datos.

## 4. Dónde se procesa el texto

- **Por defecto, en OVHcloud AI Endpoints**, en la Unión Europea, con el modelo abierto gpt-oss-120b. OVHcloud declara en su web que no guarda los datos de las peticiones ni los usa para entrenar modelos. No hemos podido comprobarlo en un contrato, así que consulta sus condiciones antes de enviar textos no publicados.
- **Si una organización usa la app con un servicio externo**, debe firmar con el proveedor un contrato de encargo del tratamiento (RGPD, art. 28).
- **Con un modelo local** (por ejemplo, con Ollama), el texto no sale del ordenador. Es la opción recomendada para borradores y textos internos.

## 5. Cuánto tiempo se conservan

Nada se conserva después de la sesión. Al cerrar o recargar la página, o al pulsar «Empezar de nuevo», se borran los textos, las predicciones y las correcciones. Los archivos descargados quedan en el dispositivo de la persona usuaria, bajo su responsabilidad.

## 6. Cookies y estadísticas

- La app solo usa una cookie técnica de seguridad de Streamlit (`_streamlit_xsrf`), necesaria para que funcione.
- No usa cookies de analítica ni de publicidad.
- Las estadísticas de uso que Streamlit envía por defecto están desactivadas en la configuración (`gatherUsageStats = false`).

## 7. Datos del estudio publicados en el repositorio

- El repositorio publica el conjunto de datos del estudio:
  - noticias con licencia CC BY 4.0;
  - anotaciones humanas;
  - predicciones del modelo.
- Incluye nombres de personas reales tal como aparecen en esas noticias, junto con el papel público que se les da.
- Cualquier persona que aparezca puede pedir que se retire su nombre abriendo una incidencia en el repositorio. Se sustituirá por un identificador.

## 8. Derechos

- Como la app no guarda datos de las sesiones, no hay datos que consultar, rectificar ni suprimir después de cerrarlas.
- Para los datos del estudio publicados en el repositorio, se pueden ejercer los derechos de acceso, rectificación, supresión, oposición y limitación del tratamiento mediante una incidencia en el repositorio.
- También se puede presentar una reclamación ante la Agencia Española de Protección de Datos (www.aepd.es).

## 9. Normativa

- Reglamento (UE) 2016/679 (RGPD).
- Ley Orgánica 3/2018 de Protección de Datos Personales y garantía de los derechos digitales (LOPDGDD).
- Ley 34/2002 de servicios de la sociedad de la información (LSSI), en lo relativo a cookies.
