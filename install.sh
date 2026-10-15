#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="Keyboard Mouse"
# Resolve the directory containing this installer, regardless of where the
# project folder is located (e.g. Desktop/keyboard-mouse or Downloads/keyboard-mouse).
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$PROJECT_DIR"
TARGET_DIR="$HOME/.config/scripts"

LAUNCHER_SRC="$SOURCE_DIR/keyboard-mouse.sh"
DAEMON_SRC="$SOURCE_DIR/keyboard-mouse-daemon.py"
UI_SRC="$SOURCE_DIR/keyboard-mouse-ui.py"

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

trap 'rc=$?; err "Installation stopped unexpectedly (line: $LINENO, exit code: $rc)."; exit "$rc"' ERR

printf '%s\n' "====================================" \
              "       $APP_NAME Installer" \
              "===================================="

step "Checking source files"
[[ -f "$LAUNCHER_SRC" ]] || die "Source file not found: $LAUNCHER_SRC"
[[ -f "$DAEMON_SRC" ]] || die "Source file not found: $DAEMON_SRC"
[[ -f "$UI_SRC" ]] || die "Source file not found: $UI_SRC"
ok "Launcher, daemon, and UI source files were found in: $SOURCE_DIR"

for cmd in python3 systemctl; do
    command -v "$cmd" >/dev/null 2>&1 || die "Required command not found: $cmd"
done

step "Installing required packages"
if command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed python-evdev ydotool libnotify
    ok "Required packages are installed."
elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3-evdev ydotool libnotify-bin
    ok "Required packages are installed."
else
    die "Unsupported package manager. Install python-evdev, ydotool, and libnotify manually."
fi

step "Enabling and starting ydotool"
if systemctl --user list-unit-files ydotool.service --no-legend 2>/dev/null | grep -q 'ydotool.service'; then
    systemctl --user enable --now ydotool.service
    ok "ydotool.service was enabled and started."
else
    warn "ydotool.service was not found. Check whether the ydotool package/service is installed; continuing."
fi

step "Checking input-device permissions"
if getent group input >/dev/null 2>&1; then
    if id -nG "$USER" | tr ' ' '\n' | grep -Fxq input; then
        ok "$USER is already a member of the input group."
    else
        if command -v sudo >/dev/null 2>&1; then
            sudo usermod -aG input "$USER"
            warn "$USER was added to the input group. Log out and log back in for the group change to take full effect."
        else
            die "sudo was not found; unable to add the user to the input group."
        fi
    fi
else
    warn "The 'input' group does not exist on this system. Check input-device permissions separately."
fi

step "Copying files to $TARGET_DIR"
mkdir -p "$TARGET_DIR"
install -m 755 "$LAUNCHER_SRC" "$LAUNCHER_DST"
install -m 755 "$DAEMON_SRC" "$DAEMON_DST"
install -m 755 "$UI_SRC" "$UI_DST"
ok "keyboard-mouse.sh, keyboard-mouse-daemon.py, and keyboard-mouse-ui.py were copied."

step "Checking Python syntax"
python3 -m py_compile "$DAEMON_DST" "$UI_DST"
ok "Python syntax checks passed."

step "Starting the daemon"
if "$LAUNCHER_DST" daemon; then
    sleep 0.5
    if pgrep -u "$(id -u)" -f '[k]eyboard-mouse-daemon\.py' >/dev/null 2>&1; then
        ok "The daemon process appears to be running."
    else
        warn "The start command returned, but the daemon process was not detected. Checking the log."
        if [[ -f /tmp/keyboard-mouse-daemon.log ]]; then
            tail -n 40 /tmp/keyboard-mouse-daemon.log
        fi
        warn "Please verify that the daemon is running."
    fi
else
    warn "The daemon start command failed."
    [[ -f /tmp/keyboard-mouse-daemon.log ]] && tail -n 40 /tmp/keyboard-mouse-daemon.log || true
fi

step "Reloading the Hyprland configuration"
if command -v hyprctl >/dev/null 2>&1 && [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
    if hyprctl reload; then
        ok "The Hyprland configuration was reloaded."
    else
        warn "hyprctl reload failed. Check your Hyprland session."
    fi

    step "Checking Hyprland configuration errors"
    if hyprctl configerrors; then
        ok "The configerrors command completed."
    else
        warn "hyprctl configerrors failed."
    fi
else
    warn "No active Hyprland session was detected; skipping hyprctl reload/configerrors."
fi

printf "\n====================================\n"
printf "${GREEN}Installation steps completed.${RESET}\n"
printf "Settings UI: %s\n" "$UI_DST"
printf "Daemon log:  %s\n" "/tmp/keyboard-mouse-daemon.log"
printf "To open settings:\n  python3 '%s'\n" "$UI_DST"
printf "To restart the daemon:\n  '%s' restart-daemon\n" "$LAUNCHER_DST"
printf "====================================\n"
