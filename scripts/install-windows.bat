@echo off
rem Instalator QuizScanner dla Windows (wersja ze źródeł - alternatywa dla .exe).
rem Wymaga zainstalowanego Pythona 3 (python.org, zaznacz "Add to PATH").
cd /d "%~dp0.."

echo ==================================================
echo   Instalacja QuizScanner (Windows, ze źródeł)
echo ==================================================

where python >nul 2>nul
if errorlevel 1 (
  echo BŁĄD: nie znaleziono Pythona.
  echo Pobierz z https://www.python.org/downloads/ i zaznacz "Add Python to PATH".
  pause
  exit /b 1
)

echo Tworzę środowisko .venv ...
python -m venv .venv
call .venv\Scripts\activate.bat

echo Instaluje zależności ...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo ==================================================
echo   Gotowe. Uruchom aplikacje:  python launcher.py
echo   (albo dwuklik w Uruchom.bat)
echo ==================================================
pause
