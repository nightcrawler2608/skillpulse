# Job matching evaluation (2026-11-24)

Resumes: 20 · judged pairs: 307 · metric: Precision@5 (pooled, blind judging)

| Method | Precision@5 | Hybrid better / worse on |
|---|---|---|
| hybrid | **0.40** | — |
| meaning | **0.37** | 5 / 4 resumes |
| skills | **0.42** | 3 / 5 resumes |
| newest | **0.38** | 9 / 5 resumes |
| hybrid+level | **0.64** | 0 / 14 resumes |
| full | **0.75** | 0 / 17 resumes |

| Resume | hybrid | meaning | skills | newest | hybrid+level | full |
|---|---|---|---|---|---|---|
| s01.txt | 0.8 | 0.8 | 0.8 | 0.4 | 1.0 | 1.0 |
| s02.txt | 0.6 | 0.8 | 0.8 | 0.4 | 1.0 | 1.0 |
| s03.txt | 0.2 | 0.4 | 0.0 | 0.0 | 0.8 | 0.8 |
| s04.txt | 0.4 | 0.6 | 0.4 | 0.4 | 0.8 | 0.8 |
| s05.txt | 0.4 | 0.0 | 0.6 | 0.2 | 0.4 | 0.8 |
| s06.txt | 0.6 | 0.2 | 0.4 | 0.8 | 0.8 | 0.8 |
| s07.txt | 0.2 | 0.2 | 0.4 | 0.2 | 0.8 | 1.0 |
| s08.txt | 0.8 | 0.8 | 0.8 | 0.6 | 1.0 | 1.0 |
| s09.txt | 0.2 | 0.0 | 0.2 | 0.8 | 0.4 | 0.6 |
| s10.txt | 0.4 | 0.4 | 0.4 | 0.8 | 0.6 | 0.8 |
| s11.txt | 0.2 | 0.4 | 0.2 | 0.2 | 0.6 | 0.6 |
| s12.txt | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 | 0.6 |
| s13.txt | 0.6 | 0.4 | 0.6 | 0.4 | 0.6 | 0.6 |
| s14.txt | 0.6 | 0.6 | 0.8 | 0.6 | 0.8 | 0.8 |
| s15.txt | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| s16.txt | 0.2 | 0.2 | 0.2 | 0.0 | 0.2 | 0.2 |
| s17.txt | 0.4 | 0.2 | 0.2 | 0.2 | 0.6 | 1.0 |
| s18.txt | 0.4 | 0.4 | 0.4 | 0.2 | 0.4 | 0.6 |
| s19.txt | 0.2 | 0.2 | 0.2 | 0.4 | 0.6 | 1.0 |
| s20.txt | 0.4 | 0.4 | 0.6 | 0.6 | 1.0 | 1.0 |

## What this is

- **Synthetic tuning ("dev") set, not the final evaluation.** 20 fictional resumes (2 per role,
  freshers and 1-3 years), written by Claude; relevance judged by Claude, blind (shuffled sheet,
  no method/rank/score shown). Rule fixed before judging: 1 = target role (or very close) **and**
  level fits (no Senior/Lead/5+ yrs for a fresher; at most ~1 year above the candidate) **and**
  core stack overlaps. Real resumes + human judges are still needed (`--set eval`).
- 100 slots per method, so differences of 0.03-0.05 are noise.
- **Because the rules below were tuned on this set, its scores are optimistic.** The fair check
  is the held-out set: [matching_eval_heldout.md](matching_eval_heldout.md).

## Round 1: original methods tie (0.37-0.42)

Of 166 jobs judged not relevant, **105 (63%) had senior-level titles** vs. 6 of 100 relevant
ones; 42 more stated 4+ years. Meaning and skills can't see level.

## Round 2: hybrid + experience level (v1) -> 0.64

Read years asked (stated "N+ years" first, else title) vs. years the resume states; fit x 0.85
per year beyond a 1-year slack (floor 0.3). Better on 14 resumes, worse on 0.

## Round 3: "full" -> 0.75

Failure analysis of round 2's 36 bad top-5 jobs: unread level words (~12), wrong tech stack
(~12), wrong specialisation such as embedded/clinical (~8), internship for an experienced
person (1). Changes: more level words (Advisor, Founding, L4, Specialist, "looking for an
experienced ..."), work date ranges on resumes ("Jul 2023 - Present"), internships down-ranked
for 1+ years, and a tech-stack check (no shared language/framework -> fit x 0.6).

## Caveats

1. The judging rule includes level, so a level step is bound to help on it.
2. New rows from later rounds were the empty ones, so the judge knew they came from a new
   method (the same written rule was applied).
3. Rules were tuned on this data; see the held-out report for an untouched check.
