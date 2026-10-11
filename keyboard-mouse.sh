#!/usr/bin/env bash
set -u

STATE_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/keyboard-mouse"
ACTIVE_FILE="$STATE_DIR/active"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DAEMON="$SCRIPT_DIR/keyboard-mouse-daemon.py"
UI="$SCRIPT_DIR/keyboard-mouse-ui.py"
CONFIG_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/keyboard-mouse/config.json"
PID_FILE="$STATE_DIR/daemon.pid"

mkdir -p "$STATE_DIR"

start_daemon() {
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        return 0
    fi
    rm -f "$PID_FILE"
    nohup python3 "$DAEMON" >>/tmp/keyboard-mouse-daemon.log 2>&1 &
    echo $! > "$PID_FILE"
    sleep 0.2
    if ! kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Daemon başlatılamadı. Log:"
        cat /tmp/keyboard-mouse-daemon.log
        rm -f "$PID_FILE"
        return 1
    fi
}

stop_daemon() {
    if [[ -f "$PID_FILE" ]]; then
        pid="$(cat "$PID_FILE")"
        kill "$pid" 2>/dev/null || true
        rm -f "$PID_FILE"
    fi

    # Eski/elle başlatılmış daemon'ları da kapat.
    # Böylece eski config kullanan ikinci bir daemon End/Ctrl+End gibi
    # tuşlara cevap vermeye devam edemez.
    while read -r pid; do
        [[ -n "$pid" ]] || continue
        kill "$pid" 2>/dev/null || true
    done < <(pgrep -f '[k]eyboard-mouse-daemon\.py' 2>/dev/null || true)

    sleep 0.15
}

format_keys() {
    local which="$1"

    python3 - "$CONFIG_FILE" "$which" <<'PY'
import json
import sys

config_file = sys.argv[1]
which = sys.argv[2]

pretty = {
    "KEY_LEFT": "←", "KEY_RIGHT": "→", "KEY_UP": "↑", "KEY_DOWN": "↓",
    "KEY_LEFTCTRL": "Left Ctrl", "KEY_RIGHTCTRL": "Right Ctrl",
    "KEY_LEFTSHIFT": "Left Shift", "KEY_RIGHTSHIFT": "Right Shift",
    "KEY_LEFTALT": "Left Alt", "KEY_RIGHTALT": "Right Alt",
    "KEY_LEFTMETA": "Left Super", "KEY_RIGHTMETA": "Right Super",
    "KEY_ESC": "Esc", "KEY_END": "End", "KEY_ENTER": "Enter",
    "KEY_SPACE": "Space", "KEY_TAB": "Tab", "KEY_BACKSPACE": "Backspace",
    "KEY_HOME": "Home", "KEY_PAGEUP": "Page Up", "KEY_PAGEDOWN": "Page Down",
    "KEY_INSERT": "Insert", "KEY_DELETE": "Delete", "KEY_CAPSLOCK": "Caps Lock",
}

def pretty_key(k):
    k = str(k).upper()
    return pretty.get(k, k[4:] if k.startswith("KEY_") else k)

try:
    with open(config_file, encoding="utf-8") as f:
        c = json.load(f)

    # IMPORTANT: UI/daemon config uses mode.open / mode.close.
    groups = c.get("mode", {}).get(which, [])
    result = []

    for group in groups:
        if isinstance(group, list):
            keys = [pretty_key(k) for k in group]
            if keys:
                result.append(" + ".join(keys))

    print(" / ".join(result) if result else "Tanımsız")
except Exception:
    print("Tanımsız")
PY
}

notify_mode() {
    local mode="$1"
    local open_keys close_keys language title message

    if ! command -v notify-send >/dev/null 2>&1; then
        return 0
    fi

    open_keys="$(format_keys open)"
    close_keys="$(format_keys close)"

    # UI dilini kullan: ~/.config/keyboard-mouse/ui-language.json
    language="English"
    if [[ -f "${XDG_CONFIG_HOME:-$HOME/.config}/keyboard-mouse/ui-language.json" ]]; then
        language="$(python3 - "${XDG_CONFIG_HOME:-$HOME/.config}/keyboard-mouse/ui-language.json" <<'PY'
import json
import sys
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        d = json.load(f)
    print(d.get("language", "English"))
except Exception:
    print("English")
PY
)"
    fi

    title="Keyboard Mouse"

    if [[ "$mode" == "open" ]]; then
        if [[ "$language" == "Türkçe" ]]; then
            message="Mouse modu etkin — $close_keys ile mouse modunu kapat"
        else
            message="Mouse mode enabled — $close_keys to stop mouse mode"
        fi
    else
        if [[ "$language" == "Türkçe" ]]; then
            message="Mouse modu devre dışı — $open_keys ile mouse modunu başlat"
        else
            message="Mouse mode disabled — $open_keys to start mouse mode"
        fi
    fi

    # Tek bildirim gönder.
    notify-send         -a "Keyboard Mouse"         -t 4500         "$title"         "$message"
}

case "${1:-}" in
    daemon)
        start_daemon
        ;;
    start)
        start_daemon || exit 1
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
            start_daemon || exit 1
            touch "$ACTIVE_FILE"
            notify_mode open
        fi
        ;;
    settings|config)
        exec python3 "$UI"
        ;;
    left-click) ydotool click 0xC0 ;;
    middle-click) ydotool click 0xC2 ;;
    right-click) ydotool click 0xC1 ;;
    restart-daemon)
        stop_daemon
        start_daemon
        ;;
    *)
        echo "Usage: $0 {daemon|start|stop|toggle|settings|left-click|middle-click|right-click|restart-daemon}"
        exit 1
        ;;
esac
