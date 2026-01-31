"""
Input system for configurable, per-player key bindings.
Loads key mappings from JSON and converts key names to pygame key codes.
"""
from __future__ import annotations
import json
import os
from typing import Dict, Tuple
import pygame


class InputHandler:
    """Data-driven input handler supporting per-player key mappings.

    The JSON format uses human-readable key names, which are converted to
    pygame key codes via `pygame.key.key_code` at runtime. This keeps
    the system configurable without hardcoding values in code.

    Example JSON structure:
    {
      "players": {
        "1": {"up": "w", "down": "s", "left": "a", "right": "d"},
        "2": {"up": "up", "down": "down", "left": "left", "right": "right"}
      }
    }
    """

    def __init__(self, mappings: Dict[int, Dict[str, int]]):
        # mappings: {player_id: {action: key_code}}
        self._mappings = mappings

    @staticmethod
    def _convert_names_to_codes(name_map: Dict[str, str]) -> Dict[str, int]:
        """Convert action->keyname map to action->keycode using pygame's key_code.
        Accepts names like "w", "left", "KP_8" etc.
        """
        out: Dict[str, int] = {}
        for action, key_name in name_map.items():
            try:
                out[action] = pygame.key.key_code(key_name)
            except Exception:
                # Fallback: if unknown name, leave unmapped
                out[action] = -1
        return out

    @classmethod
    def from_file(cls, path: str) -> "InputHandler":
        """Load key mappings from JSON file, or generate defaults if missing.
        This function does not hardcode key values in code—defaults are
        written to a JSON file so users can edit them freely.
        """
        if not os.path.exists(path):
            # Create default file with readable names
            default = cls.default_bindings()
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        mappings: Dict[int, Dict[str, int]] = {}
        players = data.get("players", {})
        for pid_str, actions in players.items():
            pid = int(pid_str)
            mappings[pid] = cls._convert_names_to_codes(actions)
        return cls(mappings)

    @staticmethod
    def default_bindings() -> Dict:
        """Return default readable key-name bindings for up to 4 players.
        These are stored in JSON (not hardcoded in runtime logic).
        """
        return {
            "players": {
                "1": {"up": "w", "down": "s", "left": "a", "right": "d"},
                "2": {"up": "up", "down": "down", "left": "left", "right": "right"},
                "3": {"up": "i", "down": "k", "left": "j", "right": "l"},
                "4": {"up": "KP_8", "down": "KP_5", "left": "KP_4", "right": "KP_6"}
            }
        }

    def get_direction(self, player_id: int, pressed: Tuple[bool, ...]) -> Tuple[float, float]:
        """Return movement direction (dx, dy) for a player based on pressed keys.
        Direction is normalized so diagonal speed matches straight-line speed.
        """
        mapping = self._mappings.get(player_id, {})
        up = mapping.get("up", -1)
        down = mapping.get("down", -1)
        left = mapping.get("left", -1)
        right = mapping.get("right", -1)

        dx = 0
        dy = 0
        if left != -1 and left < len(pressed) and pressed[left]:
            dx -= 1
        if right != -1 and right < len(pressed) and pressed[right]:
            dx += 1
        if up != -1 and up < len(pressed) and pressed[up]:
            dy -= 1
        if down != -1 and down < len(pressed) and pressed[down]:
            dy += 1

        # Normalize diagonal movement
        if dx != 0 and dy != 0:
            return (dx * 0.70710678, dy * 0.70710678)  # 1/sqrt(2)
        return (float(dx), float(dy))
