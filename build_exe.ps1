# Buduje jednoplikowy plik QuizScanner.exe (Windows).
# Wymaga: Python + zainstalowane zależności + PyInstaller.
#   pip install -r requirements.txt
#   pip install pyinstaller
# Uruchomienie:  powershell -ExecutionPolicy Bypass -File build_exe.ps1
#
# WAŻNE: plik wynikowy MA w nazwie numer wersji (np. QuizScanner-v2.0.1.exe).
# Podnieś $Version przy każdym nowym wydaniu i pod tą nazwą wgraj do Releases.

Set-Location $PSScriptRoot

$Version = "2.0.1"
$Name = "QuizScanner-v$Version"

Write-Host "Buduję $Name.exe ..." -ForegroundColor Cyan
python -m PyInstaller --onefile --noconsole --name $Name `
  --add-data "web;web" `
  --add-data "quizzes;quizzes" `
  --add-data "students.csv;." `
  --hidden-import generate_cards `
  --hidden-import aruco_common `
  --hidden-import i18n `
  --hidden-import overlay `
  --noconfirm launcher.py

if (Test-Path "dist\$Name.exe") {
    $mb = (Get-Item "dist\$Name.exe").Length / 1MB
    Write-Host ("Gotowe: dist\$Name.exe  ({0:N1} MB)" -f $mb) -ForegroundColor Green
    Write-Host "Wgraj do Releases dokładnie pod tą nazwą (z numerem wersji)." -ForegroundColor Green
} else {
    Write-Host "Budowanie nie powiodło się." -ForegroundColor Red
}
