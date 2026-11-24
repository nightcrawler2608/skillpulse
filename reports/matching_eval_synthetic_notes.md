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
