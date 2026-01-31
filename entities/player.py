"""
Player classes for the arcade framework.
All characters are rectangular boxes using pygame.Rect.
"""
from __future__ import annotations
from typing import List, Optional, Tuple
import pygame


class Player:
    def __init__(self, player_id: int, name: str, rect: pygame.Rect, color: Tuple[int, int, int], speed: float, is_human: bool):
        self.player_id = player_id
        self.name = name
        self.rect = rect
        self.color = color
        self.speed = speed
        self.is_human = is_human
        self.is_it = False
        self.it_time = 0.0  # seconds spent as IT

    def move(self, dx: float, dy: float, dt: float):
        self.rect.x += int(dx * self.speed * dt)
        self.rect.y += int(dy * self.speed * dt)

    def clamp_to_bounds(self, bounds: pygame.Rect):
        if self.rect.left < bounds.left:
            self.rect.left = bounds.left
        if self.rect.right > bounds.right:
            self.rect.right = bounds.right
        if self.rect.top < bounds.top:
            self.rect.top = bounds.top
        if self.rect.bottom > bounds.bottom:
            self.rect.bottom = bounds.bottom

    def draw(self, surface: pygame.Surface):
        pygame.draw.rect(surface, self.color, self.rect)


class HumanPlayer(Player):
    def update(self, dt: float, input_handler, pressed):
        dx, dy = input_handler.get_direction(self.player_id, pressed)
        self.move(dx, dy, dt)


class BotPlayer(Player):
    def update(self, dt: float, players: List[Player], current_it_id: int):
        # Simple AI: If IT, chase nearest non-IT. Else, avoid the IT.
        target_dx, target_dy = 0.0, 0.0

        me = self
        if me.is_it:
            # Chase nearest non-IT
            target = _nearest_non_it(me, players)
            if target:
                target_dx, target_dy = _direction_to(me.rect, target.rect)
        else:
            # Run away from IT
            it_player = _find_by_id(players, current_it_id)
            if it_player:
                dx, dy = _direction_to(me.rect, it_player.rect)
                target_dx, target_dy = (-dx, -dy)

        # Normalize movement and move
        if target_dx != 0 and target_dy != 0:
            target_dx *= 0.70710678
            target_dy *= 0.70710678
        self.move(target_dx, target_dy, dt)


def _find_by_id(players: List[Player], pid: int) -> Optional[Player]:
    for p in players:
        if p.player_id == pid:
            return p
    return None


def _nearest_non_it(me: Player, players: List[Player]) -> Optional[Player]:
    best = None
    best_d2 = 0.0
    for p in players:
        if p is me or p.is_it:
            continue
        dx = (p.rect.centerx - me.rect.centerx)
        dy = (p.rect.centery - me.rect.centery)
        d2 = dx * dx + dy * dy
        if best is None or d2 < best_d2:
            best = p
            best_d2 = d2
    return best


def _direction_to(a: pygame.Rect, b: pygame.Rect) -> Tuple[float, float]:
    dx = b.centerx - a.centerx
    dy = b.centery - a.centery
    # Convert to -1, 0, 1 steps
    step_x = 0.0
    step_y = 0.0
    if dx > 0:
        step_x = 1.0
    elif dx < 0:
        step_x = -1.0
    if dy > 0:
        step_y = 1.0
    elif dy < 0:
        step_y = -1.0
    return (step_x, step_y)
