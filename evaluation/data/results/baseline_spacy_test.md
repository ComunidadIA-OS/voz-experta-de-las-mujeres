# Baseline: spaCy against the LLM · Elena · test

40 annotated articles. Reference: the people annotated by hand. spaCy (es_core_news_md) takes 0.12 s per article and costs nothing.

| Method | People found | Missed | Extra (not annotated) | Women found |
| --- | --- | --- | --- | --- |
| spaCy | 62 of 65 | 3 | 61 | 19 of 20 |
| LLM | 65 of 65 | 0 | 6 | 20 of 20 |

spaCy only finds names: quotes, roles, work role and gender still need the LLM or the annotation.