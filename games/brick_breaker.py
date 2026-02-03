from __future__ import annotations
import random
import pygame

class BrickBreakerGame:
    def __init__(self, bounds: pygame.Rect):
        self.bounds = bounds
        # Paddle
        self.paddle = pygame.Rect(0, 0, 100, 12)
        self.paddle.centerx = bounds.centerx
        self.paddle.bottom = bounds.bottom - 8
        self.paddle_speed = 300.0
        self.move_left = False
        self.move_right = False
        # Ball
        self.ball_size = 10
        self.ball_x = float(self.paddle.centerx)
        self.ball_y = float(self.paddle.top - 16)
        self.ball_vx = float(random.choice([-160, -120, 120, 160]))
        self.ball_vy = -220.0
        self.ball_speed = 260.0
        self.prev_ball_x = self.ball_x
        self.prev_ball_y = self.ball_y
        # Bricks
        self.bricks = []
        self.rows = 6
        self.cols = 10
        self.brick_gap = 4
        self._init_bricks()
        # State
        self.score = 0
        self.lives = 3
        self.is_over = False
        self.results_header = None
        self.higher_time_wins = False
        self.show_time_in_results = False
        self.result_label = "Score"

    def _init_bricks(self):
        top_margin = self.bounds.top + 20
        left_margin = self.bounds.left + 20
        area_w = self.bounds.width - 40
        brick_w = (area_w - (self.cols - 1) * self.brick_gap) // self.cols
        brick_h = 18
        for r in range(self.rows):
            for c in range(self.cols):
                x = left_margin + c * (brick_w + self.brick_gap)
                y = top_margin + r * (brick_h + self.brick_gap)
                self.bricks.append(pygame.Rect(x, y, brick_w, brick_h))

    def reset(self):
        self.paddle.centerx = self.bounds.centerx
        self.move_left = False
        self.move_right = False
        self.ball_x = float(self.paddle.centerx)
        self.ball_y = float(self.paddle.top - 16)
        self.ball_vx = float(random.choice([-160, -120, 120, 160]))
        self.ball_vy = -220.0
        self.bricks.clear()
        self._init_bricks()
        self.score = 0
        self.lives = 3
        self.is_over = False
        self.results_header = None

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_a:
                self.move_left = True
            elif event.key == pygame.K_d:
                self.move_right = True
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_a:
                self.move_left = False
            elif event.key == pygame.K_d:
                self.move_right = False

    def _ball_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.ball_x), int(self.ball_y), self.ball_size, self.ball_size)

    def _reflect_from_rect(self, rect: pygame.Rect):
        # Decide reflection axis based on minimal overlap
        ball = self._ball_rect()
        dx = min(ball.right - rect.left, rect.right - ball.left)
        dy = min(ball.bottom - rect.top, rect.bottom - ball.top)
        if dx < dy:
            self.ball_vx = -self.ball_vx
        else:
            self.ball_vy = -self.ball_vy

    def update(self, dt: float, input_handler, pressed):
        if self.is_over:
            return
        # Store previous position before movement
        self.prev_ball_x = self.ball_x
        self.prev_ball_y = self.ball_y
        # Paddle movement
        if self.move_left:
            self.paddle.x -= int(self.paddle_speed * dt)
        if self.move_right:
            self.paddle.x += int(self.paddle_speed * dt)
        # Clamp paddle
        if self.paddle.left < self.bounds.left + 4:
            self.paddle.left = self.bounds.left + 4
        if self.paddle.right > self.bounds.right - 4:
            self.paddle.right = self.bounds.right - 4
        # Ball movement
        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt
        ball = self._ball_rect()
        # Wall collisions with position correction
        if ball.left <= self.bounds.left:
            self.ball_x = float(self.bounds.left)
            self.ball_vx = abs(self.ball_vx)
            ball = self._ball_rect()
        if ball.right >= self.bounds.right:
            self.ball_x = float(self.bounds.right - self.ball_size)
            self.ball_vx = -abs(self.ball_vx)
            ball = self._ball_rect()
        if ball.top <= self.bounds.top:
            self.ball_y = float(self.bounds.top)
            self.ball_vy = abs(self.ball_vy)
            ball = self._ball_rect()
        # Paddle collision
        if ball.colliderect(self.paddle) and self.ball_vy > 0:
            prev = pygame.Rect(int(self.prev_ball_x), int(self.prev_ball_y), self.ball_size, self.ball_size)
            if prev.bottom <= self.paddle.top:
                # Came from above: reflect vertically with angle
                hit_offset = (ball.centerx - self.paddle.centerx) / (self.paddle.width / 2)
                self.ball_vy = -abs(self.ball_vy)
                self.ball_vx = hit_offset * self.ball_speed
                # Normalize to target speed
                sp = (self.ball_vx**2 + self.ball_vy**2) ** 0.5
                if sp > 1e-3:
                    scale = self.ball_speed / sp
                    self.ball_vx *= scale
                    self.ball_vy *= scale
                # Position just above paddle
                self.ball_y = float(self.paddle.top - self.ball_size - 1)
                ball = self._ball_rect()
            else:
                # Side hit: reflect horizontally
                if prev.right <= self.paddle.left:
                    # Came from left
                    self.ball_vx = -abs(self.ball_vx)
                    self.ball_x = float(self.paddle.left - self.ball_size - 1)
                elif prev.left >= self.paddle.right:
                    # Came from right
                    self.ball_vx = abs(self.ball_vx)
                    self.ball_x = float(self.paddle.right + 1)
                else:
                    # Fallback: vertical
                    self.ball_vy = -abs(self.ball_vy)
                    self.ball_y = float(self.paddle.top - self.ball_size - 1)
                ball = self._ball_rect()
        # Brick collisions
        hit_index = None
        for i, b in enumerate(self.bricks):
            if ball.colliderect(b):
                hit_index = i
                break
        if hit_index is not None:
            rect = self.bricks.pop(hit_index)
            self.score += 1
            prev = pygame.Rect(int(self.prev_ball_x), int(self.prev_ball_y), self.ball_size, self.ball_size)
            # Determine impact side using previous position
            if prev.bottom <= rect.top and ball.bottom >= rect.top:
                # Hit from above
                self.ball_vy = -abs(self.ball_vy)
                self.ball_y = float(rect.top - self.ball_size - 1)
            elif prev.top >= rect.bottom and ball.top <= rect.bottom:
                # Hit from below
                self.ball_vy = abs(self.ball_vy)
                self.ball_y = float(rect.bottom + 1)
            elif prev.right <= rect.left and ball.right >= rect.left:
                # Hit from left
                self.ball_vx = -abs(self.ball_vx)
                self.ball_x = float(rect.left - self.ball_size - 1)
            elif prev.left >= rect.right and ball.left <= rect.right:
                # Hit from right
                self.ball_vx = abs(self.ball_vx)
                self.ball_x = float(rect.right + 1)
            else:
                # Fallback: invert vertical
                self.ball_vy = -self.ball_vy
            ball = self._ball_rect()
        # Lose condition (ball below bounds)
        if ball.top > self.bounds.bottom:
            self.lives -= 1
            if self.lives <= 0:
                self.is_over = True
                self.results_header = "Game Over"
            else:
                # Reset ball above paddle
                self.ball_x = float(self.paddle.centerx - self.ball_size / 2)
                self.ball_y = float(self.paddle.top - 16)
                self.ball_vx = float(random.choice([-160, -120, 120, 160]))
                self.ball_vy = -220.0
        # Win condition
        if not self.bricks and not self.is_over:
            self.is_over = True
            self.results_header = "Victory!"

    def scores(self):
        return [("Solo", float(self.score))]

    def draw(self, surface: pygame.Surface, font: pygame.font.Font):
        # Bounds
        pygame.draw.rect(surface, (80, 80, 100), self.bounds, 2)
        # Bricks
        for r in self.bricks:
            pygame.draw.rect(surface, (200, 80, 100), r)
            pygame.draw.rect(surface, (240, 200, 220), r, 2)
        # Paddle
        pygame.draw.rect(surface, (100, 160, 220), self.paddle)
        pygame.draw.rect(surface, (220, 230, 240), self.paddle, 2)
        # Ball
        ball = self._ball_rect()
        pygame.draw.rect(surface, (240, 240, 240), ball)
        # HUD
        stext = font.render(f"Score: {self.score}", True, (255, 255, 255))
        surface.blit(stext, (10, 10))
        ltext = font.render(f"Lives: {self.lives}", True, (230, 230, 230))
        surface.blit(ltext, (10, 34))
