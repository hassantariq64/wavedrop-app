#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  WaveDrop — Setup Script (macOS)
#  Installs: Homebrew, Python, ffmpeg, yt-dlp, customtkinter
# ─────────────────────────────────────────────────────────────

set -e
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
RESET="\033[0m"

echo ""
echo -e "${BOLD}◉ WaveDrop Setup${RESET}"
echo -e "  Universal media downloader for macOS"
echo "────────────────────────────────────────"

# ── 1. Homebrew ───────────────────────────────────────────────
echo ""
echo -e "${BOLD}[1/4] Checking Homebrew…${RESET}"
if ! command -v brew &>/dev/null; then
    echo -e "${YELLOW}  Homebrew not found. Installing…${RESET}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add brew to PATH for Apple Silicon
    eval "$(/opt/homebrew/bin/brew shellenv)" 2>/dev/null || true
    eval "$(/usr/local/bin/brew shellenv)" 2>/dev/null || true
else
    echo -e "${GREEN}  ✓ Homebrew already installed${RESET}"
fi

# ── 2. Python 3 ───────────────────────────────────────────────
echo ""
echo -e "${BOLD}[2/4] Checking Python…${RESET}"
if ! command -v python3 &>/dev/null; then
    echo -e "${YELLOW}  Installing Python via Homebrew…${RESET}"
    brew install python
else
    PYVER=$(python3 --version 2>&1)
    echo -e "${GREEN}  ✓ $PYVER${RESET}"
fi

# ── 3. ffmpeg ─────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[3/4] Checking ffmpeg…${RESET}"
if ! command -v ffmpeg &>/dev/null; then
    echo -e "${YELLOW}  Installing ffmpeg via Homebrew…${RESET}"
    brew install ffmpeg
else
    echo -e "${GREEN}  ✓ ffmpeg already installed${RESET}"
fi

# ── 4. Python packages ────────────────────────────────────────
echo ""
echo -e "${BOLD}[4/4] Installing Python packages…${RESET}"
pip3 install --upgrade pip --quiet
pip3 install customtkinter yt-dlp --quiet

echo ""
echo -e "${GREEN}${BOLD}✓ Setup complete!${RESET}"
echo ""
echo -e "  Run the app with:"
echo -e "  ${BOLD}python3 app.py${RESET}"
echo ""
echo -e "  Or double-click ${BOLD}launch.sh${RESET} in Finder."
echo ""
