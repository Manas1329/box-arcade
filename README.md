# Box Arcade Framework (Pygame)

A modular local-multiplayer arcade framework using rectangular box characters (`pygame.Rect`). First game implemented: **TAG**.

## Features
- Python + Pygame
- All characters are colored boxes (no sprites/assets)
- 1–4 human players + optional bots (same keyboard)
- Configurable per-player key bindings via `keybindings.json`
- Clean OOP: Game loop, Players, InputHandler, Collision, Timer/Score, Scenes
- Scene flow: Menu → Game → Results

## Run
Ensure Python 3.9+ is installed. Install pygame if needed:

```bash
python -m pip install pygame
```

Start the game:

```bash
python main.py
```

## Key Bindings
Editable in `keybindings.json`. Use readable names: `w`, `left`, `up`, `i`, `j`, `k`, `l`, `KP_8`, `KP_4`, `KP_5`, `KP_6`.
Bindings are loaded at runtime and converted to pygame key codes; values are not hardcoded in code.

## Game: TAG
- One player starts as **IT**.
- Colliding with another player transfers **IT** status.
- Match is timer-based; players accumulate seconds spent as IT.
- Fewer IT seconds wins.
- Movement is smooth and clamped to boundaries.
- HUD shows current IT player and remaining time.

## Controls (Menu)
- Left/Right: adjust humans (1–4)
- Up/Down: adjust bots (0–4)
- PageUp/PageDown: match time (10–300s)
- Enter: start, Esc: quit/back

## Files
- `main.py`: Game loop + scenes
- `input.py`: JSON-driven key mapping
- `player.py`: `HumanPlayer` and `BotPlayer`
- `games/tag.py`: Tag rules, collision, timer & scoring

## Extend
Add new games under `games/`. Reuse `Player` and `InputHandler`. Keep physics in `pygame.Rect`.
