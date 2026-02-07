"""Side-view platformer-style Tag game using rectangular players.

Rules:
- One player is IT.
- Side-on platformer movement with gravity and jumping.
- Solid ground and floating platforms you can stand on.
- IT transfers on collision with another player, with short
  post-tag invulnerability to avoid chain tags.
- Timer-based match; least time as IT wins.
"""
from __future__ import annotations
import random
from typing import List, Tuple
import pygame

from entities.player import Player


class TagGame:
    def __init__(self, players: List[Player], bounds: pygame.Rect, match_time: int = 60):
        self.players = players
        self.bounds = bounds
        self.match_time = float(match_time)
        self.remaining = float(match_time)

        # Physics parameters
        self.gravity = 1400.0
        self.move_speed = 260.0
        self.jump_speed = 650.0
        self.ground_height = 40

        # World geometry: ground + simple platform set
        self.ground_rect = pygame.Rect(
            bounds.left,
            bounds.bottom - self.ground_height,
            bounds.width,
            self.ground_height,
        )
        self.platforms: List[pygame.Rect] = []
        self._generate_platforms()

        # Per-player physics state parallel to self.players
        n = len(self.players)
        self.vel_x: List[float] = [0.0] * n
        self.vel_y: List[float] = [0.0] * n
        self.grounded: List[bool] = [False] * n
        self.last_jump_pressed: List[bool] = [False] * n

        # Tag state and scoring
        self.current_it_id = random.choice(players).player_id if players else 1
        self.is_over = False
        self.tag_cooldown = 0.0  # seconds of post-tag invulnerability
        self.tag_cooldown_duration = 0.8
        self.higher_time_wins = False
        self.show_time_in_results = True
        self.result_label = "IT"

        # Initialize IT state and reset player timers
        for p in self.players:
            p.is_it = (p.player_id == self.current_it_id)
            p.it_time = 0.0

    # ------------------------------------------------------------------
    # World generation
    # ------------------------------------------------------------------
    def _generate_platforms(self):
        """Generate a handful of flat platforms at jump-reachable heights.

        The layout is intentionally simple: several horizontal platforms
        staggered across the arena, all within jump reach from the one
        below so players can traverse the stack.
        """
        self.platforms.clear()
        if self.bounds.height < 160:
            return

        # Vertical spacing tuned to be comfortably below maximum jump height
        max_step = 160
        base_top = self.ground_rect.top
        # Create 3-4 rows of platforms
        rows = 4
        for i in range(rows):
            top = base_top - (i + 1) * max_step
            if top < self.bounds.top + 40:
                break
            # Two platforms per row, left and right
            margin_x = 80
            plat_width = max(160, self.bounds.width // 5)
            h = 22
            left_plat = pygame.Rect(
                self.bounds.left + margin_x,
                top,
                plat_width,
                h,
            )
            right_plat = pygame.Rect(
                self.bounds.right - margin_x - plat_width,
                top,
                plat_width,
                h,
            )
            self.platforms.extend([left_plat, right_plat])

    def reset(self):
        # Reset timers and IT state but keep the same world; regenerate
        # platforms for some variety.
        self.remaining = self.match_time
        self.is_over = False
        self.current_it_id = random.choice(self.players).player_id
        self.tag_cooldown = 0.0
        self._generate_platforms()

        n = len(self.players)
        self.vel_x = [0.0] * n
        self.vel_y = [0.0] * n
        self.grounded = [False] * n
        self.last_jump_pressed = [False] * n

        # Spawn players roughly above the ground, spread horizontally
        if n:
            spacing = self.bounds.width // (n + 1)
            for i, p in enumerate(self.players):
                px = self.bounds.left + spacing * (i + 1)
                p.rect.x = px - p.rect.width // 2
                p.rect.bottom = self.ground_rect.top
                p.is_it = (p.player_id == self.current_it_id)
                p.it_time = 0.0

    # ------------------------------------------------------------------
    # Core update
    # ------------------------------------------------------------------
    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return

        # Timer and tag cooldown
        self.remaining -= dt
        if self.remaining <= 0:
            self.remaining = 0
            self.is_over = True
            return

        if self.tag_cooldown > 0.0:
            self.tag_cooldown = max(0.0, self.tag_cooldown - dt)

        # Physics and controls per player
        for i, p in enumerate(self.players):
            pid = p.player_id

            # Horizontal movement from configured left/right keys
            dx, _ = input_handler.get_axes(pid, pressed)
            self.vel_x[i] = dx * self.move_speed

            # Jump: use "up" action as jump key (edge-triggered)
            jump_pressed = input_handler.is_action_pressed(pid, "up", pressed)
            if jump_pressed and not self.last_jump_pressed[i] and self.grounded[i]:
                self.vel_y[i] = -self.jump_speed
                self.grounded[i] = False
            self.last_jump_pressed[i] = jump_pressed

            # Apply gravity
            self.vel_y[i] += self.gravity * dt

            # Horizontal integration
            p.rect.x += int(self.vel_x[i] * dt)
            # Clamp to arena horizontally
            if p.rect.left < self.bounds.left:
                p.rect.left = self.bounds.left
            if p.rect.right > self.bounds.right:
                p.rect.right = self.bounds.right

            # Vertical integration with simple platform collisions
            old_bottom = p.rect.bottom
            p.rect.y += int(self.vel_y[i] * dt)
            self.grounded[i] = False

            # Ceiling
            if p.rect.top < self.bounds.top:
                p.rect.top = self.bounds.top
                if self.vel_y[i] < 0:
                    self.vel_y[i] = 0.0

            # Ground collision (land on top only)
            if (
                self.vel_y[i] >= 0
                and p.rect.colliderect(self.ground_rect)
                and old_bottom <= self.ground_rect.top
            ):
                p.rect.bottom = self.ground_rect.top
                self.vel_y[i] = 0.0
                self.grounded[i] = True

            # Platform collisions: only from above
            for plat in self.platforms:
                if (
                    self.vel_y[i] >= 0
                    and p.rect.colliderect(plat)
                    and old_bottom <= plat.top
                ):
                    p.rect.bottom = plat.top
                    self.vel_y[i] = 0.0
                    self.grounded[i] = True

        # Collision detection & IT transfer (with brief invulnerability)
        it_player = next((x for x in self.players if x.player_id == self.current_it_id), None)
        if it_player and self.tag_cooldown <= 0.0:
            for p in self.players:
                if p is it_player:
                    continue
                if it_player.rect.colliderect(p.rect):
                    # Transfer IT to collided player
                    it_player.is_it = False
                    p.is_it = True
                    self.current_it_id = p.player_id
                    it_player = p
                    self.tag_cooldown = self.tag_cooldown_duration
                    # Only transfer once per frame to avoid chain transfers
                    break

        # Accumulate IT time for whichever player is currently IT
        if it_player:
            it_player.it_time += dt

    def scores(self) -> List[Tuple[str, float]]:
        # Returns list of (name, it_time)
        return [(p.name, p.it_time) for p in self.players]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # World: ground and platforms
        ground_color = (60, 60, 80)
        plat_color = (80, 80, 110)
        pygame.draw.rect(surface, ground_color, self.ground_rect)
        for plat in self.platforms:
            pygame.draw.rect(surface, plat_color, plat)

        # Draw players with IT highlight
        for p in self.players:
            pygame.draw.rect(surface, p.color, p.rect)
            if getattr(p, "is_it", False):
                # Outline around IT player
                outline = p.rect.inflate(6, 6)
                pygame.draw.rect(surface, (250, 230, 120), outline, 3)

        # HUD: current IT & remaining time
        it_text = f"IT: Player {self.current_it_id}"
        time_text = f"Time Left: {int(self.remaining)}s"
        hint_text = "Move: per-player left/right keys   Jump: per-player up key"
        it_surf = font.render(it_text, True, (255, 255, 255))
        time_surf = font.render(time_text, True, (255, 255, 255))
        hint_surf = font.render(hint_text, True, (220, 220, 220))
        surface.blit(it_surf, (self.bounds.left + 10, self.bounds.top + 8))
        surface.blit(time_surf, (self.bounds.left + 10, self.bounds.top + 32))
        surface.blit(hint_surf, (self.bounds.left + 10, self.bounds.top + 56))
