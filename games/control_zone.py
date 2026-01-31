"""
Control Zone (PvP)

Objective:
- Players earn score by standing inside the active control zone.
- Only one zone exists at a time; if multiple players are inside, no one scores.
- Lasers act as periodic hazards: warn first, then activate across entire axis.
- Players can be stunned (1–2s) by active lasers; no elimination.
- Player-to-player collisions cause soft pushing.

Game ends when match timer expires; highest zone time wins.
"""
from __future__ import annotations
from typing import List, Tuple, Dict
import random
import pygame

from entities.player import HumanPlayer
from games.survival import HAZARD_COLOR


class Laser:
    """Axis-spanning laser with warn -> active phases."""
    def __init__(self, bounds: pygame.Rect, orientation: str, pos: int,
                 warn_duration: float = 0.8, active_duration: float = 0.6, thickness: int = 12):
        self.bounds = bounds
        self.orientation = orientation  # 'h' (horizontal) or 'v' (vertical)
        self.pos = pos  # y for horizontal, x for vertical (within bounds)
        self.warn_duration = warn_duration
        self.active_duration = active_duration
        self.thickness = thickness
        self.age = 0.0

    @property
    def is_warning(self) -> bool:
        return self.age < self.warn_duration

    @property
    def is_active(self) -> bool:
        return self.warn_duration <= self.age < (self.warn_duration + self.active_duration)

    @property
    def is_done(self) -> bool:
        return self.age >= (self.warn_duration + self.active_duration)

    def update(self, dt: float):
        self.age += dt

    def rect(self) -> pygame.Rect:
        b = self.bounds
        t = self.thickness
        if self.orientation == 'h':
            y = max(b.top, min(b.bottom - t, self.pos))
            return pygame.Rect(b.left, y, b.width, t)
        else:
            x = max(b.left, min(b.right - t, self.pos))
            return pygame.Rect(x, b.top, t, b.height)

    def draw(self, surface: pygame.Surface):
        r = self.rect()
        if self.is_warning:
            color = (255, 200, 80)  # amber warning
            pygame.draw.rect(surface, color, r, 2)
        elif self.is_active:
            color = (255, 60, 60)   # red active
            pygame.draw.rect(surface, color, r)
            pygame.draw.rect(surface, (255, 220, 220), r, 2)

    def hits(self, player_rect: pygame.Rect) -> bool:
        return self.is_active and self.rect().colliderect(player_rect)


class ControlZoneGame:
    def __init__(self, players: List[HumanPlayer], bounds: pygame.Rect, match_time: float = 60.0):
        self.players = players
        self.bounds = bounds
        self.match_time = match_time
        self.elapsed = 0.0
        self.is_over = False
        # Results display hints
        self.higher_time_wins = True
        self.show_time_in_results = True
        self.result_label = "Zone"

        # Scoring
        self.zone_scores: Dict[int, float] = {p.player_id: 0.0 for p in players}

        # Control zone
        self.zone_size = (140, 140)
        self.zone = pygame.Rect(0, 0, *self.zone_size)
        self.zone_relocate_interval = 8.0
        self.zone_timer = 0.0
        self._relocate_zone()

        # Stuns
        self.stun_until: Dict[int, float] = {p.player_id: 0.0 for p in players}

        # Lasers
        self.lasers: List[Laser] = []
        self.laser_spawn_interval = 2.5
        self.laser_timer = 0.0

    def reset(self):
        self.elapsed = 0.0
        self.is_over = False
        for pid in self.zone_scores.keys():
            self.zone_scores[pid] = 0.0
        self.zone_timer = 0.0
        self.laser_timer = 0.0
        self.lasers.clear()
        self._relocate_zone()
        # Spawn players at corners/centers
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

    def _relocate_zone(self):
        b = self.bounds
        w, h = self.zone_size
        # Margin so zone fully inside
        margin = 20
        x = random.randint(b.left + margin, b.right - margin - w)
        y = random.randint(b.top + margin, b.bottom - margin - h)
        self.zone.topleft = (x, y)

    def _spawn_laser(self):
        b = self.bounds
        if random.random() < 0.5:
            # Horizontal
            y = random.randint(b.top + 20, b.bottom - 20)
            self.lasers.append(Laser(b, 'h', y))
        else:
            x = random.randint(b.left + 20, b.right - 20)
            self.lasers.append(Laser(b, 'v', x))

    def _resolve_player_collisions(self):
        # Soft pushing: separate overlapping players along minimum axis
        # Do a couple of iterations for stability
        for _ in range(2):
            for i in range(len(self.players)):
                a = self.players[i]
                for j in range(i + 1, len(self.players)):
                    b = self.players[j]
                    if a.rect.colliderect(b.rect):
                        overlap_w = min(a.rect.right, b.rect.right) - max(a.rect.left, b.rect.left)
                        overlap_h = min(a.rect.bottom, b.rect.bottom) - max(a.rect.top, b.rect.top)
                        if overlap_w <= 0 or overlap_h <= 0:
                            continue
                        if overlap_w < overlap_h:
                            # Push horizontally
                            shift = overlap_w // 2 + 1
                            if a.rect.centerx < b.rect.centerx:
                                a.rect.x -= shift
                                b.rect.x += shift
                            else:
                                a.rect.x += shift
                                b.rect.x -= shift
                        else:
                            # Push vertically
                            shift = overlap_h // 2 + 1
                            if a.rect.centery < b.rect.centery:
                                a.rect.y -= shift
                                b.rect.y += shift
                            else:
                                a.rect.y += shift
                                b.rect.y -= shift
                        # Clamp to bounds after push
                        a.clamp_to_bounds(self.bounds)
                        b.clamp_to_bounds(self.bounds)

    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return

        # Timer and zone relocation
        self.elapsed += dt
        self.zone_timer += dt
        if self.zone_timer >= self.zone_relocate_interval:
            self.zone_timer = 0.0
            self._relocate_zone()

        # Lasers spawning and lifecycle
        self.laser_timer += dt
        if self.laser_timer >= self.laser_spawn_interval:
            self.laser_timer = 0.0
            # Increase intensity: +1 laser every 15 seconds of match time
            count = 1 + int(self.elapsed // 15.0)
            for _ in range(count):
                self._spawn_laser()
        keep: List[Laser] = []
        for l in self.lasers:
            l.update(dt)
            if not l.is_done:
                keep.append(l)
        self.lasers = keep

        # Update players (skip movement if stunned), clamp and resolve collisions
        for p in self.players:
            if self.elapsed >= self.stun_until[p.player_id]:
                p.update(dt, input_handler, pressed)
            # Always clamp after potential movement
            p.clamp_to_bounds(self.bounds)
        # Collisions cause soft pushing
        self._resolve_player_collisions()

        # Laser hits -> stun (no chain-stun)
        for l in self.lasers:
            if not l.is_active:
                continue
            for p in self.players:
                if self.elapsed < self.stun_until[p.player_id]:
                    continue  # already stunned
                if l.hits(p.rect):
                    self.stun_until[p.player_id] = self.elapsed + random.uniform(1.0, 2.0)

        # Zone scoring: only one player inside scores
        inside = [p for p in self.players if self.zone.colliderect(p.rect)]
        if len(inside) == 1:
            pid = inside[0].player_id
            self.zone_scores[pid] += dt

        # End condition
        if self.elapsed >= self.match_time:
            self.is_over = True

    def scores(self) -> List[Tuple[str, float]]:
        # Return list of (name, zone_time)
        out: List[Tuple[str, float]] = []
        for p in self.players:
            out.append((p.name, self.zone_scores.get(p.player_id, 0.0)))
        return out

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Draw zone (use same color as hazard: maroon)
        zone_fill = HAZARD_COLOR
        zone_outline = (min(255, int(HAZARD_COLOR[0] * 1.15)),
                        min(255, int(HAZARD_COLOR[1] * 1.15)),
                        min(255, int(HAZARD_COLOR[2] * 1.15)))
        pygame.draw.rect(surface, zone_fill, self.zone)
        pygame.draw.rect(surface, zone_outline, self.zone, 3)

        # Draw lasers
        for l in self.lasers:
            l.draw(surface)

        # Draw players; stunned overlay
        for p in self.players:
            pygame.draw.rect(surface, p.color, p.rect)
            if self.elapsed < self.stun_until[p.player_id]:
                # White translucent overlay to indicate stun
                overlay = pygame.Surface((p.rect.width, p.rect.height), pygame.SRCALPHA)
                overlay.fill((255, 255, 255, 120))
                surface.blit(overlay, p.rect.topleft)

        # HUD
        t_text = font.render(f"Time Left: {max(0.0, self.match_time - self.elapsed):.1f}s", True, (255, 255, 255))
        surface.blit(t_text, (10, 10))
        # Scores
        y = 36
        for p in self.players:
            val = self.zone_scores.get(p.player_id, 0.0)
            line = font.render(f"{p.name}: {val:.1f}s", True, (230, 230, 230))
            surface.blit(line, (10, y))
            y += 22
