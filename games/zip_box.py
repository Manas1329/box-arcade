from __future__ import annotations
import pygame
from typing import List, Tuple, Optional


class ZipBoxGame:
    """Linked-number path puzzle inspired by LinkedIn's Zip.

    Connect numbered nodes in order with non-overlapping paths that
    fill the grid completely.
    """

    def __init__(self, bounds: pygame.Rect):
        self.bounds = bounds
        # Levels: grid size and numbered node positions (index, x, y)
        self.levels: List[dict] = [
            {
                "size": (5, 5),
                "nodes": [(1, 0, 0), (2, 4, 0), (3, 4, 4), (4, 0, 4)],
            },
            {
                "size": (5, 5),
                "nodes": [(1, 2, 0), (2, 4, 2), (3, 2, 4), (4, 0, 2)],
            },
            {
                "size": (6, 6),
                "nodes": [(1, 0, 0), (2, 5, 1), (3, 0, 3), (4, 5, 4), (5, 2, 5)],
            },
        ]
        self.current_level = 0

        # Grid & geometry
        self.cols = 0
        self.rows = 0
        self.cell_size = 0
        self.board_rect: pygame.Rect = bounds.copy()

        # Node and path data
        self.node_grid: List[List[int]] = []  # 0 or node index
        # Visited cells for the single global path
        self.visited: List[List[bool]] = []
        self.node_positions: dict[int, Tuple[int, int]] = {}
        self.max_index: int = 0

        # Single continuous path: ordered list of grid cells
        self.path: List[Tuple[int, int]] = []
        self.drawing: bool = False
        # Highest numbered node reached so far along the path
        self.highest_node_visited: int = 0

        # Keyboard cursor
        self.cursor: Tuple[int, int] = (0, 0)

        # Timing / results
        self.elapsed = 0.0
        self.is_over = False
        self.results_header: Optional[str] = None
        self.higher_time_wins = False
        self.show_time_in_results = True
        self.result_label = "Time"

        self._load_level(self.current_level)

    # ------------------------------------------------------------------
    # Level setup
    # ------------------------------------------------------------------
    def _load_level(self, idx: int):
        level = self.levels[idx % len(self.levels)]
        self.cols, self.rows = level["size"]
        # Compute cell size and centered board within bounds
        self.cell_size = min(self.bounds.width // self.cols, self.bounds.height // self.rows)
        board_w = self.cell_size * self.cols
        board_h = self.cell_size * self.rows
        self.board_rect = pygame.Rect(0, 0, board_w, board_h)
        self.board_rect.center = self.bounds.center

        self.node_grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.visited = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        self.node_positions.clear()
        self.max_index = 0

        for index, x, y in level["nodes"]:
            if 0 <= x < self.cols and 0 <= y < self.rows:
                self.node_grid[y][x] = index
                self.node_positions[index] = (x, y)
                self.max_index = max(self.max_index, index)

        self.path = []
        self.drawing = False
        self.highest_node_visited = 0
        self.cursor = (0, 0)
        self.elapsed = 0.0
        self.is_over = False
        self.results_header = None

    def reset(self):
        # Restart current level
        self._load_level(self.current_level)

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------
    def _cell_from_pos(self, pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        x, y = pos
        if not self.board_rect.collidepoint(x, y):
            return None
        gx = (x - self.board_rect.left) // self.cell_size
        gy = (y - self.board_rect.top) // self.cell_size
        if 0 <= gx < self.cols and 0 <= gy < self.rows:
            return gx, gy
        return None

    # ------------------------------------------------------------------
    # Path logic (single global path 1 -> N)
    # ------------------------------------------------------------------
    def _rebuild_visit_state(self):
        """Recompute visited flags and highest_node_visited from self.path."""
        self.visited = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        self.highest_node_visited = 0
        for x, y in self.path:
            if 0 <= x < self.cols and 0 <= y < self.rows:
                self.visited[y][x] = True
                node_idx = self.node_grid[y][x]
                if node_idx > 0 and node_idx == self.highest_node_visited + 1:
                    self.highest_node_visited = node_idx

    def _start_or_edit_path_at(self, gx: int, gy: int):
        node_idx = self.node_grid[gy][gx]
        # If we already have a path, allow editing by clicking on any cell on it
        if self.path:
            for i, (px, py) in enumerate(self.path):
                if (px, py) == (gx, gy):
                    # Truncate path to this point and continue drawing from here
                    self.path = self.path[: i + 1]
                    self._rebuild_visit_state()
                    self.drawing = True
                    return
        # Otherwise, or if click is not on an existing path, start from node 1 only
        if not self.path and node_idx == 1:
            self.path = [(gx, gy)]
            self._rebuild_visit_state()
            self.drawing = True

    def _extend_path_to(self, gx: int, gy: int):
        if not self.drawing or not self.path:
            return
        last_x, last_y = self.path[-1]
        if (gx, gy) == (last_x, last_y):
            return
        # Must move orthogonally by one cell
        if abs(gx - last_x) + abs(gy - last_y) != 1:
            return

        # Backtracking: moving into previous cell removes last segment
        if len(self.path) >= 2 and (gx, gy) == self.path[-2]:
            px, py = self.path.pop()
            # Rebuild full state to keep node visits/order correct
            self._rebuild_visit_state()
            return

        # Cannot cross or overlap: block entering any already-visited cell
        if self.visited[gy][gx]:
            return

        node_idx = self.node_grid[gy][gx]
        # Enforce increasing order for numbered nodes along the path
        if node_idx > 0:
            # Cannot skip ahead: you must visit 1,2,3,...,max in order
            if node_idx > self.highest_node_visited + 1:
                return

        # Extend
        self.path.append((gx, gy))
        self.visited[gy][gx] = True
        if node_idx > 0 and node_idx == self.highest_node_visited + 1:
            self.highest_node_visited = node_idx

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event):
        if self.is_over:
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                # Advance to next level or restart
                self.current_level = (self.current_level + 1) % len(self.levels)
                self._load_level(self.current_level)
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = self._cell_from_pos(event.pos)
            if cell is not None:
                gx, gy = cell
                self.drawing = True
                self._start_or_edit_path_at(gx, gy)
        elif event.type == pygame.MOUSEMOTION and self.drawing:
            cell = self._cell_from_pos(event.pos)
            if cell is not None:
                self._extend_path_to(*cell)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.drawing = False
        elif event.type == pygame.KEYDOWN:
            cx, cy = self.cursor
            if event.key == pygame.K_LEFT:
                cx = max(0, cx - 1)
            elif event.key == pygame.K_RIGHT:
                cx = min(self.cols - 1, cx + 1)
            elif event.key == pygame.K_UP:
                cy = max(0, cy - 1)
            elif event.key == pygame.K_DOWN:
                cy = min(self.rows - 1, cy + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                # Toggle drawing from cursor position
                if not self.drawing:
                    self._start_or_edit_path_at(cx, cy)
                    # If we successfully started, enable drawing
                    if self.path and self.path[-1] == (cx, cy):
                        self.drawing = True
                else:
                    self.drawing = False
            self.cursor = (cx, cy)
            # When moving cursor with an active path, extend if legal
            if self.drawing and event.key in (
                pygame.K_LEFT,
                pygame.K_RIGHT,
                pygame.K_UP,
                pygame.K_DOWN,
            ):
                self._extend_path_to(cx, cy)

    # ------------------------------------------------------------------
    # Update & victory check
    # ------------------------------------------------------------------
    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return
        self.elapsed += dt
        if self._check_complete():
            self.is_over = True
            self.results_header = f"Zip Box — Solved in {self.elapsed:0.1f}s"

    def _check_complete(self) -> bool:
        # Need at least one path and at least 2 numbered nodes
        if self.max_index < 2 or not self.path:
            return False

        # Path must start at node 1 and end at the highest node
        sx, sy = self.path[0]
        ex, ey = self.path[-1]
        if self.node_grid[sy][sx] != 1:
            return False
        if self.node_grid[ey][ex] != self.max_index:
            return False

        # Ensure nodes appear in strictly increasing order along the path
        seen = 0
        seen_nodes = set()
        for x, y in self.path:
            idx = self.node_grid[y][x]
            if idx > 0:
                if idx in seen_nodes:
                    # Already visited this numbered cell earlier
                    return False
                if idx != seen + 1:
                    return False
                seen = idx
                seen_nodes.add(idx)
        if seen != self.max_index:
            return False

        # Grid must be completely filled: every cell visited exactly once
        if len(self.path) != self.cols * self.rows:
            return False
        # Also verify no holes according to visited flags
        for y in range(self.rows):
            for x in range(self.cols):
                if not self.visited[y][x]:
                    return False
        return True

    # ------------------------------------------------------------------
    # Results integration
    # ------------------------------------------------------------------
    def scores(self):
        # Lower time is better; ResultsScene uses higher_time_wins=False
        return [("Solo", float(self.elapsed))]

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _cell_rect(self, x: int, y: int) -> pygame.Rect:
        bx, by = self.board_rect.topleft
        return pygame.Rect(bx + x * self.cell_size, by + y * self.cell_size,
                           self.cell_size, self.cell_size)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Background
        pygame.draw.rect(surface, (15, 15, 25), self.bounds)

        # Grid background and lines
        pygame.draw.rect(surface, (20, 20, 32), self.board_rect)
        for c in range(self.cols + 1):
            x = self.board_rect.left + c * self.cell_size
            pygame.draw.line(surface, (60, 60, 90), (x, self.board_rect.top), (x, self.board_rect.bottom))
        for r in range(self.rows + 1):
            y = self.board_rect.top + r * self.cell_size
            pygame.draw.line(surface, (60, 60, 90), (self.board_rect.left, y), (self.board_rect.right, y))
        pygame.draw.rect(surface, (120, 120, 170), self.board_rect, 2)

        # Draw single path (uniform color) based on visited cells
        path_color = (84, 160, 240)
        for y in range(self.rows):
            for x in range(self.cols):
                if self.visited[y][x]:
                    rect = self._cell_rect(x, y)
                    pygame.draw.rect(surface, path_color, rect)

        # Draw nodes on top
        for idx, (nx, ny) in self.node_positions.items():
            rect = self._cell_rect(nx, ny)
            pygame.draw.rect(surface, (20, 20, 28), rect)
            pygame.draw.rect(surface, (240, 240, 250), rect, 2)
            text = font.render(str(idx), True, (240, 240, 250))
            surface.blit(
                text,
                (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2),
            )

        # Cursor outline for keyboard navigation
        cx, cy = self.cursor
        if 0 <= cx < self.cols and 0 <= cy < self.rows:
            rect = self._cell_rect(cx, cy)
            pygame.draw.rect(surface, (240, 240, 255), rect, 2)

        # HUD
        level_label = font.render(f"Level {self.current_level + 1}/{len(self.levels)}", True, (230, 230, 230))
        time_label = font.render(f"Time: {self.elapsed:0.1f}s", True, (220, 220, 220))
        hint = font.render("Drag or Arrows+Enter/Space to draw", True, (200, 200, 210))
        surface.blit(level_label, (self.bounds.left + 10, self.bounds.top + 8))
        surface.blit(time_label, (self.bounds.left + 10, self.bounds.top + 32))
        surface.blit(hint, (self.bounds.left + 10, self.bounds.bottom - 26))
