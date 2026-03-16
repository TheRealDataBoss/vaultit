# vaultit-ai installer — PowerShell
# Usage: irm https://raw.githubusercontent.com/TheRealDataBoss/vaultit/main/installer/install.ps1 | iex

$ErrorActionPreference = "Stop"

$VaultItHome = Join-Path $env:USERPROFILE ".vaultit"
$VaultItBin  = Join-Path $VaultItHome "bin"
$VaultItSrc  = Join-Path $VaultItHome "src"
$RepoUrl       = "https://github.com/TheRealDataBoss/vaultit.git"
$Version       = "0.1.0"

function Write-Info  { param($Msg) Write-Host "[vaultit] $Msg" -ForegroundColor Cyan }
function Write-Ok    { param($Msg) Write-Host "[vaultit] $Msg" -ForegroundColor Green }
function Write-Warn  { param($Msg) Write-Host "[vaultit] $Msg" -ForegroundColor Yellow }

function Test-Command {
    param($Name)
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

# --- Check prerequisites ---

Write-Info "vaultit-ai installer v$Version"
Write-Info "================================="

if (-not (Test-Command "git")) {
    Write-Error "git is required but not found. Install git and retry."
    exit 1
}
Write-Info "git: $(git --version)"

if (Test-Command "node") {
    Write-Info "node: $(node --version)"
} else {
    Write-Warn "node not found. npm CLI will not be available. Install Node.js 18+ for full functionality."
}

if (Test-Command "python") {
    Write-Info "python: $(python --version 2>&1)"
} else {
    Write-Warn "python not found. Python CLI will not be available. Install Python 3.10+ for full functionality."
}

# --- Install ---

Write-Info "Installing vaultit-ai v$Version to $VaultItHome"

if (Test-Path $VaultItSrc) {
    Write-Info "Existing installation found. Updating..."
    Push-Location $VaultItSrc
    git pull --ff-only origin main
    if ($LASTEXITCODE -ne 0) {
        Pop-Location
        Write-Error "Failed to update vaultit-ai. Check your network connection."
        exit 1
    }
    Pop-Location
} else {
    New-Item -ItemType Directory -Force -Path $VaultItHome | Out-Null
    New-Item -ItemType Directory -Force -Path $VaultItBin  | Out-Null

    Write-Info "Cloning vaultit-ai repository..."
    git clone --depth 1 $RepoUrl $VaultItSrc
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to clone repository. Check your network connection."
        exit 1
    }
}

# Create bin wrapper script
$WrapperPath = Join-Path $VaultItBin "vaultit.ps1"
$WrapperContent = @'
$VaultItSrc = Join-Path $env:USERPROFILE ".vaultit\src"
if (Get-Command node -ErrorAction SilentlyContinue) {
    & node (Join-Path $VaultItSrc "packages\npm\bin\vaultit.js") @args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m vaultit.cli @args
} else {
    Write-Error "vaultit-ai requires Node.js 18+ or Python 3.10+"
    exit 1
}
'@
Set-Content -Path $WrapperPath -Value $WrapperContent -Encoding UTF8

# Create cmd wrapper for non-PowerShell terminals
$CmdWrapperPath = Join-Path $VaultItBin "vaultit.cmd"
$CmdContent = "@echo off`r`npowershell -NoProfile -ExecutionPolicy Bypass -File `"%~dp0vaultit.ps1`" %*"
Set-Content -Path $CmdWrapperPath -Value $CmdContent -Encoding UTF8

Write-Ok "Binary installed to $VaultItBin"

# --- Update PATH ---

$CurrentUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($CurrentUserPath -notlike "*$VaultItBin*") {
    $NewPath = "$VaultItBin;$CurrentUserPath"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    Write-Ok "Added $VaultItBin to user PATH"
} else {
    Write-Info "PATH already contains $VaultItBin"
}

# Add to current session
if ($env:Path -notlike "*$VaultItBin*") {
    $env:Path = "$VaultItBin;$env:Path"
}

# --- Verify ---

if (Test-Command "vaultit") {
    Write-Ok "Installation verified: vaultit is on PATH"
} else {
    Write-Warn "vaultit is installed but may not be on PATH until you restart your terminal."
}

Write-Host ""
Write-Ok "vaultit-ai v$Version installed successfully!"
Write-Host ""
Write-Info "Next steps:"
Write-Info "  1. cd into your project directory"
Write-Info "  2. Run: vaultit init"
Write-Info "  3. Run: vaultit sync"
Write-Host ""
Write-Info "Documentation: https://github.com/TheRealDataBoss/vaultit"
