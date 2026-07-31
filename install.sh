#!/usr/bin/env bash
# Instalator QuizScanner dla Linux / macOS.
# Tworzy srodowisko wirtualne, instaluje zaleznosci i skrypt startowy.
#
# Uzycie:
#   chmod +x install.sh
#   ./install.sh
set -e
cd "$(dirname "$0")"

echo "=================================================="
echo "  Instalacja QuizScanner (Linux / macOS)"
echo "=================================================="

# 1. Python 3
if ! command -v python3 >/dev/null 2>&1; then
  echo "BLAD: brak Python 3."
  echo "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
  echo "  Fedora:        sudo dnf install python3 python3-pip"
  echo "  macOS:         brew install python  (lub pobierz z python.org)"
  exit 1
fi
echo "Python: $(python3 --version)"

# 2. Srodowisko wirtualne
echo "Tworze srodowisko .venv ..."
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

# 3. Zaleznosci
echo "Instaluje zaleznosci (opencv, numpy, pillow) ..."
python -m pip install --upgrade pip >/dev/null
python -m pip install -r requirements.txt

# 4. Skrypt startowy
cat > start.sh <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate
# Serwer + automatyczne otwarcie przegladarki (panel nauczyciela).
python app.py "$@"
EOF
chmod +x start.sh

echo ""
echo "=================================================="
echo "  Gotowe. Uruchom aplikacje poleceniem:"
echo "      ./start.sh"
echo "  Inna kamera:   ./start.sh --camera 1"
echo "=================================================="
echo "Uwaga (Linux): jesli kamera nie dziala, sprawdz uprawnienia"
echo "do /dev/video0 (grupa 'video')."
