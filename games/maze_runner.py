from __future__ import annotations
import random
import pygame
from typing import List, Tuple


class MazeRunnerGame:
    def __init__(self, bounds: pygame.Rect):
        self.bounds = bounds
        # Grid setup (odd dimensions for nicer mazes)
        self.grid_cols = 15
        self.grid_rows = 11
        self.cell_w = self.bounds.width // self.grid_cols
        self.cell_h = self.bounds.height // self.grid_rows
        # Maze: 0 = empty, 1 = wall
        self.maze: List[List[int]] = self._make_maze()
        # Player and goal in grid coordinates
        self.player_pos: Tuple[int, int] = (1, 1)
        self.goal: Tuple[int, int] = (self.grid_cols - 2, self.grid_rows - 2)
        # Movement state for continuous stepping
        self.move_dir: Tuple[int, int] = (0, 0)
        self.move_delay = 0.12  # seconds between grid steps while holding
        self.move_timer = 0.0
        # State
        self.is_over = False
        self.results_header = None
        self.elapsed = 0.0
        self.higher_time_wins = False
        self.show_time_in_results = True
        self.result_label = "Time"

    def _make_maze(self) -> List[List[int]]:
        cols, rows = self.grid_cols, self.grid_rows
        # Start with all walls
        maze = [[1 for _ in range(cols)] for _ in range(rows)]

        def in_bounds(cx: int, cy: int) -> bool:
            return 0 < cx < cols - 1 and 0 < cy < rows - 1

        # DFS backtracker on odd cells
        start = (1, 1)
        stack = [start]
        maze[start[1]][start[0]] = 0

        while stack:
            x, y = stack[-1]
            # Neighbors two steps away
            neighbors = []
            for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                nx, ny = x + dx, y + dy
                if in_bounds(nx, ny) and maze[ny][nx] == 1:
                    neighbors.append((nx, ny))
            if not neighbors:
                stack.pop()
                continue
            nx, ny = random.choice(neighbors)
            # Carve through the wall between
            wx, wy = (x + nx) // 2, (y + ny) // 2
            maze[wy][wx] = 0
            maze[ny][nx] = 0
            stack.append((nx, ny))

        # Ensure start and goal cells are open
        maze[1][1] = 0
        gx, gy = self.grid_cols - 2, self.grid_rows - 2
        maze[gy][gx] = 0
        # Carve a path around goal if boxed in
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ax, ay = gx + dx, gy + dy
            if 0 < ax < cols - 1 and 0 < ay < rows - 1:
                maze[ay][ax] = 0

        return maze

    def reset(self):
        self.player_pos = (1, 1)
        self.elapsed = 0.0
        self.is_over = False
        self.results_header = None
        self.move_dir = (0, 0)
        self.move_timer = 0.0

    def handle_event(self, event: pygame.event.Event):
        if self.is_over:
            return
        if event.type == pygame.KEYDOWN:
            dx, dy = 0, 0
            if event.key in (pygame.K_LEFT, pygame.K_a):
                dx = -1
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                dx = 1
            elif event.key in (pygame.K_UP, pygame.K_w):
                dy = -1
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                dy = 1
            if dx != 0 or dy != 0:
                # Set continuous movement direction
                self.move_dir = (dx, dy)
                # Immediate step on press
                self._try_move(dx, dy)
                self.move_timer = self.move_delay
        elif event.type == pygame.KEYUP:
            # Stop movement when the released key matches current direction
            if event.key in (pygame.K_LEFT, pygame.K_a) and self.move_dir == (-1, 0):
                self.move_dir = (0, 0)
            elif event.key in (pygame.K_RIGHT, pygame.K_d) and self.move_dir == (1, 0):
                self.move_dir = (0, 0)
            elif event.key in (pygame.K_UP, pygame.K_w) and self.move_dir == (0, -1):
                self.move_dir = (0, 0)
            elif event.key in (pygame.K_DOWN, pygame.K_s) and self.move_dir == (0, 1):
                self.move_dir = (0, 0)

    def _try_move(self, dx: int, dy: int):
        px, py = self.player_pos
        nx, ny = px + dx, py + dy
        # Block walls
        if self._is_wall(nx, ny):
            return
        self.player_pos = (nx, ny)
        if self.player_pos == self.goal:
            self.is_over = True
            self.results_header = f"Maze Complete!"

    def _is_wall(self, gx: int, gy: int) -> bool:
        if not (0 <= gx < self.grid_cols and 0 <= gy < self.grid_rows):
            return True
        return self.maze[gy][gx] == 1

    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return
        self.elapsed += dt
        # Continuous grid stepping while a direction is held
        if self.move_dir != (0, 0):
            self.move_timer -= dt
            if self.move_timer <= 0.0:
                self._try_move(self.move_dir[0], self.move_dir[1])
                self.move_timer = self.move_delay

    def scores(self):
        # Lower time is better
        return [("Solo", float(self.elapsed))]

    def _cell_rect(self, gx: int, gy: int) -> pygame.Rect:
        return pygame.Rect(self.bounds.left + gx * self.cell_w,
                           self.bounds.top + gy * self.cell_h,
                           self.cell_w, self.cell_h)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Maze walls
        for y in range(self.grid_rows):
            for x in range(self.grid_cols):
                r = self._cell_rect(x, y)
                if self.maze[y][x] == 1:
                    pygame.draw.rect(surface, (70, 70, 90), r)
                    pygame.draw.rect(surface, (150, 150, 190), r, 2)
        # Goal
        gr = self._cell_rect(self.goal[0], self.goal[1])
        pygame.draw.rect(surface, (90, 180, 100), gr)
        pygame.draw.rect(surface, (200, 240, 210), gr, 2)
        # Player
        pr = self._cell_rect(self.player_pos[0], self.player_pos[1])
        pygame.draw.rect(surface, (200, 200, 240), pr)
        pygame.draw.rect(surface, (240, 240, 250), pr, 2)
        # HUD
        t = font.render(f"Time: {self.elapsed:.1f}s", True, (255, 255, 255))
        surface.blit(t, (10, 10))
