# Términos y condiciones de uso

Última actualización: 29 de octubre de 2026.

Estos términos regulan el uso de **Voz experta de las mujeres**, una herramienta de código abierto que mide con indicadores estándar el papel de las mujeres en las noticias de ciencia. Para analizar noticias hay que aceptarlos. Complementan la [política de privacidad](PRIVACIDAD.md) y el [aviso legal](AVISO_LEGAL.md).

## 1. Qué hace la herramienta

La herramienta recibe noticias, pegadas como texto o mediante su enlace. Un modelo de lenguaje propone, para cada persona que aparece:

- su género según el texto;
- si se le atribuyen citas;
- si se la presenta como especialista;
- su relación con el trabajo que cuenta la noticia;
- si aparece en el titular o la entradilla.

Cada propuesta va acompañada de la frase de la noticia en que se basa. La persona usuaria revisa y corrige esas propuestas, y la herramienta calcula con ellas los indicadores y los deja descargar. Las definiciones y fórmulas están en «Cómo se calculan los indicadores».

## 2. Quién puede usarla

- **Organizaciones y medios**, para medir su propio contenido de forma periódica.
- **Periodistas**, para revisar sus noticias antes de publicarlas.
- **Ciudadanía, docencia e investigación**, para analizar noticias ya publicadas con una licencia abierta Creative Commons.

Al elegir un uso, la persona usuaria declara que es el que corresponde a su caso.

## 3. Qué textos se pueden analizar

1. Solo textos sobre los que se tenga derecho de uso: textos propios, de la organización para la que se trabaja o publicados con una licencia que permita su análisis, como **CC BY 4.0**.
2. Con el perfil «Ciudadanía, docencia e investigación», la app solo analiza enlaces cuya página declare una licencia Creative Commons, mediante un enlace a la licencia o una línea de derechos del tipo «Derechos: Creative Commons». La detección es automática y puede fallar. La responsabilidad de comprobar la licencia sigue siendo de quien introduce el enlace.
3. El análisis automatizado de textos a los que se tiene acceso legítimo se ampara en las excepciones de minería de textos y datos de la Directiva (UE) 2019/790, artículos 3 y 4, incorporadas al derecho español por el Real Decreto-ley 24/2021. La excepción no se aplica si el titular se ha reservado expresamente ese uso.
4. No deben introducirse textos con datos personales que no sean necesarios para el análisis, como datos de salud o direcciones, ni borradores confidenciales si se usa un servicio de modelo externo. Para esos casos, la herramienta permite usar un modelo local.

## 4. Usos no permitidos

No está permitido usar la herramienta para:

- copiar, almacenar o redistribuir contenidos protegidos;
- eludir muros de pago o medidas técnicas de protección;
- descargar páginas de forma masiva o automatizada;
- señalar, acosar o desacreditar a personas concretas, o clasificar a medios en rankings públicos sin indicar el método y sus límites;
- tomar decisiones sobre personas, como contrataciones, evaluaciones, subvenciones o sanciones;
- presentar los resultados como una auditoría oficial o como un juicio sobre la calidad periodística;
- deducir el género, el origen u otras características de una persona más allá de lo que dice el texto;
- presentar resultados sin revisar como si lo estuvieran.

## 5. Límites de los resultados

- El modelo de lenguaje se equivoca. En la evaluación del proyecto, con 40 noticias anotadas a mano, el error del porcentaje final fue de 4 puntos como máximo. Las etiquetas por persona fallan más, sobre todo la relación con el trabajo. Los detalles están en «Cómo se calculan los indicadores».
- La verificación automática comprueba que cada frase de evidencia existe en la noticia, no que la interpretación sea correcta.
- El género solo se toma del texto. Si el texto no lo indica, la persona se cuenta aparte como «no indicado».
- Con pocas noticias, los intervalos de confianza son muy amplios. Las cifras tienen sentido en conjunto y a lo largo del tiempo, no noticia a noticia.

## 6. Revisión humana y publicación de cifras

1. Antes de usar las cifras, la persona usuaria debe revisar y, si hace falta, corregir las propuestas del modelo.
2. El archivo descargado distingue la predicción del modelo de la versión revisada, e indica si cada noticia se revisó (`human_reviewed`) o no (`model_only`).
3. Si se publican indicadores, hay que indicar:
   - cuántas noticias incluyen;
   - cuántas se revisaron a mano;
   - el periodo;
   - la versión de los indicadores que figura en el archivo.

## 7. Disponibilidad del servicio

- La herramienta es un prototipo de investigación y se ofrece sin garantía de disponibilidad.
- Puede haber límites de uso, como un máximo de 20 enlaces por análisis, y el servicio puede interrumpirse o cambiar sin aviso previo.
- La app no guarda nada entre sesiones: al cerrar o recargar la página se pierde lo que no se haya descargado.

## 8. Propiedad intelectual

- El código se publica con la licencia **Apache-2.0**. Se puede usar, modificar y redistribuir según esa licencia.
- Los textos analizados conservan sus derechos y licencias.
- Los resultados que genera la persona usuaria le pertenecen. Si redistribuye textos de terceros dentro de ellos, debe respetar sus licencias.

## 9. Responsabilidad

- La persona usuaria es responsable de los textos que introduce, de tener derechos sobre ellos, del tratamiento de los datos personales que contengan y del uso que haga de los resultados.
- La herramienta se ofrece «tal cual», sin garantías, como establece la licencia Apache-2.0. El equipo que la desarrolló no responde de decisiones tomadas a partir de sus resultados.
- Cada instalación de la herramienta es responsabilidad de quien la opera.

## 10. Cambios en estos términos

Los términos se publican con el código y sus cambios quedan registrados en el historial del repositorio. La versión aplicable es la vigente en el momento de usar la herramienta.

## 11. Legislación aplicable

Estos términos se rigen por la legislación española, sin perjuicio de los derechos que la normativa de consumo reconozca a las personas usuarias.

## 12. Contacto

Las dudas, incidencias y solicitudes se gestionan abriendo una incidencia (*issue*) en el repositorio del proyecto.
