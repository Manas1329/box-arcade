"""
Singleplayer Survival / Color Sync Survival

Core loop:
- One human player enters an arena
- Hazards (same color boxes) spawn outside the screen and move across the arena
- Survive as long as possible; score = time survived

Hazards are generated and move in simple straight lines (no AI).
Difficulty scales by increasing spawn rate and hazard speed over time.
"""
from __future__ import annotations
from typing import List, Tuple
import math
import random
import pygame

# Distinct hazard base color (not used by any player colors), theme-friendly on dark bg
HAZARD_COLOR = (255, 64, 192)  # electric magenta

from entities.player import Player, HumanPlayer


class SurvivalGame:
    def __init__(self, player: HumanPlayer, bounds: pygame.Rect):
        self.player = player
        self.bounds = bounds
        self.elapsed = 0.0
        self.is_over = False

        # Hazard generator state
        self.hazards: List[Tuple[pygame.Rect, Tuple[float, float]]] = []  # (rect, (vx, vy))
        # Independent generators per edge to avoid safe zones and allow overlap
        self.spawn_timers = {"left": 0.0, "right": 0.0, "top": 0.0, "bottom": 0.0}
        self.spawn_interval = 1.0  # seconds, will decrease
        self.min_spawn_interval = 0.30
        self.base_speed = 150.0     # px/s, will increase
        self.max_speed = 380.0
        self.side_cycle_idx = 0

    def reset(self):
        self.elapsed = 0.0
        self.is_over = False
        self.hazards.clear()
        for k in self.spawn_timers.keys():
            self.spawn_timers[k] = 0.0
        self.spawn_interval = 1.0
        self.side_cycle_idx = 0
        # Safe spawn near corner
        spawn_x = self.bounds.left + 60
        spawn_y = self.bounds.top + 60
        self.player.rect.center = (spawn_x, spawn_y)

    def _difficulty(self) -> Tuple[float, float, int, int]:
        # Returns (spawn_interval, speed, active_sides, concurrent_per_side)
        # Scale over ~45s for a smooth curve
        t = min(self.elapsed / 45.0, 1.0)
        cur_interval = self.spawn_interval - t * (self.spawn_interval - self.min_spawn_interval)
        cur_interval = max(self.min_spawn_interval, cur_interval)
        cur_speed = self.base_speed + t * (self.max_speed - self.base_speed)
        cur_speed = min(self.max_speed, cur_speed)
        # Increase active generators: start with 2, then 3, then 4
        if self.elapsed < 12.0:
            active_sides = 2
        elif self.elapsed < 24.0:
            active_sides = 3
        else:
            active_sides = 4
        # Occasional double/triple spawns per side as time progresses
        concurrent = 1 if self.elapsed < 15.0 else (2 if self.elapsed < 30.0 else 3)
        return (cur_interval, cur_speed, active_sides, concurrent)

    def _spawn_hazard(self, side: str, speed: float):
        # Spawn a hazard rectangle outside bounds with velocity toward arena
        w, h = 40, 40
        bx, by, bw, bh = self.bounds.left, self.bounds.top, self.bounds.width, self.bounds.height
        if side == "left":
            x = bx - w - 12
            y = random.randint(by + 20, by + bh - 20 - h)
            vx, vy = speed, 0.0
        elif side == "right":
            x = bx + bw + 12
            y = random.randint(by + 20, by + bh - 20 - h)
            vx, vy = -speed, 0.0
        elif side == "top":
            x = random.randint(bx + 20, bx + bw - 20 - w)
            y = by - h - 12
            vx, vy = 0.0, speed
        else:  # bottom
            x = random.randint(bx + 20, bx + bw - 20 - w)
            y = by + bh + 12
            vx, vy = 0.0, -speed
        rect = pygame.Rect(int(x), int(y), w, h)
        self.hazards.append((rect, (vx, vy)))

    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return

        # Movement
        if isinstance(self.player, HumanPlayer):
            self.player.update(dt, input_handler, pressed)

        # Out of bounds -> fail
        if not self.bounds.contains(self.player.rect):
            self.is_over = True
            return

        # Difficulty & spawns (per-side generators)
        cur_interval, cur_speed, active_sides, concurrent = self._difficulty()
        # Rotate active sides to vary patterns and coverage
        order = ["left", "top", "right", "bottom"]
        rot = self.side_cycle_idx % 4
        order = order[rot:] + order[:rot]
        sides_to_use = order[:active_sides]
        self.side_cycle_idx += 1
        for side in sides_to_use:
            self.spawn_timers[side] += dt
            if self.spawn_timers[side] >= cur_interval:
                self.spawn_timers[side] = 0.0
                for _ in range(concurrent):
                    self._spawn_hazard(side, cur_speed)

        # Move hazards and check collisions
        keep: List[Tuple[pygame.Rect, Tuple[float, float]]] = []
        for rect, (vx, vy) in self.hazards:
            rect.x += int(vx * dt)
            rect.y += int(vy * dt)
            # Collision with player
            if rect.colliderect(self.player.rect):
                self.is_over = True
                return
            # Keep if still nearby (within expanded bounds)
            expanded = self.bounds.inflate(120, 120)
            if expanded.colliderect(rect):
                keep.append((rect, (vx, vy)))
        self.hazards = keep

        # Accumulate survival time
        self.elapsed += dt

    def scores(self) -> List[Tuple[str, float]]:
        return [(self.player.name, self.elapsed)]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Bounds
        pygame.draw.rect(surface, (80, 80, 100), self.bounds, 2)
        # Hazards: distinct base color, shaded + outlined for visibility
        base = HAZARD_COLOR
        # Slight pulse for outline thickness
        pulse = 0.5 + 0.5 * math.sin(self.elapsed * 5.0)
        thickness = 2 + int(pulse * 2)  # 2..3
        # Shaded fill (20% darker) with clamping
        fill = (max(0, int(base[0] * 0.8)), max(0, int(base[1] * 0.8)), max(0, int(base[2] * 0.8)))
        # Outline is lighter tint
        outline = (min(255, int(base[0] * 1.2)), min(255, int(base[1] * 1.2)), min(255, int(base[2] * 1.2)))
        for rect, _vel in self.hazards:
            pygame.draw.rect(surface, fill, rect)
            pygame.draw.rect(surface, outline, rect, thickness)
        # Player
        pygame.draw.rect(surface, self.player.color, self.player.rect)
        # HUD
        t_text = font.render(f"Time: {self.elapsed:.1f}s", True, (255, 255, 255))
        surface.blit(t_text, (10, 10))


class SurvivalPvpGame:
    """Local PvP Survival: 2–4 players share the arena and hazards.
    Touching a hazard eliminates the player. Last survivor wins.
    """
    def __init__(self, players: List[HumanPlayer], bounds: pygame.Rect):
        self.players = players
        self.bounds = bounds
        self.elapsed = 0.0
        self.is_over = False
        self.higher_time_wins = True  # Let ResultsScene sort descending

        # Player state
        self.alive = {p.player_id: True for p in players}
        self.elim_time = {p.player_id: 0.0 for p in players}

        # Hazard generator (same as Survival, multi-edge)
        self.hazards: List[Tuple[pygame.Rect, Tuple[float, float]]] = []
        self.spawn_timers = {"left": 0.0, "right": 0.0, "top": 0.0, "bottom": 0.0}
        self.spawn_interval = 1.0
        self.min_spawn_interval = 0.30
        self.base_speed = 150.0
        self.max_speed = 380.0
        self.side_cycle_idx = 0

    def reset(self):
        self.elapsed = 0.0
        self.is_over = False
        for p in self.players:
            self.alive[p.player_id] = True
            self.elim_time[p.player_id] = 0.0
        self.hazards.clear()
        for k in self.spawn_timers.keys():
            self.spawn_timers[k] = 0.0
        self.spawn_interval = 1.0
        self.side_cycle_idx = 0
        # Spawn grid (corners/centers)
        b = self.bounds
        spawns = [
            (b.left + 40, b.top + 40),
            (b.right - 80, b.top + 40),
            (b.left + 40, b.bottom - 80),
            (b.right - 80, b.bottom - 80),
            (b.centerx - 40, b.centery - 40),
            (b.centerx + 40, b.centery - 40),
            (b.centerx - 40, b.centery + 40),
            (b.centerx + 40, b.centery + 40),
        ]
        for i, p in enumerate(self.players):
            x, y = spawns[i % len(spawns)]
            p.rect.topleft = (x, y)

    def _difficulty(self) -> Tuple[float, float, int, int]:
        t = min(self.elapsed / 45.0, 1.0)
        cur_interval = self.spawn_interval - t * (self.spawn_interval - self.min_spawn_interval)
        cur_interval = max(self.min_spawn_interval, cur_interval)
        cur_speed = self.base_speed + t * (self.max_speed - self.base_speed)
        cur_speed = min(self.max_speed, cur_speed)
        active_sides = 2 if self.elapsed < 12.0 else (3 if self.elapsed < 24.0 else 4)
        concurrent = 1 if self.elapsed < 15.0 else (2 if self.elapsed < 30.0 else 3)
        return (cur_interval, cur_speed, active_sides, concurrent)

    def _spawn_hazard(self, side: str, speed: float):
        w, h = 40, 40
        bx, by, bw, bh = self.bounds.left, self.bounds.top, self.bounds.width, self.bounds.height
        if side == "left":
            x = bx - w - 12
            y = random.randint(by + 20, by + bh - 20 - h)
            vx, vy = speed, 0.0
        elif side == "right":
            x = bx + bw + 12
            y = random.randint(by + 20, by + bh - 20 - h)
            vx, vy = -speed, 0.0
        elif side == "top":
            x = random.randint(bx + 20, bx + bw - 20 - w)
            y = by - h - 12
            vx, vy = 0.0, speed
        else:
            x = random.randint(bx + 20, bx + bw - 20 - w)
            y = by + bh + 12
            vx, vy = 0.0, -speed
        rect = pygame.Rect(int(x), int(y), w, h)
        self.hazards.append((rect, (vx, vy)))

    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return
        # Move alive players and clamp to bounds (hazards are only threat)
        for p in self.players:
            if not self.alive[p.player_id]:
                continue
            p.update(dt, input_handler, pressed)
            p.clamp_to_bounds(self.bounds)

        # Difficulty & spawns
        cur_interval, cur_speed, active_sides, concurrent = self._difficulty()
        order = ["left", "top", "right", "bottom"]
        rot = self.side_cycle_idx % 4
        order = order[rot:] + order[:rot]
        sides_to_use = order[:active_sides]
        self.side_cycle_idx += 1
        for side in sides_to_use:
            self.spawn_timers[side] += dt
            if self.spawn_timers[side] >= cur_interval:
                self.spawn_timers[side] = 0.0
                for _ in range(concurrent):
                    self._spawn_hazard(side, cur_speed)

        # Move hazards and check collisions per player
        keep: List[Tuple[pygame.Rect, Tuple[float, float]]] = []
        for rect, (vx, vy) in self.hazards:
            rect.x += int(vx * dt)
            rect.y += int(vy * dt)
            expanded = self.bounds.inflate(120, 120)
            if expanded.colliderect(rect):
                keep.append((rect, (vx, vy)))
        self.hazards = keep

        # Collisions: eliminate on contact
        for p in self.players:
            if not self.alive[p.player_id]:
                continue
            for rect, _vel in self.hazards:
                if rect.colliderect(p.rect):
                    self.alive[p.player_id] = False
                    self.elim_time[p.player_id] = self.elapsed
                    break

        # Count survivors
        survivors = [pid for pid, ok in self.alive.items() if ok]
        self.elapsed += dt
        if len(survivors) <= 1:
            self.is_over = True

    def scores(self) -> List[Tuple[str, float]]:
        # Return survival time; non-survivors have their elimination time
        # Survivors (winner) get total elapsed to appear first when sorting descending
        out = []
        for p in self.players:
            t = self.elim_time[p.player_id]
            if self.alive[p.player_id]:
                t = self.elapsed
            out.append((p.name, t))
        return out

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        pygame.draw.rect(surface, (80, 80, 100), self.bounds, 2)
        # Hazards
        base = HAZARD_COLOR
        pulse = 0.5 + 0.5 * math.sin(self.elapsed * 5.0)
        thickness = 2 + int(pulse * 2)
        fill = (max(0, int(base[0] * 0.8)), max(0, int(base[1] * 0.8)), max(0, int(base[2] * 0.8)))
        outline = (min(255, int(base[0] * 1.2)), min(255, int(base[1] * 1.2)), min(255, int(base[2] * 1.2)))
        for rect, _vel in self.hazards:
            pygame.draw.rect(surface, fill, rect)
            pygame.draw.rect(surface, outline, rect, thickness)
        # Players (distinct colors, with light outline)
        for p in self.players:
            color = p.color
            pygame.draw.rect(surface, color, p.rect)
            pygame.draw.rect(surface, (230, 230, 230), p.rect, 2)
            label = font.render(p.name, True, (230, 230, 230))
            surface.blit(label, (p.rect.centerx - label.get_width()//2, p.rect.top - label.get_height() - 2))
