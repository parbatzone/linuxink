<p align="center">
  <img src="assets/logo.png" width="140" height="140">
</p>

<h1 align="center">LinuxInk - Screen Annotation Tool</h1>

<p align="center">
  <b>Created by Limox</b>
</p>

<p align="center">
  LinuxInk is a lightweight, high-performance screen annotation tool for Linux. It lets you draw over any application, highlight areas, and take annotated screenshots with ease.
</p>

---

## Features

- Multiple Tools: Pen, Highlighter, Eraser, Line, Rectangle, Circle, Triangle, Star, Arrow, Text, and Laser Pointer
- Customizable: Adjust colors, brush size, and opacity in real time
- Global Hotkeys: Instantly toggle the drawing overlay
- Screenshots: Capture screen with annotations and save as PNG
- Modern UI: Sleek, draggable toolbar with dark theme
- History Support: Undo and redo drawing actions

---

## Installation

### Prerequisites

- Python 3.10+
- PyQt6
- Linux (X11 or Wayland with XWayland support)

### Fast Install (Ubuntu / Debian / Kali / Mint)

1. Extract the ZIP or clone the repository
2. Open terminal in project folder
3. Run:

```bash
sudo bash install.sh
```

---

## Usage

### Run the app

```bash
linuxink
```

or from application menu: **LinuxInk**

---

## Controls

| Action | Shortcut |
|--------|----------|
| Toggle Overlay | Ctrl + Shift + D |
| Undo | Ctrl + Z |
| Redo | Ctrl + Y |
| Clear All | Ctrl + Shift + X |
| Screenshot | Ctrl + Shift + S |
| Pen | P |
| Highlighter | H |
| Eraser | E |
| Line | L |
| Rectangle | R |
| Circle | C |
| Arrow | A |
| Text | T |
| Triangle | Shift + T |
| Star | Shift + S |
| Laser Pointer | Space |
| Exit | Esc |

---

## GitHub Setup

Clone and run:

```bash
git clone https://github.com/parbatzone/linuxink.git
cd linuxink
pip install PyQt6
python3 main.py
```

---

## Advanced Features

- Geometric drawing tools (Triangle, Star)
- Laser pointer mode for presentations
- Transparent screen overlay system

---

## File Structure

```text
linuxink/
├── main.py
├── install.sh
├── linuxink.desktop
├── README.md
├── assets/
│   ├── style.qss
│   └── logo.png
└── src/
    ├── core/
    │   ├── app_controller.py
    │   ├── config_manager.py
    │   └── hotkey_manager.py
    ├── ui/
    │   ├── overlay_window.py
    │   └── toolbar.py
    └── rendering/
        └── canvas.py
```

---

## Troubleshooting

- Wayland issue (no transparency):

```bash
QT_QPA_PLATFORM=xcb linuxink
```

- Permission denied:

```bash
sudo bash install.sh
```

---

*Created and maintained by Limox*
