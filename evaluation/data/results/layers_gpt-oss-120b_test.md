# Gender layers against Elena · test

40 annotated articles. Women among people mentioned, human annotation: 35 %.

| Setting | Same gender as human | Gender unknown | Women mentioned | Error |
| --- | --- | --- | --- | --- |
| LLM only | 46 of 65 | 29 of 71 | 31 % | -4 points |
| LLM + grammar rules | 61 of 65 | 12 of 71 | 36 % | +1 points |
| LLM + grammar + name (INE, WIPO) | 55 of 65 | 0 of 71 | 39 % | +4 points |

Each layer only fills genders the previous ones left unknown; the text always wins.