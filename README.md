## 👀 keyboard-mouse Overview  
**Keyboard Mouse** is a Linux utility that lets you control your mouse using keyboard shortcuts, with configurable key bindings, adjustable movement speed, and a dedicated settings interface for easy customization.

![keyboard-mouse Demo Video](https://github.com/FURK4NGG/keyboard-mouse/blob/main/%7B%7D/keyboard-mouse.gif)

![keyboard-mouse_install Demo Image](https://github.com/FURK4NGG/keyboard-mouse/blob/main/%7B%7D/keyboard-mouse_install.webp)


<br><br>

✅ Works On  
Wayland compositors (Hyprland)  

⚠️ Compatibility  
Other Wayland compositors and desktop environments have not been verified yet.
<br><br>

## 🚀 Features

- [x] Control the mouse entirely with keyboard shortcuts
- [x] Customizable key bindings for all mouse actions
- [x] Adjustable mouse movement speed
- [x] Fast and slow movement modes
- [x] Left, middle, and right mouse clicks
- [x] Vertical scrolling
- [x] Configurable shortcuts to enable and disable mouse mode
- [x] Dedicated graphical settings interface
- [x] Persistent configuration across sessions
- [x] Background daemon for continuous input monitoring
- [x] Linux input handling through `evdev`
- [x] Mouse input simulation via `ydotool`
- [x] Hyprland integration with automatic configuration reload
- [x] English and Turkish interface languages



## 📦 Setup

Directory Structure  
~/.config/keyboard-mouse/  
├── install.sh  
├── keyboard-mouse-daemon.py  
├── keyboard-mouse-ui.py  
├── keyboard-mouse.sh  
├── config.json  (This file is auto-generated)  
└── ui-language.json  (This file is auto-generated)  
<br>


```
systemctl --user enable --now ydotool.service
sudo usermod -aG input "$USER"
sudo mkdir -p ~/.config/scripts/

git clone https://github.com/FURK4NGG/keyboard-mouse.git
cd keyboard-mouse
mkdir -p ~/.config/keyboard-mouse
cp keyboard-mouse-daemon.py \
   keyboard-mouse-ui.py \
   keyboard-mouse.sh \
   install.sh \
   LICENSE \
   README.md \
   ~/.config/keyboard-mouse/

sudo chown "$USER:$USER" ~/.config/scripts/keyboard-mouse.sh
sudo chown "$USER:$USER" ~/.config/scripts/keyboard-mouse-daemon.py
sudo chown "$USER:$USER" ~/.config/scripts/keyboard-mouse-ui.py
chmod +x ~/.config/keyboard-mouse/keyboard-mouse-daemon.py  
chmod +x ~/.config/keyboard-mouse/keyboard-mouse-ui.py  
chmod +x ~/.config/keyboard-mouse/keyboard-mouse.sh  
```


Arch
```
sudo pacman -S python-evdev ydotool libnotify
hyprctl reload
hyprctl configerrors
```
Debian / Ubuntu
```
sudo apt update
sudo apt install -y python3-evdev ydotool ydotoold libnotify-bin xdotool

python3 - <<'PY'
from pathlib import Path
import re

path = Path.home() / ".config/keyboard-mouse/keyboard-mouse-daemon.py"
source = path.read_text()

pattern = r"(?ms)^def send_move\(.*?(?=^def current_speed\()"

replacement = '''def send_move(x, y, step=None):
    """Move the cursor using the active desktop's appropriate tool."""
    if step is None:
        step = current_speed()

    dx = int(x * step)
    dy = int(y * step)

    if dx == 0 and dy == 0:
        return

    import os
    import shutil

    # Prefer the native Wayland path on Hyprland.
    is_hyprland = bool(os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"))
    is_wayland = os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"

    try:
        if is_hyprland or is_wayland:
            if not shutil.which("ydotool"):
                print("Mouse movement failed: ydotool is not installed.", flush=True)
                return

            # ydotool uses absolute coordinates on this setup.
            # Read the current cursor position from Hyprland and apply
            # the requested relative offset before sending the new position.
            if is_hyprland and shutil.which("hyprctl"):
                result = subprocess.run(
                    ["hyprctl", "cursorpos"],
                    capture_output=True, text=True, timeout=2, check=True
                )
                match = re.search(r"(-?\\\\d+)\\\\s*,\\\\s*(-?\\\\d+)", result.stdout)
                if not match:
                    print(
                        f"Could not read Hyprland cursor position: {result.stdout.strip()}",
                        flush=True
                    )
                    return

                current_x, current_y = map(int, match.groups())
                target_x = current_x + dx
                target_y = current_y + dy

                result = subprocess.run(
                    ["ydotool", "mousemove", "--", str(target_x), str(target_y)],
                    capture_output=True, text=True, timeout=2, check=False
                )
            else:
                print(
                    "Wayland detected, but relative movement currently requires "
                    "Hyprland cursor-position support.",
                    flush=True
                )
                return
        else:
            # X11: xdotool supports true relative movement.
            if not shutil.which("xdotool"):
                print("Mouse movement failed: install xdotool.", flush=True)
                return

            result = subprocess.run(
                ["xdotool", "mousemove_relative", "--", str(dx), str(dy)],
                capture_output=True, text=True, timeout=2, check=False
            )

        if result.returncode != 0:
            print(
                f"Mouse movement failed: {result.stderr.strip()}",
                flush=True
            )

    except Exception as exc:
        print(f"Mouse movement error: {exc}", flush=True)

'''

updated, count = re.subn(pattern, replacement, source, count=1)
if count != 1:
    raise SystemExit(
        "Could not find send_move() and current_speed() in the expected format. "
        "No changes were made."
    )

backup = path.with_suffix(path.suffix + ".bak")
backup.write_text(source)
path.write_text(updated)
print(f"Updated: {path}")
print(f"Backup:  {backup}")
PY


python3 -m py_compile ~/.config/keyboard-mouse/keyboard-mouse-daemon.py
~/.config/keyboard-mouse/keyboard-mouse.sh restart-daemon
```
Fedora
```
sudo dnf install python3-evdev ydotool libnotify
```
<br><br>

## 🎉 Run
```
~/.config/keyboard-mouse/keyboard-mouse.sh daemon
```

Settings UI: ```/home/bob/.config/keyboard-mouse/keyboard-mouse-ui.py```  

Daemon log:  ```/tmp/keyboard-mouse-daemon.log```  

To open settings:```python3 '/home/bob/.config/keyboard-mouse/keyboard-mouse-ui.py'```  

To restart the daemon:```'/home/bob/.config/keyboard-mouse/keyboard-mouse.sh' restart-daemon```  

To kill the daemon:```pkill -f '[k]eyboard-mouse-daemon'```  


<br><br>


## ❓ HOW IT WORKS ❓

Physical Keyboard / Mouse  
&nbsp;&nbsp;&nbsp;│  
&nbsp;&nbsp;&nbsp;▼  
`keyboard-mouse-daemon.py`  
&nbsp;&nbsp;&nbsp;│  
&nbsp;&nbsp;&nbsp;▼  
`ydotool` → Virtual Mouse Input  
&nbsp;&nbsp;&nbsp;│  
&nbsp;&nbsp;&nbsp;▼  
Linux Desktop
<br><br><br>

`keyboard-mouse-ui.py`  
&nbsp;&nbsp;&nbsp;│  
&nbsp;&nbsp;&nbsp;▼  
`~/.config/keyboard-mouse/config.json`
<br><br><br>

`keyboard-mouse.sh`  
&nbsp;&nbsp;&nbsp;│  
&nbsp;&nbsp;&nbsp;├── Daemon management  
&nbsp;&nbsp;&nbsp;├── Settings interface launcher  
&nbsp;&nbsp;&nbsp;└── Process control

## [`keyboard-mouse.sh`]

- Provides command-line controls for managing the Keyboard Mouse daemon.  
  Keyboard Mouse daemon'unu yönetmek için komut satırı kontrolleri sağlar.

- Starts the daemon in the background.  
  Daemon'u arka planda başlatır.

- Stops the running daemon and cleans up its processes.  
  Çalışan daemon'u durdurur ve işlemlerini temizler.

- Restarts the daemon when needed.  
  Gerektiğinde daemon'u yeniden başlatır.

- Launches the graphical settings interface.  
  Grafiksel ayarlar arayüzünü açar.

- Uses runtime state and PID files to help manage daemon instances.  
  Daemon örneklerini yönetmeye yardımcı olmak için çalışma zamanı durum ve PID dosyalarını kullanır.

- Redirects daemon output to a log file for troubleshooting.  
  Hata ayıklamayı kolaylaştırmak için daemon çıktısını bir günlük dosyasına yönlendirir.

## [`keyboard-mouse-daemon.py`]

- Monitors keyboard and mouse events using `evdev`.  
  `evdev` kullanarak klavye ve fare olaylarını izler.

- Detects configured shortcuts for mouse movement, clicking, and scrolling.  
  Fare hareketi, tıklama ve kaydırma için yapılandırılmış kısayolları algılar.

- Simulates mouse actions through `ydotool`.  
  `ydotool` aracılığıyla fare hareketlerini simüle eder.

- Supports adjustable movement speed and fast/slow modes.  
  Ayarlanabilir hareket hızını ve hızlı/yavaş modlarını destekler.

- Manages mouse mode activation and deactivation.  
  Fare modunun etkinleştirilmesini ve devre dışı bırakılmasını yönetir.

## [`keyboard-mouse-ui.py`]

- Provides a graphical interface for customizing keyboard shortcuts.  
  Klavye kısayollarını özelleştirmek için grafiksel bir arayüz sunar.

- Allows customization of movement, clicking, scrolling, and mouse mode controls.  
  Hareket, tıklama, kaydırma ve fare modu kontrollerinin özelleştirilmesini sağlar.

- Saves settings to a persistent JSON configuration file.  
  Ayarları kalıcı bir JSON yapılandırma dosyasına kaydeder.

- Lets users configure controls without manually editing configuration files.  
  Kullanıcıların yapılandırma dosyalarını elle düzenlemeden kontrolleri ayarlamasını sağlar.


# Fast Installation  

sudo pacman -Syu git  
git clone https://github.com/FURK4NGG/keyboard-mouse.git  
cd keyboard-mouse  
chmod +x install.sh  
./install.sh  

## 🔒 License  
<h1 align="center">📜 GPL-3.0 License</h1>
