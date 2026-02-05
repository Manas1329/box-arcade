from __future__ import annotations
import random
from typing import List, Optional, Tuple

import pygame


COLS = 10
ROWS = 20


class TetrisBoxGame:
    """Classic singleplayer Tetris with box-only visuals."""

    def __init__(self, bounds: pygame.Rect):
        self.bounds = bounds
        # Derive cell size and board placement inside bounds
        self.cell_size = min(bounds.width // COLS, bounds.height // ROWS)
        board_w = self.cell_size * COLS
        board_h = self.cell_size * ROWS
        self.board_rect = pygame.Rect(0, 0, board_w, board_h)
        self.board_rect.center = bounds.center

        # Grid: ROWS x COLS of Optional[color]
        self.grid: List[List[Optional[Tuple[int, int, int]]]] = [
            [None for _ in range(COLS)] for _ in range(ROWS)
        ]

        # Piece definitions: list of rotation states (each is list of (x, y))
        self.shapes = self._build_shapes()
        self.shape_colors = {
            "I": (84, 200, 240),
            "O": (240, 220, 84),
            "T": (200, 120, 240),
            "S": (120, 220, 140),
            "Z": (240, 120, 120),
            "J": (120, 140, 240),
            "L": (240, 180, 120),
        }

        # Current piece state
        self.current_shape: Optional[str] = None
        self.current_rot: int = 0
        self.current_pos: Tuple[int, int] = (0, 0)  # (x, y) in grid coords

        # Next piece preview
        self.next_shape: Optional[str] = None

        # Timing
        self.fall_interval = 0.7
        self.fall_timer = 0.0
        self.level = 1
        self.lines_cleared = 0

        # Input helpers
        self.soft_drop = False

        # Game state / scoring
        self.score = 0
        self.is_over = False
        self.results_header: Optional[str] = None
        self.higher_time_wins = True   # treat score as "higher is better"
        self.show_time_in_results = True
        self.result_label = "Score"

        self.reset()

    # ------------------------------------------------------------------
    # Setup and pieces
    # ------------------------------------------------------------------
    def _build_shapes(self):
        # Each shape is a list of rotation states, each state is a list
        # of (x, y) offsets within a 4x4 region.
        return {
            "I": [
                [(0, 1), (1, 1), (2, 1), (3, 1)],
                [(2, 0), (2, 1), (2, 2), (2, 3)],
            ],
            "O": [
                [(1, 0), (2, 0), (1, 1), (2, 1)],
            ],
            "T": [
                [(1, 0), (0, 1), (1, 1), (2, 1)],
                [(1, 0), (1, 1), (2, 1), (1, 2)],
                [(0, 1), (1, 1), (2, 1), (1, 2)],
                [(1, 0), (0, 1), (1, 1), (1, 2)],
            ],
            "S": [
                [(1, 0), (2, 0), (0, 1), (1, 1)],
                [(1, 0), (1, 1), (2, 1), (2, 2)],
            ],
            "Z": [
                [(0, 0), (1, 0), (1, 1), (2, 1)],
                [(2, 0), (1, 1), (2, 1), (1, 2)],
            ],
            "J": [
                [(0, 0), (0, 1), (1, 1), (2, 1)],
                [(1, 0), (2, 0), (1, 1), (1, 2)],
                [(0, 1), (1, 1), (2, 1), (2, 2)],
                [(1, 0), (1, 1), (0, 2), (1, 2)],
            ],
            "L": [
                [(2, 0), (0, 1), (1, 1), (2, 1)],
                [(1, 0), (1, 1), (1, 2), (2, 2)],
                [(0, 1), (1, 1), (2, 1), (0, 2)],
                [(0, 0), (1, 0), (1, 1), (1, 2)],
            ],
        }

    def reset(self):
        self.grid = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.level = 1
        self.lines_cleared = 0
        self.score = 0
        self.fall_interval = 0.7
        self.fall_timer = 0.0
        self.soft_drop = False
        self.is_over = False
        self.results_header = None
        self.next_shape = random.choice(list(self.shapes.keys()))
        self._spawn_new_piece()

    # ------------------------------------------------------------------
    # Input and control
    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event):
        if self.is_over:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.reset()
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self._try_move(-1, 0, 0)
            elif event.key == pygame.K_RIGHT:
                self._try_move(1, 0, 0)
            elif event.key == pygame.K_DOWN:
                self.soft_drop = True
                self._try_move(0, 1, 0)
            elif event.key in (pygame.K_UP, pygame.K_SPACE):
                self._try_move(0, 0, 1)
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_DOWN:
                self.soft_drop = False

    # ------------------------------------------------------------------
    # Core mechanics
    # ------------------------------------------------------------------
    def _spawn_new_piece(self):
        self.current_shape = self.next_shape
        self.current_rot = 0
        # Spawn near top center
        spawn_x = COLS // 2 - 2
        spawn_y = 0
        self.current_pos = (spawn_x, spawn_y)
        # Choose next
        self.next_shape = random.choice(list(self.shapes.keys()))
        # Check immediate collision for game over
        if not self._can_place(self.current_shape, self.current_rot, self.current_pos):
            self.is_over = True
            self.results_header = "Tetris — Game Over"

    def _can_place(self, shape: Optional[str], rot: int, pos: Tuple[int, int]) -> bool:
        if shape is None:
            return False
        blocks = self.shapes[shape][rot]
        px, py = pos
        for bx, by in blocks:
            x = px + bx
            y = py + by
            if x < 0 or x >= COLS or y >= ROWS:
                return False
            if y >= 0 and self.grid[y][x] is not None:
                return False
        return True

    def _try_move(self, dx: int, dy: int, drot: int):
        if self.current_shape is None:
            return
        new_rot = self.current_rot
        if drot != 0:
            states = len(self.shapes[self.current_shape])
            new_rot = (self.current_rot + drot) % states
        px, py = self.current_pos
        new_pos = (px + dx, py + dy)
        if self._can_place(self.current_shape, new_rot, new_pos):
            self.current_rot = new_rot
            self.current_pos = new_pos
            return True
        return False

    def _lock_piece(self):
        if self.current_shape is None:
            return
        blocks = self.shapes[self.current_shape][self.current_rot]
        px, py = self.current_pos
        color = self.shape_colors[self.current_shape]
        for bx, by in blocks:
            x = px + bx
            y = py + by
            if 0 <= x < COLS and 0 <= y < ROWS:
                self.grid[y][x] = color
        self._clear_lines()
        self._spawn_new_piece()

    def _clear_lines(self):
        new_rows: List[List[Optional[Tuple[int, int, int]]]] = []
        lines = 0
        for row in self.grid:
            if all(cell is not None for cell in row):
                lines += 1
            else:
                new_rows.append(row)
        if lines > 0:
            # Add empty rows at the top
            for _ in range(lines):
                new_rows.insert(0, [None for _ in range(COLS)])
            self.grid = new_rows
            self.lines_cleared += lines
            # Simple scoring: 40, 100, 300, 1200 like classic Tetris
            if lines == 1:
                self.score += 40 * self.level
            elif lines == 2:
                self.score += 100 * self.level
            elif lines == 3:
                self.score += 300 * self.level
            else:
                self.score += 1200 * self.level
            # Level up every 10 lines
            self.level = 1 + self.lines_cleared // 10
            self.fall_interval = max(0.12, 0.7 - (self.level - 1) * 0.06)

    def update(self, dt: float, input_handler, pressed):
        if self.is_over or self.current_shape is None:
            return

        speed = self.fall_interval
        if self.soft_drop:
            speed *= 0.2
        self.fall_timer += dt
        if self.fall_timer >= speed:
            self.fall_timer -= speed
            moved = self._try_move(0, 1, 0)
            if not moved:
                # Lock piece when it can no longer move down
                self._lock_piece()

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------
    def scores(self):
        return [("Solo", float(self.score))]

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def _cell_rect(self, x: int, y: int) -> pygame.Rect:
        bx, by = self.board_rect.topleft
        return pygame.Rect(bx + x * self.cell_size, by + y * self.cell_size,
                           self.cell_size, self.cell_size)

    def _draw_grid(self, surface: pygame.Surface):
        # Background
        pygame.draw.rect(surface, (20, 20, 30), self.board_rect)
        # Grid lines
        for c in range(COLS + 1):
            x = self.board_rect.left + c * self.cell_size
            pygame.draw.line(surface, (60, 60, 80), (x, self.board_rect.top), (x, self.board_rect.bottom))
        for r in range(ROWS + 1):
            y = self.board_rect.top + r * self.cell_size
            pygame.draw.line(surface, (60, 60, 80), (self.board_rect.left, y), (self.board_rect.right, y))
        pygame.draw.rect(surface, (120, 120, 160), self.board_rect, 2)

    def _draw_locked_blocks(self, surface: pygame.Surface):
        for y in range(ROWS):
            for x in range(COLS):
                color = self.grid[y][x]
                if color is not None:
                    rect = self._cell_rect(x, y)
                    pygame.draw.rect(surface, color, rect)
                    pygame.draw.rect(surface, (240, 240, 250), rect, 1)

    def _draw_current_piece(self, surface: pygame.Surface):
        if self.current_shape is None:
            return
        blocks = self.shapes[self.current_shape][self.current_rot]
        px, py = self.current_pos
        color = self.shape_colors[self.current_shape]
        for bx, by in blocks:
            x = px + bx
            y = py + by
            if y < 0:
                continue
            if 0 <= x < COLS and 0 <= y < ROWS:
                rect = self._cell_rect(x, y)
                pygame.draw.rect(surface, color, rect)
                pygame.draw.rect(surface, (250, 250, 255), rect, 1)

    def _draw_next_preview(self, surface: pygame.Surface, font: pygame.font.Font):
        if self.next_shape is None:
            return
        # Draw to the right of the board
        label = font.render("Next", True, (230, 230, 230))
        label_pos = (self.board_rect.right + 24, self.board_rect.top)
        surface.blit(label, label_pos)

        preview_size = self.cell_size // 2
        preview_rect = pygame.Rect(
            self.board_rect.right + 24,
            self.board_rect.top + 28,
            preview_size * 4,
            preview_size * 4,
        )
        pygame.draw.rect(surface, (30, 30, 50), preview_rect)
        pygame.draw.rect(surface, (120, 120, 160), preview_rect, 2)

        blocks = self.shapes[self.next_shape][0]
        color = self.shape_colors[self.next_shape]
        # Center the shape in the 4x4 preview box
        for bx, by in blocks:
            x = preview_rect.left + bx * preview_size
            y = preview_rect.top + by * preview_size
            rect = pygame.Rect(x, y, preview_size, preview_size)
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, (240, 240, 250), rect, 1)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Clear bounds area
        pygame.draw.rect(surface, (10, 10, 20), self.bounds)

        self._draw_grid(surface)
        self._draw_locked_blocks(surface)
        self._draw_current_piece(surface)
        self._draw_next_preview(surface, font)

        # HUD
        hud_x = self.board_rect.left - 140
        score_surf = font.render(f"Score: {self.score}", True, (255, 255, 255))
        level_surf = font.render(f"Level: {self.level}", True, (230, 230, 230))
        lines_surf = font.render(f"Lines: {self.lines_cleared}", True, (220, 220, 220))
        hint = font.render("Arrows: Move/Soft  Up/Space: Rotate", True, (200, 200, 210))

        surface.blit(score_surf, (hud_x, self.board_rect.top))
        surface.blit(level_surf, (hud_x, self.board_rect.top + 24))
        surface.blit(lines_surf, (hud_x, self.board_rect.top + 48))
        surface.blit(hint, (hud_x, self.board_rect.bottom - 24))
