# Steven Wazlavek — Operator Profile
schema_version: vaultit-v1.0

## Identity
- Full name: Steven Wazlavek
- Handle: @theRealDataBoss
- Email: steven@originami.com
- Organization: Originami.com

## Role
Senior Data Scientist and research-level quantitative analyst. Enrolled in MIT Data Science & Machine Learning certification. Objective: ship production-grade, reproducible, research-quality analytics and ML solutions that demonstrate rigor, interpretability, and business impact.

## Primary Machine
Predator Helios 16 — i9 14th Gen, NVidia 4070, 64GB RAM
OS: Windows. Shell: PowerShell only. Never bash. Never heredocs.

## Environment
- Python 3.13, Django 5, .venv
- Node.js / React / Three.js (R3F) for visualization projects
- AWS EC2 keypair: Originami (RSA .pem)
- Ubuntu VM: C:\Users\swazl\OneDrive\Documents\Virtual Machines\Ubuntu 64-bit (Hadoop only)

## Key Paths
- Data science / ML work: C:\Users\Steven\Pedipro\pipeline
- Django portfolio: C:\Users\Steven\Portfolio
- 3dpie chart project: C:\Users\Steven\Chart generator\repo\git
- VaultIt: C:\Users\Steven\vaultit

## Response Style
PhD-level, evidence-backed, defensible answers. Short conclusion first, then assumptions, methods, results, limitations, next steps. Dense technical paragraphs. No fluff. Quantify uncertainty. Cite papers or state what evidence is missing.

## Code Standards
- PEP8, runnable, reproducible
- Never drop rows — flag outliers with boolean columns
- Notebook structure: markdown(objective) → code → markdown(observations + business rationale)
- Outlier consensus: Mahalanobis distance + PCA reconstruction error + Isolation Forest + One-Class SVM — majority vote flag
- Defensive programming: handle missing packages, empty bins, sparse features
- PowerShell only on Windows

## Visualization Standards
- Colormap: coolwarm for all value-to-color mappings
- Palette: PALETTE = {"blue":"#4878CF","orange":"#E8944A","green":"#6ACC65","red":"#D65F5F","gray":"#B0B0B0"}
- Always include labeled colorbars with numeric metrics (AUCs, CIs, mu±SD)
- Publication and portfolio quality only — no decorative elements
- No interactive plots unless Steven explicitly requests
- SHAP: if feature has 3 or fewer unique values, replace dependence plots with mean-|SHAP| bar charts sorted by importance

## Modeling Standards
- Benchmarks required: AUC, calibration, KS statistic, Lorenz/Gini, lift charts
- Orchestrator auto-produces: ROC/PR curves, calibration, learning curves, PDP/ICE/ALE, feature importance, SHAP/LIME
- No manual thresholding unless Steven explicitly requests
- Every result requires explicit business interpretation section
- Novelty detection: cross-validated One-Class SVM when requested

## Communication Rules
- Direct, decisive, technical
- No sycophancy
- Concrete next steps or ranked options always
- Short inline emojis only if Steven leads casual tone
- Token-object pattern for large specs — short IDs, not repeated full specs
- Phased prompts: Plan → Implement → Expand
