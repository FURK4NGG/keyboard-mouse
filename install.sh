
#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="Keyboard Mouse"
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

TARGET_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/keyboard-mouse"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/keyboard-mouse"
LOG_FILE="/tmp/keyboard-mouse-daemon.log"

LAUNCHER_SRC="$PROJECT_DIR/keyboard-mouse.sh"
DAEMON_SRC="$PROJECT_DIR/keyboard-mouse-daemon.py"
UI_SRC="$PROJECT_DIR/keyboard-mouse-ui.py"

LAUNCHER_DST="$TARGET_DIR/keyboard-mouse.sh"
DAEMON_DST="$TARGET_DIR/keyboard-mouse-daemon.py"
UI_DST="$TARGET_DIR/keyboard-mouse-ui.py"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
RESET='\033[0m'

step() { printf "\n${BLUE}==>${RESET} %s\n" "$*"; }
ok()   { printf "${GREEN}[OK]${RESET} %s\n" "$*"; }
warn() { printf "${YELLOW}[WARNING]${RESET} %s\n" "$*"; }
err()  { printf "${RED}[ERROR]${RESET} %s\n" "$*" >&2; }
die()  { err "$*"; exit 1; }

trap 'rc=$?; err "Installation failed at line $LINENO (exit code: $rc)."; exit "$rc"' ERR

printf '%s\n' \
    "====================================" \
    "       $APP_NAME Installer" \
    "===================================="

# --------------------------------------------------
# Check source files
# --------------------------------------------------

step "Checking source files"

[[ -f "$LAUNCHER_SRC" ]] || die "Missing file: $LAUNCHER_SRC"
[[ -f "$DAEMON_SRC" ]] || die "Missing file: $DAEMON_SRC"
[[ -f "$UI_SRC" ]] || die "Missing file: $UI_SRC"

command -v python3 >/dev/null 2>&1 ||
    die "Python 3 is not installed."

ok "All source files found."

# --------------------------------------------------
# Detect package manager
# --------------------------------------------------

step "Detecting package manager"

if command -v pacman >/dev/null 2>&1; then
    PM="pacman"
elif command -v apt-get >/dev/null 2>&1; then
    PM="apt"
elif command -v dnf >/dev/null 2>&1; then
    PM="dnf"
else
    die "Unsupported package manager."
fi

# --------------------------------------------------
# Install dependencies
# --------------------------------------------------

step "Installing dependencies"

case "$PM" in
    pacman)
        sudo pacman -S --needed \
            python-gobject \
            gtk4 \
            python-evdev \
            ydotool \
            libnotify
        ;;
    apt)
        sudo apt-get update
        sudo apt-get install -y \
            python3-gi \
            gir1.2-gtk-4.0 \
            python3-evdev \
            ydotool \
            libnotify-bin
        ;;
    dnf)
        sudo dnf install -y \
            python3-gobject \
            gtk4 \
            python3-evdev \
            ydotool \
            libnotify
        ;;
esac

ok "Dependency installation completed."

# --------------------------------------------------
# Create directories
# --------------------------------------------------

step "Creating directories"

mkdir -p "$TARGET_DIR"
mkdir -p "$STATE_DIR"

chmod 700 "$STATE_DIR"

ok "Application directory: $TARGET_DIR"

# --------------------------------------------------
# Stop an old daemon before replacing its files
# --------------------------------------------------

step "Stopping an existing daemon"

if [[ -x "$LAUNCHER_DST" ]]; then
    "$LAUNCHER_DST" restart-daemon >/dev/null 2>&1 || true
    "$LAUNCHER_DST" stop >/dev/null 2>&1 || true
fi

# --------------------------------------------------
# Copy application files
# --------------------------------------------------

step "Installing application files"

install -m 755 "$LAUNCHER_SRC" "$LAUNCHER_DST"
install -m 755 "$DAEMON_SRC" "$DAEMON_DST"
install -m 755 "$UI_SRC" "$UI_DST"

ok "Launcher, daemon and UI installed."

# --------------------------------------------------
# Check Python
# --------------------------------------------------

step "Checking Python"

if python3 -c 'import math; import evdev' >/dev/null 2>&1; then
    ok "Python and evdev imports succeeded."
else
    warn "Python or evdev import failed."
    warn "The daemon may not start. Check the error below:"
    python3 -c 'import math; import evdev' 2>&1 || true
fi

# Syntax check does not guarantee that imports will work.
if python3 -m py_compile "$DAEMON_DST" "$UI_DST" 2>/dev/null; then
    ok "Python syntax checks passed."
else
    warn "Python syntax check failed."
fi

# --------------------------------------------------
# Start ydotool service if available
# --------------------------------------------------

step "Checking ydotool service"

if command -v systemctl >/dev/null 2>&1 &&
   systemctl --user list-unit-files ydotool.service \
       --no-legend 2>/dev/null |
       grep -q 'ydotool.service'; then

    if systemctl --user enable --now ydotool.service; then
        ok "ydotool service started."
    else
        warn "Could not start ydotool service."
    fi
else
    warn "ydotool user service not found; continuing."
fi

# --------------------------------------------------
# Input permissions
# --------------------------------------------------

step "Checking input permissions"

CURRENT_USER="$(id -un)"

if getent group input >/dev/null 2>&1; then
    if id -nG "$CURRENT_USER" |
        tr ' ' '\n' |
        grep -Fxq input; then
        ok "User already belongs to the input group."
    else
        printf "Add %s to the input group? [y/N] " "$CURRENT_USER"
        read -r INPUT_CHOICE

        if [[ "$INPUT_CHOICE" =~ ^[Yy]$ ]]; then
            sudo usermod -aG input "$CURRENT_USER"
            warn "Log out and log in again for group changes to apply."
        else
            warn "Input-group change skipped."
        fi
    fi
else
    warn "The input group does not exist."
fi

# --------------------------------------------------
# Ask whether to start the latest daemon
# --------------------------------------------------

step "Daemon startup"

printf "Start the Keyboard Mouse daemon now? [y/N] "
read -r START_CHOICE

if [[ "$START_CHOICE" =~ ^[Yy]$ ]]; then
    # Restart ensures that an old daemon is not mistaken
    # for the newly installed process.
    if "$LAUNCHER_DST" restart-daemon; then
        sleep 1

        if pgrep -u "$(id -u)" -f \
            '[k]eyboard-mouse-daemon\.py' >/dev/null 2>&1; then
            ok "Daemon process detected."
        else
            warn "Daemon process was not detected."
            [[ -f "$LOG_FILE" ]] && tail -n 50 "$LOG_FILE" || true
        fi
    else
        warn "Daemon startup failed."
        [[ -f "$LOG_FILE" ]] && tail -n 50 "$LOG_FILE" || true
    fi
else
    ok "Daemon startup skipped."
fi

# --------------------------------------------------
# Reload Hyprland if available
# --------------------------------------------------

step "Checking Hyprland"

if command -v hyprctl >/dev/null 2>&1 &&
   [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then

    hyprctl reload || warn "Hyprland reload failed."
    hyprctl configerrors || warn "Could not check Hyprland config errors."
else
    warn "No active Hyprland session detected; skipping reload."
fi

# --------------------------------------------------
# Finish
# --------------------------------------------------

printf "\n====================================\n"
printf "${GREEN}Installation finished.${RESET}\n"
printf "Application directory: %s\n" "$TARGET_DIR"
printf "Settings UI: %s\n" "$UI_DST"
printf "Daemon log: %s\n" "$LOG_FILE"
printf "Open settings: %s settings\n" "$LAUNCHER_DST"
printf "Stop mouse mode: %s stop\n" "$LAUNCHER_DST"
printf "Restart daemon: %s restart-daemon\n" "$LAUNCHER_DST"
printf "Kill daemon: pkill -f '[k]eyboard-mouse-daemon'\n"
printf "====================================\n"
