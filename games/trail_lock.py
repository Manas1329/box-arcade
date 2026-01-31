"""
TrailLock (PvP only)

2–4 players compete leaving solid trails. Touching any trail, boundaries,
or another player eliminates you for the round. Last survivor gets 1 point.
First to target score wins the match.
"""
from __future__ import annotations
from typing import List, Tuple, Dict
import random
import pygame

from entities.player import HumanPlayer


class TrailLockGame:
    def __init__(self, players: List[HumanPlayer], bounds: pygame.Rect, target_score: int = 5):
        self.players = players
        self.bounds = bounds
        self.arena = bounds.copy()  # shrinking arena
        self.shrink_rate = 1.0      # px per side per second (gentle shrink)
        self.shrink_accum = 0.0     # accumulate fractional shrink
        # Best of 10: ignore early target_score wins; end after max_rounds
        self.target_score = target_score
        self.is_over = False
        self.elapsed = 0.0

        # Results sorting & labels
        self.higher_time_wins = True  # use descending order
        self.show_time_in_results = True
        self.result_label = "Score"

        # Round state
        self.round_index = 0
        self.max_rounds = 10
        self.round_prep_time = 0.8  # delay before trails start
        self.trails_active = False
        self.round_over = False
        self.round_over_timer = 0.0
        self.round_over_delay = 2.0
        self.round_winner: int | None = None

        # Per-player state
        self.alive: Dict[int, bool] = {p.player_id: True for p in players}
        self.score_board: Dict[int, int] = {p.player_id: 0 for p in players}
        self.prev_rect: Dict[int, pygame.Rect] = {p.player_id: p.rect.copy() for p in players}
        # Forced movement direction per player (cannot stop)
        self.move_dir: Dict[int, Tuple[float, float]] = {p.player_id: (0.0, 0.0) for p in players}

        # Trails: list of (rect, color, owner_id) for rendering & collision
        self.trails: List[Tuple[pygame.Rect, Tuple[int, int, int], int]] = []

        self.reset_round()

    def reset_round(self):
        self.trails.clear()
        self.trails_active = False
        self.round_over = False
        self.round_over_timer = 0.0
        self.round_winner = None
        self.arena = self.bounds.copy()
        # Spawn positions (corners & near center)
        b = self.bounds
        margin = 100
        spawns = [
            (b.left + margin, b.top + margin),
            (b.right - margin - 40, b.top + margin),
            (b.left + margin, b.bottom - margin - 40),
            (b.right - margin - 40, b.bottom - margin - 40),
            (b.centerx - 60, b.centery - 60),
            (b.centerx + 60, b.centery - 60),
            (b.centerx - 60, b.centery + 60),
            (b.centerx + 60, b.centery + 60),
        ]
        for i, p in enumerate(self.players):
            x, y = spawns[i % len(spawns)]
            p.rect.topleft = (x, y)
            self.alive[p.player_id] = True
            self.prev_rect[p.player_id] = p.rect.copy()
            # Initial direction biased toward center to avoid instant border hits
            cx, cy = b.centerx, b.centery
            dx = 1.0 if x < cx else -1.0
            dy = 1.0 if y < cy else -1.0
            # Normalize diagonal speed
            if dx != 0.0 and dy != 0.0:
                dx *= 0.70710678
                dy *= 0.70710678
            self.move_dir[p.player_id] = (dx, dy)
        self.elapsed = 0.0

    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return

        if self.round_over:
            self.round_over_timer += dt
            if self.round_over_timer >= self.round_over_delay:
                # Check end condition: round cap only (best of 10)
                if (self.round_index + 1) >= self.max_rounds:
                    self.is_over = True
                    return
                # Next round
                self.round_index += 1
                self.reset_round()
            return

        # Pre-round delay before trails start
        self.elapsed += dt
        if not self.trails_active and self.elapsed >= self.round_prep_time:
            self.trails_active = True

        # Move players with forced movement (cannot stop); boundaries eliminate
        for p in self.players:
            if not self.alive[p.player_id]:
                continue
            prev = self.prev_rect[p.player_id]
            # Read input direction; if zero, continue in previous direction
            dx, dy = input_handler.get_direction(p.player_id, pressed)
            if dx != 0.0 or dy != 0.0:
                # Update direction to input
                self.move_dir[p.player_id] = (dx, dy)
            # Move using current direction
            cur_dx, cur_dy = self.move_dir[p.player_id]
            p.move(cur_dx, cur_dy, dt)
            # Boundary elimination if touching or exiting bounds
            if not self.arena.contains(p.rect):
                self.alive[p.player_id] = False
                continue
            # Spawn trail segment at previous position once trails are active and moved
            if self.trails_active:
                if prev.x != p.rect.x or prev.y != p.rect.y:
                    # Trail segment uses darker tint of player color
                    c = p.color
                    darker = (max(0, int(c[0] * 0.7)), max(0, int(c[1] * 0.7)), max(0, int(c[2] * 0.7)))
                    # Store owner to avoid self-collision immediately after moving
                    # Slightly smaller than player rect for visual clarity
                    margin = 6
                    trail_rect = prev.inflate(-margin, -margin)
                    self.trails.append((trail_rect, darker, p.player_id))
            # Update previous position
            self.prev_rect[p.player_id] = p.rect.copy()

        # Shrink arena over time
        # Accumulate shrink and apply whole pixels symmetrically
        self.shrink_accum += self.shrink_rate * dt
        while self.shrink_accum >= 1.0 and self.arena.width > 120 and self.arena.height > 120:
            self.arena = self.arena.inflate(-2, -2)
            self.shrink_accum -= 1.0

        # Solid player collisions: eliminate both on contact
        alive_players = [p for p in self.players if self.alive[p.player_id]]
        for i in range(len(alive_players)):
            a = alive_players[i]
            for j in range(i + 1, len(alive_players)):
                b = alive_players[j]
                if a.rect.colliderect(b.rect):
                    self.alive[a.player_id] = False
                    self.alive[b.player_id] = False

        # Trail collisions: touching any trail eliminates
        for p in self.players:
            if not self.alive[p.player_id]:
                continue
            for rect, _color, owner in self.trails:
                # Do not eliminate on own trail to avoid instant self-hit
                if owner == p.player_id:
                    continue
                if rect.colliderect(p.rect):
                    self.alive[p.player_id] = False
                    break

        # Check survivors
        survivors = [pid for pid, ok in self.alive.items() if ok]
        if len(survivors) <= 1:
            self.round_over = True
            # Award point if there is a winner
            if len(survivors) == 1:
                self.round_winner = survivors[0]
                self.score_board[self.round_winner] += 1

    def scores(self) -> List[Tuple[str, float]]:
        # Return overall scores (for results screen)
        out: List[Tuple[str, float]] = []
        for p in self.players:
            out.append((p.name, float(self.score_board.get(p.player_id, 0))))
        return out

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Draw shrinking arena border
        pygame.draw.rect(surface, (80, 80, 100), self.arena, 2)
        # Draw trails (borderless, slightly smaller)
        for rect, color, _owner in self.trails:
            pygame.draw.rect(surface, color, rect)
        # Draw players
        for p in self.players:
            if self.alive[p.player_id]:
                pygame.draw.rect(surface, p.color, p.rect)
                pygame.draw.rect(surface, (230, 230, 230), p.rect, 2)
            else:
                # Faded box for eliminated
                overlay = pygame.Surface((p.rect.width, p.rect.height), pygame.SRCALPHA)
                overlay.fill((120, 120, 120, 140))
                surface.blit(overlay, p.rect.topleft)
        # HUD: round info and scoreboard
        status = "Trails ON" if self.trails_active else "Get Ready"
        hud = font.render(f"Round {self.round_index + 1} — {status}", True, (255, 255, 255))
        surface.blit(hud, (10, 10))
        y = 34
        for p in self.players:
            sc = self.score_board.get(p.player_id, 0)
            line = font.render(f"{p.name}: {sc}", True, (230, 230, 230))
            surface.blit(line, (10, y))
            y += 22
        # Inter-round banner
        if self.round_over:
            text = "Round Over"
            if self.round_winner is not None:
                winner = next((p for p in self.players if p.player_id == self.round_winner), None)
                if winner:
                    text = f"Round Winner: {winner.name}"
            banner = font.render(text, True, (255, 240, 120))
            surface.blit(banner, (surface.get_width()//2 - banner.get_width()//2, 10))
