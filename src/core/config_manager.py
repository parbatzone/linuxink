"""
Configuration manager - loads/saves user settings
"""

import json
import os
from pathlib import Path


DEFAULT_CONFIG = {
    "hotkeys": {
        "toggle_overlay": "Ctrl+Shift+D",
        "undo": "Ctrl+Z",
        "redo": "Ctrl+Y",
        "clear": "Ctrl+Shift+X",
        "screenshot": "Ctrl+Shift+S",
        "pen": "P",
        "highlighter": "H",
        "eraser": "E",
        "line": "L",
        "rectangle": "R",
        "circle": "C",
        "arrow": "A",
        "text": "T",
    },
    "defaults": {
        "color": "#FF0000",
        "brush_size": 4,
        "opacity": 1.0,
        "tool": "pen",
    },
    "ui": {
        "toolbar_position": "left",
        "toolbar_opacity": 0.92,
        "show_tooltips": True,
    },
    "performance": {
        "anti_aliasing": True,
        "tablet_pressure": True,
        "smooth_curves": True,
    }
}


class ConfigManager:
    def __init__(self):
        self.config_dir = Path.home() / ".config" / "linuxink"
        self.config_file = self.config_dir / "config.json"
        self.config = {}
        self.load()

    def load(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    loaded = json.load(f)
                self.config = self._merge(DEFAULT_CONFIG, loaded)
            except Exception:
                self.config = DEFAULT_CONFIG.copy()
        else:
            self.config = DEFAULT_CONFIG.copy()
            self.save()

    def save(self):
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")

    def get(self, *keys, default=None):
        val = self.config
        for key in keys:
            if isinstance(val, dict) and key in val:
                val = val[key]
            else:
                return default
        return val

    def set(self, value, *keys):
        d = self.config
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value
        self.save()

    def _merge(self, base, override):
        result = base.copy()
        for key, val in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(val, dict):
                result[key] = self._merge(result[key], val)
            else:
                result[key] = val
        return result
