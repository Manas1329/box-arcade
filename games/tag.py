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
        # Slightly stronger jump to feel snappier in the taller arena
        self.jump_speed = 700.0
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
        # For edge-triggered jumping
        self.last_jump_pressed: List[bool] = [False] * n
        # Jump input buffer so quick taps slightly before landing still jump
        self.jump_buffer: List[float] = [0.0] * n

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

        base_top = self.ground_rect.top
        # Approximate max jump height in pixels; keep steps below this
        max_jump_height = (self.jump_speed * self.jump_speed) / (2 * self.gravity)
        min_step = int(max_jump_height * 0.45)
        max_step = int(max_jump_height * 0.75)
        min_step = max(60, min_step)
        max_step = max(min_step + 10, max_step)

        rows = 4
        cur_top = base_top
        for _ in range(rows):
            step = random.randint(min_step, max_step)
            top = cur_top - step
            if top < self.bounds.top + 80:
                break
            cur_top = top

            # 2–3 platforms per row, with random widths and positions
            num_plats = random.randint(2, 3)
            h = 20
            for _ in range(num_plats):
                min_width = max(80, self.bounds.width // 10)
                max_width = max(min_width + 20, self.bounds.width // 6)
                width = random.randint(min_width, max_width)
                margin_x = 40
                max_x = self.bounds.right - margin_x - width
                min_x = self.bounds.left + margin_x
                if max_x <= min_x:
                    continue
                x = random.randint(min_x, max_x)
                plat = pygame.Rect(x, top, width, h)
                self.platforms.append(plat)

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
        self.jump_buffer = [0.0] * n

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

            # Jump: use "up" action as jump key (edge-triggered) with buffering
            jump_pressed = input_handler.is_action_pressed(pid, "up", pressed)
            if jump_pressed and not self.last_jump_pressed[i]:
                # Store a small buffer so taps just before landing still trigger
                self.jump_buffer[i] = 0.18
            self.last_jump_pressed[i] = jump_pressed

            # Consume jump buffer when grounded
            if self.grounded[i] and self.jump_buffer[i] > 0.0:
                self.vel_y[i] = -self.jump_speed
                self.grounded[i] = False
                self.jump_buffer[i] = 0.0

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
            # Not grounded until we resolve collisions this frame
            if self.vel_y[i] > 0:
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

            # Update jump buffer timer
            if self.jump_buffer[i] > 0.0:
                self.jump_buffer[i] = max(0.0, self.jump_buffer[i] - dt)

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
