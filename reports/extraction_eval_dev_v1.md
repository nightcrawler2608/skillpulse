# Skill extraction evaluation

Date: 2026-11-24 · Jobs labelled: 144 · Skills in dictionary: 249 · True job-skill pairs: 329

| Method | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| Dictionary only (Layer A) | 0.866 | 0.729 | 0.792 | 240 | 37 | 89 |
| Dictionary + embeddings @ 0.70 | 0.596 | 0.827 | 0.693 | 272 | 184 | 57 |
| Dictionary + embeddings @ 0.75 | 0.695 | 0.802 | 0.745 | 264 | 116 | 65 |
| Dictionary + embeddings @ 0.80 | 0.767 | 0.781 | 0.774 | 257 | 78 | 72 |
| Dictionary + embeddings @ 0.85 | 0.817 | 0.760 | 0.787 | 250 | 56 | 79 |
| Dictionary + embeddings @ 0.90 | 0.850 | 0.742 | 0.792 | 244 | 43 | 85 |

## Layer A: most missed skills (false negatives)

- Teamwork: 12
- Artificial Intelligence: 10
- Leadership: 8
- Model Deployment: 5
- Responsive Design: 5
- Data Analysis: 4
- Cybersecurity: 3
- Requirements Gathering: 3
- Cloud Computing: 3
- Data Quality: 2

## Layer A: most wrongly added skills (false positives)

- Teamwork: 7
- Linux: 4
- Leadership: 3
- Cloud Computing: 3
- Communication: 2
- Algorithms: 2
- AI Agents: 2
- Artificial Intelligence: 2
- Oracle Database: 2
- Agile: 2

## Skills labellers needed that are not in the dictionary

- master data management: 2
- blockchain: 1
- qa: 1
- data integration: 1
- llmops: 1
- anomaly detection: 1
- fraud detection: 1
- domo: 1
- clean code: 1
- reinforcement learning: 1
- sft: 1
- dpo: 1
- model risk: 1
- model validation: 1
- video generation: 1
- unity: 1
- distributed databases: 1
- newsql: 1
- dataflow: 1
- teradata: 1
