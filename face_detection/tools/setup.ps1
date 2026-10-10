param(
    [ValidateSet('Flash','Full')][string]$Mode = 'Flash',
    [string]$Python = '',
    [switch]$Offline
)
$ErrorActionPreference = 'Stop'
$faceRoot = Split-Path -Parent $PSScriptRoot
if (-not $Python) {
    $platformPython = Join-Path $env:USERPROFILE '.platformio/penv/Scripts/python.exe'
    if (Test-Path -LiteralPath $platformPython) { $Python = $platformPython }
    else { $Python = (Get-Command python -ErrorAction Stop).Source }
}
& $Python -c "import sys,struct; assert sys.version_info[:2]==(3,11) and struct.calcsize('P')==8, 'Use Python 3.11 64-bit'"
if ($LASTEXITCODE -ne 0) { throw 'Pass -Python with a Python 3.11 64-bit executable.' }
New-Item -ItemType Directory -Force -Path (Join-Path $faceRoot 'logs'), (Join-Path $faceRoot 'data') | Out-Null
function Install-Environment([string]$name, [string]$requirements) {
    $directory = Join-Path $faceRoot $name
    $runtime = Join-Path $directory 'Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $runtime)) {
        & $Python -m venv $directory
        if ($LASTEXITCODE -ne 0) { throw "Could not create $name" }
    }
    if ($Offline) { return }
    if ($name -eq '.venv') {
        & $runtime -m pip install --index-url https://download.pytorch.org/whl/cpu 'torch==2.2.2+cpu' 'torchvision==0.17.2+cpu'
        if ($LASTEXITCODE -ne 0) { throw 'PyTorch CPU installation failed.' }
    }
    & $runtime -m pip install -r (Join-Path $faceRoot $requirements)
    if ($LASTEXITCODE -ne 0) { throw "Installation failed: $name" }
}
Install-Environment '.vela-venv' 'requirements-vela-lock.txt'
if ($Mode -eq 'Full') {
    Install-Environment '.venv' 'requirements-inference-lock.txt'
    Install-Environment '.convert-venv' 'requirements-conversion-lock.txt'
    $assetArgs = @((Join-Path $PSScriptRoot 'bootstrap_assets.py'))
    if ($Offline) { $assetArgs += '--offline' }
    & $Python @assetArgs
    if ($LASTEXITCODE -ne 0) { throw 'SDK/toolchain setup failed.' }
}
Write-Output "Setup completed: $Mode. Offline mode skips pip installations."
