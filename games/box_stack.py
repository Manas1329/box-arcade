from __future__ import annotations
import pygame
from typing import List, Optional, Tuple


class BoxStackGame:
    BEST_SCORE: int = 0  # session best

    def __init__(self, bounds: pygame.Rect):
        self.bounds = bounds
        # Stack geometry
        self.layer_height = 24
        self.base_width = bounds.width // 2
        # Stack layers (bottom at bounds.bottom)
        base_rect = pygame.Rect(0, 0, self.base_width, self.layer_height)
        base_rect.centerx = bounds.centerx
        base_rect.bottom = bounds.bottom - 10
        self.layers: List[pygame.Rect] = [base_rect]
        # Active moving layer
        self.active: Optional[pygame.Rect] = None
        self.active_speed = 220.0
        self.active_dir = 1
        # Game state
        self.score = 1  # base layer
        self.is_over = False
        self.results_header: Optional[str] = None
        self.higher_time_wins = True   # higher height is better
        self.show_time_in_results = False
        self.result_label = "Height"
        # Visuals
        self.cut_flash: Optional[pygame.Rect] = None
        self.cut_flash_time = 0.0
        # Minimum width before game ends
        self.min_width = 20
        self._spawn_next_layer()

    def reset(self):
        self.layers.clear()
        base_rect = pygame.Rect(0, 0, self.base_width, self.layer_height)
        base_rect.centerx = self.bounds.centerx
        base_rect.bottom = self.bounds.bottom - 10
        self.layers.append(base_rect)
        self.active = None
        self.active_dir = 1
        self.score = 1
        self.is_over = False
        self.results_header = None
        self.cut_flash = None
        self.cut_flash_time = 0.0
        self._spawn_next_layer()

    def _spawn_next_layer(self):
        top = self.layers[-1]
        rect = pygame.Rect(0, 0, top.width, self.layer_height)
        rect.bottom = top.top
        # Start off-screen left or right alternately
        if len(self.layers) % 2 == 0:
            rect.left = self.bounds.left
            self.active_dir = 1
        else:
            rect.right = self.bounds.right
            self.active_dir = -1
        self.active = rect
        # Slightly ramp up speed with height
        self.active_speed = 200.0 + 8.0 * (len(self.layers) - 1)

    def handle_event(self, event: pygame.event.Event):
        if self.is_over:
            return
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._drop_active()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._drop_active()

    def _drop_active(self):
        if self.is_over or self.active is None:
            return
        top = self.layers[-1]
        placed = self.active
        # Overlap with previous layer
        overlap = placed.clip(top)
        if overlap.width <= 0:
            # No overlap: game over, keep current score
            self.is_over = True
            self.results_header = f"Stack Collapsed (Height {self.score})"
            if self.score > BoxStackGame.BEST_SCORE:
                BoxStackGame.BEST_SCORE = self.score
            return
        # Misaligned parts are cut off
        self.layers.append(overlap)
        self.score = len(self.layers)
        if self.score > BoxStackGame.BEST_SCORE:
            BoxStackGame.BEST_SCORE = self.score
        # Flash the cut region for feedback
        if overlap.width < placed.width:
            # Compute cut rect as difference
            if overlap.left > placed.left:
                cut = pygame.Rect(placed.left, placed.top,
                                   overlap.left - placed.left, placed.height)
            else:
                cut = pygame.Rect(overlap.right, placed.top,
                                   placed.right - overlap.right, placed.height)
            self.cut_flash = cut
            self.cut_flash_time = 0.15
        else:
            self.cut_flash = None
            self.cut_flash_time = 0.0
        self.active = None
        # Check size threshold
        if overlap.width <= self.min_width:
            self.is_over = True
            self.results_header = f"Stack Too Small (Height {self.score})"
        else:
            self._spawn_next_layer()

    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return
        if self.active is not None:
            dx = int(self.active_speed * dt * self.active_dir)
            self.active.x += dx
            # Bounce at bounds
            if self.active.right >= self.bounds.right:
                self.active.right = self.bounds.right
                self.active_dir = -1
            elif self.active.left <= self.bounds.left:
                self.active.left = self.bounds.left
                self.active_dir = 1
        if self.cut_flash_time > 0.0:
            self.cut_flash_time -= dt
            if self.cut_flash_time <= 0.0:
                self.cut_flash = None

    def scores(self):
        # Height achieved
        return [("Solo", float(self.score))]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Bounds
        pygame.draw.rect(surface, (80, 80, 100), self.bounds, 2)
        # Draw stack layers
        for i, r in enumerate(self.layers):
            col = (90 + i * 10 % 80, 150, 200)
            pygame.draw.rect(surface, col, r)
            pygame.draw.rect(surface, (230, 240, 250), r, 2)
        # Active moving layer
        if self.active is not None:
            pygame.draw.rect(surface, (220, 160, 120), self.active)
            pygame.draw.rect(surface, (250, 230, 210), self.active, 2)
        # Cut flash
        if self.cut_flash is not None and self.cut_flash_time > 0.0:
            s = pygame.Surface((self.cut_flash.width, self.cut_flash.height), pygame.SRCALPHA)
            s.fill((255, 230, 150, 160))
            surface.blit(s, self.cut_flash.topleft)
        # HUD
        h_text = font.render(f"Height: {self.score}", True, (255, 255, 255))
        b_text = font.render(f"Best: {BoxStackGame.BEST_SCORE}", True, (230, 230, 230))
        hint = font.render("Space/Click: Drop", True, (210, 210, 210))
        surface.blit(h_text, (10, 10))
        surface.blit(b_text, (10, 34))
        surface.blit(hint, (10, 58))
