#!/usr/bin/env sh
# vaultit-ai installer — POSIX shell
# Usage: curl -fsSL https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/installer/install.sh | sh

set -eu

VAULTIT_HOME="${HOME}/.vaultit"
VAULTIT_BIN="${VAULTIT_HOME}/bin"
REPO_URL="https://github.com/TheRealDataBoss/vaultit.git"
VERSION="0.1.0"

# --- Helpers ---

info()  { printf "\033[36m[vaultit]\033[0m %s\n" "$1"; }
ok()    { printf "\033[32m[vaultit]\033[0m %s\n" "$1"; }
warn()  { printf "\033[33m[vaultit]\033[0m %s\n" "$1"; }
fail()  { printf "\033[31m[vaultit]\033[0m %s\n" "$1" >&2; exit 1; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

# --- Detect OS ---

detect_os() {
    case "$(uname -s)" in
        Linux*)   OS="linux" ;;
        Darwin*)  OS="macos" ;;
        CYGWIN*|MINGW*|MSYS*) OS="windows-wsl" ;;
        *)        OS="unknown" ;;
    esac
    info "Detected OS: ${OS}"
}

# --- Check prerequisites ---

check_prerequisites() {
    if ! command_exists git; then
        fail "git is required but not found. Install git and retry."
    fi
    info "git: $(git --version)"

    if command_exists node; then
        info "node: $(node --version)"
    else
        warn "node not found. npm CLI will not be available. Install Node.js 18+ for full functionality."
    fi

    if command_exists python3; then
        info "python3: $(python3 --version)"
    elif command_exists python; then
        info "python: $(python --version)"
    else
        warn "python not found. Python CLI will not be available. Install Python 3.10+ for full functionality."
    fi
}

# --- Install ---

install_vaultit() {
    info "Installing vaultit-ai v${VERSION} to ${VAULTIT_HOME}"

    if [ -d "${VAULTIT_HOME}" ]; then
        info "Existing installation found. Updating..."
        cd "${VAULTIT_HOME}/src"
        git pull --ff-only origin main || fail "Failed to update vaultit-ai. Check your network connection."
        cd - >/dev/null
    else
        mkdir -p "${VAULTIT_HOME}"
        mkdir -p "${VAULTIT_BIN}"
        info "Cloning vaultit-ai repository..."
        git clone --depth 1 "${REPO_URL}" "${VAULTIT_HOME}/src" || fail "Failed to clone repository. Check your network connection."
    fi

    # Create bin wrapper that delegates to npm or python CLI
    cat > "${VAULTIT_BIN}/vaultit" << 'WRAPPER'
#!/usr/bin/env sh
set -eu
VAULTIT_SRC="${HOME}/.vaultit/src"

if command -v node >/dev/null 2>&1; then
    exec node "${VAULTIT_SRC}/packages/npm/bin/vaultit.js" "$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 -m vaultit.cli "$@"
elif command -v python >/dev/null 2>&1; then
    exec python -m vaultit.cli "$@"
else
    echo "Error: vaultit-ai requires Node.js 18+ or Python 3.10+" >&2
    exit 1
fi
WRAPPER
    chmod +x "${VAULTIT_BIN}/vaultit"

    ok "Binary installed to ${VAULTIT_BIN}/vaultit"
}

# --- Update PATH ---

update_path() {
    SHELL_NAME="$(basename "${SHELL:-/bin/sh}")"
    PATH_LINE="export PATH=\"${VAULTIT_BIN}:\$PATH\""

    case "${SHELL_NAME}" in
        zsh)  RC_FILE="${HOME}/.zshrc" ;;
        bash) RC_FILE="${HOME}/.bashrc" ;;
        fish)
            RC_FILE="${HOME}/.config/fish/config.fish"
            PATH_LINE="set -gx PATH ${VAULTIT_BIN} \$PATH"
            ;;
        *)    RC_FILE="${HOME}/.profile" ;;
    esac

    if [ -f "${RC_FILE}" ] && grep -qF "${VAULTIT_BIN}" "${RC_FILE}" 2>/dev/null; then
        info "PATH already configured in ${RC_FILE}"
    else
        printf "\n# vaultit-ai\n%s\n" "${PATH_LINE}" >> "${RC_FILE}"
        ok "Added ${VAULTIT_BIN} to PATH in ${RC_FILE}"
    fi

    # Make it available in current session
    export PATH="${VAULTIT_BIN}:${PATH}"
}

# --- Verify ---

verify_installation() {
    if command_exists vaultit; then
        ok "Installation verified: vaultit is on PATH"
    else
        warn "vaultit is installed but not yet on PATH. Restart your shell or run:"
        info "  export PATH=\"${VAULTIT_BIN}:\$PATH\""
    fi
}

# --- Main ---

main() {
    info "vaultit-ai installer v${VERSION}"
    info "================================="
    detect_os
    check_prerequisites
    install_vaultit
    update_path
    verify_installation

    echo ""
    ok "vaultit-ai v${VERSION} installed successfully!"
    echo ""
    info "Next steps:"
    info "  1. cd into your project directory"
    info "  2. Run: vaultit init"
    info "  3. Run: vaultit sync"
    echo ""
    info "Documentation: https://github.com/TheRealDataBoss/vaultit"
}

main
