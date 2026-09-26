#!/usr/bin/env bash
# Instalator QuizScanner dla Linux / macOS.
# Tworzy środowisko wirtualne, instaluje zależności i skrypt startowy.
#
# Użycie:
#   chmod +x scripts/install.sh
#   ./scripts/install.sh
set -e
cd "$(dirname "$0")/.."     # skrypt leży w scripts/, pracujemy w katalogu projektu

echo "=================================================="
echo "  Instalacja QuizScanner (Linux / macOS)"
echo "=================================================="

# 1. Python 3
if ! command -v python3 >/dev/null 2>&1; then
  echo "BŁĄD: brak Python 3."
  echo "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
  echo "  Fedora:        sudo dnf install python3 python3-pip"
  echo "  macOS:         brew install python  (lub pobierz z python.org)"
  exit 1
fi
echo "Python: $(python3 --version)"

# 2. Środowisko wirtualne
echo "Tworzę środowisko .venv ..."
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

# 3. Zależności
echo "Instaluje zależności (opencv, numpy, pillow) ..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt

# 4. Skrypt startowy
cat > start.sh <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate
# Serwer + automatyczne otwarcie przeglądarki (panel nauczyciela).
python -m quizscanner "$@"
EOF
chmod +x start.sh

echo ""
echo "=================================================="
echo "  Gotowe. Uruchom aplikacje poleceniem:"
echo "      ./start.sh"
echo "  Inna kamera:   ./start.sh --camera 1"
echo "=================================================="
echo "Uwaga (Linux): jeśli kamera nie działa, sprawdź uprawnienia"
echo "do /dev/video0 (grupa 'video')."
