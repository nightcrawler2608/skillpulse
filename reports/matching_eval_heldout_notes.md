## What this is

- **Held-out synthetic set: the fair check.** 20 *new* fictional resumes (2 per role, freshers
  and 2-4.5 years; most use date ranges like "Jul 2023 - Present"), written **before** the
  round-3 changes and not looked at while tuning. All 6 methods were run once and all 305
  pooled pairs judged blind in one shuffled sheet, with the same written rule as the dev set.
- Still synthetic and judged by Claude, so this is a trial, not the final user evaluation.
- Note: `hybrid+level` here already uses the round-3 level rules (the code changed before
  this set was run), so it equals `full` minus the internship and tech-stack steps.

## Findings

1. **Experience level is the big win: 0.48 -> 0.76** (+0.28). Better on 15 of 20 resumes,
   worse on 0 (two-sided sign test on 15 vs 0: p ~ 0.00006). It held up on resumes it was never tuned on.
2. **The tech-stack and internship steps added nothing measurable:** `full` and `hybrid+level`
   produced the same top 5 for 19 of 20 resumes. They are kept because they are sensible and
   did no harm, but no improvement is claimed for them.
3. **What's left is mostly a shortage of suitable jobs, not ranking.** The Python backend
   developer (h16) gets the few Python jobs in the database and then nothing suitable remains;
   the Java backend fresher (h15) finds mostly 4+ year Java roles. More job data (more
   search terms per role, more days of collection) is the next lever, not more re-ranking.
4. Remaining ranking misses: wrong specialisation (clinical programming, embedded, "Alexa
   Connections" asking to "lead"), which neither meaning nor skills separate well.
