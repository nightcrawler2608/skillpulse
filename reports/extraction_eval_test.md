# Skill extraction evaluation: test set

Date: 2026-11-24 · Jobs labelled: 90 · Skills in dictionary: 249 · True job-skill pairs: 186

| Method | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Dictionary only (Layer A) | 0.936 | 0.860 | 0.896 | 160 | 11 | 26 |
| Dictionary + embeddings @ 0.70 | 0.639 | 0.903 | 0.748 | 168 | 95 | 18 |
| Dictionary + embeddings @ 0.75 | 0.743 | 0.887 | 0.809 | 165 | 57 | 21 |
| Dictionary + embeddings @ 0.80 | 0.841 | 0.882 | 0.861 | 164 | 31 | 22 |
| Dictionary + embeddings @ 0.85 | 0.915 | 0.871 | 0.893 | 162 | 15 | 24 |
| Dictionary + embeddings @ 0.90 | 0.925 | 0.866 | 0.894 | 161 | 13 | 25 |

## Layer A: most missed skills (false negatives)

- Requirements Gathering: 5
- REST APIs: 4
- Data Analysis: 3
- Cloud Computing: 2
- Teamwork: 2
- Data Modeling: 1
- JavaScript: 1
- Data Quality: 1
- Artificial Intelligence: 1
- Data Cleaning: 1

## Layer A: most wrongly added skills (false positives)

- Teamwork: 2
- Cloud Computing: 2
- Java: 1
- Algorithms: 1
- SAP: 1
- REST APIs: 1
- Market Research: 1
- Machine Learning: 1
- Data Analysis: 1

## Skills labellers needed that are not in the dictionary

- streaming ingestion: 1
- optimizely: 1
- cms: 1
- data profiling: 1
- attribution modeling: 1
- marketing mix modeling: 1
- clinical data: 1
- chatbots: 1
- microsoft bi: 1
- salesforce data cloud: 1
- cpq: 1
- microsoft fabric: 1
- function calling: 1
- guardrails: 1
- sigma: 1
- dataiku: 1
- uat: 1
- stress testing: 1
- market risk: 1
- prd: 1
