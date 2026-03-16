# Code Standards — Authoritative
schema_version: vaultit-v1.0

## Language Defaults
- Python 3.13, PEP8, runnable, reproducible
- PowerShell only on Windows — never bash, never heredocs
- Front-end: modern testable React, accessibility-aware, CI-friendly

## Data Integrity
- Never drop rows. Flag outliers with boolean columns.
- Preserve all original data through the full pipeline.

## Notebook Structure
Required for every code block without exception:
1. Markdown cell: objective and why
2. Code cell
3. Markdown cell: observations, results, business rationale

## Outlier Consensus Logic
Run all four methods. Consensus flag = majority vote (3 of 4):
1. Mahalanobis distance
2. PCA reconstruction error
3. Isolation Forest
4. One-Class SVM

## Defensive Programming
- Handle missing packages gracefully
- Handle empty bins and sparse features
- Write unit-testable snippets
- Validate inputs at function boundaries

## Reproducibility
- Set random seeds explicitly
- Pin package versions in requirements files
- Document all preprocessing steps in markdown
