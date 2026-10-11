#!/usr/bin/env python3

import asyncio
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from evdev import InputDevice, ecodes, list_devices


# ============================================================
# PATHS
# ============================================================

RUNTIME_DIR = Path(
    os.environ.get(
        "XDG_RUNTIME_DIR",
        f"/run/user/{os.getuid()}"
    )
)

STATE_DIR = RUNTIME_DIR / "keyboard-mouse"
ACTIVE_FILE = STATE_DIR / "active"
LOCK_FILE = STATE_DIR / "daemon.lock"

CONFIG_DIR = (
    Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    / "keyboard-mouse"
)

CONFIG_FILE = CONFIG_DIR / "config.json"


# ============================================================
# DEFAULT CONFIG
# ============================================================

DEFAULT_CONFIG = {
    "speed": 8,

    "movement": {
        "left": [["KEY_LEFT"]],
        "right": [["KEY_RIGHT"]],
        "up": [["KEY_UP"]],
        "down": [["KEY_DOWN"]],
    },

    "speed_keys": {
        "fast": [
            ["KEY_LEFTSHIFT"],
            ["KEY_RIGHTSHIFT"]
        ],
        "slow": [
            ["KEY_LEFTCTRL"],
            ["KEY_RIGHTCTRL"]
        ],
    },

    "mouse": {
        "left": [["KEY_F3"]],
        "middle": [["KEY_F2"]],
        "right": [["KEY_F1"]],
        "scroll_up": [["REL_WHEEL_UP"]],
        "scroll_down": [["REL_WHEEL_DOWN"]],
    },

    "mode": {
        "open": [
            ["KEY_RIGHTCTRL", "KEY_END"]
        ],
        "close": [
            ["KEY_ESC"],
            ["KEY_RIGHTCTRL", "KEY_END"]
        ],
        "toggle": [],
    },
}


# ============================================================
# GLOBALS
# ============================================================

FRAME_DELAY = 0.012

pressed_inputs = set()

running = True

config = None
last_config_mtime = None
last_scroll_up_time = 0.0
last_scroll_down_time = 0.0


# ============================================================
# PRETTY NAMES
# ============================================================

PRETTY = {
    "KEY_LEFT": "←",
    "KEY_RIGHT": "→",
    "KEY_UP": "↑",
    "KEY_DOWN": "↓",

    "KEY_LEFTSHIFT": "Left Shift",
    "KEY_RIGHTSHIFT": "Right Shift",

    "KEY_LEFTCTRL": "Left Ctrl",
    "KEY_RIGHTCTRL": "Right Ctrl",

    "KEY_LEFTALT": "Left Alt",
    "KEY_RIGHTALT": "Right Alt",

    "KEY_LEFTMETA": "Left Super",
    "KEY_RIGHTMETA": "Right Super",

    "KEY_ESC": "Esc",
    "KEY_END": "End",
    "KEY_ENTER": "Enter",
    "KEY_SPACE": "Space",
    "KEY_TAB": "Tab",
    "KEY_BACKSPACE": "Backspace",

    "BTN_LEFT": "Mouse Left",
    "BTN_MIDDLE": "Mouse Middle",
    "BTN_RIGHT": "Mouse Right",
    "BTN_SIDE": "Mouse Side",
    "BTN_EXTRA": "Mouse Extra",
    "BTN_FORWARD": "Mouse Forward",
    "BTN_BACK": "Mouse Back",

    "REL_WHEEL_UP": "Scroll Up",
    "REL_WHEEL_DOWN": "Scroll Down",
    "REL_HWHEEL_LEFT": "Scroll Left",
    "REL_HWHEEL_RIGHT": "Scroll Right",
}


# ============================================================
# CONFIG
# ============================================================

def deep_copy_default():
    return json.loads(json.dumps(DEFAULT_CONFIG))


def merge_config(data):
    result = deep_copy_default()

    if not isinstance(data, dict):
        return result

    # Speed
    if isinstance(data.get("speed"), (int, float)):
        result["speed"] = max(
            1,
            min(100, int(data["speed"]))
        )

    # Other sections
    for section in (
        "movement",
        "speed_keys",
        "mouse",
        "mode"
    ):
        section_data = data.get(section)

        if not isinstance(section_data, dict):
            continue

        for key in result[section]:

            if key not in section_data:
                continue

            value = section_data[key]

            # IMPORTANT:
            # Empty lists are valid.
            # They must NOT restore the default key.
            if isinstance(value, list):
                result[section][key] = value

    return result


def load_config():
    global last_config_mtime

    CONFIG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(
            json.dumps(
                DEFAULT_CONFIG,
                indent=4,
                ensure_ascii=False
            ) + "\n",
            encoding="utf-8"
        )

    try:
        data = json.loads(
            CONFIG_FILE.read_text(
                encoding="utf-8"
            )
        )

        result = merge_config(data)

        last_config_mtime = (
            CONFIG_FILE.stat().st_mtime_ns
        )

        return result

    except (
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError
    ) as exc:

        print(
            f"Config okunamadı, varsayılanlar kullanılacak: {exc}",
            file=sys.stderr
        )

        return deep_copy_default()


def maybe_reload_config():
    global config
    global last_config_mtime

    try:
        mtime = CONFIG_FILE.stat().st_mtime_ns
    except OSError:
        return

    if mtime != last_config_mtime:

        config = load_config()

        # Eski basılı tuşları temizle.
        pressed_inputs.clear()

        print(
            "Config yeniden yüklendi.",
            flush=True
        )


# ============================================================
# TOKEN / KEY HANDLING
# ============================================================

def canonical_token(name):
    """Convert every keyboard/button token to one stable evdev-style name."""
    if not isinstance(name, str):
        return None

    name = name.strip().upper()
    if not name:
        return None

    if name in {
        "REL_WHEEL_UP",
        "REL_WHEEL_DOWN",
        "REL_HWHEEL_LEFT",
        "REL_HWHEEL_RIGHT",
    }:
        return name

    if name.startswith(("KEY_", "BTN_")):
        return name

    return "KEY_" + name


def token_code(name):

    name = canonical_token(name)
    if not name:
        return None

    # Virtual wheel tokens do not have an EV_KEY code.
    if name in {
        "REL_WHEEL_UP",
        "REL_WHEEL_DOWN",
        "REL_HWHEEL_LEFT",
        "REL_HWHEEL_RIGHT",
    }:
        return name

    return getattr(ecodes, name, None)


def combo_pressed(combo):

    if not isinstance(combo, list):
        return False

    if not combo:
        return False

    tokens = [
        x
        for x in combo
        if isinstance(x, str)
        and x.strip()
    ]

    if not tokens:
        return False

    return all(
        token_is_pressed(x)
        for x in tokens
    )


def token_is_pressed(token):

    token = canonical_token(token)
    if not token:
        return False

    # Wheel events are instantaneous.
    if token in {
        "REL_WHEEL_UP",
        "REL_WHEEL_DOWN",
        "REL_HWHEEL_LEFT",
        "REL_HWHEEL_RIGHT",
    }:
        return False

    code = token_code(token)

    return (
        code is not None
        and (token, code) in pressed_inputs
    )


def action_pressed(groups):

    return any(
        combo_pressed(combo)
        for combo in groups
        if isinstance(combo, list)
    )


def combo_matches_new_input(
    groups,
    new_token
):

    new_token = canonical_token(new_token)
    if not new_token:
        return False

    for combo in groups:

        if not isinstance(combo, list):
            continue

        tokens = [
            canonical_token(x)
            for x in combo
            if canonical_token(x)
        ]

        if not tokens:
            continue

        if new_token not in tokens:
            continue

        ok = True

        for token in tokens:

            if token == new_token:
                continue

            if not token_is_pressed(token):
                ok = False
                break

        if ok:
            return True

    return False


def combo_matches_mode_input(groups, new_token):
    """
    Match a mode OPEN/CLOSE combination exactly.

    A configured single key must NOT also match when another key is held.
    Example:
        close = [End]

    End alone  -> closes
    Ctrl+End   -> does NOT close

    If the configuration explicitly contains [RightCtrl, End], then
    RightCtrl+End matches that combination.

    This prevents a key that is part of a combination from accidentally
    triggering a single-key mode action.
    """
    new_token = canonical_token(new_token)
    if not new_token:
        return False

    # The newly pressed key has already been added to pressed_inputs
    # before handle_new_input() is called.
    held_tokens = {
        canonical_token(token)
        for token, _code in pressed_inputs
        if canonical_token(token)
    }

    for combo in groups:
        if not isinstance(combo, list):
            continue

        tokens = {
            canonical_token(x)
            for x in combo
            if canonical_token(x)
        }

        if not tokens or new_token not in tokens:
            continue

        # Wheel events are instantaneous and are not stored in
        # pressed_inputs. For wheel-based mode combinations, retain the
        # normal "all configured non-wheel keys are held" behavior.
        has_wheel = any(
            token in {
                "REL_WHEEL_UP",
                "REL_WHEEL_DOWN",
                "REL_HWHEEL_LEFT",
                "REL_HWHEEL_RIGHT",
            }
            for token in tokens
        )

        if has_wheel:
            if all(
                token == new_token or token_is_pressed(token)
                for token in tokens
            ):
                return True
            continue

        # Exact set matching is the important part: no extra held key
        # may turn [End] into a match for Ctrl+End.
        if held_tokens == tokens:
            return True

    return False


def add_pressed(token):

    token = canonical_token(token)
    code = token_code(token)

    if token and code is not None:
        pressed_inputs.add(
            (
                token,
                code
            )
        )


def remove_pressed(token):

    token = canonical_token(token)
    code = token_code(token)

    if token and code is not None:
        pressed_inputs.discard(
            (
                token,
                code
            )
        )


# ============================================================
# NOTIFICATION
# ============================================================

def notify(
    title,
    body,
    timeout=1800
):
    """Send a notification without replacement-id suppression.

    A fixed -r ID can cause notification daemons such as swaync to update an
    existing notification instead of displaying a new one. Every state change
    should be visible, so notifications intentionally use no replacement ID.
    """

    try:
        env = os.environ.copy()

        uid = os.getuid()
        env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{uid}")

        if "DBUS_SESSION_BUS_ADDRESS" not in env:
            env["DBUS_SESSION_BUS_ADDRESS"] = (
                f"unix:path={env['XDG_RUNTIME_DIR']}/bus"
            )

        result = subprocess.run(
            [
                "notify-send",
                "-a", "Keyboard Mouse",
                "-u", "normal",
                "-t", str(timeout),
                title,
                body,
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(
                f"notify-send failed ({result.returncode}): "
                f"{result.stderr.strip()}",
                file=sys.stderr,
                flush=True,
            )

    except Exception as exc:
        print(
            f"notify-send error: {exc}",
            file=sys.stderr,
            flush=True,
        )


# ============================================================
# KEY DISPLAY
# ============================================================

def pretty_token(token):

    token = str(token).upper()

    return PRETTY.get(
        token,
        token.replace(
            "KEY_",
            "",
            1
        )
    )


def format_groups(groups):

    alternatives = []

    if not isinstance(groups, list):
        return "atanmamış"

    for combo in groups:

        if not isinstance(combo, list):
            continue

        vals = [
            pretty_token(x)
            for x in combo
            if isinstance(x, str)
            and x.strip()
        ]

        if vals:
            alternatives.append(
                " + ".join(vals)
            )

    return (
        " / ".join(alternatives)
        if alternatives
        else "atanmamış"
    )


# ============================================================
# MOUSE
# ============================================================

def send_click(button):

    codes = {
        "left": "0xC0",
        "right": "0xC1",
        "middle": "0xC2",
    }

    code = codes.get(button)

    if code:

        subprocess.run(
            [
                "ydotool",
                "click",
                code
            ],

            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,

            check=False,
        )


def scroll_settings(mode="normal"):
    """
    Calculate scroll amount and repeat interval.

    Speed Up intentionally does NOT make ydotool run more often. Instead,
    each ydotool call sends more wheel units. This prevents rapid spawning
    of ydotool processes when the speed key is held.

    At sensitivity 8:
      normal = 1 wheel unit / ~100 ms
      fast   = 3 wheel units / ~100 ms
      slow   = 1 wheel unit / ~200 ms

    Higher sensitivity increases the normal amount and also makes the
    normal repeat interval shorter, preserving the existing sensitivity
    behavior while keeping Speed Up efficient.
    """
    sensitivity = max(1, int(config.get("speed", 8)))

    # Base amount follows the same Speed/Sensitivity setting.
    base_amount = max(1, round(sensitivity / 8))

    # Repeat interval follows the same Speed/Sensitivity setting.
    interval = max(0.025, 0.80 / sensitivity)

    if mode == "fast":
        # IMPORTANT: Do not reduce the interval. Send more wheel units
        # in the same ydotool invocation instead.
        amount = base_amount * 3
    elif mode == "slow":
        amount = base_amount
        interval *= 2.0
    else:
        amount = base_amount

    return amount, interval


def send_scroll(direction, mode="normal"):
    """Emit one real mouse-wheel event through ydotool."""
    amount, _interval = scroll_settings(mode)

    if direction == "down":
        amount = -amount

    subprocess.run(
        ["ydotool", "mousemove", "-w", "--", "0", str(amount)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )



def send_move(
    x,
    y,
    step=None
):

    if step is None:
        step = current_speed()

    subprocess.run(
        [
            "ydotool",
            "mousemove",
            "--",
            str(x * step),
            str(y * step),
        ],

        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,

        check=False,
    )


def current_speed():

    base = int(
        config["speed"]
    )

    if action_pressed(
        config["speed_keys"]["fast"]
    ):
        return base * 3

    if action_pressed(
        config["speed_keys"]["slow"]
    ):
        return max(
            1,
            base // 4
        )

    return base


# ============================================================
# MODE
# ============================================================

def set_mode(active):
    if active:
        ACTIVE_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        ACTIVE_FILE.touch()

        # Mouse mode açıldı: SADECE kapatma kombinasyonlarını göster.
        close_groups = config.get("mode", {}).get("close", [])
        close_text = format_groups(close_groups)

        if not close_text or close_text == "atanmamış":
            close_text = "atanmamış"

        message = f"Mouse mode enabled — {close_text} to stop mouse mode"

        notify(
            "Keyboard Mouse",
            message,
            4500
        )

        print(
            message,
            flush=True
        )

    else:
        try:
            ACTIVE_FILE.unlink()

        except FileNotFoundError:
            pass

        # Mouse mode kapandı: SADECE açma kombinasyonlarını göster.
        open_groups = config.get("mode", {}).get("open", [])
        open_text = format_groups(open_groups)

        if not open_text or open_text == "atanmamış":
            open_text = "atanmamış"

        message = f"Mouse mode disabled — {open_text} to start mouse mode"

        notify(
            "Keyboard Mouse",
            message,
            3000
        )

        print(
            message,
            flush=True
        )


# ============================================================
# INPUT HANDLER
# ============================================================

def handle_new_input(token):
    """
    Mode control is strictly state-dependent.

    OFF:
      Only configured OPEN groups can open the mode.

    ON:
      Only configured CLOSE groups can close the mode.
      OPEN groups are ignored while the mode is already ON.

    Each group is AND; multiple groups are OR.
    """

    # --------------------------------------------------------
    # TOGGLE MODE: configured exact combination works in BOTH states
    # --------------------------------------------------------
    # If a toggle combination is configured, it has priority over the
    # state-specific OPEN/CLOSE bindings and simply flips the current mode.
    toggle_groups = config["mode"].get("toggle", [])
    if combo_matches_mode_input(toggle_groups, token):
        set_mode(not ACTIVE_FILE.exists())
        return True

    # --------------------------------------------------------
    # MODE OFF: ONLY OPEN ACTIONS
    # --------------------------------------------------------
    if not ACTIVE_FILE.exists():
        if combo_matches_mode_input(
            config["mode"].get("open", []),
            token
        ):
            set_mode(True)
            return True

        # Close keys do absolutely nothing while mode is OFF.
        return False

    # --------------------------------------------------------
    # MODE ON: ONLY CLOSE ACTIONS
    # --------------------------------------------------------
    if combo_matches_mode_input(
        config["mode"].get("close", []),
        token
    ):
        set_mode(False)
        return True

    # Open keys do absolutely nothing while mode is ON.
    # Mouse commands continue below.

    mouse = config["mouse"]

    # --------------------------------------------------------
    # ASSIGNED SCROLL KEYS
    # --------------------------------------------------------
    # Keyboard/mouse-button scroll mappings are handled continuously
    # by movement_loop while their assigned keys/buttons remain pressed.
    # A physical wheel event is instantaneous, so emit one event here.
    if token == "REL_WHEEL_UP":
        if combo_matches_new_input(
            mouse.get("scroll_up", []),
            token
        ):
            send_scroll("up")
            return True

    if token == "REL_WHEEL_DOWN":
        if combo_matches_new_input(
            mouse.get("scroll_down", []),
            token
        ):
            send_scroll("down")
            return True

    # --------------------------------------------------------
    # CLICK
    # --------------------------------------------------------
    for name in ("left", "middle", "right"):
        if combo_matches_new_input(
            mouse.get(name, []),
            token
        ):
            send_click(name)
            return True

    # --------------------------------------------------------
    # MOVEMENT
    # --------------------------------------------------------
    movement = config["movement"]

    x = (
        1 if combo_matches_new_input(movement["right"], token) else 0
    ) - (
        1 if combo_matches_new_input(movement["left"], token) else 0
    )

    y = (
        1 if combo_matches_new_input(movement["down"], token) else 0
    ) - (
        1 if combo_matches_new_input(movement["up"], token) else 0
    )

    if x or y:
        send_move(x, y)
        return True

    return False


# ============================================================
# EVDEV NAME HELPERS
# ============================================================

def key_name(code):

    try:
        return ecodes.KEY[code]

    except (
        KeyError,
        TypeError
    ):
        return None


def button_name(code):

    try:
        return ecodes.BTN[code]

    except (
        KeyError,
        TypeError
    ):
        return None


def rel_token(
    code,
    value
):

    if code == ecodes.REL_WHEEL:

        if value > 0:
            return "REL_WHEEL_UP"

        return "REL_WHEEL_DOWN"

    if code == ecodes.REL_HWHEEL:

        if value < 0:
            return "REL_HWHEEL_LEFT"

        return "REL_HWHEEL_RIGHT"

    return None


# ============================================================
# INPUT DEVICES
# ============================================================

def find_input_devices():

    devices = []

    for path in list_devices():

        try:

            device = InputDevice(path)

            name = (
                device.name or ""
            ).lower()

            # ydotool sanal cihazını alma.
            if "ydotool" in name:

                device.close()

                continue

            caps = device.capabilities()

            keys = set(
                caps.get(
                    ecodes.EV_KEY,
                    []
                )
            )

            rels = set(
                caps.get(
                    ecodes.EV_REL,
                    []
                )
            )

            is_keyboard = all(
                k in keys
                for k in (
                    ecodes.KEY_A,
                    ecodes.KEY_Z,
                    ecodes.KEY_LEFT,
                    ecodes.KEY_RIGHT,
                    ecodes.KEY_UP,
                    ecodes.KEY_DOWN,
                )
            )

            is_mouse = bool(
                keys.intersection(
                    {
                        ecodes.BTN_LEFT,
                        ecodes.BTN_MIDDLE,
                        ecodes.BTN_RIGHT,
                        getattr(
                            ecodes,
                            "BTN_SIDE",
                            -1
                        ),
                        getattr(
                            ecodes,
                            "BTN_EXTRA",
                            -1
                        ),
                    }
                )
            ) or bool(
                rels.intersection(
                    {
                        ecodes.REL_WHEEL,
                        ecodes.REL_HWHEEL,
                    }
                )
            )

            if is_keyboard or is_mouse:

                devices.append(device)

            else:

                device.close()

        except (
            PermissionError,
            OSError
        ):

            continue

    return devices


# ============================================================
# EVENT LOOP
# ============================================================

async def read_input(device):

    global running

    try:

        async for event in device.async_read_loop():

            if not running:
                return

            # ------------------------------------------------
            # KEY / BUTTON
            # ------------------------------------------------

            if event.type == ecodes.EV_KEY:

                token = (
                    key_name(event.code)
                    or button_name(event.code)
                )

                if not token:
                    continue

                token = token.upper()

                # Press / repeat
                if event.value in (1, 2):

                    already = token_is_pressed(
                        token
                    )

                    add_pressed(token)

                    # Sadece gerçek yeni basışta.
                    if (
                        event.value == 1
                        and not already
                    ):

                        try:
                            handle_new_input(token)
                        except Exception as exc:
                            # A bad physical mouse/keyboard event must never
                            # terminate the daemon. Log it and keep listening.
                            print(
                                f"Input handler error ({token}): {exc}",
                                file=sys.stderr,
                                flush=True,
                            )

                # Release
                elif event.value == 0:

                    remove_pressed(
                        token
                    )

            # ------------------------------------------------
            # SCROLL
            # ------------------------------------------------

            elif event.type == ecodes.EV_REL:

                token = rel_token(
                    event.code,
                    event.value
                )

                if token:

                    try:
                        handle_new_input(token)
                    except Exception as exc:
                        # Scroll/button handling must not stop the daemon.
                        print(
                            f"Input handler error ({token}): {exc}",
                            file=sys.stderr,
                            flush=True,
                        )

    except asyncio.CancelledError:
        raise
    except OSError as exc:
        # A physical device can disappear/reconnect. Keep the daemon alive.
        print(
            f"Input device closed ({device.path}): {exc}",
            file=sys.stderr,
            flush=True,
        )
        return
    except Exception as exc:
        # Unexpected input errors must not terminate the daemon.
        print(
            f"Input device error ({device.path}): {exc}",
            file=sys.stderr,
            flush=True,
        )
        return


def handle_held_scroll():
    """Kept for compatibility; continuous scroll is handled by movement_loop."""
    return


# ============================================================
# MOVEMENT LOOP
# ============================================================

async def movement_loop():

    global last_scroll_up_time, last_scroll_down_time

    while running:

        maybe_reload_config()

        if ACTIVE_FILE.exists():

            # Keyboard/button scroll mappings repeat while held.
            # Physical wheel events are handled once in read_input().
            handle_held_scroll()

            x = (
                1
                if action_pressed(
                    config["movement"]["right"]
                )
                else 0
            ) - (
                1
                if action_pressed(
                    config["movement"]["left"]
                )
                else 0
            )

            y = (
                1
                if action_pressed(
                    config["movement"]["down"]
                )
                else 0
            ) - (
                1
                if action_pressed(
                    config["movement"]["up"]
                )
                else 0
            )

            if x or y:

                send_move(
                    x,
                    y
                )

            # ------------------------------------------------
            # CONTINUOUS SCROLL WHILE ASSIGNED INPUT IS HELD
            # ------------------------------------------------
            # The configured scroll action can be a keyboard key,
            # mouse button, or an AND combination. action_pressed()
            # checks the currently held physical inputs.
            mouse = config["mouse"]

            now = time.monotonic()

            if action_pressed(mouse.get("scroll_up", [])):
                if action_pressed(config["speed_keys"]["fast"]):
                    scroll_mode = "fast"
                elif action_pressed(config["speed_keys"]["slow"]):
                    scroll_mode = "slow"
                else:
                    scroll_mode = "normal"

                _, interval = scroll_settings(scroll_mode)
                if now - last_scroll_up_time >= interval:
                    send_scroll("up", scroll_mode)
                    last_scroll_up_time = now

            if action_pressed(mouse.get("scroll_down", [])):
                if action_pressed(config["speed_keys"]["fast"]):
                    scroll_mode = "fast"
                elif action_pressed(config["speed_keys"]["slow"]):
                    scroll_mode = "slow"
                else:
                    scroll_mode = "normal"

                _, interval = scroll_settings(scroll_mode)
                if now - last_scroll_down_time >= interval:
                    send_scroll("down", scroll_mode)
                    last_scroll_down_time = now

        await asyncio.sleep(
            FRAME_DELAY
        )


# ============================================================
# SIGNAL
# ============================================================

def stop_daemon(*_):

    global running

    running = False


# ============================================================
# MAIN
# ============================================================

async def main():

    global config

    STATE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Only one daemon instance may read input at a time.
    # This prevents an older daemon with old settings from also responding.
    lock_handle = LOCK_FILE.open("w")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Daemon zaten çalışıyor; ikinci instance başlatılmadı.", flush=True)
        lock_handle.close()
        return 0

    config = load_config()

    devices = find_input_devices()

    if not devices:

        print(
            "Erişilebilir klavye/mouse bulunamadı.",
            file=sys.stderr
        )

        print(
            'Kullanıcının "input" grubunda olduğunu kontrol et.',
            file=sys.stderr
        )

        return 1

    for device in devices:

        print(
            f"Input: {device.path} — {device.name}",
            flush=True
        )

    print(
        f"Config: {CONFIG_FILE}",
        flush=True
    )

    print(
        f"Modu aç: {config['mode']['open']}",
        flush=True
    )

    print(
        f"Modu kapat: {config['mode']['close']}",
        flush=True
    )

    tasks = [
        asyncio.create_task(
            read_input(device)
        )
        for device in devices
    ]

    tasks.append(
        asyncio.create_task(
            movement_loop()
        )
    )

    try:

        await asyncio.gather(
            *tasks
        )

    finally:

        try:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        lock_handle.close()

        for task in tasks:
            task.cancel()

        for device in devices:

            try:
                device.close()

            except OSError:
                pass

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    signal.signal(
        signal.SIGINT,
        stop_daemon
    )

    signal.signal(
        signal.SIGTERM,
        stop_daemon
    )

    raise SystemExit(
        asyncio.run(main())
    )
