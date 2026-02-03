from __future__ import annotations
import random
import pygame
from typing import List, Optional, Tuple

class SimonGridGame:
    def __init__(self, bounds: pygame.Rect, grid_size: int = 3):
        self.bounds = bounds
        self.grid_size = max(2, min(5, grid_size))
        # Layout
        self.cell_w = self.bounds.width // self.grid_size
        self.cell_h = self.bounds.height // self.grid_size
        # Tiles
        self.tiles: List[pygame.Rect] = []
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                x = self.bounds.left + c * self.cell_w
                y = self.bounds.top + r * self.cell_h
                self.tiles.append(pygame.Rect(x+2, y+2, self.cell_w-4, self.cell_h-4))
        # Sequence and state
        self.sequence: List[int] = []
        self.state: str = "show"  # show | input | over
        self.show_index = -1
        self.show_phase = "off"  # on | off
        self.show_timer = 0.0
        self.on_duration = 0.5
        self.off_duration = 0.25
        self.input_index = 0
        self.player_flash_idx: Optional[int] = None
        self.player_flash_timer = 0.0
        self.is_over = False
        self.results_header: Optional[str] = None
        self.score = 0
        self.higher_time_wins = False
        self.show_time_in_results = False
        self.result_label = "Score"
        # Colors
        self.color_tile = (70, 70, 90)
        self.color_outline = (150, 150, 190)
        self.color_highlight_game = (220, 210, 120)
        self.color_highlight_player = (120, 200, 140)
        # Start game
        self.reset()

    def reset(self):
        self.sequence = [random.randrange(self.grid_size * self.grid_size)]
        self.state = "show"
        self.show_index = -1
        self.show_phase = "off"
        self.show_timer = 0.0
        self.input_index = 0
        self.player_flash_idx = None
        self.player_flash_timer = 0.0
        self.is_over = False
        self.results_header = None
        self.score = 0

    def handle_event(self, event: pygame.event.Event):
        if self.is_over:
            return
        if self.state != "input":
            return  # disable input during sequence show
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            idx = self._index_from_pos(mx, my)
            if idx is not None:
                self._player_select(idx)
        elif event.type == pygame.KEYDOWN:
            # Map 1-9 to 3x3 grid if grid_size==3
            if self.grid_size == 3:
                key_to_idx = {
                    pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2,
                    pygame.K_4: 3, pygame.K_5: 4, pygame.K_6: 5,
                    pygame.K_7: 6, pygame.K_8: 7, pygame.K_9: 8,
                }
                if event.key in key_to_idx:
                    self._player_select(key_to_idx[event.key])

    def _index_from_pos(self, x: int, y: int) -> Optional[int]:
        for i, rect in enumerate(self.tiles):
            if rect.collidepoint(x, y):
                return i
        return None

    def _player_select(self, idx: int):
        self.player_flash_idx = idx
        self.player_flash_timer = 0.2
        # Check correctness
        if idx == self.sequence[self.input_index]:
            self.input_index += 1
            if self.input_index >= len(self.sequence):
                # Round success
                self.score = len(self.sequence)  # completed this round
                self.sequence.append(random.randrange(self.grid_size * self.grid_size))
                # Next round: show sequence again
                self.state = "show"
                self.show_index = -1
                self.show_phase = "off"
                self.show_timer = 0.0
                self.input_index = 0
                # Clear any lingering player highlight while showing sequence
                self.player_flash_idx = None
                self.player_flash_timer = 0.0
        else:
            # Failure
            self.is_over = True
            self.state = "over"
            # Score is last completed length
            self.score = max(0, len(self.sequence) - 1)
            self.results_header = f"Failed at round {len(self.sequence)}"

    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return
        if self.state == "show":
            if self.show_index == -1:
                # initialize display
                self.show_index = 0
                self.show_phase = "on"
                self.show_timer = self.on_duration
            else:
                self.show_timer -= dt
                if self.show_timer <= 0:
                    if self.show_phase == "on":
                        # turn off then wait
                        self.show_phase = "off"
                        self.show_timer = self.off_duration
                    else:
                        # advance to next tile
                        self.show_index += 1
                        if self.show_index >= len(self.sequence):
                            # done showing
                            self.state = "input"
                            self.input_index = 0
                            self.player_flash_idx = None
                            self.player_flash_timer = 0.0
                        else:
                            self.show_phase = "on"
                            self.show_timer = self.on_duration
        elif self.state == "input":
            if self.player_flash_timer > 0:
                self.player_flash_timer -= dt
                if self.player_flash_timer <= 0:
                    self.player_flash_idx = None

    def scores(self):
        return [("Solo", float(self.score))]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Bounds
        pygame.draw.rect(surface, (80, 80, 100), self.bounds, 2)
        # Tiles
        highlight_idx: Optional[int] = None
        if self.state == "show" and self.show_phase == "on" and 0 <= self.show_index < len(self.sequence):
            highlight_idx = self.sequence[self.show_index]
        for i, rect in enumerate(self.tiles):
            if i == highlight_idx:
                color = self.color_highlight_game
            elif self.state == "input" and self.player_flash_idx is not None and i == self.player_flash_idx:
                color = self.color_highlight_player
            else:
                color = self.color_tile
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, self.color_outline, rect, 2)
        # HUD
        round_text = font.render(f"Round: {len(self.sequence)}", True, (255, 255, 255))
        surface.blit(round_text, (10, 10))
        status = "Watch" if self.state == "show" else ("Your turn" if self.state == "input" else "Done")
        stext = font.render(status, True, (220, 220, 230))
        surface.blit(stext, (10, 34))
