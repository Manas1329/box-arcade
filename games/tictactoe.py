"""
Tic Tac Toe (Singleplayer / Local 1v1)
- 3x3 grid, alternate turns, detect win/draw.
- Keyboard-only: use arrows to move cursor, Enter to place.
- Singleplayer uses a simple rule-based AI (win, block, center, corner, random).
"""
from __future__ import annotations
from typing import List, Optional, Tuple, Dict
import random
import pygame


class TicTacToeGame:
    def __init__(self, bounds: pygame.Rect, mode: str = "single", *,
                 player_names: Optional[Tuple[str, str]] = None,
                 scoreboard: Optional[Dict[str, int]] = None,
                 human_symbol: Optional[str] = None,
                 start_symbol: Optional[str] = None):
        self.bounds = bounds
        self.mode = mode  # "single" or "pvp"
        self.grid: List[List[Optional[str]]] = [[None for _ in range(3)] for _ in range(3)]
        # Names and scoreboard
        if player_names is None:
            player_names = ("Player 1", "Player 2") if mode == "pvp" else ("You", "Bot")
        self.names = player_names
        self.scoreboard: Dict[str, int] = scoreboard if scoreboard is not None else {self.names[0]: 0, self.names[1]: 0}

        # Symbol assignment
        if mode == "single":
            # human_symbol optionally provided; else random
            if human_symbol is None:
                human_symbol = random.choice(['X', 'O'])
            self.human_symbol = human_symbol
            self.ai_symbol = 'O' if human_symbol == 'X' else 'X'
        else:
            # PvP alternating externally via launcher; default X for names[0]
            self.human_symbol = 'X'  # unused in pvp
            self.ai_symbol = 'O'     # unused in pvp

        # Starting symbol
        self.turn = start_symbol if start_symbol in ('X', 'O') else 'X'
        self.cursor = (1, 1)
        self.is_over = False
        self.winner: Optional[str] = None  # 'X', 'O', or None for draw
        # Results formatting
        self.higher_time_wins = True
        self.show_time_in_results = True
        self.result_label = "Wins"
        self.results_header: Optional[str] = None

        # Layout
        self.cell_w = self.bounds.width // 3
        self.cell_h = self.bounds.height // 3

    def handle_event(self, event: pygame.event.Event):
        if self.is_over:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self.cursor = (max(0, self.cursor[0] - 1), self.cursor[1])
            elif event.key == pygame.K_RIGHT:
                self.cursor = (min(2, self.cursor[0] + 1), self.cursor[1])
            elif event.key == pygame.K_UP:
                self.cursor = (self.cursor[0], max(0, self.cursor[1] - 1))
            elif event.key == pygame.K_DOWN:
                self.cursor = (self.cursor[0], min(2, self.cursor[1] + 1))
            elif event.key == pygame.K_RETURN:
                # In singleplayer, only allow human to place on their turn
                if self.mode == "single":
                    if self.turn == self.human_symbol:
                        self._place_at_cursor()
                else:
                    self._place_at_cursor()

    def _place_at_cursor(self):
        if self.is_over:
            return
        x, y = self.cursor
        if self.grid[y][x] is not None:
            return
        self.grid[y][x] = self.turn
        if self._check_end():
            return
        self.turn = 'O' if self.turn == 'X' else 'X'
        if self.mode == "single" and self.turn == self.ai_symbol:
            self._ai_move()

    def _ai_move(self):
        # Try to win
        move = self._find_winning_move('O')
        if move is None:
            # Try to block X
            move = self._find_winning_move('X')
        if move is None:
            # Center
            if self.grid[1][1] is None:
                move = (1, 1)
        if move is None:
            # Corners
            corners = [(0,0),(2,0),(0,2),(2,2)]
            empt = [(x,y) for (x,y) in corners if self.grid[y][x] is None]
            if empt:
                move = random.choice(empt)
        if move is None:
            # Any empty
            empt = [(x,y) for y in range(3) for x in range(3) if self.grid[y][x] is None]
            if empt:
                move = random.choice(empt)
        if move is not None:
            self.grid[move[1]][move[0]] = self.ai_symbol
            if self._check_end():
                return
            self.turn = self.human_symbol

    def _find_winning_move(self, player: str) -> Optional[Tuple[int,int]]:
        # Check all empties for immediate win
        for y in range(3):
            for x in range(3):
                if self.grid[y][x] is None:
                    self.grid[y][x] = player
                    win = self._has_won(player)
                    self.grid[y][x] = None
                    if win:
                        return (x, y)
        return None

    def _has_won(self, player: str) -> bool:
        g = self.grid
        # Rows/Cols
        for i in range(3):
            if all(g[i][j] == player for j in range(3)):
                return True
            if all(g[j][i] == player for j in range(3)):
                return True
        # Diagonals
        if all(g[i][i] == player for i in range(3)):
            return True
        if all(g[i][2-i] == player for i in range(3)):
            return True
        return False

    def _check_end(self) -> bool:
        if self._has_won('X'):
            self.is_over = True
            self.winner = 'X'
            who = self._owner_of('X')
            self.results_header = f"Winner: {who} (X)" if who else "Winner: X"
            if who:
                self.scoreboard[who] = self.scoreboard.get(who, 0) + 1
            return True
        if self._has_won('O'):
            self.is_over = True
            self.winner = 'O'
            who = self._owner_of('O')
            self.results_header = f"Winner: {who} (O)" if who else "Winner: O"
            if who:
                self.scoreboard[who] = self.scoreboard.get(who, 0) + 1
            return True
        # Draw
        if all(self.grid[y][x] is not None for y in range(3) for x in range(3)):
            self.is_over = True
            self.winner = None
            self.results_header = "Draw"
            return True
        return False

    def update(self, dt: float, input_handler, pressed):
        # No continuous updates needed; moves handled in handle_event or AI
        # If singleplayer and AI starts, make the initial move automatically
        if not self.is_over and self.mode == "single" and self.turn == self.ai_symbol:
            self._ai_move()

    def scores(self):
        # Provide cumulative scoreboard without symbols
        return [(self.names[0], float(self.scoreboard.get(self.names[0], 0))),
                (self.names[1], float(self.scoreboard.get(self.names[1], 0)))]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Board
        pygame.draw.rect(surface, (80, 80, 100), self.bounds, 2)
        # Grid lines
        for i in [1, 2]:
            x = self.bounds.left + i * self.cell_w
            y = self.bounds.top + i * self.cell_h
            pygame.draw.line(surface, (150, 150, 180), (x, self.bounds.top), (x, self.bounds.bottom), 2)
            pygame.draw.line(surface, (150, 150, 180), (self.bounds.left, y), (self.bounds.right, y), 2)
        # Cursor highlight
        cx, cy = self.cursor
        cur_rect = pygame.Rect(self.bounds.left + cx * self.cell_w, self.bounds.top + cy * self.cell_h, self.cell_w, self.cell_h)
        pygame.draw.rect(surface, (120, 120, 180), cur_rect, 3)
        # Pieces
        for y in range(3):
            for x in range(3):
                v = self.grid[y][x]
                if v is None:
                    continue
                r = pygame.Rect(self.bounds.left + x * self.cell_w, self.bounds.top + y * self.cell_h, self.cell_w, self.cell_h)
                if v == 'X':
                    # Draw X
                    pad = 12
                    pygame.draw.line(surface, (240, 84, 84), (r.left+pad, r.top+pad), (r.right-pad, r.bottom-pad), 3)
                    pygame.draw.line(surface, (240, 84, 84), (r.left+pad, r.bottom-pad), (r.right-pad, r.top+pad), 3)
                else:
                    # Draw O
                    pad = 10
                    pygame.draw.ellipse(surface, (84, 160, 240), r.inflate(-pad, -pad), 3)
        # HUD
        # Turn HUD
        owner = self._owner_of(self.turn)
        if self.mode == "single":
            turn_text = f"Turn: {'You' if owner == self.names[0] else 'Bot'} ({self.turn})"
        else:
            turn_text = f"Turn: {owner} ({self.turn})" if owner else f"Turn: {self.turn}"
        hud = font.render(turn_text, True, (255, 255, 255))
        surface.blit(hud, (10, 10))

        # Scoreboard HUD (stacking)
        sc_a = self.scoreboard.get(self.names[0], 0)
        sc_b = self.scoreboard.get(self.names[1], 0)
        s1 = font.render(f"{self.names[0]}: {sc_a}", True, (230, 230, 230))
        s2 = font.render(f"{self.names[1]}: {sc_b}", True, (230, 230, 230))
        surface.blit(s1, (10, 36))
        surface.blit(s2, (10, 58))

    def _owner_of(self, symbol: str) -> Optional[str]:
        if self.mode == "single":
            return self.names[0] if symbol == self.human_symbol else self.names[1]
        else:
            # PvP: names[0] assigned to X, names[1] to O by launcher configuration
            return self.names[0] if symbol == 'X' else self.names[1]
