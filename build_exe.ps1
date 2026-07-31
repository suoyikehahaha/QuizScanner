# Buduje jednoplikowy QuizScanner.exe (Windows).
# Wymaga: Python + zainstalowane zaleznosci + PyInstaller.
#   pip install -r requirements.txt
#   pip install pyinstaller
# Uruchomienie:  powershell -ExecutionPolicy Bypass -File build_exe.ps1
#
# WAZNE: plik wynikowy MA w nazwie numer wersji (np. QuizScanner-v1.1.0.exe).
# Podnies $Version przy kazdym nowym wydaniu i pod ta nazwa wgraj do Releases.

Set-Location $PSScriptRoot

$Version = "1.1.0"
$Name = "QuizScanner-v$Version"

Write-Host "Buduje $Name.exe ..." -ForegroundColor Cyan
python -m PyInstaller --onefile --noconsole --name $Name `
  --add-data "web;web" `
  --add-data "quizzes;quizzes" `
  --add-data "students.csv;." `
  --hidden-import generate_cards `
  --hidden-import aruco_common `
  --noconfirm launcher.py

if (Test-Path "dist\$Name.exe") {
    $mb = (Get-Item "dist\$Name.exe").Length / 1MB
    Write-Host ("Gotowe: dist\$Name.exe  ({0:N1} MB)" -f $mb) -ForegroundColor Green
    Write-Host "Wgraj do Releases pod ta wlasnie nazwa (z wersja)." -ForegroundColor Green
} else {
    Write-Host "Build sie nie powiodl." -ForegroundColor Red
}
