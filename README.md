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
