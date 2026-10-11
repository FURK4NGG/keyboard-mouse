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

`keyboard-mouse-ui.py`  
&nbsp;&nbsp;&nbsp;│  
&nbsp;&nbsp;&nbsp;▼  
`~/.config/keyboard-mouse/config.json`

`keyboard-mouse.sh`  
│  
├── Starts and stops the daemon  
├── Restarts the daemon  
├── Opens the settings interface  
└── Manages daemon process state

## [`keyboard-mouse.sh`]
- Provides command-line controls for managing the Keyboard Mouse daemon.
- Starts the daemon in the background.
- Stops the running daemon and handles its process cleanup.
- Restarts the daemon when needed.
- Launches the graphical settings interface.
- Uses PID and runtime state files to help manage daemon instances.
- Redirects daemon output to a log file for troubleshooting.

## [`keyboard-mouse-daemon.py`]
- Reads keyboard and mouse events using `evdev`.
- Detects configured shortcuts for mouse movement, clicking, and scrolling.
- Simulates mouse actions through `ydotool`.
- Supports configurable movement speed and mouse mode controls.

## [`keyboard-mouse-ui.py`]
- Provides a graphical interface for customizing key bindings.
- Configures mouse movement, clicks, scrolling, and mode shortcuts.
- Saves settings to a JSON configuration file.


# Fast Installation  

sudo pacman -Syu git  
git clone https://github.com/FURK4NGG/keyboard-mouse.git  
cd keyboard-mouse  
chmod +x install.sh  
./install.sh  

## 🔒 License  
<h1 align="center">📜 GPL-3.0 License</h1>
