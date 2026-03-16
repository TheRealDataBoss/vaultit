# Modeling Standards — Authoritative
schema_version: vaultit-v1.0

## Required Benchmarks
Every model evaluation must include:
- AUC (ROC)
- Calibration plot
- KS statistic
- Lorenz curve / Gini coefficient
- Lift charts

## Orchestrator Contract
Auto-produce without being asked:
- ROC and PR curves
- Calibration curve
- Learning curves
- PDP, ICE, ALE plots
- Feature importance
- SHAP and LIME explainability

## Thresholding
No manual thresholding unless Steven explicitly requests it.

## Business Interpretation
Every result section must include explicit business interpretation. Numbers alone are insufficient.

## Row Preservation
Never drop rows. Ever. Flag anomalies. Preserve originals.

## Novelty Detection
Cross-validated One-Class SVM when requested. Document contamination parameter choice.

## Outlier Detection
Consensus method — see CODE_STANDARDS.md. Never rely on single method.
