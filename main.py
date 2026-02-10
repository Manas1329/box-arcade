"""
Pygame-based local multiplayer arcade framework using rectangular box characters.
Includes: Game Loop Manager, InputHandler, Player classes, collision, timer/score,
scene management (menu → game → results) and TAG game implementation.
"""
from __future__ import annotations
import os
import sys
import json
from typing import List, Any
import random
import pygame

from core.input_handler import InputHandler
from entities.player import Player, HumanPlayer, BotPlayer
from games.tag import TagGame
from games.survival import SurvivalGame, SurvivalPvpGame
from games.snake import SnakeGame
from games.control_zone import ControlZoneGame
from games.trail_lock import TrailLockGame
from games.tictactoe import TicTacToeGame
from games.sudoku import SudokuGame
from games.tictactoe import TicTacToeGame
from games.brick_breaker import BrickBreakerGame
from games.simon_grid import SimonGridGame
from games.maze_runner import MazeRunnerGame
from games.whack_a_box import WhackABoxGame
from games.box_stack import BoxStackGame
from games.flappy_box import FlappyBoxGame
from games.tetris_box import TetrisBoxGame
from games.zip_box import ZipBoxGame

# Window settings (upscaled for side-view platformer arenas)
WIDTH, HEIGHT = 1280, 720
BG_COLOR = (20, 20, 30)

# Player colors (distinct boxes)
PLAYER_COLORS = [
    (240, 84, 84),   # red
    (84, 160, 240),  # blue
    (84, 240, 120),  # green
    (240, 200, 84),  # yellow
    (200, 84, 240),  # purple
    (84, 240, 220),  # cyan
    (240, 140, 140), # salmon
    (140, 240, 140), # light green
]


class Scene:
    def handle_event(self, event: pygame.event.Event):
        pass

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        pass


class SceneManager:
    def __init__(self, initial: Scene):
        self.current = initial

    def set(self, scene: Scene):
        self.current = scene


class LobbyState:
    def __init__(self):
        self.mode: str | None = None  # 'pvp' or 'single'
        self.game: str | None = None  # e.g., 'tag'
        self.num_players: int = 2     # PvP setup (2–4)
        # Tag-specific settings
        self.tag_double_jump: bool = False
        self.tag_map_index: int = 0
        self.tag_enable_moving: bool = False
        self.tag_enable_dropthrough: bool = False
        self.tag_enable_speed: bool = False


class BaseMenuScene(Scene):
    """Reusable rectangular box-based menu scene.

    Keyboard-only navigation with Up/Down, Enter for select, Esc for back.
    Draws centered boxes for items and highlights the selected one.
    """

    def __init__(self, app: "App", title: str, items: list[str]):
        self.app = app
        self.title = title
        self.items = items
        self.selected = 0
        self.font = app.font
        self.big_font = app.big_font

        # Box layout
        self.box_w = 420
        self.box_h = 44
        self.box_gap = 14
        self.box_color = (70, 70, 90)
        self.box_highlight = (120, 120, 180)
        self.box_outline = (180, 180, 220)

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if not self.items:
                return
            # Support arrows and WASD/AD-style navigation
            if event.key in (pygame.K_UP, pygame.K_w, pygame.K_a):
                self.selected = (self.selected - 1) % len(self.items)
            elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_d):
                self.selected = (self.selected + 1) % len(self.items)
            elif event.key == pygame.K_RETURN:
                self.handle_select(self.selected)
            elif event.key == pygame.K_ESCAPE:
                self.handle_back()
        elif event.type == pygame.MOUSEMOTION:
            # Hover to change selection
            if not self.items:
                return
            rects, _, _, _, _ = self._layout()
            mx, my = event.pos
            for i, r in enumerate(rects):
                if r.collidepoint(mx, my):
                    self.selected = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Click to activate
            if not self.items:
                return
            rects, _, _, _, _ = self._layout()
            mx, my = event.pos
            for i, r in enumerate(rects):
                if r.collidepoint(mx, my):
                    self.selected = i
                    self.handle_select(i)
                    break
        elif event.type == pygame.MOUSEWHEEL:
            if not self.items:
                return
            if event.y > 0:
                self.selected = (self.selected - 1) % len(self.items)
            elif event.y < 0:
                self.selected = (self.selected + 1) % len(self.items)

    def handle_select(self, index: int):
        pass

    def handle_back(self):
        # Default: go to Home
        self.app.scene_manager.set(HomeScene(self.app))

    def update(self, dt: float):
        pass

    def _menu_rects(self) -> list[pygame.Rect]:
        total_h = len(self.items) * self.box_h + (len(self.items) - 1) * self.box_gap
        start_y = (HEIGHT // 2) - (total_h // 2)
        rects = []
        for i in range(len(self.items)):
            x = WIDTH // 2 - self.box_w // 2
            y = start_y + i * (self.box_h + self.box_gap)
            rects.append(pygame.Rect(x, y, self.box_w, self.box_h))
        return rects

    def _layout(self):
        """Compute menu rects and shared title/footer layout.

        Returns (rects, title_surf, title_pos, hint_surf, hint_pos).
        Used by both draw and mouse hit-testing to keep geometry in sync.
        """
        rects = self._menu_rects()

        title = self.big_font.render(self.title, True, (255, 255, 255))
        title_y = 90
        title_pos = (WIDTH // 2 - title.get_width() // 2, title_y)

        hint = self.font.render("Up/Down: Navigate  Enter: Select  Esc: Back", True, (180, 180, 180))
        hint_y = HEIGHT - 60
        hint_pos = (WIDTH // 2 - hint.get_width() // 2, hint_y)

        # Ensure menu doesn't overlap the title/footer
        if rects:
            min_start = title_y + title.get_height() + 30
            dy_down = max(0, min_start - rects[0].top)
            if dy_down > 0:
                rects = [r.move(0, dy_down) for r in rects]
            bottom_max = hint_y - 20
            if rects[-1].bottom > bottom_max:
                over = rects[-1].bottom - bottom_max
                rects = [r.move(0, -over) for r in rects]
                dy_down = max(0, min_start - rects[0].top)
                if dy_down > 0:
                    rects = [r.move(0, dy_down) for r in rects]

        return rects, title, title_pos, hint, hint_pos

    def draw(self, surface: pygame.Surface):
        surface.fill(BG_COLOR)
        rects, title, title_pos, hint, hint_pos = self._layout()

        # Title
        surface.blit(title, title_pos)
        for i, rect in enumerate(rects):
            is_sel = (i == self.selected)
            fill = self.box_highlight if is_sel else self.box_color
            pygame.draw.rect(surface, fill, rect)
            pygame.draw.rect(surface, self.box_outline, rect, 2)

            label = self.items[i]
            surf = self.font.render(label, True, (240, 240, 240))
            surface.blit(surf, (rect.centerx - surf.get_width()//2, rect.centery - surf.get_height()//2))
        surface.blit(hint, hint_pos)


class HomeScene(BaseMenuScene):
    def __init__(self, app: "App"):
        items = ["Play", "Controls", "Quit"]
        super().__init__(app, "BOX ARCADE", items)

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        # Show current selections
        mode = self.app.lobby.mode or "(none)"
        game = self.app.lobby.game or "(none)"
        status = self.font.render(f"Mode: {mode}   Game: {game}", True, (200, 200, 200))
        surface.blit(status, (WIDTH//2 - status.get_width()//2, 150))

    def handle_select(self, index: int):
        if self.items[index] == "Play":
            self.app.scene_manager.set(ModeSelectScene(self.app))
        elif self.items[index] == "Controls":
            self.app.scene_manager.set(ControlsScene(self.app))
        elif self.items[index] == "Quit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def handle_back(self):
        pygame.event.post(pygame.event.Event(pygame.QUIT))


class ModeSelectScene(BaseMenuScene):
    def __init__(self, app: "App"):
        items = ["Single Player", "PvP (Local)"]
        super().__init__(app, "Mode Select", items)

    def handle_select(self, index: int):
        label = self.items[index]
        if label.startswith("Single"):
            self.app.lobby.mode = "single"
            # Use dedicated card-based selector for single player games
            self.app.scene_manager.set(SinglePlayerGameSelectScene(self.app))
        elif label.startswith("PvP"):
            self.app.lobby.mode = "pvp"
            # Use card-based selector for PvP games as well
            self.app.scene_manager.set(PvpGameSelectScene(self.app))


class GameSelectScene(BaseMenuScene):
    def __init__(self, app: "App"):
        mode = app.lobby.mode or "single"
        # This menu is now used only for PvP selection; single-player
        # uses SinglePlayerGameSelectScene.
        if mode != "pvp":
            mode = "pvp"
        items = ["Tag (Boxes)", "Survival (PvP)", "Control Zone", "TrailLock", "Tic Tac Toe", "Back"]
        super().__init__(app, "PvP Game Select", items)

    def handle_select(self, index: int):
        label = self.items[index]
        mode = self.app.lobby.mode or "single"
        if label == "Back":
            self.app.scene_manager.set(ModeSelectScene(self.app))
            return
        if mode == "pvp" and label.startswith("Tag"):
            self.app.lobby.game = "tag"
            self.app.scene_manager.set(PlayerSetupScene(self.app))
        elif mode == "pvp" and label.startswith("Survival"):
            self.app.lobby.game = "survival_pvp"
            self.app.scene_manager.set(PlayerSetupScene(self.app))
        elif mode == "pvp" and label.startswith("Control Zone"):
            self.app.lobby.game = "control_zone"
            self.app.scene_manager.set(PlayerSetupScene(self.app))
        elif mode == "pvp" and label.startswith("TrailLock"):
            self.app.lobby.game = "trail_lock"
            self.app.scene_manager.set(PlayerSetupScene(self.app))
        elif mode == "pvp" and label.startswith("Tic Tac Toe"):
            self.app.lobby.game = "ttt_pvp"
            self.app.launch_ttt_pvp()


class PvpGameSelectScene(Scene):
    """Card-based selector for local PvP games.

    Mirrors the single-player card layout but launches PvP modes.
    """

    def __init__(self, app: "App"):
        self.app = app
        self.font = app.font
        self.big_font = app.big_font
        self.card_font = pygame.font.SysFont("consolas", 18)

        # Available PvP games with short descriptions.
        self.cards: list[dict[str, Any]] = [
            {"id": "tag", "title": "Tag (Boxes)", "desc": "Side-view tag arena.", "mode": "PvP"},
            {"id": "survival_pvp", "title": "Survival (PvP)", "desc": "Last box standing wins.", "mode": "PvP"},
            {"id": "control_zone", "title": "Control Zone", "desc": "Hold the zone to score.", "mode": "PvP"},
            {"id": "trail_lock", "title": "TrailLock", "desc": "Box Tron-style trails.", "mode": "PvP"},
            {"id": "ttt_pvp", "title": "Tic Tac Toe (PvP)", "desc": "Classic 2-player grid.", "mode": "PvP"},
        ]

        # Use two columns for consistency with single-player cards
        self.cols = 2
        self.selected_index = 0
        self.card_rects: list[pygame.Rect] = []
        self._build_layout()

        if self.card_rects:
            cx, cy = self.card_rects[0].center
        else:
            cx, cy = WIDTH // 2, HEIGHT // 2
        self.highlight_center = [float(cx), float(cy)]

    def _build_layout(self):
        margin_x = 80
        margin_top = 140
        margin_bottom = 90
        region = pygame.Rect(margin_x, margin_top,
                             WIDTH - 2 * margin_x,
                             HEIGHT - margin_top - margin_bottom)
        gap_x = 22
        gap_y = 22
        card_w = (region.width - gap_x * (self.cols - 1)) // self.cols
        rows = (len(self.cards) + self.cols - 1) // self.cols
        card_h = (region.height - gap_y * (rows - 1)) // max(1, rows)
        self.card_rects.clear()
        for i, _ in enumerate(self.cards):
            row = i // self.cols
            col = i % self.cols
            x = region.left + col * (card_w + gap_x)
            y = region.top + row * (card_h + gap_y)
            self.card_rects.append(pygame.Rect(x, y, card_w, card_h))

    def _fit_text(self, text: str, max_width: int) -> str:
        if not text:
            return text
        surf = self.card_font.render(text, True, (0, 0, 0))
        if surf.get_width() <= max_width:
            return text
        ellipsis = "..."
        trimmed = text
        while trimmed and self.card_font.render(trimmed + ellipsis, True, (0, 0, 0)).get_width() > max_width:
            trimmed = trimmed[:-1]
        return trimmed + ellipsis if trimmed else ellipsis

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.scene_manager.set(ModeSelectScene(self.app))
                return
            if not self.card_rects:
                return
            cols = self.cols
            idx = self.selected_index
            row = idx // cols
            col = idx % cols
            if event.key in (pygame.K_LEFT, pygame.K_a):
                if col > 0:
                    idx -= 1
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                if col < cols - 1 and idx + 1 < len(self.cards):
                    idx += 1
            elif event.key in (pygame.K_UP, pygame.K_w):
                if row > 0:
                    idx -= cols
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                if idx + cols < len(self.cards):
                    idx += cols
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate(self.selected_index)
            self.selected_index = max(0, min(idx, len(self.cards) - 1))
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            for i, r in enumerate(self.card_rects):
                if r.collidepoint(mx, my):
                    self.selected_index = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, r in enumerate(self.card_rects):
                if r.collidepoint(mx, my):
                    self.selected_index = i
                    self._activate(i)
                    break
        elif event.type == pygame.MOUSEWHEEL:
            if not self.card_rects:
                return
            cols = self.cols
            idx = self.selected_index
            if event.y > 0 and idx - cols >= 0:
                idx -= cols
            elif event.y < 0 and idx + cols < len(self.cards):
                idx += cols
            self.selected_index = idx

    def _activate(self, index: int):
        if index < 0 or index >= len(self.cards):
            return
        card = self.cards[index]
        # Step 2: go to PvP game detail page
        self.app.scene_manager.set(PvpGameDetailScene(self.app, card))

    def update(self, dt: float):
        if not self.card_rects or self.selected_index >= len(self.card_rects):
            return
        target = self.card_rects[self.selected_index].center
        speed = 12.0
        for i in (0, 1):
            delta = target[i] - self.highlight_center[i]
            self.highlight_center[i] += delta * min(1.0, speed * dt)

    def draw(self, surface: pygame.Surface):
        surface.fill(BG_COLOR)
        title = self.big_font.render("PvP (Local)", True, (255, 255, 255))
        title_y = 80
        surface.blit(title, (WIDTH // 2 - title.get_width() // 2, title_y))

        hint = self.font.render("Arrows/Mouse: Select  Enter/Click: Start  Esc: Back", True, (180, 180, 180))
        hint_y = HEIGHT - 50
        surface.blit(hint, (WIDTH // 2 - hint.get_width() // 2, hint_y))

        base_col = (50, 50, 80)
        hover_col = (90, 90, 140)
        outline_col = (180, 180, 230)

        for i, (card, rect) in enumerate(zip(self.cards, self.card_rects)):
            is_sel = (i == self.selected_index)
            fill = hover_col if is_sel else base_col
            pygame.draw.rect(surface, fill, rect)
            pygame.draw.rect(surface, outline_col, rect, 2)
            # Compact card: only render game title centered in the box
            max_text_w = rect.width - 24
            title_text = self._fit_text(card["title"], max_text_w)
            t_surf = self.card_font.render(title_text, True, (240, 240, 240))
            t_x = rect.centerx - t_surf.get_width() // 2
            t_y = rect.centery - t_surf.get_height() // 2
            surface.blit(t_surf, (t_x, t_y))

        if self.card_rects:
            hw = self.card_rects[0].width + 16
            hh = self.card_rects[0].height + 16
            frame = pygame.Rect(0, 0, hw, hh)
            frame.center = (int(self.highlight_center[0]), int(self.highlight_center[1]))
            pygame.draw.rect(surface, (230, 230, 255), frame, 3)


class PvpGameDetailScene(BaseMenuScene):
    """Step 2: detail page for a PvP game.

    Shows title, description, per-player controls, and Start/Back.
    """

    def __init__(self, app: "App", card: dict[str, Any]):
        items = ["Start", "Back"]
        super().__init__(app, "PvP — Game", items)
        self.card = card

    def _load_bindings(self) -> dict:
        cfg_path = os.path.join(os.path.dirname(__file__), "keybindings.json")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"players": {}}

    def handle_select(self, index: int):
        label = self.items[index]
        if label == "Start":
            self._start_game()
        elif label == "Back":
            # Return to the PvP grid
            self.app.scene_manager.set(PvpGameSelectScene(self.app))

    def _start_game(self):
        cid = self.card.get("id", "")
        self.app.lobby.mode = "pvp"
        if cid == "tag":
            self.app.lobby.game = "tag"
            self.app.scene_manager.set(PlayerSetupScene(self.app))
        elif cid == "survival_pvp":
            self.app.lobby.game = "survival_pvp"
            self.app.scene_manager.set(PlayerSetupScene(self.app))
        elif cid == "control_zone":
            self.app.lobby.game = "control_zone"
            self.app.scene_manager.set(PlayerSetupScene(self.app))
        elif cid == "trail_lock":
            self.app.lobby.game = "trail_lock"
            self.app.scene_manager.set(PlayerSetupScene(self.app))
        elif cid == "ttt_pvp":
            self.app.lobby.game = "ttt_pvp"
            self.app.launch_ttt_pvp()

    def draw(self, surface: pygame.Surface):
        # Base menu draws title, Start/Back, and hint
        super().draw(surface)

        # Info panel box
        panel_w = WIDTH - 200
        panel_h = 300
        panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
        panel_rect.center = (WIDTH // 2, HEIGHT // 2)
        pygame.draw.rect(surface, (40, 40, 70), panel_rect)
        pygame.draw.rect(surface, (160, 160, 210), panel_rect, 2)

        title_text = self.card.get("title", "")
        desc_text = self.card.get("desc", "")

        y = panel_rect.top + 20
        title_surf = self.big_font.render(title_text, True, (245, 245, 255))
        surface.blit(title_surf, (panel_rect.centerx - title_surf.get_width() // 2, y))
        y += title_surf.get_height() + 12

        if desc_text:
            desc_surf = self.font.render(desc_text, True, (225, 225, 235))
            surface.blit(desc_surf, (panel_rect.centerx - desc_surf.get_width() // 2, y))
            y += desc_surf.get_height() + 18

        # Controls: show up to 4 players' bindings
        cfg = self._load_bindings()
        players = cfg.get("players", {})
        for pnum in range(1, 5):
            pid = str(pnum)
            actions = players.get(pid, {})
            line = (
                f"P{pid}: up={actions.get('up','')} down={actions.get('down','')} "
                f"left={actions.get('left','')} right={actions.get('right','')}"
            )
            ctrl_surf = self.font.render(line, True, (210, 210, 230))
            surface.blit(ctrl_surf, (panel_rect.left + 40, y))
            y += ctrl_surf.get_height() + 4


class SinglePlayerGameSelectScene(Scene):
    """Card-based selector for single-player games.

    Displays fixed-size game cards in a grid with keyboard and mouse
    navigation and a smooth-moving highlight frame.
    """

    def __init__(self, app: "App"):
        self.app = app
        self.font = app.font
        self.big_font = app.big_font
        # Slightly smaller font for card content so text fits cleanly.
        self.card_font = pygame.font.SysFont("consolas", 18)

        # Define available single-player games with metadata.
        # Keep descriptions very short so they fit comfortably on one line.
        self.cards: list[dict[str, Any]] = [
            {"id": "snake", "title": "Snake", "desc": "Classic snake.", "mode": "Singleplayer"},
            {"id": "brick_breaker", "title": "Brick Breaker", "desc": "Break falling bricks.", "mode": "Singleplayer"},
            {"id": "whack_a_box", "title": "Whack-a-Box", "desc": "Hit popping boxes.", "mode": "Singleplayer"},
            {"id": "box_stack", "title": "Box Stack", "desc": "Stack moving boxes.", "mode": "Singleplayer"},
            {"id": "simon_grid", "title": "Simon Grid", "desc": "Repeat the pattern.", "mode": "Singleplayer"},
            {"id": "maze_runner", "title": "Maze Runner", "desc": "Escape the maze.", "mode": "Singleplayer"},
            {"id": "ttt_single", "title": "Tic Tac Toe (Solo)", "desc": "Beat the bot.", "mode": "Singleplayer"},
            {"id": "sudoku", "title": "Sudoku", "desc": "Solve 9x9 puzzles.", "mode": "Singleplayer"},
            {"id": "survival", "title": "Survival", "desc": "Dodge hazards.", "mode": "Singleplayer"},
            {"id": "flappy_box", "title": "Flappy Box", "desc": "Flap through pipe gaps.", "mode": "Singleplayer"},
            {"id": "tetris_box", "title": "Tetris Box", "desc": "Clear lines with falling blocks.", "mode": "Singleplayer"},
            {"id": "zip_box", "title": "Zip Box", "desc": "Connect numbers with paths.", "mode": "Singleplayer"},
        ]

        # Use two columns so each card has more horizontal space
        # for its title and description text.
        self.cols = 2
        self.selected_index = 0
        self.card_rects: list[pygame.Rect] = []
        self._build_layout()

        # Highlight frame center for smooth movement
        if self.card_rects:
            cx, cy = self.card_rects[0].center
        else:
            cx, cy = WIDTH // 2, HEIGHT // 2
        self.highlight_center = [float(cx), float(cy)]

    def _build_layout(self):
        # Define a grid region under the title and above the footer.
        margin_x = 80
        margin_top = 140
        margin_bottom = 90
        region = pygame.Rect(margin_x, margin_top,
                             WIDTH - 2 * margin_x,
                             HEIGHT - margin_top - margin_bottom)
        gap_x = 22
        gap_y = 22
        card_w = (region.width - gap_x * (self.cols - 1)) // self.cols
        rows = (len(self.cards) + self.cols - 1) // self.cols
        card_h = (region.height - gap_y * (rows - 1)) // max(1, rows)
        self.card_rects.clear()
        for i, _ in enumerate(self.cards):
            row = i // self.cols
            col = i % self.cols
            x = region.left + col * (card_w + gap_x)
            y = region.top + row * (card_h + gap_y)
            self.card_rects.append(pygame.Rect(x, y, card_w, card_h))

    def _fit_text(self, text: str, max_width: int) -> str:
        """Trim text with ellipsis so it fits within max_width pixels."""
        if not text:
            return text
        surf = self.card_font.render(text, True, (0, 0, 0))
        if surf.get_width() <= max_width:
            return text
        ellipsis = "..."
        trimmed = text
        while trimmed and self.card_font.render(trimmed + ellipsis, True, (0, 0, 0)).get_width() > max_width:
            trimmed = trimmed[:-1]
        return trimmed + ellipsis if trimmed else ellipsis

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.scene_manager.set(ModeSelectScene(self.app))
                return
            if not self.card_rects:
                return
            cols = self.cols
            idx = self.selected_index
            row = idx // cols
            col = idx % cols
            if event.key in (pygame.K_LEFT, pygame.K_a):
                if col > 0:
                    idx -= 1
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                if col < cols - 1 and idx + 1 < len(self.cards):
                    idx += 1
            elif event.key in (pygame.K_UP, pygame.K_w):
                if row > 0:
                    idx -= cols
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                if idx + cols < len(self.cards):
                    idx += cols
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate(self.selected_index)
            self.selected_index = max(0, min(idx, len(self.cards) - 1))
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            for i, r in enumerate(self.card_rects):
                if r.collidepoint(mx, my):
                    self.selected_index = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, r in enumerate(self.card_rects):
                if r.collidepoint(mx, my):
                    self.selected_index = i
                    self._activate(i)
                    break
        elif event.type == pygame.MOUSEWHEEL:
            # Scroll up/down by rows
            if not self.card_rects:
                return
            cols = self.cols
            idx = self.selected_index
            if event.y > 0 and idx - cols >= 0:
                idx -= cols
            elif event.y < 0 and idx + cols < len(self.cards):
                idx += cols
            self.selected_index = idx

    def _activate(self, index: int):
        if index < 0 or index >= len(self.cards):
            return
        card = self.cards[index]
        # Step 2: go to single-player game detail page
        self.app.scene_manager.set(SinglePlayerGameDetailScene(self.app, card))

    def update(self, dt: float):
        # Smoothly move highlight frame toward the selected card.
        if not self.card_rects or self.selected_index >= len(self.card_rects):
            return
        target = self.card_rects[self.selected_index].center
        speed = 12.0
        for i in (0, 1):
            delta = target[i] - self.highlight_center[i]
            self.highlight_center[i] += delta * min(1.0, speed * dt)

    def draw(self, surface: pygame.Surface):
        surface.fill(BG_COLOR)
        # Title
        title = self.big_font.render("Single Player", True, (255, 255, 255))
        title_y = 80
        surface.blit(title, (WIDTH // 2 - title.get_width() // 2, title_y))

        # Footer hint
        hint = self.font.render("Arrows/Mouse: Select  Enter/Click: Start  Esc: Back", True, (180, 180, 180))
        hint_y = HEIGHT - 50
        surface.blit(hint, (WIDTH // 2 - hint.get_width() // 2, hint_y))

        # Draw cards
        base_col = (50, 50, 80)
        hover_col = (90, 90, 140)
        outline_col = (180, 180, 230)

        for i, (card, rect) in enumerate(zip(self.cards, self.card_rects)):
            is_sel = (i == self.selected_index)
            fill = hover_col if is_sel else base_col
            pygame.draw.rect(surface, fill, rect)
            pygame.draw.rect(surface, outline_col, rect, 2)
            # Compact card: only render game title centered in the box
            max_text_w = rect.width - 24  # horizontal padding
            title_text = self._fit_text(card["title"], max_text_w)
            t_surf = self.card_font.render(title_text, True, (240, 240, 240))
            t_x = rect.centerx - t_surf.get_width() // 2
            t_y = rect.centery - t_surf.get_height() // 2
            surface.blit(t_surf, (t_x, t_y))

        # Highlight frame with smooth movement
        if self.card_rects:
            hw = self.card_rects[0].width + 16
            hh = self.card_rects[0].height + 16
            frame = pygame.Rect(0, 0, hw, hh)
            frame.center = (int(self.highlight_center[0]), int(self.highlight_center[1]))
            pygame.draw.rect(surface, (230, 230, 255), frame, 3)


class SinglePlayerGameDetailScene(BaseMenuScene):
    """Step 2: detail page for a single-player game.

    Shows title, description, controls, and Start/Back buttons.
    """

    def __init__(self, app: "App", card: dict[str, Any]):
        items = ["Start", "Back"]
        super().__init__(app, "Single Player — Game", items)
        self.card = card

    def _load_bindings(self) -> dict:
        cfg_path = os.path.join(os.path.dirname(__file__), "keybindings.json")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"players": {}}

    def handle_select(self, index: int):
        label = self.items[index]
        if label == "Start":
            self._start_game()
        elif label == "Back":
            # Return to the single-player grid
            self.app.scene_manager.set(SinglePlayerGameSelectScene(self.app))

    def _start_game(self):
        cid = self.card.get("id", "")
        self.app.lobby.mode = "single"
        if cid == "snake":
            self.app.lobby.game = "snake"
            self.app.launch_snake_game()
        elif cid == "control_zone":
            self.app.lobby.game = "control_zone"
            self.app.launch_control_zone_game(1)
        elif cid == "trail_lock":
            self.app.lobby.game = "trail_lock"
            self.app.launch_trail_lock_game(1)
        elif cid == "brick_breaker":
            self.app.lobby.game = "brick_breaker"
            self.app.launch_brick_breaker_game()
        elif cid == "whack_a_box":
            self.app.lobby.game = "whack_a_box"
            self.app.launch_whack_a_box_game()
        elif cid == "box_stack":
            self.app.lobby.game = "box_stack"
            self.app.launch_box_stack_game()
        elif cid == "simon_grid":
            self.app.lobby.game = "simon_grid"
            self.app.launch_simon_grid_game()
        elif cid == "maze_runner":
            self.app.lobby.game = "maze_runner"
            self.app.launch_maze_runner_game()
        elif cid == "ttt_single":
            self.app.lobby.game = "ttt_single"
            self.app.scene_manager.set(TttSingleLevelSelectScene(self.app))
        elif cid == "sudoku":
            self.app.lobby.game = "sudoku"
            self.app.scene_manager.set(SudokuLevelSelectScene(self.app))
        elif cid == "survival":
            self.app.lobby.game = "survival"
            self.app.launch_survival_game()
        elif cid == "flappy_box":
            self.app.lobby.game = "flappy_box"
            self.app.launch_flappy_box_game()
        elif cid == "tetris_box":
            self.app.lobby.game = "tetris_box"
            self.app.launch_tetris_box_game()
        elif cid == "zip_box":
            self.app.lobby.game = "zip_box"
            self.app.launch_zip_box_game()

    def draw(self, surface: pygame.Surface):
        # Use BaseMenuScene to draw the title, Start/Back buttons, and hints
        super().draw(surface)

        # Info panel box
        panel_w = WIDTH - 200
        panel_h = 260
        panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
        panel_rect.center = (WIDTH // 2, HEIGHT // 2)
        pygame.draw.rect(surface, (40, 40, 70), panel_rect)
        pygame.draw.rect(surface, (160, 160, 210), panel_rect, 2)

        title_text = self.card.get("title", "")
        desc_text = self.card.get("desc", "")

        y = panel_rect.top + 20
        title_surf = self.big_font.render(title_text, True, (245, 245, 255))
        surface.blit(title_surf, (panel_rect.centerx - title_surf.get_width() // 2, y))
        y += title_surf.get_height() + 12

        if desc_text:
            desc_surf = self.font.render(desc_text, True, (225, 225, 235))
            surface.blit(desc_surf, (panel_rect.centerx - desc_surf.get_width() // 2, y))
            y += desc_surf.get_height() + 18

        # Controls (single-player: show P1 only)
        cfg = self._load_bindings()
        players = cfg.get("players", {})
        p1 = players.get("1", {})
        ctrl_line = (
            f"P1 Controls: up={p1.get('up','')} down={p1.get('down','')} "
            f"left={p1.get('left','')} right={p1.get('right','')}"
        )
        ctrl_surf = self.font.render(ctrl_line, True, (210, 210, 230))
        surface.blit(ctrl_surf, (panel_rect.centerx - ctrl_surf.get_width() // 2, y))



class ControlsScene(BaseMenuScene):
    def __init__(self, app: "App"):
        items = ["Back"]
        super().__init__(app, "Controls", items)
        self.cfg_path = os.path.join(os.path.dirname(__file__), "keybindings.json")
        try:
            with open(self.cfg_path, "r", encoding="utf-8") as f:
                self.cfg = json.load(f)
        except Exception:
            self.cfg = {"players": {}}

        players = self.cfg.get("players", {})
        # Sorted list of player ID strings ("1", "2", ...)
        self.player_ids = sorted(players.keys(), key=lambda x: int(x)) if players else []
        # Editable actions per player
        self.actions = ["up", "down", "left", "right"]
        self.selected_player_index = 0
        self.selected_action_index = 0
        # When True, the next non-ESC key press becomes the new binding
        self.waiting_for_key = False

    def handle_select(self, index: int):
        # Only one menu item (Back); go home
        self.app.scene_manager.set(HomeScene(self.app))

    def _keycode_to_binding_name(self, key: int) -> str:
        """Convert a pygame keycode to a readable binding name for JSON.

        Produces values that InputHandler._normalize_key_name understands.
        """
        # Letters: map to K_X style
        try:
            ch = chr(key)
            if "a" <= ch <= "z" or "A" <= ch <= "Z":
                return f"K_{ch.upper()}"
        except Exception:
            pass

        # Arrow keys
        if key == pygame.K_UP:
            return "K_UP"
        if key == pygame.K_DOWN:
            return "K_DOWN"
        if key == pygame.K_LEFT:
            return "K_LEFT"
        if key == pygame.K_RIGHT:
            return "K_RIGHT"

        # Numpad digits 0-9
        if pygame.K_KP0 <= key <= pygame.K_KP9:
            digit = key - pygame.K_KP0
            return f"K_KP{digit}"

        # Fallback to pygame key name (e.g., "space"), which
        # InputHandler.from_file can resolve via pygame.key.key_code.
        return pygame.key.name(key)

    def handle_event(self, event: pygame.event.Event):
        # Custom handling so this scene can edit keybindings.
        if event.type == pygame.KEYDOWN:
            # Cancel current rebind or leave controls screen
            if event.key == pygame.K_ESCAPE:
                if self.waiting_for_key:
                    # Cancel rebind, stay in scene
                    self.waiting_for_key = False
                else:
                    self.app.scene_manager.set(HomeScene(self.app))
                return

            # If we're waiting for a new key, capture it
            if self.waiting_for_key and self.player_ids:
                binding_name = self._keycode_to_binding_name(event.key)
                pid = self.player_ids[self.selected_player_index]
                players = self.cfg.setdefault("players", {})
                actions_map = players.setdefault(pid, {})
                action = self.actions[self.selected_action_index]
                actions_map[action] = binding_name

                # Persist to disk
                try:
                    with open(self.cfg_path, "w", encoding="utf-8") as f:
                        json.dump(self.cfg, f, indent=2)
                except Exception:
                    pass

                # Reload input handler so changes are live
                try:
                    self.app.input_handler = InputHandler.from_file(self.cfg_path)
                except Exception:
                    pass

                self.waiting_for_key = False
                return

            # Navigation between players and actions when not rebinding
            if not self.player_ids:
                return
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_player_index = (self.selected_player_index - 1) % len(self.player_ids)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_player_index = (self.selected_player_index + 1) % len(self.player_ids)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.selected_action_index = (self.selected_action_index - 1) % len(self.actions)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.selected_action_index = (self.selected_action_index + 1) % len(self.actions)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                # Begin waiting for the next key press to assign
                self.waiting_for_key = True

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Allow clicking the Back button
            rects, _, _, _, _ = self._layout()
            if rects and rects[0].collidepoint(event.pos):
                self.app.scene_manager.set(HomeScene(self.app))

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        players = self.cfg.get("players", {})
        start_y = 160
        box_w = 560
        box_h = 70
        gap = 12
        # Ensure internal player_ids stays in sync if config changed
        if players and not getattr(self, "player_ids", None):
            self.player_ids = sorted(players.keys(), key=lambda x: int(x))

        for i, pid in enumerate(sorted(players.keys(), key=lambda x: int(x))):
            rect = pygame.Rect(WIDTH//2 - box_w//2, start_y + i*(box_h+gap), box_w, box_h)
            is_sel_player = (self.player_ids and pid == self.player_ids[self.selected_player_index])
            fill_col = (80, 80, 110) if is_sel_player else (60, 60, 80)
            border_col = (190, 190, 230) if is_sel_player else (150, 150, 190)
            pygame.draw.rect(surface, fill_col, rect)
            pygame.draw.rect(surface, border_col, rect, 2)

            color = PLAYER_COLORS[(int(pid)-1) % len(PLAYER_COLORS)]
            swatch = pygame.Rect(rect.left+10, rect.top+10, 40, 40)
            pygame.draw.rect(surface, color, swatch)

            actions = players.get(pid, {})
            # Highlight the currently selected action for this player
            def decorate(action_name: str, idx: int) -> str:
                val = actions.get(action_name, "")
                if is_sel_player and idx == self.selected_action_index:
                    return f"[{val or 'UNSET'}]"
                return val or ""

            up_val = decorate("up", 0)
            down_val = decorate("down", 1)
            left_val = decorate("left", 2)
            right_val = decorate("right", 3)

            text = (
                f"P{pid}: up={up_val} down={down_val} "
                f"left={left_val} right={right_val}"
            )
            surf = self.font.render(text, True, (220, 220, 230))
            surface.blit(surf, (swatch.right + 12, rect.centery - surf.get_height()//2))

        # Instructions / status line
        if getattr(self, "player_ids", None) and self.player_ids:
            pid = self.player_ids[self.selected_player_index]
            action = self.actions[self.selected_action_index]
            if self.waiting_for_key:
                msg = f"Press a key for P{pid} {action.upper()}  (ESC to cancel)"
            else:
                msg = "Arrows: select player/action   Enter: rebind   ESC: Back"
            info = self.font.render(msg, True, (230, 230, 240))
            surface.blit(info, (WIDTH//2 - info.get_width()//2, HEIGHT - 80))


class PlayerSetupScene(BaseMenuScene):
    def __init__(self, app: "App"):
        items = ["Start Game", "Back"]
        super().__init__(app, "Player Setup (PvP)", items)
        self.min_players = 2
        self.max_players = 4
        if not hasattr(self.app.lobby, "num_players"):
            self.app.lobby.num_players = self.min_players

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.app.lobby.num_players = max(self.min_players, self.app.lobby.num_players - 1)
            elif event.key == pygame.K_RIGHT:
                self.app.lobby.num_players = min(self.max_players, self.app.lobby.num_players + 1)
        super().handle_event(event)

    def handle_select(self, index: int):
        label = self.items[index]
        if label == "Start Game":
            if self.app.lobby.game == "tag":
                # Go to Tag-specific settings before starting the match
                self.app.scene_manager.set(TagSettingsScene(self.app))
            elif self.app.lobby.game == "survival_pvp":
                self.app.launch_survival_pvp_game(self.app.lobby.num_players)
            elif self.app.lobby.game == "control_zone":
                self.app.launch_control_zone_game(self.app.lobby.num_players)
            elif self.app.lobby.game == "trail_lock":
                self.app.launch_trail_lock_game(self.app.lobby.num_players)
        elif label == "Back":
            self.app.scene_manager.set(GameSelectScene(self.app))

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        counter_rect = pygame.Rect(WIDTH//2 - 140, 150, 280, 50)
        pygame.draw.rect(surface, (60, 60, 80), counter_rect)
        pygame.draw.rect(surface, (150, 150, 190), counter_rect, 2)
        text = self.font.render(f"Players: {self.app.lobby.num_players}  (Left/Right)", True, (220, 220, 230))
        surface.blit(text, (counter_rect.centerx - text.get_width()//2, counter_rect.centery - text.get_height()//2))

        cfg_path = os.path.join(os.path.dirname(__file__), "keybindings.json")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {"players": {}}
        players_map = cfg.get("players", {})

        start_y = 220
        box_w = 600
        box_h = 64
        gap = 10
        for i in range(self.app.lobby.num_players):
            pid = str(i+1)
            rect = pygame.Rect(WIDTH//2 - box_w//2, start_y + i*(box_h+gap), box_w, box_h)
            pygame.draw.rect(surface, (60, 60, 80), rect)
            pygame.draw.rect(surface, (150, 150, 190), rect, 2)
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            swatch = pygame.Rect(rect.left+10, rect.top+12, 40, 40)
            pygame.draw.rect(surface, color, swatch)
            actions = players_map.get(pid, {})
            text = f"P{pid}: up={actions.get('up','')} down={actions.get('down','')} left={actions.get('left','')} right={actions.get('right','')}"
            surf = self.font.render(text, True, (220, 220, 230))
            surface.blit(surf, (swatch.right + 12, rect.centery - surf.get_height()//2))


class TagSettingsScene(BaseMenuScene):
    """Pregame settings screen for PvP Tag variants."""

    def __init__(self, app: "App"):
        # Items are placeholders; labels are filled dynamically in draw()
        items = [
            "Double Jump",
            "Map",
            "Moving Platforms",
            "Drop-through Platforms",
            "Speed Platforms",
            "Start Match",
            "Back",
        ]
        super().__init__(app, "Tag Settings", items)

    def handle_select(self, index: int):
        lobby = self.app.lobby
        if index == 0:
            lobby.tag_double_jump = not lobby.tag_double_jump
        elif index == 1:
            lobby.tag_map_index = (lobby.tag_map_index + 1) % 3
        elif index == 2:
            lobby.tag_enable_moving = not lobby.tag_enable_moving
        elif index == 3:
            lobby.tag_enable_dropthrough = not lobby.tag_enable_dropthrough
        elif index == 4:
            lobby.tag_enable_speed = not lobby.tag_enable_speed
        elif index == 5:
            # Start the Tag match with current settings
            self.app.launch_tag_game(self.app.lobby.num_players)
        elif index == 6:
            self.app.scene_manager.set(PlayerSetupScene(self.app))

    def draw(self, surface: pygame.Surface):
        # Update labels to reflect current settings before drawing
        lobby = self.app.lobby
        self.items[0] = f"Double Jump: {'ON' if lobby.tag_double_jump else 'OFF'}"
        self.items[1] = f"Map: {lobby.tag_map_index + 1}/3"
        self.items[2] = f"Moving Platforms: {'ON' if lobby.tag_enable_moving else 'OFF'}"
        self.items[3] = f"Drop-through Platforms: {'ON' if lobby.tag_enable_dropthrough else 'OFF'}"
        self.items[4] = f"Speed Platforms: {'ON' if lobby.tag_enable_speed else 'OFF'}"
        # Last two items are static
        self.items[5] = "Start Match"
        self.items[6] = "Back"
        super().draw(surface)


class MenuScene(Scene):
    def __init__(self, app: "App"):
        self.app = app
        self.font = app.font
        self.big_font = app.big_font
        self.num_humans = 2
        self.num_bots = 0
        self.match_time = 60

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.start_game()
            elif event.key == pygame.K_ESCAPE:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            elif event.key == pygame.K_RIGHT:
                self.num_humans = min(4, self.num_humans + 1)
            elif event.key == pygame.K_LEFT:
                self.num_humans = max(1, self.num_humans - 1)
            elif event.key == pygame.K_UP:
                self.num_bots = min(4, self.num_bots + 1)
            elif event.key == pygame.K_DOWN:
                self.num_bots = max(0, self.num_bots - 1)
            elif event.key == pygame.K_PAGEUP:
                self.match_time = min(300, self.match_time + 10)
            elif event.key == pygame.K_PAGEDOWN:
                self.match_time = max(10, self.match_time - 10)

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        surface.fill(BG_COLOR)
        title = self.big_font.render("BOX ARCADE - TAG", True, (255, 255, 255))
        surface.blit(title, (WIDTH//2 - title.get_width()//2, 80))

        lines = [
            f"Humans: {self.num_humans}  (Left/Right)",
            f"Bots: {self.num_bots}      (Up/Down)",
            f"Match Time: {self.match_time}s (PageUp/PageDown)",
            "Press Enter to Start",
            "Esc to Quit",
        ]
        for i, text in enumerate(lines):
            surf = self.font.render(text, True, (220, 220, 220))
            surface.blit(surf, (WIDTH//2 - surf.get_width()//2, 200 + i * 28))

        info = [
            "Per-player key bindings are in keybindings.json.",
            "Use symbolic names (e.g., 'K_W', 'K_LEFT', 'K_KP8').",
        ]
        for i, text in enumerate(info):
            surf = self.font.render(text, True, (180, 180, 180))
            surface.blit(surf, (WIDTH//2 - surf.get_width()//2, 370 + i * 22))

    def start_game(self):
        players: List[Player] = []
        bounds = pygame.Rect(20, 60, WIDTH - 40, HEIGHT - 80)
        # Spawn grid positions
        spawn_positions = [
            (bounds.left + 40, bounds.top + 40),
            (bounds.right - 80, bounds.top + 40),
            (bounds.left + 40, bounds.bottom - 80),
            (bounds.right - 80, bounds.bottom - 80),
            (bounds.centerx - 40, bounds.centery - 40),
            (bounds.centerx + 40, bounds.centery - 40),
            (bounds.centerx - 40, bounds.centery + 40),
            (bounds.centerx + 40, bounds.centery + 40),
        ]

        speed = 220.0
        size = 36
        idx = 0
        # Humans
        for i in range(self.num_humans):
            x, y = spawn_positions[idx % len(spawn_positions)]
            idx += 1
            rect = pygame.Rect(x, y, size, size)
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            players.append(HumanPlayer(i + 1, f"P{i+1}", rect, color, speed, True))
        # Bots
        for b in range(self.num_bots):
            x, y = spawn_positions[idx % len(spawn_positions)]
            idx += 1
            rect = pygame.Rect(x, y, size, size)
            color = PLAYER_COLORS[(self.num_humans + b) % len(PLAYER_COLORS)]
            players.append(BotPlayer(self.num_humans + b + 1, f"Bot{b+1}", rect, color, speed * 0.95, False))

        game = TagGame(players, bounds, match_time=self.match_time)
        self.app.scene_manager.set(GameScene(self.app, game))


class GameScene(Scene):
    def __init__(self, app: "App", game: Any):
        self.app = app
        self.game = game
        self.font = app.font

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Open pause menu
                self.app.scene_manager.set(PauseScene(self.app))
        # Forward input events to handler for unified pressed tracking
        self.app.input_handler.handle_event(event)
        # Forward discrete events to the game if it supports its own handler (e.g., grid navigation)
        if hasattr(self.game, "handle_event"):
            self.game.handle_event(event)

    def update(self, dt: float):
        # Use InputHandler's unified event-tracked state (pass None)
        self.game.update(dt, self.app.input_handler, None)
        if self.game.is_over:
            self.app.scene_manager.set(ResultsScene(self.app, self.game))

    def draw(self, surface: pygame.Surface):
        surface.fill(BG_COLOR)
        # Draw playfield bounds
        pygame.draw.rect(surface, (80, 80, 100), self.game.bounds, 2)
        self.game.draw(surface, self.font)


class ResultsScene(Scene):
    def __init__(self, app: "App", game: Any):
        self.app = app
        self.game = game
        self.font = app.font
        self.big_font = app.big_font
        self.items = ["Play Again", "Main Menu"]
        self.selected = 0
        # Sort based on mode (e.g., survival/control zone want highest time first)
        reverse = getattr(game, "higher_time_wins", False)
        self.sorted_scores = sorted(game.scores(), key=lambda x: x[1], reverse=reverse)
        # Map player name -> color for swatches on the results screen
        self.name_colors: dict[str, tuple[int, int, int]] = {}
        if hasattr(game, "players"):
            try:
                for p in game.players:
                    self.name_colors[p.name] = getattr(p, "color", (200, 200, 200))
            except Exception:
                pass
        elif hasattr(game, "player"):
            p = game.player
            self.name_colors[p.name] = getattr(p, "color", (200, 200, 200))

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w, pygame.K_a):
                self.selected = (self.selected - 1) % len(self.items)
            elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_d):
                self.selected = (self.selected + 1) % len(self.items)
            elif event.key == pygame.K_RETURN:
                self._activate_selected()
            elif event.key == pygame.K_ESCAPE:
                self.app.scene_manager.set(HomeScene(self.app))
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            for i, r in enumerate(self._button_rects()):
                if r.collidepoint(mx, my):
                    self.selected = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, r in enumerate(self._button_rects()):
                if r.collidepoint(mx, my):
                    self.selected = i
                    self._activate_selected()
                    break
        elif event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                self.selected = (self.selected - 1) % len(self.items)
            elif event.y < 0:
                self.selected = (self.selected + 1) % len(self.items)

    def _activate_selected(self):
        label = self.items[self.selected]
        if label == "Play Again":
            if hasattr(self.app, "current_game_launcher") and self.app.current_game_launcher:
                self.app.current_game_launcher()
        elif label == "Main Menu":
            self.app.scene_manager.set(HomeScene(self.app))

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        surface.fill(BG_COLOR)
        title = self.big_font.render("Results", True, (255, 255, 255))
        surface.blit(title, (WIDTH//2 - title.get_width()//2, 80))

        if self.sorted_scores:
            winner, t = self.sorted_scores[0]
            show_values = (not getattr(self.game, "higher_time_wins", False)) or getattr(self.game, "show_time_in_results", False)
            label = getattr(self.game, "result_label", "IT")
            # Only add 's' unit for time-based labels
            is_time_label = label.lower() in ("it", "time")
            if hasattr(self.game, "results_header") and getattr(self.game, "results_header"):
                wtext = self.font.render(str(getattr(self.game, "results_header")), True, (240, 240, 240))
            elif show_values:
                val_text = f"{t:.1f}s" if is_time_label else f"{int(t)}"
                wtext = self.font.render(f"Winner: {winner} ({label}: {val_text})", True, (240, 240, 240))
            else:
                wtext = self.font.render(f"Winner: {winner}", True, (240, 240, 240))
            # Draw color swatch next to winner
            win_color = self.name_colors.get(winner)
            x_text = WIDTH//2 - wtext.get_width()//2
            y_text = 140
            if win_color:
                box_size = 14
                box_x = x_text - box_size - 8
                box_y = y_text + (wtext.get_height() - box_size)//2
                box = pygame.Rect(box_x, box_y, box_size, box_size)
                pygame.draw.rect(surface, win_color, box)
                pygame.draw.rect(surface, (230, 230, 230), box, 2)
            surface.blit(wtext, (x_text, y_text))

        show_values = (not getattr(self.game, "higher_time_wins", False)) or getattr(self.game, "show_time_in_results", False)
        for i, (name, it_time) in enumerate(self.sorted_scores):
            if show_values:
                label = getattr(self.game, "result_label", "IT")
                is_time_label = label.lower() in ("it", "time")
                val_text = f"{it_time:.1f}s" if is_time_label else f"{int(it_time)}"
                line = f"{i+1}. {name} — {label}: {val_text}"
            else:
                line = f"{i+1}. {name}"
            surf = self.font.render(line, True, (220, 220, 220))
            # Draw color swatch next to each entry
            color = self.name_colors.get(name)
            line_x = WIDTH//2 - surf.get_width()//2
            line_y = 180 + i * 26
            if color:
                box_size = 12
                box_x = line_x - box_size - 8
                box_y = line_y + (surf.get_height() - box_size)//2
                box = pygame.Rect(box_x, box_y, box_size, box_size)
                pygame.draw.rect(surface, color, box)
                pygame.draw.rect(surface, (220, 220, 220), box, 2)
            surface.blit(surf, (line_x, line_y))

        for i, label in enumerate(self.items):
            rect = self._button_rects()[i]
            fill = (120, 120, 180) if i == self.selected else (70, 70, 90)
            pygame.draw.rect(surface, fill, rect)
            pygame.draw.rect(surface, (180, 180, 220), rect, 2)
            surf = self.font.render(label, True, (240, 240, 240))
            surface.blit(surf, (rect.centerx - surf.get_width()//2, rect.centery - surf.get_height()//2))

    def _button_rects(self) -> list[pygame.Rect]:
        box_w = 300
        box_h = 44
        gap = 14
        start_y = HEIGHT - 160
        return [
            pygame.Rect(WIDTH//2 - box_w//2, start_y + i*(box_h+gap), box_w, box_h)
            for i in range(len(self.items))
        ]


class PauseScene(BaseMenuScene):
    def __init__(self, app: "App"):
        items = ["Resume", "Restart", "Quit to Menu"]
        super().__init__(app, "Paused", items)

    def handle_select(self, index: int):
        label = self.items[index]
        if label == "Resume":
            # Resume by returning to the current game scene
            # The existing game continues running when we switch back.
            # Simply set the scene to the existing GameScene stored in app.
            if hasattr(self.app, "_active_game_scene") and self.app._active_game_scene:
                self.app.scene_manager.set(self.app._active_game_scene)
            else:
                self.app.scene_manager.set(HomeScene(self.app))
        elif label == "Restart":
            if hasattr(self.app, "current_game_launcher") and self.app.current_game_launcher:
                self.app.current_game_launcher()
        elif label == "Quit to Menu":
            self.app.scene_manager.set(HomeScene(self.app))


class TttSingleLevelSelectScene(BaseMenuScene):
    def __init__(self, app: "App"):
        items = ["Easy", "Medium", "Hard", "Back"]
        super().__init__(app, "Tic Tac Toe Difficulty", items)

    def handle_select(self, index: int):
        label = self.items[index]
        if label == "Back":
            self.app.scene_manager.set(GameSelectScene(self.app))
            return
        level = label.lower()
        self.app.launch_ttt_single(level)

class SudokuLevelSelectScene(BaseMenuScene):
    def __init__(self, app: "App"):
        items = ["Easy", "Medium", "Hard", "Back"]
        super().__init__(app, "Sudoku Difficulty", items)

    def handle_select(self, index: int):
        label = self.items[index]
        if label == "Back":
            self.app.scene_manager.set(GameSelectScene(self.app))
            return
        level = label.lower()
        self.app.launch_sudoku_game(level)


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Box Arcade - TAG")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 20)
        self.big_font = pygame.font.SysFont("consolas", 36)

        # Load input handler (creates default JSON if missing)
        cfg_path = os.path.join(os.path.dirname(__file__), "keybindings.json")
        self.input_handler = InputHandler.from_file(cfg_path)

        self.lobby = LobbyState()
        self.current_game_launcher = None
        self._active_game_scene = None
        # Start at Home scene for lobby/system navigation
        self.scene_manager = SceneManager(HomeScene(self))

    def launch_tag_game(self, num_players: int):
        bounds = pygame.Rect(20, 60, WIDTH - 40, HEIGHT - 80)
        spawn_positions = [
            (bounds.left + 40, bounds.top + 40),
            (bounds.right - 80, bounds.top + 40),
            (bounds.left + 40, bounds.bottom - 80),
            (bounds.right - 80, bounds.bottom - 80),
            (bounds.centerx - 40, bounds.centery - 40),
            (bounds.centerx + 40, bounds.centery - 40),
            (bounds.centerx - 40, bounds.centery + 40),
            (bounds.centerx + 40, bounds.centery + 40),
        ]
        players: List[Player] = []
        speed = 220.0
        # Slightly smaller player boxes so arena feels larger
        size = 28
        for i in range(num_players):
            x, y = spawn_positions[i % len(spawn_positions)]
            rect = pygame.Rect(x, y, size, size)
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            players.append(HumanPlayer(i + 1, f"P{i+1}", rect, color, speed, True))

        # Build Tag settings from lobby
        lobby = self.lobby
        settings = {
            "double_jump": getattr(lobby, "tag_double_jump", False),
            "map_index": getattr(lobby, "tag_map_index", 0),
            "enable_moving": getattr(lobby, "tag_enable_moving", False),
            "enable_dropthrough": getattr(lobby, "tag_enable_dropthrough", False),
            "enable_speed": getattr(lobby, "tag_enable_speed", False),
        }

        game = TagGame(players, bounds, match_time=60, settings=settings)
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = lambda: self.launch_tag_game(num_players)
        self.scene_manager.set(scene)

    def launch_survival_game(self):
        # Single player in arena; reuse existing movement and input systems
        bounds = pygame.Rect(20, 60, WIDTH - 40, HEIGHT - 80)
        size = 36
        speed = 220.0
        # Center spawn
        rect = pygame.Rect(0, 0, size, size)
        rect.center = bounds.center
        color = PLAYER_COLORS[0]
        player = HumanPlayer(1, "Solo", rect, color, speed, True)

        game = SurvivalGame(player, bounds)
        game.reset()
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = self.launch_survival_game
        self.scene_manager.set(scene)

    def launch_snake_game(self):
        bounds = pygame.Rect(20, 60, WIDTH - 40, HEIGHT - 80)
        game = SnakeGame(bounds)
        # Optional: ensure clean start
        game.reset()
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = self.launch_snake_game
        self.scene_manager.set(scene)

    def launch_brick_breaker_game(self):
        bounds = pygame.Rect(20, 60, WIDTH - 40, HEIGHT - 80)
        game = BrickBreakerGame(bounds)
        game.reset()
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = self.launch_brick_breaker_game
        self.scene_manager.set(scene)

    def launch_whack_a_box_game(self):
        bounds = pygame.Rect(40, 80, WIDTH - 80, HEIGHT - 140)
        game = WhackABoxGame(bounds, round_duration=30.0)
        game.reset()
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = self.launch_whack_a_box_game
        self.scene_manager.set(scene)

    def launch_flappy_box_game(self):
        bounds = pygame.Rect(80, 60, WIDTH - 160, HEIGHT - 120)
        game = FlappyBoxGame(bounds)
        game.reset()
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = self.launch_flappy_box_game
        self.scene_manager.set(scene)

    def launch_tetris_box_game(self):
        # Slight margins so the 10x20 grid and side HUD fit cleanly
        bounds = pygame.Rect(60, 40, WIDTH - 120, HEIGHT - 80)
        game = TetrisBoxGame(bounds)
        game.reset()
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = self.launch_tetris_box_game
        self.scene_manager.set(scene)

    def launch_zip_box_game(self):
        # Central board area for the numbered-grid puzzle.
        # For Zip Box we keep a single game instance and reuse it so
        # that "Play Again" can advance to the next level while
        # pause-menu "Restart" restarts the current level.
        bounds = pygame.Rect(60, 60, WIDTH - 120, HEIGHT - 120)
        game = ZipBoxGame(bounds)
        scene = GameScene(self, game)
        self._active_game_scene = scene
        # Launcher decides whether to restart or go to next level based
        # on which scene is currently active (Pause vs Results).
        self.current_game_launcher = lambda g=game: self._restart_or_advance_zip_box(g)
        self.scene_manager.set(scene)

    def _restart_or_advance_zip_box(self, game: ZipBoxGame):
        """Helper used by current_game_launcher for Zip Box.

        - From ResultsScene → advance to next level.
        - From PauseScene (Restart) → restart current level.
        """
        from_typescene = self.scene_manager.current
        # If we're on the results screen, move to the next puzzle.
        if isinstance(from_typescene, ResultsScene):
            if hasattr(game, "next_level"):
                game.next_level()
            else:
                game.current_level = (game.current_level + 1) % len(game.levels)
                game.reset()
        else:
            # From pause or other callers, just restart this level.
            game.reset()

        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.scene_manager.set(scene)

    def launch_box_stack_game(self):
        bounds = pygame.Rect(120, 80, WIDTH - 240, HEIGHT - 140)
        game = BoxStackGame(bounds)
        game.reset()
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = self.launch_box_stack_game
        self.scene_manager.set(scene)

    def launch_simon_grid_game(self):
        # Square-ish board area centered with top HUD room
        bounds = pygame.Rect(140, 80, WIDTH - 280, HEIGHT - 160)
        game = SimonGridGame(bounds, grid_size=3)
        # game.reset() not required (constructor calls reset), but safe to ensure
        game.reset()
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = self.launch_simon_grid_game
        self.scene_manager.set(scene)

    def launch_maze_runner_game(self):
        bounds = pygame.Rect(40, 60, WIDTH - 80, HEIGHT - 120)
        game = MazeRunnerGame(bounds)
        game.reset()
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = self.launch_maze_runner_game
        self.scene_manager.set(scene)

    def launch_sudoku_game(self, level: str = "easy"):
        # Centered board with margin for HUD
        bounds = pygame.Rect(100, 60, WIDTH - 200, HEIGHT - 120)
        game = SudokuGame(bounds, level=level)
        game.reset()
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = lambda lvl=level: self.launch_sudoku_game(lvl)
        self.scene_manager.set(scene)

    def launch_survival_pvp_game(self, num_players: int):
        bounds = pygame.Rect(20, 60, WIDTH - 40, HEIGHT - 80)
        size = 36
        speed = 220.0
        players: List[HumanPlayer] = []
        # Spawn colors & IDs
        for i in range(num_players):
            rect = pygame.Rect(0, 0, size, size)
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            players.append(HumanPlayer(i + 1, f"P{i+1}", rect, color, speed, True))
        game = SurvivalPvpGame(players, bounds)
        game.reset()
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = lambda: self.launch_survival_pvp_game(num_players)
        self.scene_manager.set(scene)

    def launch_control_zone_game(self, num_players: int):
        bounds = pygame.Rect(20, 60, WIDTH - 40, HEIGHT - 80)
        size = 36
        speed = 220.0
        players: List[HumanPlayer] = []
        for i in range(num_players):
            rect = pygame.Rect(0, 0, size, size)
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            players.append(HumanPlayer(i + 1, f"P{i+1}", rect, color, speed, True))
        game = ControlZoneGame(players, bounds, match_time=60.0)
        game.reset()
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = lambda: self.launch_control_zone_game(num_players)
        self.scene_manager.set(scene)

    def launch_trail_lock_game(self, num_players: int):
        bounds = pygame.Rect(20, 60, WIDTH - 40, HEIGHT - 80)
        size = 28
        speed = 170.0
        players: List[HumanPlayer] = []
        for i in range(num_players):
            rect = pygame.Rect(0, 0, size, size)
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            players.append(HumanPlayer(i + 1, f"P{i+1}", rect, color, speed, True))
        game = TrailLockGame(players, bounds, target_score=5)
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = lambda: self.launch_trail_lock_game(num_players)
        self.scene_manager.set(scene)

    def launch_ttt_single(self, level: str = "hard"):
        # Persistent scoreboard across replays
        if not hasattr(self, "ttt_single_scores_by_level"):
            self.ttt_single_scores_by_level = {}
        scoreboard = self.ttt_single_scores_by_level.setdefault(level, {"You": 0, "Bot": 0})
        # Randomize who is X and who starts
        human_is_x = bool(random.getrandbits(1))
        start_symbol = random.choice(['X', 'O'])
        bounds = pygame.Rect(120, 100, WIDTH - 240, HEIGHT - 200)
        game = TicTacToeGame(bounds, mode="single",
                     player_names=("You", "Bot"),
                     scoreboard=scoreboard,
                             human_symbol=('X' if human_is_x else 'O'),
                             start_symbol=start_symbol,
                             ai_level=level)
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = lambda lvl=level: self.launch_ttt_single(lvl)
        self.scene_manager.set(scene)

    def launch_ttt_pvp(self):
        # Persistent scoreboard and alternating assignment
        if not hasattr(self, "ttt_pvp_scores"):
            self.ttt_pvp_scores = {"P1": 0, "P2": 0}
        if not hasattr(self, "ttt_pvp_toggle"):
            self.ttt_pvp_toggle = True  # True: P1 gets X first; then alternate
        bounds = pygame.Rect(120, 100, WIDTH - 240, HEIGHT - 200)
        # Determine starting assignment and starting player alternately
        if self.ttt_pvp_toggle:
            # P1 as X, starts
            start_symbol = 'X'
            names = ("P1", "P2")
        else:
            start_symbol = 'O'
            names = ("P1", "P2")
        game = TicTacToeGame(bounds, mode="pvp",
                             player_names=names,
                             scoreboard=self.ttt_pvp_scores,
                             start_symbol=start_symbol)
        # Flip toggle for next game
        self.ttt_pvp_toggle = not self.ttt_pvp_toggle
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = self.launch_ttt_pvp
        self.scene_manager.set(scene)

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0  # seconds
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                # Update unified input state for KEYDOWN/KEYUP across scenes
                self.input_handler.handle_event(event)
                self.scene_manager.current.handle_event(event)

            self.scene_manager.current.update(dt)
            self.scene_manager.current.draw(self.screen)
            pygame.display.flip()


if __name__ == "__main__":
    App().run()
