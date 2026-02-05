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
        # Compute horizontal overlap with previous layer only.
        # Vertically the moving layer sits exactly above the previous one,
        # so full-rect clipping would report no intersection.
        left = max(placed.left, top.left)
        right = min(placed.right, top.right)
        width = right - left
        if width <= 0:
            # No horizontal overlap: game over, keep current score
            self.is_over = True
            self.results_header = f"Stack Collapsed (Height {self.score})"
            if self.score > BoxStackGame.BEST_SCORE:
                BoxStackGame.BEST_SCORE = self.score
            return

        # Create the new stacked layer using the horizontal overlap
        overlap = pygame.Rect(left, 0, width, self.layer_height)
        overlap.bottom = top.top

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

        # After placing a layer, adjust stack so the active part stays visible
        self._adjust_stack_vertical()

    def _adjust_stack_vertical(self):
        """Ensure the visible action stays within the playfield without a camera.

        Once the stack grows tall enough that its top is too close to the
        upper edge, we nudge the *entire* stack downward and drop bottom
        layers that slide past the bottom. This makes lower boxes disappear
        over time while keeping the active area on-screen, with no camera
        offset math.
        """
        if not self.layers:
            return

        top_layer = self.layers[-1]
        top_y = top_layer.top

        # If there's still plenty of room above the tower, do nothing.
        safe_margin = 40
        target_top = self.bounds.top + safe_margin
        if top_y >= target_top:
            return

        # Shift everything down just enough so the top sits at target_top.
        delta = target_top - top_y  # positive
        for r in self.layers:
            r.y += delta
        if self.active is not None:
            self.active.y += delta
        if self.cut_flash is not None:
            self.cut_flash.y += delta

        # Remove bottom layers that have fallen below the bottom edge.
        bottom_limit = self.bounds.bottom - 10
        while len(self.layers) > 1 and self.layers[0].bottom > bottom_limit:
            self.layers.pop(0)
        # Keep score in sync with current visible layers
        self.score = len(self.layers)

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
