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

# Window settings
WIDTH, HEIGHT = 800, 600
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
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.items)
            elif event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.items)
            elif event.key == pygame.K_RETURN:
                self.handle_select(self.selected)
            elif event.key == pygame.K_ESCAPE:
                self.handle_back()

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

    def draw(self, surface: pygame.Surface):
        surface.fill(BG_COLOR)
        # Title
        title = self.big_font.render(self.title, True, (255, 255, 255))
        surface.blit(title, (WIDTH//2 - title.get_width()//2, 90))

        rects = self._menu_rects()
        for i, rect in enumerate(rects):
            is_sel = (i == self.selected)
            fill = self.box_highlight if is_sel else self.box_color
            pygame.draw.rect(surface, fill, rect)
            pygame.draw.rect(surface, self.box_outline, rect, 2)

            label = self.items[i]
            surf = self.font.render(label, True, (240, 240, 240))
            surface.blit(surf, (rect.centerx - surf.get_width()//2, rect.centery - surf.get_height()//2))

        hint = self.font.render("Up/Down: Navigate  Enter: Select  Esc: Back", True, (180, 180, 180))
        surface.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 60))


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
        elif label.startswith("PvP"):
            self.app.lobby.mode = "pvp"
        self.app.scene_manager.set(GameSelectScene(self.app))


class GameSelectScene(BaseMenuScene):
    def __init__(self, app: "App"):
        mode = app.lobby.mode or "single"
        if mode == "single":
            items = ["Snake", "Tic Tac Toe (Solo)", "Survival (Solo)", "Back"]
        else:
            items = ["Tag (Boxes)", "Survival (PvP)", "Control Zone", "TrailLock", "Tic Tac Toe", "Back"]
        super().__init__(app, "Game Select", items)

    def handle_select(self, index: int):
        label = self.items[index]
        mode = self.app.lobby.mode or "single"
        if label == "Back":
            self.app.scene_manager.set(ModeSelectScene(self.app))
            return
        if mode == "pvp" and label.startswith("Tag"):
            self.app.lobby.game = "tag"
            self.app.scene_manager.set(PlayerSetupScene(self.app))
        elif mode == "single" and label.startswith("Survival"):
            self.app.lobby.game = "survival"
            self.app.launch_survival_game()
        elif mode == "single" and label.startswith("Snake"):
            self.app.lobby.game = "snake"
            self.app.launch_snake_game()
        elif mode == "single" and label.startswith("Tic Tac Toe"):
            self.app.lobby.game = "ttt_single"
            self.app.launch_ttt_single()
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


class ControlsScene(BaseMenuScene):
    def __init__(self, app: "App"):
        items = ["Back"]
        super().__init__(app, "Controls", items)
        cfg_path = os.path.join(os.path.dirname(__file__), "keybindings.json")
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                self.cfg = json.load(f)
        except Exception:
            self.cfg = {"players": {}}

    def handle_select(self, index: int):
        self.app.scene_manager.set(HomeScene(self.app))

    def draw(self, surface: pygame.Surface):
        super().draw(surface)
        players = self.cfg.get("players", {})
        start_y = 160
        box_w = 560
        box_h = 70
        gap = 12
        for i, pid in enumerate(sorted(players.keys(), key=lambda x: int(x))):
            rect = pygame.Rect(WIDTH//2 - box_w//2, start_y + i*(box_h+gap), box_w, box_h)
            pygame.draw.rect(surface, (60, 60, 80), rect)
            pygame.draw.rect(surface, (150, 150, 190), rect, 2)
            color = PLAYER_COLORS[(int(pid)-1) % len(PLAYER_COLORS)]
            swatch = pygame.Rect(rect.left+10, rect.top+10, 40, 40)
            pygame.draw.rect(surface, color, swatch)
            actions = players[pid]
            text = f"P{pid}: up={actions.get('up','')} down={actions.get('down','')} left={actions.get('left','')} right={actions.get('right','')}"
            surf = self.font.render(text, True, (220, 220, 230))
            surface.blit(surf, (swatch.right + 12, rect.centery - surf.get_height()//2))


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
                self.app.launch_tag_game(self.app.lobby.num_players)
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
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.items)
            elif event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.items)
            elif event.key == pygame.K_RETURN:
                label = self.items[self.selected]
                if label == "Play Again":
                    if hasattr(self.app, "current_game_launcher") and self.app.current_game_launcher:
                        self.app.current_game_launcher()
                elif label == "Main Menu":
                    self.app.scene_manager.set(HomeScene(self.app))
            elif event.key == pygame.K_ESCAPE:
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

        box_w = 300
        box_h = 44
        gap = 14
        start_y = HEIGHT - 160
        for i, label in enumerate(self.items):
            rect = pygame.Rect(WIDTH//2 - box_w//2, start_y + i*(box_h+gap), box_w, box_h)
            fill = (120, 120, 180) if i == self.selected else (70, 70, 90)
            pygame.draw.rect(surface, fill, rect)
            pygame.draw.rect(surface, (180, 180, 220), rect, 2)
            surf = self.font.render(label, True, (240, 240, 240))
            surface.blit(surf, (rect.centerx - surf.get_width()//2, rect.centery - surf.get_height()//2))


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
        size = 36
        for i in range(num_players):
            x, y = spawn_positions[i % len(spawn_positions)]
            rect = pygame.Rect(x, y, size, size)
            color = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            players.append(HumanPlayer(i + 1, f"P{i+1}", rect, color, speed, True))

        game = TagGame(players, bounds, match_time=60)
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

    def launch_ttt_single(self):
        # Persistent scoreboard across replays
        if not hasattr(self, "ttt_single_scores"):
            self.ttt_single_scores = {"You": 0, "Bot": 0}
        # Randomize who is X and who starts
        human_is_x = bool(random.getrandbits(1))
        start_symbol = random.choice(['X', 'O'])
        bounds = pygame.Rect(120, 100, WIDTH - 240, HEIGHT - 200)
        game = TicTacToeGame(bounds, mode="single",
                             player_names=("You", "Bot"),
                             scoreboard=self.ttt_single_scores,
                             human_symbol=('X' if human_is_x else 'O'),
                             start_symbol=start_symbol)
        scene = GameScene(self, game)
        self._active_game_scene = scene
        self.current_game_launcher = self.launch_ttt_single
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
