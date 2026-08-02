# Buduje jednoplikowy plik QuizScanner.exe (Windows).
# Wymaga: Python + zainstalowane zależności + PyInstaller.
#   pip install -r requirements.txt
#   pip install pyinstaller
# Uruchomienie:  powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
#
# WAŻNE: plik wynikowy MA w nazwie numer wersji (np. QuizScanner-v3.0.0.exe).
# Numer bierzemy z quizscanner/__init__.py — jedno miejsce prawdy; wbudowany
# aktualizator porównuje wydanie z GitHuba właśnie z nim.

Set-Location (Join-Path $PSScriptRoot "..")

$init = Get-Content "quizscanner\__init__.py" -Raw
if ($init -notmatch 'VERSION\s*=\s*"([^"]+)"') {
    Write-Host "Nie mogę odczytać VERSION z quizscanner\__init__.py" -ForegroundColor Red
    exit 1
}
$Version = $Matches[1]
$Name = "QuizScanner-v$Version"

Write-Host "Buduję $Name.exe ..." -ForegroundColor Cyan
# Uwaga: w .exe zasoby leżą płasko — web trafia do <_MEIPASS>\web, dane do <_MEIPASS>\data
# (tak samo jak wylicza je quizscanner/paths.py).
python -m PyInstaller --onefile --noconsole --name $Name `
  --add-data "quizscanner\web;web" `
  --add-data "data\quizzes;data\quizzes" `
  --add-data "data\students.csv;data" `
  --hidden-import quizscanner.cards `
  --hidden-import quizscanner.aruco `
  --hidden-import quizscanner.i18n `
  --hidden-import quizscanner.overlay `
  --hidden-import quizscanner.report `
  --hidden-import quizscanner.updater `
  --noconfirm launcher.py

if (Test-Path "dist\$Name.exe") {
    $mb = (Get-Item "dist\$Name.exe").Length / 1MB
    Write-Host ("Gotowe: dist\$Name.exe  ({0:N1} MB)" -f $mb) -ForegroundColor Green
    Write-Host "Wgraj do Releases dokładnie pod tą nazwą (z numerem wersji)." -ForegroundColor Green
    Write-Host "Tag wydania musi brzmieć v$Version — po nim aktualizator poznaje nowszą wersję." -ForegroundColor Green
} else {
    Write-Host "Budowanie nie powiodło się." -ForegroundColor Red
}
