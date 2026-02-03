"""
Sudoku (Singleplayer)
- 9x9 grid divided into 3x3 subgrids.
- Some cells are pre-filled and locked.
- Player fills empty cells with numbers 1–9.
- Enforces Sudoku rules for rows, columns, and subgrids.
- Click to select cell, type number keys to fill.
- Shows time taken on completion; Results offers New Puzzle / Back to Menu via existing Play Again/Main Menu.
"""
from __future__ import annotations
from typing import List, Optional, Tuple
import random
import pygame

CELL_SIZE = 40
GRID_SIZE = 9

# Preset puzzles by difficulty (0 represents empty)
PRESET_PUZZLES_BY_LEVEL = {
    "easy": [
        [
            [5, 3, 0, 0, 7, 0, 0, 0, 0],
            [6, 0, 0, 1, 9, 5, 0, 0, 0],
            [0, 9, 8, 0, 0, 0, 0, 6, 0],
            [8, 0, 0, 0, 6, 0, 0, 0, 3],
            [4, 0, 0, 8, 0, 3, 0, 0, 1],
            [7, 0, 0, 0, 2, 0, 0, 0, 6],
            [0, 6, 0, 0, 0, 0, 2, 8, 0],
            [0, 0, 0, 4, 1, 9, 0, 0, 5],
            [0, 0, 0, 0, 8, 0, 0, 7, 9],
        ],
        [
            [0, 0, 0, 2, 6, 0, 7, 0, 1],
            [6, 8, 0, 0, 7, 0, 0, 9, 0],
            [1, 9, 0, 0, 0, 4, 5, 0, 0],
            [8, 2, 0, 1, 0, 0, 0, 4, 0],
            [0, 0, 4, 6, 0, 2, 9, 0, 0],
            [0, 5, 0, 0, 0, 3, 0, 2, 8],
            [0, 0, 9, 3, 0, 0, 0, 7, 4],
            [0, 4, 0, 0, 5, 0, 0, 3, 6],
            [7, 0, 3, 0, 1, 8, 0, 0, 0],
        ],
        [
            [0, 0, 0, 0, 0, 0, 2, 0, 0],
            [0, 8, 0, 0, 0, 7, 0, 9, 0],
            [6, 0, 2, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 1, 0, 0, 0, 0],
            [0, 0, 0, 6, 0, 2, 0, 0, 0],
            [0, 0, 0, 0, 0, 3, 0, 2, 8],
            [0, 0, 9, 3, 0, 0, 0, 7, 0],
            [0, 4, 0, 0, 5, 0, 0, 3, 6],
            [7, 0, 3, 0, 0, 8, 0, 0, 0],
        ],
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 3, 0, 8, 5],
            [0, 0, 1, 0, 2, 0, 0, 0, 0],
            [0, 0, 0, 5, 0, 7, 0, 0, 0],
            [0, 0, 4, 0, 0, 0, 1, 0, 0],
            [0, 9, 0, 0, 0, 0, 0, 0, 0],
            [5, 0, 0, 0, 0, 0, 0, 7, 3],
            [0, 0, 2, 0, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 4, 0, 0, 0, 9],
        ],
    ],
    "medium": [
        [
            [0, 2, 0, 6, 0, 8, 0, 0, 0],
            [5, 8, 0, 0, 0, 9, 7, 0, 0],
            [0, 0, 0, 0, 4, 0, 0, 0, 0],
            [3, 7, 0, 0, 0, 0, 5, 0, 0],
            [6, 0, 0, 0, 0, 0, 0, 0, 4],
            [0, 0, 8, 0, 0, 0, 0, 1, 3],
            [0, 0, 0, 0, 2, 0, 0, 0, 0],
            [0, 0, 9, 8, 0, 0, 0, 3, 6],
            [0, 0, 0, 3, 0, 6, 0, 0, 0],
        ],
        [
            [0, 0, 0, 0, 0, 0, 0, 1, 2],
            [0, 0, 0, 0, 0, 5, 0, 0, 0],
            [0, 0, 4, 0, 0, 0, 3, 0, 0],
            [0, 0, 0, 0, 4, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0, 2, 0],
            [0, 0, 0, 0, 5, 0, 0, 0, 0],
            [0, 0, 3, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 2, 0, 0, 0, 0, 0],
            [5, 2, 0, 0, 0, 0, 0, 0, 0],
        ],
        [
            [1, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 7, 0, 9, 0],
            [0, 0, 0, 0, 4, 0, 5, 0, 0],
            [0, 0, 0, 1, 0, 0, 0, 0, 3],
            [0, 0, 4, 6, 0, 2, 9, 0, 0],
            [0, 5, 0, 0, 0, 3, 0, 2, 8],
            [0, 0, 9, 3, 0, 0, 0, 7, 4],
            [0, 4, 0, 0, 5, 0, 0, 3, 6],
            [7, 0, 3, 0, 1, 8, 0, 0, 0],
        ],
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [3, 0, 0, 0, 0, 0, 0, 0, 1],
            [0, 0, 1, 0, 2, 0, 0, 0, 0],
            [0, 0, 0, 5, 0, 7, 0, 0, 0],
            [0, 0, 4, 0, 0, 0, 1, 0, 0],
            [0, 9, 0, 0, 0, 0, 0, 0, 0],
            [5, 0, 0, 0, 0, 0, 0, 7, 3],
            [0, 0, 2, 0, 1, 0, 0, 0, 0],
            [0, 0, 0, 0, 4, 0, 0, 0, 9],
        ],
    ],
    "hard": [
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 2, 0, 0],
            [0, 0, 0, 0, 6, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 2, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 5, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 8, 0, 0, 0],
        ],
        [
            [0, 0, 0, 0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 5, 0, 0, 0],
            [0, 0, 4, 0, 0, 0, 3, 0, 0],
            [0, 0, 0, 0, 4, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0, 2, 0],
            [0, 0, 0, 0, 5, 0, 0, 0, 0],
            [0, 0, 3, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 2, 0, 0, 0, 0, 0],
            [5, 2, 0, 0, 0, 0, 0, 0, 0],
        ],
        [
            [0, 0, 0, 2, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 3],
            [0, 0, 0, 0, 0, 4, 0, 0, 0],
            [8, 0, 0, 0, 0, 0, 0, 4, 0],
            [0, 0, 4, 6, 0, 2, 9, 0, 0],
            [0, 5, 0, 0, 0, 3, 0, 2, 8],
            [0, 0, 0, 3, 0, 0, 0, 7, 0],
            [0, 4, 0, 0, 5, 0, 0, 3, 6],
            [7, 0, 3, 0, 1, 8, 0, 0, 0],
        ],
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 2, 0, 0],
            [0, 7, 0, 0, 9, 0, 0, 0, 0],
            [0, 5, 0, 0, 0, 7, 0, 0, 0],
            [0, 0, 0, 0, 4, 5, 7, 0, 0],
            [0, 0, 0, 1, 0, 0, 0, 3, 0],
            [0, 0, 1, 0, 0, 0, 0, 6, 8],
            [0, 0, 8, 5, 0, 0, 0, 1, 0],
            [0, 9, 0, 0, 0, 0, 4, 0, 0],
        ],
    ],
}

class SudokuGame:
    def __init__(self, bounds: pygame.Rect, level: str = "easy"):
        self.bounds = bounds
        self.level = level if level in PRESET_PUZZLES_BY_LEVEL else "easy"
        # Compute cell size to fit nicely if bounds not exact
        self.cell_w = self.bounds.width // GRID_SIZE
        self.cell_h = self.bounds.height // GRID_SIZE
        self.grid_origin = (self.bounds.left, self.bounds.top)
        # Game state
        self.grid: List[List[int]] = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]
        self.locked: List[List[bool]] = [[False]*GRID_SIZE for _ in range(GRID_SIZE)]
        self.selected: Tuple[int,int] = (0, 0)
        self.is_over = False
        self.elapsed = 0.0
        self.invalid_flash = 0.0
        self.current_puzzle_index = 0
        self.initial_grid: List[List[int]] = [[0]*GRID_SIZE for _ in range(GRID_SIZE)]
        # UI
        self.reset_btn_rect = pygame.Rect(self.bounds.right - 110, self.bounds.top - 42, 100, 32)
        # Results formatting
        self.higher_time_wins = False  # lower time is better
        self.show_time_in_results = True
        self.result_label = "Time"
        self.results_header: Optional[str] = None
        # Load a puzzle
        self._load_random_puzzle()

    def reset(self):
        self.is_over = False
        self.elapsed = 0.0
        self.invalid_flash = 0.0
        self._load_random_puzzle()

    def reset_level(self):
        # Reset the current puzzle state without resetting the timer
        self.is_over = False
        self.invalid_flash = 0.0
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                val = self.initial_grid[r][c]
                self.grid[r][c] = val
                self.locked[r][c] = (val != 0)

    def _load_random_puzzle(self):
        level_list = PRESET_PUZZLES_BY_LEVEL.get(self.level, PRESET_PUZZLES_BY_LEVEL["easy"])
        self.current_puzzle_index = random.randrange(len(level_list))
        puzzle = level_list[self.current_puzzle_index]
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                val = puzzle[r][c]
                self.grid[r][c] = val
                self.locked[r][c] = (val != 0)
                self.initial_grid[r][c] = val
        self.selected = (0, 0)

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Check reset button click
            if self.reset_btn_rect.collidepoint(mx, my):
                self.reset_level()
                return
            c = (mx - self.grid_origin[0]) // self.cell_w
            r = (my - self.grid_origin[1]) // self.cell_h
            if 0 <= c < GRID_SIZE and 0 <= r < GRID_SIZE:
                self.selected = (int(c), int(r))
        elif event.type == pygame.KEYDOWN:
            if self.is_over:
                return
            if event.key == pygame.K_r:
                self.reset_level()
                return
            c, r = self.selected
            if event.key in (pygame.K_0, pygame.K_DELETE, pygame.K_BACKSPACE):
                if not self.locked[r][c]:
                    self.grid[r][c] = 0
            else:
                # Number keys 1-9
                digit_map = {
                    pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3,
                    pygame.K_4: 4, pygame.K_5: 5, pygame.K_6: 6,
                    pygame.K_7: 7, pygame.K_8: 8, pygame.K_9: 9,
                }
                if event.key in digit_map:
                    val = digit_map[event.key]
                    if not self.locked[r][c]:
                        # Allow rewriting the selected cell directly; show feedback if invalid
                        self.grid[r][c] = val
                        if not self._is_valid_move(r, c, val):
                            self.invalid_flash = 0.35

    def _is_valid_move(self, r: int, c: int, val: int) -> bool:
        # Check row and column
        for i in range(GRID_SIZE):
            if self.grid[r][i] == val and i != c:
                return False
            if self.grid[i][c] == val and i != r:
                return False
        # Check subgrid
        sr = (r // 3) * 3
        sc = (c // 3) * 3
        for rr in range(sr, sr + 3):
            for cc in range(sc, sc + 3):
                if self.grid[rr][cc] == val and not (rr == r and cc == c):
                    return False
        return True

    def _is_complete(self) -> bool:
        # All cells filled and satisfy rules
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                val = self.grid[r][c]
                if val == 0:
                    return False
                if not self._is_valid_move(r, c, val):
                    return False
        return True

    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return
        self.elapsed += dt
        if self.invalid_flash > 0.0:
            self.invalid_flash -= dt
        if self._is_complete():
            self.is_over = True
            self.results_header = f"Sudoku Complete!"

    def scores(self):
        # Show time taken
        return [("Solo", float(self.elapsed))]

    def _cell_rect(self, c: int, r: int) -> pygame.Rect:
        x0, y0 = self.grid_origin
        return pygame.Rect(x0 + c * self.cell_w, y0 + r * self.cell_h, self.cell_w, self.cell_h)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Board
        pygame.draw.rect(surface, (80, 80, 100), self.bounds, 2)
        # Cells
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                rect = self._cell_rect(c, r)
                # Selected highlight
                if (c, r) == self.selected:
                    pygame.draw.rect(surface, (120, 120, 180), rect, 3)
                # Numbers
                val = self.grid[r][c]
                if val != 0:
                    color = (240, 240, 240) if self.locked[r][c] else (200, 220, 240)
                    text = font.render(str(val), True, color)
                    surface.blit(text, (rect.centerx - text.get_width()//2, rect.centery - text.get_height()//2))
        # Grid lines (thicker at subgrid boundaries)
        for i in range(GRID_SIZE + 1):
            x = self.bounds.left + i * self.cell_w
            y = self.bounds.top + i * self.cell_h
            w = 2 if i % 3 != 0 else 4
            pygame.draw.line(surface, (150, 150, 180), (x, self.bounds.top), (x, self.bounds.bottom), w)
            pygame.draw.line(surface, (150, 150, 180), (self.bounds.left, y), (self.bounds.right, y), w)
        # Invalid flash overlay
        if self.invalid_flash > 0.0:
            c, r = self.selected
            rect = self._cell_rect(c, r)
            overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            overlay.fill((255, 60, 60, int(120 * min(1.0, self.invalid_flash * 3))))
            surface.blit(overlay, rect.topleft)
        # HUD
        hud = font.render(f"Time: {self.elapsed:.1f}s", True, (255, 255, 255))
        surface.blit(hud, (10, 10))
        # Level and puzzle HUD
        pcount = len(PRESET_PUZZLES_BY_LEVEL.get(self.level, []))
        ptext = font.render(f"Level: {self.level.capitalize()}  Puzzle: {self.current_puzzle_index+1}/{pcount}", True, (220, 220, 230))
        surface.blit(ptext, (10, 34))
        # Reset button
        pygame.draw.rect(surface, (70, 70, 90), self.reset_btn_rect)
        pygame.draw.rect(surface, (180, 180, 220), self.reset_btn_rect, 2)
        rtext = font.render("Reset", True, (240, 240, 240))
        surface.blit(rtext, (self.reset_btn_rect.centerx - rtext.get_width()//2, self.reset_btn_rect.centery - rtext.get_height()//2))
