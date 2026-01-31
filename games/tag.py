"""
Tag game implementation using rectangular players.
Rules:
- One player is IT.
- IT transfers on collision with a non-IT player.
- Timer-based match; least time as IT wins.
"""
from __future__ import annotations
import random
from typing import List, Tuple
import pygame

from entities.player import Player, HumanPlayer, BotPlayer


class TagGame:
    def __init__(self, players: List[Player], bounds: pygame.Rect, match_time: int = 60):
        self.players = players
        self.bounds = bounds
        self.match_time = float(match_time)
        self.remaining = float(match_time)
        self.current_it_id = random.choice(players).player_id if players else 1
        self.is_over = False
        # Initialize IT state
        for p in self.players:
            p.is_it = (p.player_id == self.current_it_id)

    def reset(self):
        self.remaining = self.match_time
        self.is_over = False
        self.current_it_id = random.choice(self.players).player_id
        for p in self.players:
            p.is_it = (p.player_id == self.current_it_id)
            p.it_time = 0.0

    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return

        # Move players
        for p in self.players:
            if isinstance(p, HumanPlayer):
                p.update(dt, input_handler, pressed)
            else:
                # Bot AI needs list of players and current IT
                p.update(dt, self.players, self.current_it_id)
            p.clamp_to_bounds(self.bounds)

        # Collision detection & IT transfer
        it_player = next((x for x in self.players if x.player_id == self.current_it_id), None)
        if it_player:
            for p in self.players:
                if p is it_player:
                    continue
                if it_player.rect.colliderect(p.rect):
                    # Transfer IT to collided player
                    it_player.is_it = False
                    p.is_it = True
                    self.current_it_id = p.player_id
                    it_player = p
                    # Only transfer once per frame to avoid chain transfers
                    break

        # Accumulate IT time and decrement timer
        if it_player:
            it_player.it_time += dt
        self.remaining -= dt
        if self.remaining <= 0:
            self.remaining = 0
            self.is_over = True

    def scores(self) -> List[Tuple[str, float]]:
        # Returns list of (name, it_time)
        return [(p.name, p.it_time) for p in self.players]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Draw players
        for p in self.players:
            pygame.draw.rect(surface, p.color, p.rect)
        # HUD: current IT & remaining time
        it_text = f"IT: Player {self.current_it_id}"
        time_text = f"Time Left: {int(self.remaining)}s"
        it_surf = font.render(it_text, True, (255, 255, 255))
        time_surf = font.render(time_text, True, (255, 255, 255))
        surface.blit(it_surf, (10, 10))
        surface.blit(time_surf, (10, 35))
