#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="keyboard-mouse"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
DAEMON="$SCRIPT_DIR/keyboard-mouse-daemon.py"
UI="$SCRIPT_DIR/keyboard-mouse-ui.py"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/$APP_NAME"
CONFIG_FILE="$CONFIG_DIR/config.json"
LANG_FILE="$CONFIG_DIR/ui-language.json"
RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
STATE_DIR="$RUNTIME_DIR/$APP_NAME"
ACTIVE_FILE="$STATE_DIR/active"
PID_FILE="$STATE_DIR/daemon.pid"
LOG_FILE="${XDG_STATE_HOME:-$HOME/.local/state}/$APP_NAME/daemon.log"

mkdir -p "$STATE_DIR" "$CONFIG_DIR" "$(dirname "$LOG_FILE")"

die() { printf 'Error: %s\n' "$*" >&2; exit 1; }

format_keys() {
    python3 - "$CONFIG_FILE" "$1" <<'PY'
import json, sys
pretty = {
    "KEY_LEFT":"←", "KEY_RIGHT":"→", "KEY_UP":"↑", "KEY_DOWN":"↓",
    "KEY_LEFTCTRL":"Left Ctrl", "KEY_RIGHTCTRL":"Right Ctrl",
    "KEY_LEFTSHIFT":"Left Shift", "KEY_RIGHTSHIFT":"Right Shift",
    "KEY_ESC":"Esc", "KEY_END":"End", "KEY_ENTER":"Enter", "KEY_SPACE":"Space",
}
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        config = json.load(f)
    groups = config.get("mode", {}).get(sys.argv[2], [])
    out = []
    for group in groups:
        if isinstance(group, list):
            keys = [pretty.get(str(k).upper(), str(k).upper().removeprefix("KEY_")) for k in group]
            if keys:
                out.append(" + ".join(keys))
    print(" / ".join(out) if out else "unassigned")
except (OSError, ValueError, TypeError):
    print("unassigned")
PY
}

language() {
    python3 - "$LANG_FILE" <<'PY'
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        print(json.load(f).get("language", "English"))
except (OSError, ValueError, TypeError):
    print("English")
PY
}

notify_mode() {
    command -v notify-send >/dev/null 2>&1 || return 0
    local mode="$1" lang open_keys close_keys message
    lang="$(language)"
    open_keys="$(format_keys open)"
    close_keys="$(format_keys close)"
    if [[ "$mode" == open ]]; then
        if [[ "$lang" == "Türkçe" ]]; then
            message="Mouse modu etkin — $close_keys ile mouse modunu kapat"
        else
            message="Mouse mode enabled — $close_keys to stop mouse mode"
        fi
    else
        if [[ "$lang" == "Türkçe" ]]; then
            message="Mouse modu devre dışı — $open_keys ile mouse modunu başlat"
        else
            message="Mouse mode disabled — $open_keys to start mouse mode"
        fi
    fi
    notify-send -a "Keyboard Mouse" -t 4500 "Keyboard Mouse" "$message" || true
}

daemon_running() {
    [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE" 2>/dev/null)" 2>/dev/null
}

start_daemon() {
    [[ -f "$DAEMON" ]] || die "Daemon not found: $DAEMON"
    command -v python3 >/dev/null 2>&1 || die "python3 is required."
    if daemon_running; then return 0; fi
    rm -f "$PID_FILE"
    nohup python3 "$DAEMON" >>"$LOG_FILE" 2>&1 &
    local pid=$!
    printf '%s\n' "$pid" > "$PID_FILE"
    sleep 0.5
    if ! kill -0 "$pid" 2>/dev/null; then
        rm -f "$PID_FILE"
        printf 'Error: daemon failed to start. Log: %s\n' "$LOG_FILE" >&2
        tail -n 60 "$LOG_FILE" >&2 || true
        return 1
    fi
}

stop_daemon() {
    if daemon_running; then
        local pid
        pid="$(cat "$PID_FILE")"
        kill "$pid" 2>/dev/null || true
        for _ in {1..20}; do
            kill -0 "$pid" 2>/dev/null || break
            sleep 0.1
        done
    fi
    rm -f "$PID_FILE" "$ACTIVE_FILE"
    # Stop only processes whose command line is this project's daemon.
    pkill -f -- "$DAEMON" 2>/dev/null || true
}

case "${1:-}" in
    daemon)
        start_daemon
        ;;
    start)
        start_daemon
        touch "$ACTIVE_FILE"
        notify_mode open
        ;;
    stop)
        rm -f "$ACTIVE_FILE"
        notify_mode close
        ;;
    toggle)
        if [[ -f "$ACTIVE_FILE" ]]; then
            rm -f "$ACTIVE_FILE"
            notify_mode close
        else
            start_daemon
            touch "$ACTIVE_FILE"
            notify_mode open
        fi
        ;;
    settings|config)
        [[ -f "$UI" ]] || die "Settings UI not found: $UI"
        exec python3 "$UI"
        ;;
    left-click)
        command -v ydotool >/dev/null 2>&1 || die "ydotool is required."
        ydotool click 0xC0
        ;;
    middle-click)
        command -v ydotool >/dev/null 2>&1 || die "ydotool is required."
        ydotool click 0xC2
        ;;
    right-click)
        command -v ydotool >/dev/null 2>&1 || die "ydotool is required."
        ydotool click 0xC1
        ;;
    restart-daemon)
        stop_daemon
        start_daemon
        ;;
    status)
        if daemon_running; then echo "Daemon: running (PID $(cat "$PID_FILE"))"; else echo "Daemon: stopped"; fi
        if [[ -f "$ACTIVE_FILE" ]]; then echo "Mouse mode: enabled"; else echo "Mouse mode: disabled"; fi
        echo "Log: $LOG_FILE"
        ;;
    *)
        printf 'Usage: %s {daemon|start|stop|toggle|settings|left-click|middle-click|right-click|restart-daemon|status}\n' "$0"
        exit 2
        ;;
esac
