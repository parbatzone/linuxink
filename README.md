# LinuxInk - Live Presentation Annotation Tool for Linux

A lightweight, hotkey-driven screen annotation overlay for Linux users who conduct live presentations, tutorials, lectures, or CTF walkthroughs. Draw annotations in real-time with a floating toolbar, save screenshots instantly, and toggle between active drawing and passthrough modes seamlessly.

## Features

- **Transparent Fullscreen Overlay** – Annotations appear on top of all windows
- **7 Drawing Tools** – Pen, Line, Rectangle, Circle, Arrow, Highlighter, Text
- **Color Palette** – Red, Green, Blue, Yellow, White, Orange, Cyan
- **Adjustable Stroke Width** – Thin (2px), Medium (5px), Thick (10px)
- **Undo/Redo** – Infinite undo and redo with Ctrl+Z / Ctrl+Y
- **Active/Passthrough Modes** – Toggle mouse passthrough to interact with windows beneath
- **Instant Screenshots** – Save annotated screenshots to Desktop with F9
- **Spotlight Mode** – Darken screen except a circle around cursor (F10)
- **Floating Toolbar** – Collapsible, always-on-top control panel
- **Global Hotkeys** – Work even when overlay has focus

## Installation

### Prerequisites
- Python 3.10 or later
- pip (Python package manager)
- Linux desktop environment with X11 or Wayland support

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/parbatzone/linuxink.git
   cd linuxink
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run LinuxInk:
   ```bash
   python3 linuxink.py
   ```

## Hotkey Reference

| Hotkey | Action |
|--------|--------|
| **F6** | Toggle Active/Passthrough mode |
| **F7** | Clear all annotations |
| **F8** | Undo last annotation |
| **Ctrl+Z** | Undo (alternative) |
| **Ctrl+Y** | Redo |
| **F9** | Save screenshot to Desktop |
| **F10** | Toggle Spotlight mode |
| **Delete** | Delete selected annotation |
| **Esc** | Quit LinuxInk |

## Usage Guide

### Drawing Annotations

1. Select a tool from the toolbar (Pen, Line, Rectangle, etc.)
2. Choose a color and stroke width
3. Click and drag on the screen to draw
4. Release to finish the annotation

### Text Labels

1. Select the **Text** tool
2. Click where you want to place text
3. Type your text and press Enter to confirm

### Selecting & Deleting

1. Switch to **Passthrough** mode (F6) if you need to interact with other windows
2. In **Active** mode, click an existing annotation to select it
3. Press **Delete** to remove the selected annotation

### Spotlight Mode

1. Press **F10** to activate spotlight
2. A darkened overlay appears with a bright circle following your cursor
3. Press **F10** again to deactivate

### Saving Your Work

- Press **F9** to capture the full screen with all annotations
- Screenshots are saved to `~/Desktop/linuxink_YYYY-MM-DD_HH-MM-SS.png`
- A toast notification confirms the save

## Modes Explained

### Active Mode (Default)
- Mouse and keyboard interact with the overlay
- Draw, select, and manipulate annotations
- Toolbar buttons are responsive

### Passthrough Mode
- Click and keyboard input pass through to windows beneath
- Overlay remains visible but you can interact with desktop
- Useful for demonstrating applications while annotations stay on screen
- Hotkeys (F6, F7, etc.) still work in this mode

## Tips & Tricks

- **Quick Mode Switch**: Press F6 to switch between Active and Passthrough without breaking your flow
- **Color Selection**: Click color buttons to instantly change pen color for the next stroke
- **Width Adjustment**: Change stroke width before drawing for immediate effect
- **Non-Destructive Edits**: Undo never erases your work—use Ctrl+Y to redo
- **Layer Annotations**: Draw multiple shapes over each other; the most recent annotation appears on top

## Architecture

LinuxInk is built as a single-file Python application with the following components:

- **Annotation Classes** – Data structures for each drawing tool (Pen, Line, Rectangle, etc.)
- **FloatingToolbar** – Collapsible control panel with tool, color, and width selection
- **AnnotationOverlay** – Main fullscreen transparent window handling drawing and rendering
- **Global Hotkeys** – QShortcut registry for always-active keyboard commands

All code is self-contained in `linuxink.py` with no external dependencies beyond PyQt6.

## License

MIT License – See LICENSE file for details

## Contributing

Contributions welcome! Open an issue to report bugs or suggest features.

## Author

LinuxInk Team – Built for presenters, by presenters.

---

**Need help?** Check the hotkey reference above or press Esc to quit at any time.
