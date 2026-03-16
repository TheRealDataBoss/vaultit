# Visualization Standards — Authoritative
schema_version: vaultit-v1.0

## Colormap
coolwarm for all value-to-color mappings.

## Palette
PALETTE = {
  "blue": "#4878CF",
  "orange": "#E8944A",
  "green": "#6ACC65",
  "red": "#D65F5F",
  "gray": "#B0B0B0"
}
Always define PALETTE explicitly at top of notebook or script.

## Colorbars and Legends
- Always labeled
- Always include numeric metrics: AUCs, CIs, mu±SD
- No unlabeled color scales

## Quality Bar
- Publication and portfolio grade on every output
- No decorative or gratuitous visual elements
- No interactive plots unless Steven explicitly requests interactivity

## SHAP Rules
- If a feature has 3 or fewer unique values: replace SHAP dependence plots with mean-|SHAP| bar charts
- Bar charts sorted by importance, annotated with numeric values

## Plot Sizing
- Default: sufficient resolution for portfolio display
- Always save as PNG at minimum 150 DPI for portfolio outputs
