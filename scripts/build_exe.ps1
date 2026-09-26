# Build the current desktop version using the project spec.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$projectPython = Join-Path $projectRoot '.build-venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) { $projectPython = (Get-Command python -ErrorAction Stop).Source }
$env:PYTHONUTF8 = '1'
& $projectPython -m PyInstaller --noconfirm QuizScanner.spec
if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed.' }
