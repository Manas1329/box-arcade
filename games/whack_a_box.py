from __future__ import annotations
import random
import pygame
from typing import Optional, Tuple, List


class WhackABoxGame:
    def __init__(self, bounds: pygame.Rect, round_duration: float = 30.0):
        self.bounds = bounds
        self.round_duration = round_duration
        # Gameplay state
        self.time_remaining = self.round_duration
        self.score = 0
        self.misses = 0
        self.is_over = False
        self.results_header: Optional[str] = None
        # Box params
        self.box_size = 40
        self.box_life = 0.8  # seconds each box stays
        self.spawn_cooldown_min = 0.1
        self.spawn_cooldown_max = 0.35
        self.current_box: Optional[pygame.Rect] = None
        self.current_box_time = 0.0
        self.spawn_cooldown = 0.0
        # Visual feedback
        self.last_hit_pos: Optional[Tuple[int, int]] = None
        self.hit_flash_time = 0.0
        # Results / scoring meta
        self.higher_time_wins = True   # higher score is better
        self.show_time_in_results = True
        self.result_label = "Score"

    def reset(self):
        self.time_remaining = self.round_duration
        self.score = 0
        self.misses = 0
        self.is_over = False
        self.results_header = None
        self.current_box = None
        self.current_box_time = 0.0
        self.spawn_cooldown = 0.0
        self.last_hit_pos = None
        self.hit_flash_time = 0.0

    def _spawn_box(self):
        # Spawn a box fully inside bounds
        margin = 10
        x_min = self.bounds.left + margin
        y_min = self.bounds.top + margin
        x_max = self.bounds.right - margin - self.box_size
        y_max = self.bounds.bottom - margin - self.box_size
        if x_max <= x_min or y_max <= y_min:
            return
        x = random.randint(x_min, x_max)
        y = random.randint(y_min, y_max)
        self.current_box = pygame.Rect(x, y, self.box_size, self.box_size)
        self.current_box_time = self.box_life

    def handle_event(self, event: pygame.event.Event):
        if self.is_over:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            self._handle_click(mx, my)

    def _handle_click(self, x: int, y: int):
        if self.current_box and self.current_box.collidepoint(x, y):
            # Hit
            self.score += 1
            self.last_hit_pos = (x, y)
            self.hit_flash_time = 0.15
            self.current_box = None
            self.current_box_time = 0.0
            # Slight delay before next box
            self.spawn_cooldown = random.uniform(self.spawn_cooldown_min, self.spawn_cooldown_max)
        else:
            # Miss
            if self.score > 0:
                self.score -= 1
            self.misses += 1

    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return
        # Round timer
        self.time_remaining -= dt
        if self.time_remaining <= 0.0:
            self.time_remaining = 0.0
            self.is_over = True
            self.results_header = f"Whack-a-Box — Score: {self.score}"
            return
        # Box lifetime
        if self.current_box:
            self.current_box_time -= dt
            if self.current_box_time <= 0.0:
                # Box expired without hit
                if self.score > 0:
                    self.score -= 1
                self.misses += 1
                self.current_box = None
                self.current_box_time = 0.0
                self.spawn_cooldown = random.uniform(self.spawn_cooldown_min, self.spawn_cooldown_max)
        else:
            # No active box: countdown to next spawn
            self.spawn_cooldown -= dt
            if self.spawn_cooldown <= 0.0:
                self._spawn_box()
        # Hit flash timer
        if self.hit_flash_time > 0.0:
            self.hit_flash_time -= dt
            if self.hit_flash_time <= 0.0:
                self.last_hit_pos = None

    def scores(self) -> List[Tuple[str, float]]:
        return [("Solo", float(self.score))]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Bounds
        pygame.draw.rect(surface, (80, 80, 100), self.bounds, 2)
        # Current box
        if self.current_box:
            pygame.draw.rect(surface, (210, 80, 110), self.current_box)
            pygame.draw.rect(surface, (245, 210, 220), self.current_box, 2)
        # Hit flash
        if self.last_hit_pos and self.hit_flash_time > 0.0:
            r = 12
            cx, cy = self.last_hit_pos
            flash_rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
            pygame.draw.ellipse(surface, (240, 240, 240), flash_rect, 2)
        # HUD
        t_text = font.render(f"Time: {self.time_remaining:4.1f}s", True, (255, 255, 255))
        s_text = font.render(f"Score: {self.score}", True, (240, 240, 240))
        m_text = font.render(f"Misses: {self.misses}", True, (220, 220, 220))
        surface.blit(t_text, (10, 10))
        surface.blit(s_text, (10, 34))
        surface.blit(m_text, (10, 58))
