# Model error · gpt-oss-120b against Elena · test

40 finished annotations with a prediction. Mean annotation time: 2.1 minutes per article.

| Stage | Women (human) | 95 % CI | Women (model) | Difference |
| --- | --- | --- | --- | --- |
| Presence: mentioned | 35 % (20) | 24–48 % | 36 % | +1 points |
| Voice: quoted | 36 % (20) | 25–50 % | 38 % | +1 points |
| Authority: technical experts | 36 % (20) | 25–50 % | 33 % | -4 points |
| Protagonism: lead the work | 37 % (19) | 25–51 % | 39 % | +2 points |
| Chosen voices: comment on the work | 20 % (1) | 4–62 % | 33 % | +13 points |
| Recognition: named in headline or lead | no cases (0) | — | no cases | — |

The difference is the error of the final indicator, which is what matters for the results.

People found by the model: 65 of 65; extra people not in the annotation: 6.

| Gender (human) | Missed by the model |
| --- | --- |
| man | 0 of 37 |
| woman | 0 of 20 |
| unknown | 0 of 8 |

| Label | Same in human and model |
| --- | --- |
| gender | 61 of 65 |
| expert | 58 of 65 |
| role | 54 of 65 |
| quoted | 65 of 65 |
| work_role | 48 of 65 |
| headline_reference | 65 of 65 |

### Counts in the human annotation

| Gender | People | Times named | Quotations |
| --- | --- | --- | --- |
| woman | 20 | 53 | 73 |
| man | 37 | 86 | 135 |
| other_explicit | 0 | 0 | 0 |
| unknown | 8 | 9 | 2 |

Women among known genders: 35 % of people, 38 % of the times someone is named, 35 % of quotations.

### Counts in the model prediction

| Gender | People | Times named | Quotations |
| --- | --- | --- | --- |
| woman | 21 | 54 | 60 |
| man | 38 | 87 | 99 |
| other_explicit | 0 | 0 | 0 |
| unknown | 12 | 13 | 3 |

Women among known genders: 36 % of people, 38 % of the times someone is named, 38 % of quotations.

### Named or only described in the headline or lead: human

| Gender | In headline or lead | With their name | Only described | Named share | 95 % CI |
| --- | --- | --- | --- | --- | --- |
| woman | 0 | 0 | 0 | no cases | — |
| man | 0 | 0 | 0 | no cases | — |

### Named or only described in the headline or lead: model

| Gender | In headline or lead | With their name | Only described | Named share | 95 % CI |
| --- | --- | --- | --- | --- | --- |
| woman | 0 | 0 | 0 | no cases | — |
| man | 0 | 0 | 0 | no cases | — |
