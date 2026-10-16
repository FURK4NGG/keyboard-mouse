#!/usr/bin/env python3
import json
import os
import subprocess
from pathlib import Path
import gi

gi.require_version("Gtk", "4.0")
gi.require_version('Gdk', '4.0')
from gi.repository import Gdk, Gtk

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "keyboard-mouse"
CONFIG_FILE = CONFIG_DIR / "config.json"
LANG_FILE = CONFIG_DIR / "ui-language.json"

LANGUAGES = ["English", "Türkçe"]
TEXT = {"English":{"window_title":"Keyboard Mouse Settings","app_title":"Keyboard Mouse","movement":"Movement","left":"Move left","right":"Move right","up":"Move up","down":"Move down","speed_keys":"Speed","fast":"Speed up","slow":"Slow down","mouse":"Mouse","mouse_left":"Left click","mouse_middle":"Middle click","mouse_right":"Right click","scroll_up":"Scroll up","scroll_down":"Scroll down","mode":"Mouse mode","open":"Open mode","close":"Close mode","toggle":"Toggle mouse mode","speed":"Speed","hint":"Click a key slot, then press a keyboard key, mouse button, or mouse wheel.","key_test":"Key Test","key_test_on":"Key Test active — press a key","detected":"Detected key: ","save":"Save","default":"Default","select_key":"Select key","capture":"Press a key / mouse button / wheel…","and_tip":"Add a key to this combination (AND)","or_tip":"Add an independent alternative (OR)","toggle":"Toggle mouse mode"},"Türkçe":{"window_title":"Keyboard Mouse Ayarları","app_title":"Keyboard Mouse","movement":"Hareket","left":"Sola git","right":"Sağa git","up":"Yukarı git","down":"Aşağı git","speed_keys":"Hız","fast":"Hızlandır","slow":"Yavaşlat","mouse":"Mouse","mouse_left":"Sol tık","mouse_middle":"Orta tık","mouse_right":"Sağ tık","scroll_up":"Yukarı kaydır","scroll_down":"Aşağı kaydır","mode":"Mouse modu","open":"Modu aç","close":"Modu kapat","toggle":"Mouse modunu aç/kapat","speed":"Hız","hint":"Tuş yerinde klavye tuşuna, mouse butonuna veya mouse tekerleğine basabilirsin.","key_test":"Tuş Testi","key_test_on":"Tuş Testi aktif — bir tuşa bas","detected":"Algılanan tuş: ","save":"Kaydet","default":"Varsayılan","select_key":"Tuş seç","capture":"Bir tuşa / mouse'a basın…","and_tip":"Bu kombinasyona bir tuş ekle (AND)","or_tip":"Bağımsız yeni alternatif ekle (OR)","toggle":"Mouse modunu aç/kapat"}}
def tr(k): return TEXT.get(CURRENT_LANGUAGE,TEXT["English"]).get(k,k)
def load_language():
    try:
        d=json.loads(LANG_FILE.read_text(encoding="utf-8"))
        if d.get("language") in LANGUAGES: return d["language"]
    except Exception: pass
    return "English"
def save_language(lang):
    CONFIG_DIR.mkdir(parents=True,exist_ok=True)
    LANG_FILE.write_text(json.dumps({"language":lang},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
CURRENT_LANGUAGE=load_language()

DEFAULT_CONFIG = {
    "speed": 8,
    "movement": {
        "left": [["KEY_LEFT"]], "right": [["KEY_RIGHT"]],
        "up": [["KEY_UP"]], "down": [["KEY_DOWN"]],
    },
    "speed_keys": {
        "fast": [["KEY_LEFTSHIFT"], ["KEY_RIGHTSHIFT"]],
        "slow": [["KEY_LEFTCTRL"], ["KEY_RIGHTCTRL"]],
    },
    "mouse": {
        "left": [["KEY_F3"]], "middle": [["KEY_F2"]], "right": [["KEY_F1"]],
        "scroll_up": [["REL_WHEEL_UP"]], "scroll_down": [["REL_WHEEL_DOWN"]],
    },
    "mode": {
        "open": [["KEY_RIGHTCTRL", "KEY_END"]],
        "close": [["KEY_ESC"], ["KEY_RIGHTCTRL", "KEY_END"]],
    },
}

SPECIAL = {
    "Left": "KEY_LEFT", "Right": "KEY_RIGHT", "Up": "KEY_UP", "Down": "KEY_DOWN",
    "Escape": "KEY_ESC", "Return": "KEY_ENTER", "space": "KEY_SPACE",
    "Shift_L": "KEY_LEFTSHIFT", "Shift_R": "KEY_RIGHTSHIFT",
    "Control_L": "KEY_LEFTCTRL", "Control_R": "KEY_RIGHTCTRL",
    "Alt_L": "KEY_LEFTALT", "Alt_R": "KEY_RIGHTALT",
    "Super_L": "KEY_LEFTMETA", "Super_R": "KEY_RIGHTMETA",
    "BackSpace": "KEY_BACKSPACE", "Tab": "KEY_TAB", "Home": "KEY_HOME", "End": "KEY_END",
    "Page_Up": "KEY_PAGEUP", "Page_Down": "KEY_PAGEDOWN", "Insert": "KEY_INSERT",
    "Delete": "KEY_DELETE", "Caps_Lock": "KEY_CAPSLOCK",
}

PRETTY = {
    "KEY_LEFT": "←", "KEY_RIGHT": "→", "KEY_UP": "↑", "KEY_DOWN": "↓",
    "KEY_LEFTSHIFT": "Left Shift", "KEY_RIGHTSHIFT": "Right Shift",
    "KEY_LEFTCTRL": "Left Ctrl", "KEY_RIGHTCTRL": "Right Ctrl",
    "KEY_ESC": "Esc", "KEY_END": "End", "KEY_SPACE": "Space",
    "KEY_ENTER": "Enter", "KEY_TAB": "Tab",
    "KEY_PAGEUP": "Page Up", "KEY_PAGEDOWN": "Page Down",
    "KEY_HOME": "Home", "KEY_INSERT": "Insert", "KEY_DELETE": "Delete",
    "KEY_CAPSLOCK": "Caps Lock",
    "BTN_LEFT": "Mouse Left", "BTN_MIDDLE": "Mouse Middle", "BTN_RIGHT": "Mouse Right",
    "BTN_SIDE": "Mouse Side", "BTN_EXTRA": "Mouse Extra",
    "BTN_FORWARD": "Mouse Forward", "BTN_BACK": "Mouse Back",
    "REL_WHEEL_UP": "Scroll Up", "REL_WHEEL_DOWN": "Scroll Down",
}


def normalize(name):
    # GDK can return names such as "space", "Return", "Page_Up",
    # "Page_Down" and "End". Match SPECIAL case-insensitively.
    if name in SPECIAL:
        return SPECIAL[name]
    for special_name, token in SPECIAL.items():
        if str(name).lower() == special_name.lower():
            return token
    u = name.upper()
    if u in PRETTY:
        return u
    if u.startswith("F") and u[1:].isdigit():
        return "KEY_" + u
    if len(u) == 1 and (u.isalpha() or u.isdigit()):
        return "KEY_" + u
    if u.startswith("KP_"):
        return "KEY_" + u
    return "KEY_" + u if not u.startswith("KEY_") else u


def pretty(name):
    if not name:
        return ""
    return PRETTY.get(name, name.replace("KEY_", "", 1))


def load_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return json.loads(json.dumps(DEFAULT_CONFIG))
    result = json.loads(json.dumps(DEFAULT_CONFIG))
    if isinstance(data, dict):
        if isinstance(data.get("speed"), (int, float)):
            result["speed"] = max(1, min(100, int(data["speed"])))
        for s in ("movement", "speed_keys", "mouse", "mode"):
            if isinstance(data.get(s), dict):
                for k in result[s]:
                    if isinstance(data[s].get(k), list):
                        result[s][k] = data[s][k]
    return clean_config(result)


def clean_config(config):
    """Remove empty key slots/groups so blank slots do not return after reopening."""
    for section in ("movement", "speed_keys", "mouse", "mode"):
        for action in config.get(section, {}):
            groups = config[section][action]
            if not isinstance(groups, list):
                config[section][action] = []
                continue
            cleaned_groups = []
            for group in groups:
                if not isinstance(group, list):
                    continue
                cleaned = [x for x in group if isinstance(x, str) and x.strip()]
                if cleaned:
                    cleaned_groups.append(cleaned)
            config[section][action] = cleaned_groups
    return config


class KeyButton(Gtk.Button):
    def __init__(self, value, callback):
        super().__init__(label=pretty(value) if value else tr("select_key"))
        self.value = value or ""
        self.callback = callback
        self.capturing = False

        self.key_controller = Gtk.EventControllerKey()
        self.key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.key_controller.connect("key-pressed", self.on_key)
        self.add_controller(self.key_controller)

        self.click_controller = Gtk.GestureClick()
        self.click_controller.set_button(0)
        self.click_controller.connect("pressed", self.on_mouse_pressed)
        self.add_controller(self.click_controller)

        self.scroll_controller = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL | Gtk.EventControllerScrollFlags.HORIZONTAL
        )
        self.scroll_controller.connect("scroll", self.on_scroll)
        self.add_controller(self.scroll_controller)

        self.connect("clicked", self.capture)

    def capture(self, *_):
        # Capture mode starts with an EMPTY value. This is important:
        # if the user clicks a slot that previously contained a key and then
        # presses Save without selecting a new key, the old key must not be
        # restored or remain active in the config.
        self.capturing = True
        self.value = ""
        self.callback("")
        self.set_label(tr("capture"))
        self.grab_focus()

    def accept(self, value):
        self.value = value
        self.set_label(pretty(value) if value else tr("select_key"))
        self.capturing = False
        self.callback(value)

    def on_key(self, _controller, keyval, _keycode, _state):
        if not self.capturing:
            return False
        name = Gdk.keyval_name(keyval)
        if name:
            self.accept(normalize(name))
        return True

    def on_mouse_pressed(self, gesture, _n_press, _x, _y):
        if not self.capturing:
            return False
        button = gesture.get_current_button()
        mapping = {
            1: "BTN_LEFT", 2: "BTN_MIDDLE", 3: "BTN_RIGHT",
            8: "BTN_SIDE", 9: "BTN_EXTRA",
        }
        value = mapping.get(button)
        if value:
            self.accept(value)
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            return True
        return False

    def on_scroll(self, _controller, dx, dy):
        if not self.capturing:
            return False
        # GTK reports positive dy for scroll down and negative for scroll up.
        if dy < 0:
            self.accept("REL_WHEEL_UP")
        elif dy > 0:
            self.accept("REL_WHEEL_DOWN")
        elif dx < 0:
            self.accept("REL_HWHEEL_LEFT")
        elif dx > 0:
            self.accept("REL_HWHEEL_RIGHT")
        return True


class ComboRow(Gtk.Box):
    def __init__(self, window, section, action, group_index, group):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.window = window
        self.section, self.action, self.group_index = section, action, group_index
        self.buttons = []
        for key_index, value in enumerate(group):
            self.add_key(value, key_index)
        self.rebuild_buttons()

    def add_key(self, value, index):
        self.buttons.append(KeyButton(value, lambda v, i=index: self.change(i, v)))

    def change(self, index, value):
        self.window.config[self.section][self.action][self.group_index][index] = value
        self.buttons[index].value = value
        self.buttons[index].set_label(pretty(value) if value else tr("select_key"))

    def rebuild_buttons(self):
        while self.get_first_child():
            self.remove(self.get_first_child())
        for b in self.buttons:
            self.append(b)
        self.rebuild_controls()

    def rebuild_controls(self):
        yellow = Gtk.Button(label="+")
        yellow.set_size_request(42, 36)
        yellow.add_css_class("warning")
        yellow.add_css_class("combo-add")
        yellow.set_tooltip_text(tr("and_tip"))
        yellow.connect("clicked", self.add_combo_key)
        self.append(yellow)

        green = Gtk.Button(label="+")
        green.set_size_request(42, 36)
        green.add_css_class("success")
        green.add_css_class("alternative-add")
        green.set_tooltip_text(tr("or_tip"))
        green.connect("clicked", self.add_alternative)
        self.append(green)

        if len(self.window.config[self.section][self.action]) > 1 or self.group_index != 0:
            minus = Gtk.Button(label="−")
            minus.set_size_request(42, 36)
            minus.connect("clicked", self.remove_group)
            self.append(minus)

    def add_combo_key(self, *_):
        self.window.config[self.section][self.action][self.group_index].append("")
        self.window.refresh()

    def add_alternative(self, *_):
        self.window.config[self.section][self.action].append([""])
        self.window.refresh()

    def remove_group(self, *_):
        self.window.config[self.section][self.action].pop(self.group_index)
        self.window.refresh()


class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=tr("window_title"))
        self.language = CURRENT_LANGUAGE
        self.set_default_size(720, 780)
        self.config = load_config()
        self.keytest = False

        # Capture test keys at the window level in CAPTURE phase.
        # This prevents GTK widgets (especially buttons, scrolling and
        # activation keys such as Space/Enter) from consuming the event first.
        self.test_controller = Gtk.EventControllerKey()
        self.test_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.test_controller.connect("key-pressed", self.test_key)
        self.add_controller(self.test_controller)

        self.build()

    def install_css(self):
        css = Gtk.CssProvider()
        css.load_from_data(b"""
        button.combo-add, button.alternative-add {
            min-width: 42px;
            min-height: 36px;
            padding: 0;
            font-size: 20px;
            font-weight: bold;
        }
        button.combo-add { color: #f1c40f; }
        button.alternative-add { color: #2ecc71; }
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def build(self):
        self.install_css()
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(outer)
        header = Gtk.HeaderBar()
        self.header_title = Gtk.Label(label=tr("app_title"))
        header.set_title_widget(self.header_title)
        model = Gtk.StringList.new(LANGUAGES)
        self.language_dropdown = Gtk.DropDown(model=model)
        self.language_dropdown.set_selected(LANGUAGES.index(self.language))
        self.language_dropdown.set_tooltip_text("Language / Dil")
        self.language_dropdown.connect("notify::selected", self.on_language_changed)
        header.pack_end(self.language_dropdown)
        outer.append(header)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        outer.append(scroll)
        self.content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=12,
            margin_top=20, margin_bottom=20, margin_start=24, margin_end=24
        )
        scroll.set_child(self.content)
        self.refresh()

    def on_language_changed(self, dropdown, _param):
        selected = dropdown.get_selected()
        if selected >= len(LANGUAGES): return
        self.language = LANGUAGES[selected]
        save_language(self.language)
        global CURRENT_LANGUAGE
        CURRENT_LANGUAGE = self.language
        self.set_title(tr("window_title"))
        self.header_title.set_label(tr("app_title"))
        self.refresh()

    def restore_defaults(self, *_):
        self.config = json.loads(json.dumps(DEFAULT_CONFIG))
        self.keytest = False
        self.refresh()

    def clear(self):
        while self.content.get_first_child():
            self.content.remove(self.content.get_first_child())

    def refresh(self):
        self.clear()
        self.add_section(tr("movement"), [("movement", "left", tr("left")), ("movement", "right", tr("right")), ("movement", "up", tr("up")), ("movement", "down", tr("down"))])
        self.add_section(tr("speed_keys"), [("speed_keys", "fast", tr("fast")), ("speed_keys", "slow", tr("slow"))])
        self.add_section(tr("mouse"), [
            ("mouse", "left", tr("mouse_left")),
            ("mouse", "middle", tr("mouse_middle")),
            ("mouse", "right", tr("mouse_right")),
            ("mouse", "scroll_up", tr("scroll_up")),
            ("mouse", "scroll_down", tr("scroll_down")),
        ])
        self.add_section(tr("mode"), [("mode", "open", tr("open")), ("mode", "close", tr("close"))])

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, margin_top=8)
        label = Gtk.Label(label=tr("speed"))
        label.set_hexpand(True); label.set_xalign(0)
        row.append(label)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 1)
        scale.set_value(self.config["speed"]); scale.set_hexpand(True)
        scale.connect("value-changed", lambda s: self.set_speed(s))
        row.append(scale)
        self.content.append(row)

        hint = Gtk.Label(label=tr("hint"))
        hint.set_wrap(True); hint.set_xalign(0)
        self.content.append(hint)

        test = Gtk.Button(label=tr("key_test"))
        test.set_margin_top(15)
        test.connect("clicked", self.toggle_test)
        self.content.append(test)

        if self.keytest:
            self.test_label = Gtk.Label(label=tr("key_test_on"))
            self.content.append(self.test_label)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        default_btn = Gtk.Button(label=tr("default"))
        default_btn.connect("clicked", self.restore_defaults)
        button_row.append(default_btn)
        save = Gtk.Button(label=tr("save"))
        save.add_css_class("suggested-action")
        save.connect("clicked", self.save)
        button_row.append(save)
        self.content.append(button_row)

        # Toggle mouse mode directly from the UI.
        toggle = Gtk.Button(label=tr("toggle"))
        toggle.set_margin_top(8)
        toggle.connect("clicked", self.toggle_mouse_mode)
        self.content.append(toggle)

    def add_section(self, title, rows):
        lab = Gtk.Label()
        lab.set_markup(f"<b>{title}</b>"); lab.set_halign(Gtk.Align.START)
        lab.set_margin_top(12); self.content.append(lab)
        for section, action, text in rows:
            line = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            l = Gtk.Label(label=text); l.set_xalign(0); l.set_hexpand(True)
            top.append(l); line.append(top)
            groups = self.config[section][action]

            # Boş bir action için de ilk slotu göster ki kullanıcı yeni
            # kombinasyon ekleyebilsin. Kaydetmeden bırakılırsa clean_config
            # bunu tekrar temizler.
            if not groups:
                groups = [[""]]
                self.config[section][action] = groups

            for i, group in enumerate(groups):
                line.append(ComboRow(self, section, action, i, group))

            self.content.append(line)

    def set_speed(self, scale):
        self.config["speed"] = int(round(scale.get_value()))

    def toggle_test(self, *_):
        self.keytest = not self.keytest
        self.refresh()

    def toggle_mouse_mode(self, *_):
        # Toggle the current mouse-mode state directly from the UI.
        # No key assignment is involved.
        runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
        active_file = runtime_dir / "keyboard-mouse" / "active"
        launcher = Path(__file__).resolve().parent / "keyboard-mouse.sh"

        try:
            active = active_file.exists()
            command = "stop" if active else "start"

            if launcher.exists():
                subprocess.run(
                    [str(launcher), command],
                    cwd=str(launcher.parent),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                active_file.parent.mkdir(parents=True, exist_ok=True)
                if command == "start":
                    active_file.touch()
                else:
                    active_file.unlink(missing_ok=True)

            # Bildirimi shell script verir. UI burada tekrar notify-send
            # çağırmaz; böylece toggle ile çift bildirim oluşmaz.
        except Exception:
            pass

    def test_key(self, _c, keyval, _kc, _state):
        if not self.keytest:
            return False
        name = Gdk.keyval_name(keyval)
        if name:
            self.test_label.set_label(tr("detected") + pretty(normalize(name)))
        return True

    def save(self, *_):
        # Any slot left in capture mode is intentionally considered empty.
        # Empty slots and empty groups are removed, so they do not appear next time.
        for section in ("movement", "speed_keys", "mouse", "mode"):
            for action in self.config[section]:
                for group in self.config[section][action]:
                    for i, value in enumerate(group):
                        if not isinstance(value, str) or not value.strip():
                            group[i] = ""
        clean_config(self.config)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(self.config, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )

        # Config dosyası kaydedildi. Çalışan daemon config değişikliğini
        # kendi movement loopunda otomatik olarak yeniden yükler; daemonu
        # kapatıp yeniden başlatmaya gerek yok.
        self.close()


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="local.keyboardmouse.settings")

    def do_activate(self):
        w = self.props.active_window
        if w is None:
            w = SettingsWindow(self)
        w.present()


if __name__ == "__main__":
    raise SystemExit(App().run(None))
