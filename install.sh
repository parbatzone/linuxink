#!/bin/bash
# LinuxInk Installer
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

INSTALL_DIR="/opt/linuxink"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${CYAN}${BOLD}LinuxInk Installer${NC}"
echo ""

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Run with sudo: sudo bash install.sh${NC}"; exit 1
fi

step() { echo -e "\n${GREEN}▶${NC} ${BOLD}$*${NC}"; }
ok()   { echo -e "  ${GREEN}✓${NC} $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $*"; }

# ── System packages ────────────────────────────────────────────────────────────
step "Installing system packages..."
if command -v apt-get &>/dev/null; then
    apt-get update -q
    apt-get install -y python3 python3-pip python3-venv \
        libxcb-xinerama0 libxcb-cursor0 libgl1 libglib2.0-0 \
        libfontconfig1 libdbus-1-3 libxcb1 2>/dev/null || warn "Some packages skipped"
    # Try apt PyQt6 first
    apt-get install -y python3-pyqt6 python3-pyqt6.qtsvg 2>/dev/null && \
        ok "PyQt6 installed via apt" || warn "Will use pip/venv for PyQt6"
elif command -v dnf &>/dev/null; then
    dnf install -y python3 python3-pip python3-pyqt6 2>/dev/null || warn "Some packages skipped"
elif command -v pacman &>/dev/null; then
    pacman -Sy --noconfirm python python-pip python-pyqt6 2>/dev/null || warn "Some packages skipped"
fi

# ── Virtual environment fallback ───────────────────────────────────────────────
step "Setting up Python environment..."
VENV="$INSTALL_DIR/venv"

PYTHON=""
for py in python3.12 python3.11 python3.10 python3; do
    if command -v "$py" &>/dev/null && "$py" -c "import sys; exit(0 if sys.version_info>=(3,10) else 1)" 2>/dev/null; then
        PYTHON="$py"; break
    fi
done
[[ -z "$PYTHON" ]] && { echo -e "${RED}Python 3.10+ required${NC}"; exit 1; }
ok "Using $PYTHON"

if ! "$PYTHON" -c "import PyQt6" 2>/dev/null; then
    echo "  Creating virtualenv with PyQt6..."
    "$PYTHON" -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet PyQt6
    LAUNCHER_PYTHON="$VENV/bin/python3"
    ok "PyQt6 installed in virtualenv"
else
    LAUNCHER_PYTHON="$PYTHON"
    ok "PyQt6 already available"
fi

# ── Install files ──────────────────────────────────────────────────────────────
step "Installing to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/." "$INSTALL_DIR/"
ok "Files copied"

# ── Launcher ──────────────────────────────────────────────────────────────────
step "Creating launcher..."
cat > /usr/local/bin/linuxink << LAUNCHER
#!/bin/bash
export QT_QPA_PLATFORM="\${QT_QPA_PLATFORM:-xcb}"
export QT_LOGGING_RULES="*.debug=false;qt.qpa.*=false"
cd "$INSTALL_DIR"
exec "$LAUNCHER_PYTHON" "$INSTALL_DIR/main.py" "\$@"
LAUNCHER
chmod +x /usr/local/bin/linuxink

# ── Desktop entry ──────────────────────────────────────────────────────────────
mkdir -p /usr/share/applications /usr/share/icons/hicolor/256x256/apps
[[ -f "$INSTALL_DIR/assets/logo.png" ]] && \
    cp "$INSTALL_DIR/assets/logo.png" /usr/share/icons/hicolor/256x256/apps/linuxink.png

cat > /usr/share/applications/linuxink.desktop << DESKTOP
[Desktop Entry]
Name=LinuxInk
Comment=Screen Annotation Tool
Exec=linuxink
Icon=linuxink
Terminal=false
Type=Application
Categories=Utility;Graphics;
StartupWMClass=LinuxInk
DESKTOP

update-desktop-database /usr/share/applications/ 2>/dev/null || true
gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true
ok "Desktop entry registered"

echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  ✓  LinuxInk installed!${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Run: ${YELLOW}linuxink${NC}   or search for it in your app menu"
echo ""
