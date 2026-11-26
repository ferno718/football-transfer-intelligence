# Project Report Notes — Football Transfer Intelligence

## 1. Problem statement
Football recruitment teams work with large player datasets but need a repeatable method for discovering, profiling and comparing players while retaining an audit trail of analytical decisions.

## 2. Objectives
1. Ingest a football player performance dataset into a normalized SQLite database.
2. Engineer per-90 and percentile-based indicators.
3. Build role-aware impact scoring with a minutes-based reliability adjustment.
4. Provide DataMB-inspired radar and two-dimensional scouting views.
5. Discover similar player profiles using standardized cosine similarity.
6. Maintain a persistent recruitment shortlist.
7. Capture manual scouting and transfer-planning inputs in SQLite.
8. Save player analysis snapshots and comparison history for auditability.
9. Provide DB Browser for SQLite compatibility for examiner inspection.

## 3. Database design
- `players`: normalized source data.
- `analyses`: analytical snapshots.
- `comparison_history`: saved comparison sessions.
- `shortlist`: recruitment workflow state.
- `user_inputs`: manually entered scouting and planning data.
- `source_registry`: source provenance.

## 4. Analytics
Per-90 measures are calculated from minutes. Percentiles are calculated within the loaded sample. The impact score uses role-sensitive weights. A reliability adjustment reduces the influence of small-minute samples.

Similarity uses standardized performance features and cosine similarity. The ExtraTrees component is explicitly exploratory and does not claim to predict transfer fees.

## 5. UI/UX
The interface is a dark professional analytics workspace with persistent navigation, KPI cards, interactive Plotly visualizations, radar profiles, filters, structured forms and database audit views.

## 6. Data governance
Source-derived performance data is kept separate from manually entered transfer-planning data. Source URL and provenance are recorded. Licensing and upstream terms should be verified before redistribution.
