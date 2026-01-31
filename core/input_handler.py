"""
Input system for configurable, per-player key bindings.
Loads key mappings from JSON using symbolic key names (not characters).
Supports letters, arrows, and numpad keys with consistent behavior.
"""
from __future__ import annotations
import json
import os
from typing import Dict, Tuple, Optional, Set
import pygame


def _normalize_key_name(name: str) -> Optional[str]:
    """Normalize a human-readable key name to a pygame constant name.

    Accepted examples (case-insensitive):
    - Letters: "A", "K_A", "a" → pygame.K_a
    - Arrows: "LEFT", "K_LEFT", "ArrowLeft" → pygame.K_LEFT
    - Numpad: "KP_8", "K_KP8", "NUMPAD8", "KP8" → pygame.K_KP8

    Returns the pygame attribute name (e.g., "K_a", "K_LEFT", "K_KP8"),
    or None if not recognized.
    """
    if not name:
        return None
    s = name.strip()
    s_upper = s.upper()

    # Arrow synonyms
    arrow_map = {
        "LEFT": "K_LEFT",
        "ARROWLEFT": "K_LEFT",
        "RIGHT": "K_RIGHT",
        "ARROWRIGHT": "K_RIGHT",
        "UP": "K_UP",
        "ARROWUP": "K_UP",
        "DOWN": "K_DOWN",
        "ARROWDOWN": "K_DOWN",
    }
    if s_upper in arrow_map:
        return arrow_map[s_upper]

    # Numpad synonyms: KP_0..KP_9 and common variants
    if s_upper.startswith("NUMPAD"):
        digit = s_upper.replace("NUMPAD", "")
        if digit.isdigit():
            return f"K_KP{digit}"
    if s_upper.startswith("KP_"):
        tail = s_upper[3:]
        if tail.isdigit():
            return f"K_KP{tail}"
    if s_upper.startswith("K_KP"):
        tail = s_upper[4:]
        if tail.isdigit():
            return f"K_KP{tail}"
    # Compact form like "KP8"
    if s_upper.startswith("KP") and s_upper[2:].isdigit():
        return f"K_KP{s_upper[2:]}"

    # Pygame-style explicit names
    if s_upper.startswith("K_"):
        # Special-case letters: pygame uses lowercase (K_a)
        if len(s_upper) == 3 and s_upper[2].isalpha():
            return f"K_{s_upper[2].lower()}"
        return s_upper

    # Single letter (symbolic), prefer constants not ASCII checks
    if len(s_upper) == 1 and s_upper.isalpha():
        return f"K_{s_upper.lower()}"

    # As a final fallback, attempt pygame.key.key_code downstream
    return None


class InputHandler:
    """Data-driven input handler supporting per-player key mappings.

    The JSON format uses human-readable key names, which are converted to
    pygame key codes via `pygame.key.key_code` at runtime. This keeps
    the system configurable without hardcoding values in code.

        Example JSON structure (symbolic names preferred):
    {
            "players": {
                "1": {"up": "K_W", "down": "K_S", "left": "K_A", "right": "K_D"},
                "2": {"up": "K_UP", "down": "K_DOWN", "left": "K_LEFT", "right": "K_RIGHT"}
            }
    }
    """

    def __init__(self, mappings: Dict[int, Dict[str, int]]):
        # mappings: {player_id: {action: key_code}}
        self._mappings = mappings
        # Internal pressed set using unified pygame keycodes (event.key)
        self._pressed_keys: Set[int] = set()

    def handle_event(self, event: pygame.event.Event):
        """Track pressed keys from KEYDOWN/KEYUP events using pygame keycodes."""
        if event.type == pygame.KEYDOWN:
            self._pressed_keys.add(event.key)
        elif event.type == pygame.KEYUP:
            self._pressed_keys.discard(event.key)

    @staticmethod
    def _convert_names_to_codes(name_map: Dict[str, str]) -> Dict[str, int]:
        """Convert action->keyname map to action->pygame keycode (K_*).

        - Normalizes symbolic names (e.g., "K_LEFT", "K_a", "K_KP8").
        - Uses pygame keycodes so menu events and gameplay share identifiers.
        - Avoids character/ASCII/ord-based logic entirely.
        """
        out: Dict[str, int] = {}
        for action, key_name in name_map.items():
            code = -1
            attr_name = _normalize_key_name(key_name)
            if attr_name:
                try:
                    code = getattr(pygame, attr_name)
                except Exception:
                    code = -1
            else:
                try:
                    code = pygame.key.key_code(str(key_name))
                except Exception:
                    code = -1
            out[action] = code
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
                "1": {"up": "K_W", "down": "K_S", "left": "K_A", "right": "K_D"},
                "2": {"up": "K_UP", "down": "K_DOWN", "left": "K_LEFT", "right": "K_RIGHT"},
                "3": {"up": "K_I", "down": "K_K", "left": "K_J", "right": "K_L"},
                "4": {"up": "K_KP8", "down": "K_KP5", "left": "K_KP4", "right": "K_KP6"}
            }
        }

    def is_action_pressed(self, player_id: int, action: str, pressed: Optional[Tuple[bool, ...]]) -> bool:
        mapping = self._mappings.get(player_id, {})
        key = mapping.get(action, -1)
        if pressed is None:
            return (key != -1 and key in self._pressed_keys)
        return (key != -1 and key < len(pressed) and pressed[key])

    def get_axes(self, player_id: int, pressed: Optional[Tuple[bool, ...]]) -> Tuple[int, int]:
        """Return discrete axes (-1,0,1) for x,y.
        Useful when you don't want normalized diagonals.
        """
        mapping = self._mappings.get(player_id, {})
        up = mapping.get("up", -1)
        down = mapping.get("down", -1)
        left = mapping.get("left", -1)
        right = mapping.get("right", -1)

        dx = 0
        dy = 0
        if pressed is None:
            if left != -1 and left in self._pressed_keys:
                dx -= 1
            if right != -1 and right in self._pressed_keys:
                dx += 1
            if up != -1 and up in self._pressed_keys:
                dy -= 1
            if down != -1 and down in self._pressed_keys:
                dy += 1
        else:
            if left != -1 and left < len(pressed) and pressed[left]:
                dx -= 1
            if right != -1 and right < len(pressed) and pressed[right]:
                dx += 1
            if up != -1 and up < len(pressed) and pressed[up]:
                dy -= 1
            if down != -1 and down < len(pressed) and pressed[down]:
                dy += 1
        return (dx, dy)

    def get_direction(self, player_id: int, pressed: Optional[Tuple[bool, ...]]) -> Tuple[float, float]:
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
        if pressed is None:
            if left != -1 and left in self._pressed_keys:
                dx -= 1
            if right != -1 and right in self._pressed_keys:
                dx += 1
            if up != -1 and up in self._pressed_keys:
                dy -= 1
            if down != -1 and down in self._pressed_keys:
                dy += 1
        else:
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
