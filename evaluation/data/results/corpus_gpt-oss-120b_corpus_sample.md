# Corpus metrics · gpt-oss-120b

200 articles (0 left out without a Creative Commons licence), 447 people. Model predictions without human review: their error is measured with `metrics.py compare`.

## Funnel

### Text only

| Stage | People | Known gender | Women | 95 % CI |
| --- | --- | --- | --- | --- |
| Presence: mentioned | 447 | 359 | 38 % (135) | 33–43 % |
| Voice: quoted | 357 | 311 | 39 % (120) | 33–44 % |
| Authority: technical experts | 368 | 314 | 38 % (119) | 33–43 % |
| Protagonism: lead the work | 259 | 222 | 39 % (87) | 33–46 % |
| Chosen voices: comment on the work | 139 | 115 | 37 % (42) | 28–46 % |
| Recognition: named in headline or lead | 10 | 5 | 0 % (0) | 0–43 % |

### Text plus name layer (INE and WIPO)

| Stage | People | Known gender | Women | 95 % CI |
| --- | --- | --- | --- | --- |
| Presence: mentioned | 447 | 433 | 37 % (159) | 32–41 % |
| Voice: quoted | 357 | 349 | 38 % (133) | 33–43 % |
| Authority: technical experts | 368 | 364 | 37 % (135) | 32–42 % |
| Protagonism: lead the work | 259 | 254 | 38 % (96) | 32–44 % |
| Chosen voices: comment on the work | 139 | 133 | 35 % (47) | 28–44 % |
| Recognition: named in headline or lead | 10 | 9 | 11 % (1) | 2–44 % |

Unknown gender: 88 of 447 people with the text only; 14 with the name layer.
Where the gender comes from: text 359, INE 60, none 14, WIPO 14. Names neither the INE nor WIPO recognise: 30.

## Presence and voice in counts (text only)

Unique people, times each is named in the text, and quotations attributed to them.

| Gender | People | Times named | Quotations |
| --- | --- | --- | --- |
| woman | 135 | 247 | 252 |
| man | 224 | 426 | 439 |
| other_explicit | 0 | 0 | 0 |
| unknown | 88 | 143 | 81 |

Women among known genders: 38 % of people, 37 % of the times someone is named, 36 % of quotations.

## Recognition: named or only described in the headline or lead (text only)

| Gender | In headline or lead | With their name | Only described | Named share | 95 % CI |
| --- | --- | --- | --- | --- | --- |
| woman | 0 | 0 | 0 | no cases | — |
| man | 5 | 5 | 0 | 100 % | 57–100 % |

## Authority: role given to each person (text only)

| Role | Women | Men | Women's share |
| --- | --- | --- | --- |
| specialist | 116 | 188 | 38 % |
| spokesperson | 7 | 11 | 39 % |
| politician | 1 | 1 | 50 % |
| testimony | 2 | 1 | 67 % |
| other | 4 | 10 | 29 % |
| mentioned_only | 5 | 13 | 28 % |

## Credit loss: is the person who leads the work quoted?

| Who leads | Text only: quoted | 95 % CI | With name layer: quoted | 95 % CI |
| --- | --- | --- | --- | --- |
| woman | 90 % (78 of 87) | 81–94 % | 89 % (85 of 96) | 81–93 % |
| man | 89 % (120 of 135) | 82–93 % | 84 % (133 of 158) | 78–89 % |

## Credit loss by source type (text only)

| Source | Women who lead: quoted | Men who lead: quoted |
| --- | --- | --- |
| institution | 90 % (37 of 41) | 85 % (52 of 61) |
| sinc_newsroom | 89 % (41 of 46) | 92 % (68 of 74) |

## SINC newsroom compared with institutions' press releases (text only)

### institution

| Stage | People | Known gender | Women | 95 % CI |
| --- | --- | --- | --- | --- |
| Presence: mentioned | 226 | 179 | 37 % (66) | 30–44 % |
| Voice: quoted | 171 | 150 | 38 % (57) | 31–46 % |
| Authority: technical experts | 185 | 159 | 37 % (59) | 30–45 % |
| Protagonism: lead the work | 119 | 102 | 40 % (41) | 31–50 % |
| Chosen voices: comment on the work | 76 | 63 | 32 % (20) | 22–44 % |
| Recognition: named in headline or lead | 9 | 4 | 0 % (0) | 0–49 % |

### sinc_newsroom

| Stage | People | Known gender | Women | 95 % CI |
| --- | --- | --- | --- | --- |
| Presence: mentioned | 221 | 180 | 38 % (69) | 32–46 % |
| Voice: quoted | 186 | 161 | 39 % (63) | 32–47 % |
| Authority: technical experts | 183 | 155 | 39 % (60) | 31–47 % |
| Protagonism: lead the work | 140 | 120 | 38 % (46) | 30–47 % |
| Chosen voices: comment on the work | 63 | 52 | 42 % (22) | 30–56 % |
| Recognition: named in headline or lead | 1 | 1 | 0 % (0) | 0–79 % |
