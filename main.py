"""
Pygame-based local multiplayer arcade framework using rectangular box characters.
Includes: Game Loop Manager, InputHandler, Player classes, collision, timer/score,
scene management (menu → game → results) and TAG game implementation.
"""
from __future__ import annotations
import os
import sys
import json
from typing import List
import pygame

from core.input_handler import InputHandler
from entities.player import Player, HumanPlayer, BotPlayer
from games.tag import TagGame

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
            "Edit readable names (e.g., 'w', 'left', 'KP_8').",
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
    def __init__(self, app: "App", game: TagGame):
        self.app = app
        self.game = game
        self.font = app.font

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Return to menu
                self.app.scene_manager.set(MenuScene(self.app))

    def update(self, dt: float):
        pressed = pygame.key.get_pressed()
        self.game.update(dt, self.app.input_handler, pressed)
        if self.game.is_over:
            self.app.scene_manager.set(ResultsScene(self.app, self.game))

    def draw(self, surface: pygame.Surface):
        surface.fill(BG_COLOR)
        # Draw playfield bounds
        pygame.draw.rect(surface, (80, 80, 100), self.game.bounds, 2)
        self.game.draw(surface, self.font)


class ResultsScene(Scene):
    def __init__(self, app: "App", game: TagGame):
        self.app = app
        self.game = game
        self.font = app.font
        self.big_font = app.big_font
        self.sorted_scores = sorted(game.scores(), key=lambda x: x[1])  # least IT time first

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                # Back to menu
                self.app.scene_manager.set(MenuScene(self.app))
            elif event.key == pygame.K_ESCAPE:
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        surface.fill(BG_COLOR)
        title = self.big_font.render("Results", True, (255, 255, 255))
        surface.blit(title, (WIDTH//2 - title.get_width()//2, 80))

        for i, (name, it_time) in enumerate(self.sorted_scores):
            line = f"{i+1}. {name} — IT: {it_time:.1f}s"
            surf = self.font.render(line, True, (220, 220, 220))
            surface.blit(surf, (WIDTH//2 - surf.get_width()//2, 180 + i * 28))

        hint = self.font.render("Enter: Menu   Esc: Quit", True, (180, 180, 180))
        surface.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 120))


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

        self.scene_manager = SceneManager(MenuScene(self))

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0  # seconds
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                self.scene_manager.current.handle_event(event)

            self.scene_manager.current.update(dt)
            self.scene_manager.current.draw(self.screen)
            pygame.display.flip()


if __name__ == "__main__":
    App().run()
