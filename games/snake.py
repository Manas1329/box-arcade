"""
Snake (Singleplayer)
Grid-based snake with apples. Eating apples increases length and score.
Collision with walls or self ends the game.
"""
from __future__ import annotations
from typing import List, Tuple, Optional
import random
import pygame

CELL_SIZE = 20


class SnakeGame:
    def __init__(self, bounds: pygame.Rect):
        self.bounds = bounds
        # Compute grid dimensions that fit inside bounds
        self.cols = self.bounds.width // CELL_SIZE
        self.rows = self.bounds.height // CELL_SIZE
        # Anchor grid to top-left of bounds
        self.grid_origin = (self.bounds.left, self.bounds.top)

        self.step_time = 0.12  # seconds per cell move
        self.accum = 0.0

        self.is_over = False
        self.higher_time_wins = True
        self.show_time_in_results = True
        self.result_label = "Score"

        self.score = 0
        self.snake: List[Tuple[int, int]] = []  # list of (col, row)
        self.dir = (1, 0)
        self.pending_dir: Optional[Tuple[int, int]] = None
        self.grow = 0
        self.apple: Tuple[int, int] | None = None

        self._reset()

    def _reset(self):
        self.is_over = False
        self.accum = 0.0
        self.score = 0
        self.dir = (1, 0)
        self.pending_dir = None
        self.grow = 0
        # Start snake near center, length 3
        cx, cy = self.cols // 2, self.rows // 2
        self.snake = [(cx - 1, cy), (cx - 2, cy), (cx - 3, cy)]
        self._spawn_apple()

    def reset(self):
        self._reset()

    def _spawn_apple(self):
        # Find a random empty cell
        empty = [(c, r) for r in range(self.rows) for c in range(self.cols) if (c, r) not in self.snake]
        if not empty:
            # Snake fills the board; treat as win
            self.is_over = True
            return
        self.apple = random.choice(empty)

    def _set_direction_from_input(self, input_handler, pressed):
        # Map input to cardinal direction; prevent reversing into self
        dx, dy = input_handler.get_direction(1, pressed)
        # Prefer axis with stronger intent
        if abs(dx) > abs(dy):
            ndir = (1, 0) if dx > 0 else (-1, 0) if dx < 0 else None
        else:
            ndir = (0, 1) if dy > 0 else (0, -1) if dy < 0 else None
        if ndir is None:
            return
        curx, cury = self.dir
        if (-ndir[0], -ndir[1]) == (curx, cury):
            return  # ignore 180 turns
        self.pending_dir = ndir

    def _step(self):
        # Apply pending direction once per step
        if self.pending_dir is not None:
            self.dir = self.pending_dir
            self.pending_dir = None
        hx, hy = self.snake[0]
        dx, dy = self.dir
        nx, ny = hx + dx, hy + dy
        # Wall collision
        if nx < 0 or ny < 0 or nx >= self.cols or ny >= self.rows:
            self.is_over = True
            return
        # Move: add head
        new_head = (nx, ny)
        # Tail handling: if not growing, remove last
        if self.grow == 0:
            tail = self.snake.pop()
        else:
            self.grow -= 1
        # Self collision (after moving tail if not growing)
        if new_head in self.snake:
            self.is_over = True
            return
        self.snake.insert(0, new_head)
        # Apple consumption
        if self.apple and new_head == self.apple:
            self.score += 1
            self.grow += 1
            self._spawn_apple()

    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return
        # Read input for pending direction
        self._set_direction_from_input(input_handler, pressed)
        # Step movement at fixed rate
        self.accum += dt
        while self.accum >= self.step_time and not self.is_over:
            self.accum -= self.step_time
            self._step()

    def scores(self):
        # Higher score (apples) wins for sorting and results
        return [("Solo", float(self.score))]

    def _cell_rect(self, c: int, r: int) -> pygame.Rect:
        x0, y0 = self.grid_origin
        return pygame.Rect(x0 + c * CELL_SIZE, y0 + r * CELL_SIZE, CELL_SIZE, CELL_SIZE)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Draw playfield bounds
        pygame.draw.rect(surface, (80, 80, 100), self.bounds, 2)
        # Draw snake
        for i, (c, r) in enumerate(self.snake):
            rect = self._cell_rect(c, r)
            color = (84, 240, 120) if i == 0 else (60, 200, 100)
            pygame.draw.rect(surface, color, rect)
        # Draw apple
        if self.apple:
            rect = self._cell_rect(self.apple[0], self.apple[1])
            pygame.draw.rect(surface, (240, 84, 84), rect)
        # HUD
        hud = font.render(f"Score: {self.score}", True, (255, 255, 255))
        surface.blit(hud, (10, 10))
