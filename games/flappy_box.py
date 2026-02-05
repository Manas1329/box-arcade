from __future__ import annotations
import random
from typing import List, Tuple, Optional

import pygame


class FlappyBoxGame:
    """Singleplayer Flappy Bird–style game with box visuals."""

    # Session-wide best score shared across instances
    BEST_SCORE: int = 0

    def __init__(self, bounds: pygame.Rect):
        self.bounds = bounds
        # Player
        self.player_size = 26
        self.player_rect = pygame.Rect(0, 0, self.player_size, self.player_size)
        self.player_rect.centerx = self.bounds.left + int(self.bounds.width * 0.25)
        self.player_rect.centery = self.bounds.centery
        self.gravity = 900.0
        self.flap_velocity = -320.0
        self.velocity_y = 0.0

        # Pipes
        self.pipe_width = 60
        self.pipe_gap = 150
        self.pipe_speed = 180.0
        self.pipe_speed_max = 360.0
        self.pipe_spawn_interval = 1.4
        self._pipe_timer = 0.0
        self.pipes: List[Tuple[pygame.Rect, pygame.Rect]] = []  # (top_rect, bottom_rect)

        # Scoring
        self.score = 0
        self.passed_pipes: List[Tuple[pygame.Rect, pygame.Rect]] = []

        # State / results
        self.is_over = False
        self.results_header: Optional[str] = None
        self.higher_time_wins = True   # treat score as "higher is better"
        self.show_time_in_results = True
        self.result_label = "Score"

        self.reset()

    def reset(self):
        self.player_rect.centery = self.bounds.centery
        self.velocity_y = 0.0
        self.pipes.clear()
        self.passed_pipes.clear()
        self.score = 0
        self._pipe_timer = 0.0
        self.pipe_speed = 180.0
        self.is_over = False
        self.results_header = None

    # --- Input ------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            self._flap()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._flap()

    def _flap(self):
        if self.is_over:
            # Allow immediate restart via flap input
            self.reset()
            return
        self.velocity_y = self.flap_velocity

    # --- Core update ------------------------------------------------------
    def _spawn_pipe_pair(self):
        # Choose a random center for the gap within bounds
        margin = 40
        gap_center = random.randint(
            self.bounds.top + margin + self.pipe_gap // 2,
            self.bounds.bottom - margin - self.pipe_gap // 2,
        )
        top_bottom = gap_center - self.pipe_gap // 2
        bottom_top = gap_center + self.pipe_gap // 2

        top_rect = pygame.Rect(
            self.bounds.right,
            self.bounds.top,
            self.pipe_width,
            top_bottom - self.bounds.top,
        )
        bottom_rect = pygame.Rect(
            self.bounds.right,
            bottom_top,
            self.pipe_width,
            self.bounds.bottom - bottom_top,
        )
        self.pipes.append((top_rect, bottom_rect))

    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return

        # Gravity and vertical motion
        self.velocity_y += self.gravity * dt
        self.player_rect.y += int(self.velocity_y * dt)

        # Screen bounds collision (top/bottom of playfield)
        if self.player_rect.top <= self.bounds.top or self.player_rect.bottom >= self.bounds.bottom:
            self._game_over()
            return

        # Spawn / move pipes
        self._pipe_timer -= dt
        if self._pipe_timer <= 0.0:
            self._pipe_timer += self.pipe_spawn_interval
            self._spawn_pipe_pair()

        # Move pipes left
        for top_rect, bottom_rect in self.pipes:
            top_rect.x -= int(self.pipe_speed * dt)
            bottom_rect.x -= int(self.pipe_speed * dt)

        # Remove off-screen pipes
        self.pipes = [pair for pair in self.pipes if pair[0].right > self.bounds.left]

        # Scoring and collision
        player_mid_x = self.player_rect.centerx
        newly_passed: List[Tuple[pygame.Rect, pygame.Rect]] = []
        for pair in self.pipes:
            top_rect, bottom_rect = pair
            # Collision
            if self.player_rect.colliderect(top_rect) or self.player_rect.colliderect(bottom_rect):
                self._game_over()
                return
            # Passed check (only once per pipe pair)
            if pair not in self.passed_pipes and top_rect.right < player_mid_x:
                newly_passed.append(pair)

        for pair in newly_passed:
            self.passed_pipes.append(pair)
            self.score += 1
            # Gradually increase pipe speed
            self.pipe_speed = min(self.pipe_speed_max, self.pipe_speed + 12.0)

    def _game_over(self):
        self.is_over = True
        if self.score > FlappyBoxGame.BEST_SCORE:
            FlappyBoxGame.BEST_SCORE = self.score
        self.results_header = (
            f"Flappy Box — Score: {self.score} (Best: {FlappyBoxGame.BEST_SCORE})"
        )

    # --- Results integration ---------------------------------------------
    def scores(self):
        # Single entry for ResultsScene
        return [("Solo", float(self.score))]

    # --- Rendering --------------------------------------------------------
    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Bounds
        pygame.draw.rect(surface, (80, 80, 100), self.bounds, 2)

        # Pipes
        pipe_color = (90, 140, 220)
        pipe_outline = (210, 230, 255)
        for top_rect, bottom_rect in self.pipes:
            pygame.draw.rect(surface, pipe_color, top_rect)
            pygame.draw.rect(surface, pipe_outline, top_rect, 2)
            pygame.draw.rect(surface, pipe_color, bottom_rect)
            pygame.draw.rect(surface, pipe_outline, bottom_rect, 2)

        # Player
        pygame.draw.rect(surface, (240, 200, 80), self.player_rect)
        pygame.draw.rect(surface, (255, 240, 200), self.player_rect, 2)

        # HUD
        score_surf = font.render(f"Score: {self.score}", True, (255, 255, 255))
        best_surf = font.render(
            f"Best: {FlappyBoxGame.BEST_SCORE}", True, (230, 230, 230)
        )
        hint = font.render("Space/Click: Flap", True, (210, 210, 210))
        surface.blit(score_surf, (10, 10))
        surface.blit(best_surf, (10, 34))
        surface.blit(hint, (10, 58))
