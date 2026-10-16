#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="Keyboard Mouse"
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

TARGET_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/keyboard-mouse"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/keyboard-mouse"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
LOG_FILE="$STATE_DIR/daemon.log"
PID_FILE="$RUNTIME_DIR/keyboard-mouse/daemon.pid"

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

# Check all application source files before changing the system.
step "Checking source files"
[[ -f "$LAUNCHER_SRC" ]] || die "Missing file: $LAUNCHER_SRC"
[[ -f "$DAEMON_SRC" ]] || die "Missing file: $DAEMON_SRC"
[[ -f "$UI_SRC" ]] || die "Missing file: $UI_SRC"
command -v python3 >/dev/null 2>&1 || die "Python 3 is not installed. Install Python 3 and run this installer again."
command -v sudo >/dev/null 2>&1 || die "sudo is required to install system packages. Install sudo or install the listed dependencies manually."
ok "All source files found."

# Prefer the package manager that matches the installed distribution.
step "Detecting Linux distribution"
if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    DISTRO_ID="${ID:-unknown}"
else
    DISTRO_ID="unknown"
fi

case "$DISTRO_ID" in
    arch|manjaro|endeavouros|garuda)
        PM="pacman"
        ;;
    debian|ubuntu|linuxmint|pop)
        PM="apt"
        ;;
    fedora|nobara)
        PM="dnf"
        ;;
    *)
        if command -v pacman >/dev/null 2>&1; then
            PM="pacman"
        elif command -v apt-get >/dev/null 2>&1; then
            PM="apt"
        elif command -v dnf >/dev/null 2>&1; then
            PM="dnf"
        else
            die "Unsupported Linux distribution/package manager: $DISTRO_ID"
        fi
        warn "Distribution '$DISTRO_ID' is not explicitly tested; using detected package manager '$PM'."
        ;;
esac
ok "Distribution: $DISTRO_ID; package manager: $PM."

# Install dependencies using native package names.
step "Installing dependencies"
case "$PM" in
    pacman)
        sudo pacman -S --needed \
            python python-gobject gtk4 python-evdev ydotool libnotify
        ;;
    apt)
        sudo apt-get update
        sudo apt-get install -y \
            python3 python3-gi gir1.2-gtk-4.0 python3-evdev ydotool libnotify-bin
        ;;
    dnf)
        sudo dnf install -y \
            python3 python3-gobject gtk4 python3-evdev ydotool libnotify
        ;;
esac
ok "Dependency installation completed."

# Create private state/config directories.
step "Creating application directories"
mkdir -p "$TARGET_DIR" "$STATE_DIR" "$(dirname "$PID_FILE")"
chmod 700 "$STATE_DIR" "$(dirname "$PID_FILE")"
ok "Application directory: $TARGET_DIR"

# Stop the old mode and daemon BEFORE replacing its Python file.
step "Stopping an existing daemon"
if [[ -x "$LAUNCHER_DST" ]]; then
    "$LAUNCHER_DST" stop >/dev/null 2>&1 || true
fi
if [[ -f "$PID_FILE" ]]; then
    OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ "$OLD_PID" =~ ^[0-9]+$ ]] && kill -0 "$OLD_PID" 2>/dev/null; then
        kill "$OLD_PID" 2>/dev/null || true
        for _ in {1..20}; do
            kill -0 "$OLD_PID" 2>/dev/null || break
            sleep 0.1
        done
    fi
    rm -f "$PID_FILE"
fi
# Also clean up a stale process launched from this app's installed path.
if command -v pkill >/dev/null 2>&1; then
    pkill -f -- "$DAEMON_DST" 2>/dev/null || true
fi

# Install atomically enough to avoid running a partially copied script.
step "Installing application files"
install -m 755 "$LAUNCHER_SRC" "$LAUNCHER_DST"
install -m 755 "$DAEMON_SRC" "$DAEMON_DST"
install -m 755 "$UI_SRC" "$UI_DST"
ok "Launcher, daemon and UI installed."

# Check Python syntax and runtime imports separately.
step "Validating Python dependencies"
if python3 -m py_compile "$DAEMON_DST" "$UI_DST"; then
    ok "Python syntax checks passed."
else
    die "Python syntax check failed. No daemon was started."
fi

if python3 - <<'PY'
import gi
import evdev
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk
print("Python GTK 4, GDK 4 and evdev imports succeeded.")
PY
then
    ok "Python runtime imports passed."
else
    warn "One or more Python imports failed. The settings UI or daemon may not run; review the missing-module error above."
fi

# Check ydotoold/service without assuming every package ships the same unit.
step "Checking ydotool"
if ! command -v ydotool >/dev/null 2>&1; then
    warn "ydotool command was not found after package installation. Mouse actions will not work until ydotool is installed."
elif command -v systemctl >/dev/null 2>&1; then
    if systemctl --user list-unit-files ydotool.service --no-legend 2>/dev/null | grep -q 'ydotool.service'; then
        if systemctl --user enable --now ydotool.service; then
            ok "User ydotool.service enabled and started."
        else
            warn "Could not start user ydotool.service. Check: systemctl --user status ydotool.service"
        fi
    elif systemctl list-unit-files ydotool.service --no-legend 2>/dev/null | grep -q 'ydotool.service'; then
        if sudo systemctl enable --now ydotool.service; then
            ok "System ydotool.service enabled and started."
        else
            warn "Could not start system ydotool.service. Check: systemctl status ydotool.service"
        fi
    else
        warn "No ydotool.service unit was found. The package may require manual ydotoold/socket setup; check your distribution's ydotool documentation."
    fi
else
    warn "systemctl is unavailable. Ensure ydotoold is running and its socket is accessible before using mouse actions."
fi

# evdev access is often provided by the active desktop session's device ACLs.
# Offer input-group membership only if the group exists; do not force it.
step "Checking input-device access"
CURRENT_USER="$(id -un)"
if getent group input >/dev/null 2>&1; then
    if id -nG "$CURRENT_USER" | tr ' ' '\n' | grep -Fxq input; then
        ok "User already belongs to the input group."
    else
        printf "Add %s to the input group? This grants broad access to input devices. [y/N] " "$CURRENT_USER"
        read -r INPUT_CHOICE || INPUT_CHOICE="n"
        if [[ "$INPUT_CHOICE" =~ ^[Yy]$ ]]; then
            sudo usermod -aG input "$CURRENT_USER"
            warn "Group membership changed. Log out completely and log in again before testing the daemon."
        else
            warn "Input-group change skipped. If evdev reports Permission denied, check your session's input-device permissions."
        fi
    fi
else
    warn "No 'input' group exists. The desktop session may still grant device access; check evdev permissions if no devices are detected."
fi

# Ask before starting the daemon.
step "Daemon startup"
printf "Start the Keyboard Mouse daemon now? [y/N] "
read -r START_CHOICE || START_CHOICE="n"
if [[ "$START_CHOICE" =~ ^[Yy]$ ]]; then
    if "$LAUNCHER_DST" restart-daemon; then
        sleep 1
        if pgrep -u "$(id -u)" -f '[k]eyboard-mouse-daemon\.py' >/dev/null 2>&1; then
            ok "Daemon process detected."
        else
            warn "Daemon process was not detected. Recent log output follows:"
            [[ -f "$LOG_FILE" ]] && tail -n 50 "$LOG_FILE" || true
        fi
    else
        warn "Daemon startup failed. Recent log output follows:"
        [[ -f "$LOG_FILE" ]] && tail -n 50 "$LOG_FILE" || true
    fi
else
    ok "Daemon startup skipped."
fi

# Hyprland is optional; this app can be installed without an active Hyprland session.
step "Checking Hyprland"
if command -v hyprctl >/dev/null 2>&1 && [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
    hyprctl reload || warn "Hyprland reload failed."
    hyprctl configerrors || warn "Could not check Hyprland config errors."
else
    ok "No active Hyprland session detected; skipping optional reload."
fi

printf "\n====================================\n"
printf "${GREEN}Installation finished.${RESET}\n"
printf "Application directory: %s\n" "$TARGET_DIR"
printf "Settings UI: %s\n" "$UI_DST"
printf "Daemon log: %s\n" "$LOG_FILE"
printf "Open settings: %s settings\n" "$LAUNCHER_DST"
printf "Enable mouse mode: %s start\n" "$LAUNCHER_DST"
printf "Stop mouse mode: %s stop\n" "$LAUNCHER_DST"
printf "Restart daemon: %s restart-daemon\n" "$LAUNCHER_DST"
printf "Kill daemon: pkill -f '[k]eyboard-mouse-daemon'\n"
printf "====================================\n"
