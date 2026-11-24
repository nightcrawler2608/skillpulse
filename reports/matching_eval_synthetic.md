# Job matching evaluation (2026-11-24)

Resumes: 20 · judged pairs: 266 · metric: Precision@5 (pooled, blind judging)

| Method | Precision@5 | Hybrid better / worse on |
|---|---|---|
| hybrid | **0.40** | — |
| meaning | **0.37** | 5 / 4 resumes |
| skills | **0.42** | 3 / 5 resumes |
| newest | **0.38** | 9 / 5 resumes |

| Resume | hybrid | meaning | skills | newest |
|---|---|---|---|---|
| s01.txt | 0.8 | 0.8 | 0.8 | 0.4 |
| s02.txt | 0.6 | 0.8 | 0.8 | 0.4 |
| s03.txt | 0.2 | 0.4 | 0.0 | 0.0 |
| s04.txt | 0.4 | 0.6 | 0.4 | 0.4 |
| s05.txt | 0.4 | 0.0 | 0.6 | 0.2 |
| s06.txt | 0.6 | 0.2 | 0.4 | 0.8 |
| s07.txt | 0.2 | 0.2 | 0.4 | 0.2 |
| s08.txt | 0.8 | 0.8 | 0.8 | 0.6 |
| s09.txt | 0.2 | 0.0 | 0.2 | 0.8 |
| s10.txt | 0.4 | 0.4 | 0.4 | 0.8 |
| s11.txt | 0.2 | 0.4 | 0.2 | 0.2 |
| s12.txt | 0.4 | 0.4 | 0.4 | 0.4 |
| s13.txt | 0.6 | 0.4 | 0.6 | 0.4 |
| s14.txt | 0.6 | 0.6 | 0.8 | 0.6 |
| s15.txt | 0.0 | 0.0 | 0.0 | 0.0 |
| s16.txt | 0.2 | 0.2 | 0.2 | 0.0 |
| s17.txt | 0.4 | 0.2 | 0.2 | 0.2 |
| s18.txt | 0.4 | 0.4 | 0.4 | 0.2 |
| s19.txt | 0.2 | 0.2 | 0.2 | 0.4 |
| s20.txt | 0.4 | 0.4 | 0.6 | 0.6 |

## Read this first: what this trial is (and isn't)

- **Synthetic trial, not the final evaluation.** The 20 resumes are fictional (2 per role, a mix of
  freshers and 1-3 years' experience), written by Claude; relevance was also judged by Claude
  (blind: shuffled sheet, no method/rank/score shown). Rule fixed before judging: 1 = target role
  (or very close) **and** the level fits (no Senior/Lead/5+ yrs for a fresher; at most ~1 year
  above the candidate's experience) **and** the core stack overlaps. Real resumes and human
  judges are still needed for the final number (`--set eval`).
- 20 resumes x 5 = 100 slots per method, so a difference of 0.03-0.05 is noise.

## Findings

1. **All four methods tie (0.37-0.42).** The app's hybrid ranking is not yet better than
   simply showing the newest postings for the role.
2. **The main failure is seniority, which no method models.** Of the 166 jobs judged not
   relevant, **105 (63%) have senior-level titles** (Senior, Lead, Principal, Staff, VP,
   Manager, ...) vs. 6 of the 100 relevant ones; 42 more state 4+ years. Embeddings and skill
   overlap both rank a "Senior Data Scientist" close to a fresher data-science resume because
   the *topic* matches.
3. Some role pools are thin or skewed: the Backend Developer pool is mostly Java/5+ years,
   so the Python/Django fresher (s15) got 0.0 from every method.

## Next step this points to

Add an **experience-level signal**: read seniority from the job title and "N+ years" in the
text, estimate the resume's experience, and down-rank jobs far above it. Then re-run on
the same resumes (new jobs that enter the top 5 get judged with the same rule).
