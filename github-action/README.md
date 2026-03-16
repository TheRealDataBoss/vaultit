# VaultIt — GitHub Action

Automatically sync your project's STATE_VECTOR.json and HANDOFF.md to your vaultit bridge repo on every push, merge, or release.

## Usage

Add to `.github/workflows/vaultit-sync.yml`:

```yaml
name: VaultIt Sync

on:
  push:
    branches: [main]
    paths:
      - 'handoff/STATE_VECTOR.json'
      - 'docs/HANDOFF.md'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: TheRealDataBoss/vaultit/github-action@main
        with:
          vaultit_repo: 'TheRealDataBoss/vaultit'
          github_token: ${{ secrets.VAULTIT_TOKEN }}
          project_name: 'my-project'
```

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `vaultit_repo` | Yes | — | Your bridge repo (e.g. `TheRealDataBoss/vaultit`) |
| `github_token` | Yes | — | Token with write access to the bridge repo |
| `project_name` | Yes | — | Project slug (directory name in bridge repo) |
| `state_vector_path` | No | `handoff/STATE_VECTOR.json` | Path to STATE_VECTOR.json |
| `handoff_path` | No | `docs/HANDOFF.md` | Path to HANDOFF.md |

## Outputs

| Output | Description |
|---|---|
| `commit_sha` | Short SHA of the sync commit |
| `synced` | `true` if changes were pushed, absent if no changes |

## Token Setup

1. Create a Personal Access Token (classic) with `repo` scope
2. Add it as a repository secret named `VAULTIT_TOKEN`
3. The token must have write access to your bridge repo

## What It Does

1. Validates STATE_VECTOR.json has all required fields
2. Validates schema_version matches expected pattern
3. Clones your bridge repo
4. Copies STATE_VECTOR.json, HANDOFF.md, and NEXT_TASK.md (if present) to `projects/<project_name>/`
5. Commits and pushes with message: `chore(vaultit): sync <project> -- <timestamp>`
6. Skips commit if no files changed
