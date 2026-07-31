# Buduje jednoplikowy QuizScanner.exe (Windows).
# Wymaga: Python + zainstalowane zaleznosci + PyInstaller.
#   pip install -r requirements.txt
#   pip install pyinstaller
# Uruchomienie:  powershell -ExecutionPolicy Bypass -File build_exe.ps1

Set-Location $PSScriptRoot

Write-Host "Buduje QuizScanner.exe ..." -ForegroundColor Cyan
python -m PyInstaller --onefile --noconsole --name QuizScanner `
  --add-data "web;web" `
  --add-data "quizzes;quizzes" `
  --add-data "students.csv;." `
  --hidden-import generate_cards `
  --hidden-import aruco_common `
  --noconfirm launcher.py

if (Test-Path "dist\QuizScanner.exe") {
    $mb = (Get-Item "dist\QuizScanner.exe").Length / 1MB
    Write-Host ("Gotowe: dist\QuizScanner.exe  ({0:N1} MB)" -f $mb) -ForegroundColor Green
} else {
    Write-Host "Build sie nie powiodl." -ForegroundColor Red
}
