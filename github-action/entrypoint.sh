#!/usr/bin/env bash
set -euo pipefail

# vaultit-ai GitHub Action entrypoint
# Syncs STATE_VECTOR.json and HANDOFF.md to the vaultit bridge repo

TIMESTAMP="$(date -u +"%Y-%m-%d %H:%M UTC")"
BRIDGE_DIR="$(mktemp -d)"

trap 'rm -rf "${BRIDGE_DIR}"' EXIT

# --- Step 1: Validate STATE_VECTOR.json ---

echo "::group::Validating STATE_VECTOR.json"

STATE_FILE="${STATE_VECTOR_PATH}"

if [ ! -f "${STATE_FILE}" ]; then
    echo "::error::STATE_VECTOR.json not found at ${STATE_FILE}"
    exit 1
fi

# Basic field validation — check required fields exist
REQUIRED_FIELDS='["schema_version","project","project_type","local_path","state_machine_status","active_task_id","active_task_title","current_blocker","last_verified_state","gates","last_updated"]'

if command -v jq >/dev/null 2>&1; then
    for field in schema_version project project_type local_path state_machine_status last_verified_state gates last_updated; do
        if ! jq -e ".${field}" "${STATE_FILE}" >/dev/null 2>&1; then
            echo "::error::STATE_VECTOR.json missing required field: ${field}"
            exit 1
        fi
    done
    echo "All required fields present"

    # Validate schema_version pattern
    SCHEMA_VER="$(jq -r '.schema_version' "${STATE_FILE}")"
    if ! echo "${SCHEMA_VER}" | grep -qE '^vaultit-v[0-9]+\.[0-9]+$'; then
        echo "::error::Invalid schema_version: ${SCHEMA_VER}. Expected pattern: vaultit-v<major>.<minor>"
        exit 1
    fi
    echo "Schema version: ${SCHEMA_VER}"
else
    echo "::warning::jq not available. Skipping field validation."
fi

echo "::endgroup::"

# --- Step 2: Clone bridge repo ---

echo "::group::Cloning bridge repo"

BRIDGE_URL="https://x-access-token:${GH_TOKEN}@github.com/${VAULTIT_REPO}.git"

git clone --depth 1 "${BRIDGE_URL}" "${BRIDGE_DIR}" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "::error::Failed to clone bridge repo: ${VAULTIT_REPO}"
    exit 1
fi

echo "Cloned ${VAULTIT_REPO}"
echo "::endgroup::"

# --- Step 3: Copy state files ---

echo "::group::Copying state files"

TARGET_DIR="${BRIDGE_DIR}/projects/${PROJECT_NAME}"
mkdir -p "${TARGET_DIR}"

cp "${STATE_FILE}" "${TARGET_DIR}/STATE_VECTOR.json"
echo "Copied STATE_VECTOR.json"

if [ -f "${HANDOFF_PATH}" ]; then
    cp "${HANDOFF_PATH}" "${TARGET_DIR}/HANDOFF.md"
    echo "Copied HANDOFF.md"
fi

# Copy NEXT_TASK.md if it exists alongside HANDOFF.md
HANDOFF_DIR="$(dirname "${HANDOFF_PATH}")"
if [ -f "${HANDOFF_DIR}/NEXT_TASK.md" ]; then
    cp "${HANDOFF_DIR}/NEXT_TASK.md" "${TARGET_DIR}/NEXT_TASK.md"
    echo "Copied NEXT_TASK.md"
fi

echo "::endgroup::"

# --- Step 4: Commit and push ---

echo "::group::Committing and pushing"

cd "${BRIDGE_DIR}"

git config user.name "vaultit-ai[bot]"
git config user.email "vaultit-ai[bot]@users.noreply.github.com"

git add .

COMMIT_MSG="chore(vaultit): sync ${PROJECT_NAME} -- ${TIMESTAMP}"

if git diff --cached --quiet; then
    echo "No changes to commit for ${PROJECT_NAME}"
    echo "::endgroup::"
    exit 0
fi

git commit -m "${COMMIT_MSG}"
git push origin main

COMMIT_SHA="$(git rev-parse --short HEAD)"
echo "Pushed: ${COMMIT_MSG}"
echo "Commit: ${COMMIT_SHA}"

echo "::endgroup::"

# --- Output ---

echo "commit_sha=${COMMIT_SHA}" >> "${GITHUB_OUTPUT:-/dev/null}"
echo "synced=true" >> "${GITHUB_OUTPUT:-/dev/null}"

echo "::notice::VaultIt sync complete for ${PROJECT_NAME} (${COMMIT_SHA})"
