# Job matching evaluation (2026-11-24)

Resumes: 20 · judged pairs: 294 · metric: Precision@5 (pooled, blind judging)

| Method | Precision@5 | Hybrid better / worse on |
|---|---|---|
| hybrid | **0.40** | — |
| meaning | **0.37** | 5 / 4 resumes |
| skills | **0.42** | 3 / 5 resumes |
| newest | **0.38** | 9 / 5 resumes |
| hybrid+level | **0.64** | 0 / 14 resumes |

| Resume | hybrid | meaning | skills | newest | hybrid+level |
|---|---|---|---|---|---|
| s01.txt | 0.8 | 0.8 | 0.8 | 0.4 | 1.0 |
| s02.txt | 0.6 | 0.8 | 0.8 | 0.4 | 1.0 |
| s03.txt | 0.2 | 0.4 | 0.0 | 0.0 | 0.8 |
| s04.txt | 0.4 | 0.6 | 0.4 | 0.4 | 0.8 |
| s05.txt | 0.4 | 0.0 | 0.6 | 0.2 | 0.4 |
| s06.txt | 0.6 | 0.2 | 0.4 | 0.8 | 0.8 |
| s07.txt | 0.2 | 0.2 | 0.4 | 0.2 | 0.8 |
| s08.txt | 0.8 | 0.8 | 0.8 | 0.6 | 1.0 |
| s09.txt | 0.2 | 0.0 | 0.2 | 0.8 | 0.4 |
| s10.txt | 0.4 | 0.4 | 0.4 | 0.8 | 0.6 |
| s11.txt | 0.2 | 0.4 | 0.2 | 0.2 | 0.6 |
| s12.txt | 0.4 | 0.4 | 0.4 | 0.4 | 0.4 |
| s13.txt | 0.6 | 0.4 | 0.6 | 0.4 | 0.6 |
| s14.txt | 0.6 | 0.6 | 0.8 | 0.6 | 0.8 |
| s15.txt | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| s16.txt | 0.2 | 0.2 | 0.2 | 0.0 | 0.2 |
| s17.txt | 0.4 | 0.2 | 0.2 | 0.2 | 0.6 |
| s18.txt | 0.4 | 0.4 | 0.4 | 0.2 | 0.4 |
| s19.txt | 0.2 | 0.2 | 0.2 | 0.4 | 0.6 |
| s20.txt | 0.4 | 0.4 | 0.6 | 0.6 | 1.0 |

## Read this first: what this trial is (and isn't)

- **Synthetic trial, not the final evaluation.** The 20 resumes are fictional (2 per role, a mix of
  freshers and 1-3 years' experience), written by Claude; relevance was also judged by Claude.
  Rule fixed before any judging: 1 = target role (or very close) **and** the level fits (no
  Senior/Lead/5+ yrs for a fresher; at most ~1 year above the candidate's experience) **and** the
  core stack overlaps. Real resumes and human judges are still needed (`--set eval`).
- 20 resumes x 5 = 100 slots per method, so differences of 0.03-0.05 are noise.

## Round 1: the four original methods tie (0.37-0.42)

The app's hybrid ranking was no better than showing the newest postings. Diagnosis: of the 166
jobs judged not relevant, **105 (63%) had senior-level titles** (Senior, Lead, Principal, Staff,
VP, Manager, ...) vs. 6 of the 100 relevant ones; 42 more stated 4+ years. Meaning and skills
can't see level: "Senior Data Scientist" and a fresher's data-science resume share a topic.

## Round 2: hybrid + experience level -> 0.64

`seniority.py` reads the years a job asks for (stated "N+ years" first, else the title) and
the years a resume states, and multiplies the fit by 0.85 per year beyond a 1-year slack
(floor 0.3); unknown levels get no penalty. The database returns 100 candidates instead of 50
so there's room to re-rank. Only the new method was run; its 28 never-judged jobs were judged
with the same rule.

- **Precision@5: 0.40 -> 0.64** (+0.24). Better on **14** resumes, worse on **0**, tied on 6
  (sign test on 14 vs 0: p ~ 0.0001).

## Caveats (say these in the viva)

1. **The judging rule includes level**, so a level filter is bound to help on it. That rule
   reflects what freshers need, but real users may weigh it differently.
2. **Not fully blind for round 2:** the 28 new rows were the empty ones, so the judge knew they
   came from the new method (same written rule applied).
3. **Tuned on this data:** two level rules were adjusted after looking at these job titles
   ("Senior Associate" is senior; years written in the title count). Real resumes are the
   held-out check.
4. Some role pools stay thin: the Backend Developer pool is mostly Java, so the Python/Django
   fresher (s15) still scores 0.
