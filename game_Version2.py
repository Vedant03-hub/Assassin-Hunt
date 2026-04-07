# Assassin Hunt - simple top-down stealth/hunting game
# Save as game.py and run: python game.py
# Requires: pygame (pip install pygame)
import pygame
import math
import random
import sys
from collections import deque

# --- Config ---
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
FPS = 60

PLAYER_SPEED = 3.4
PLAYER_SIZE = 18
PLAYER_HEALTH = 100

BULLET_SPEED = 12
BULLET_SIZE = 4
PISTOL_MAG = 8
PISTOL_RELOAD_MS = 1000
PISTOL_COOLDOWN_MS = 250

KNIFE_RANGE = 28
KNIFE_COOLDOWN_MS = 400

ENEMY_SPEED = 1.6
ENEMY_CHASE_SPEED = 2.2
ENEMY_FOV_DEG = 70
ENEMY_VIEW_DISTANCE = 220
ENEMY_HEALTH = 50
ENEMY_PATROL_PAUSE_MS = 800

OBSTACLES = [
    pygame.Rect(200, 120, 120, 28),
    pygame.Rect(420, 80, 36, 220),
    pygame.Rect(680, 220, 40, 260),
    pygame.Rect(80, 400, 150, 30),
    pygame.Rect(320, 360, 200, 30),
]

# Colors
WHITE = (245, 245, 245)
BLACK = (12, 12, 12)
RED = (220, 60, 60)
GREEN = (90, 200, 120)
YELLOW = (240, 200, 30)
DARK = (28, 28, 30)
GRAY = (120, 120, 120)
SHADOW = (18, 18, 22)

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Assassin Hunt")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 18)
big_font = pygame.font.SysFont("Arial", 46)

# --- Utilities ---
def draw_text(surf, text, x, y, color=WHITE, center=False, size=18):
    f = pygame.font.SysFont("Arial", size)
    r = f.render(text, True, color)
    rect = r.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surf.blit(r, rect)

def vec_len(vx, vy):
    return math.hypot(vx, vy)

def normalize(vx, vy):
    l = vec_len(vx, vy)
    if l == 0: return 0, 0
    return vx / l, vy / l

def line_intersects_rect(p1, p2, rect):
    # Simple segment-rect intersection using clipping
    x1, y1 = p1; x2, y2 = p2
    # Check if either point inside rect
    if rect.collidepoint(x1, y1) or rect.collidepoint(x2, y2):
        return True
    # Check each rect edge
    edges = [
        ((rect.left, rect.top), (rect.right, rect.top)),
        ((rect.right, rect.top), (rect.right, rect.bottom)),
        ((rect.right, rect.bottom), (rect.left, rect.bottom)),
        ((rect.left, rect.bottom), (rect.left, rect.top)),
    ]
    for e1, e2 in edges:
        if segments_intersect((x1,y1), (x2,y2), e1, e2):
            return True
    return False

def segments_intersect(a1, a2, b1, b2):
    # Checks if segments a1-a2 and b1-b2 intersect
    def ccw(p1,p2,p3):
        return (p3[1]-p1[1])*(p2[0]-p1[0]) > (p2[1]-p1[1])*(p3[0]-p1[0])
    return (ccw(a1,b1,b2) != ccw(a2,b1,b2)) and (ccw(a1,a2,b1) != ccw(a1,a2,b2))

# --- Game Entities ---
class Bullet:
    def __init__(self, x, y, vx, vy, owner):
        self.x = x; self.y = y
        self.vx = vx; self.vy = vy
        self.owner = owner
        self.rect = pygame.Rect(self.x - BULLET_SIZE//2, self.y - BULLET_SIZE//2, BULLET_SIZE, BULLET_SIZE)
        self.alive = True

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rect.x = int(self.x - BULLET_SIZE//2); self.rect.y = int(self.y - BULLET_SIZE//2)
        if not (0 <= self.x <= SCREEN_WIDTH and 0 <= self.y <= SCREEN_HEIGHT):
            self.alive = False

    def draw(self, surf):
        pygame.draw.rect(surf, YELLOW, self.rect)

class Particle:
    def __init__(self, x, y, color, lifetime=20):
        self.x = x; self.y = y
        self.vx = random.uniform(-2,2); self.vy = random.uniform(-2,2)
        self.life = lifetime
        self.color = color

    def update(self):
        self.x += self.vx; self.y += self.vy
        self.vy += 0.12
        self.life -= 1

    def draw(self, surf):
        if self.life>0:
            pygame.draw.circle(surf, self.color, (int(self.x),int(self.y)), max(1, self.life//6))

class Player:
    def __init__(self):
        self.x = SCREEN_WIDTH//2; self.y = SCREEN_HEIGHT - 80
        self.size = PLAYER_SIZE
        self.health = PLAYER_HEALTH
        self.speed = PLAYER_SPEED
        self.crouch = False
        self.alive = True
        # weapons: pistol + knife
        self.weapon = "pistol"
        self.mag = PISTOL_MAG
        self.last_shot = -9999
        self.reloading = False
        self.reload_start = 0
        self.score = 0
        self.kills = 0

    def rect(self):
        return pygame.Rect(self.x - self.size//2, self.y - self.size//2, self.size, self.size)

    def update(self, dt, keys):
        vx = vy = 0
        speed = self.speed * (0.6 if self.crouch else 1.0)
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            vx -= speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            vx += speed
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            vy -= speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            vy += speed
        if vx!=0 and vy!=0:
            vx *= 0.7071; vy *= 0.7071
        self.x = max(16, min(SCREEN_WIDTH-16, self.x + vx * dt))
        self.y = max(16, min(SCREEN_HEIGHT-16, self.y + vy * dt))

    def draw(self, surf, mouse_pos):
        # Draw player as a triangle pointing to mouse
        mx, my = mouse_pos
        angle = math.atan2(my - self.y, mx - self.x)
        pts = []
        r = self.size
        pts.append((self.x + math.cos(angle) * r, self.y + math.sin(angle) * r))
        pts.append((self.x + math.cos(angle + 2.2) * r*0.8, self.y + math.sin(angle + 2.2) * r*0.8))
        pts.append((self.x + math.cos(angle - 2.2) * r*0.8, self.y + math.sin(angle - 2.2) * r*0.8))
        pygame.draw.polygon(surf, GREEN if not self.crouch else (60,140,80), pts)
        # health bar
        bh = 6
        w = 50
        pygame.draw.rect(surf, (80,80,80), (self.x - w//2, self.y + r + 6, w, bh))
        pygame.draw.rect(surf, RED, (self.x - w//2, self.y + r + 6, int(w * (self.health/PLAYER_HEALTH)), bh))

    def shoot(self, target_x, target_y, now):
        if self.weapon == "pistol":
            if self.reloading:
                return None
            if now - self.last_shot < PISTOL_COOLDOWN_MS:
                return None
            if self.mag <= 0:
                # start reload
                self.reloading = True; self.reload_start = now
                return None
            dx = target_x - self.x; dy = target_y - self.y
            nx, ny = normalize(dx, dy)
            bx = self.x + nx * (self.size + 6)
            by = self.y + ny * (self.size + 6)
            self.last_shot = now
            self.mag -= 1
            vx = nx * BULLET_SPEED; vy = ny * BULLET_SPEED
            return Bullet(bx, by, vx, vy, owner="player")
        elif self.weapon == "knife":
            # melee: no projectile; handled elsewhere
            return None

    def reload(self, now):
        if self.reloading and now - self.reload_start >= PISTOL_RELOAD_MS:
            self.mag = PISTOL_MAG
            self.reloading = False

class Enemy:
    def __init__(self, x, y, waypoints):
        self.x = x; self.y = y
        self.size = 18
        self.waypoints = deque(waypoints)
        self.target = self.waypoints[0] if waypoints else (x,y)
        self.speed = ENEMY_SPEED
        self.state = "patrol"  # patrol, alert, chase, searching
        self.facing = 0.0
        self.health = ENEMY_HEALTH
        self.last_seen_time = 0
        self.pause_until = 0

    def rect(self):
        return pygame.Rect(self.x - self.size//2, self.y - self.size//2, self.size, self.size)

    def update(self, dt, player, obstacles, now):
        px, py = player.x, player.y
        # state transitions
        saw = self.can_see_player(player, obstacles)
        if saw:
            self.state = "chase"
            self.last_seen_time = now
        else:
            if self.state == "chase":
                # start searching
                self.state = "searching"
                self.pause_until = now + ENEMY_PATROL_PAUSE_MS
            elif self.state == "searching" and now > self.pause_until:
                self.state = "patrol"

        # movement
        if self.state == "patrol":
            tx, ty = self.target
            dx = tx - self.x; dy = ty - self.y
            dist = vec_len(dx,dy)
            if dist < 6:
                # move to next waypoint
                if len(self.waypoints) > 1:
                    self.waypoints.rotate(-1)
                self.target = self.waypoints[0]
            else:
                nx, ny = normalize(dx, dy)
                self.x += nx * self.speed * dt
                self.y += ny * self.speed * dt
                self.facing = math.atan2(ny, nx)
        elif self.state == "chase":
            dx = px - self.x; dy = py - self.y
            nx, ny = normalize(dx, dy)
            self.x += nx * ENEMY_CHASE_SPEED * dt
            self.y += ny * ENEMY_CHASE_SPEED * dt
            self.facing = math.atan2(ny, nx)
        elif self.state == "searching":
            # idle, look around
            self.facing += 0.02 * dt

    def can_see_player(self, player, obstacles):
        dx = player.x - self.x; dy = player.y - self.y
        dist = vec_len(dx, dy)
        if dist > ENEMY_VIEW_DISTANCE:
            return False
        # reduce detection if player crouches
        effective_view = ENEMY_VIEW_DISTANCE * (0.6 if player.crouch else 1.0)
        if dist > effective_view: return False
        forward_x = math.cos(self.facing); forward_y = math.sin(self.facing)
        nx, ny = normalize(dx, dy)
        dot = forward_x * nx + forward_y * ny
        angle = math.degrees(math.acos(max(-1,min(1,dot))))
        if angle > ENEMY_FOV_DEG/2:
            return False
        # Check obstacles blocking
        for obs in obstacles:
            if line_intersects_rect((self.x,self.y),(player.x,player.y), obs):
                return False
        return True

    def draw(self, surf):
        # body
        pygame.draw.circle(surf, (200,80,80), (int(self.x), int(self.y)), self.size//2 + 2)
        pygame.draw.circle(surf, RED, (int(self.x), int(self.y)), self.size//2)
        # facing line
        fx = self.x + math.cos(self.facing)* (self.size)
        fy = self.y + math.sin(self.facing)* (self.size)
        pygame.draw.line(surf, BLACK, (self.x, self.y), (fx, fy), 2)
        # health
        w = 36; bh=5
        pygame.draw.rect(surf, (40,40,40), (self.x - w//2, self.y - self.size - 8, w, bh))
        pygame.draw.rect(surf, GREEN, (self.x - w//2, self.y - self.size - 8, int(w*(self.health/ENEMY_HEALTH)), bh))

    def draw_vision(self, surf):
        # semi-transparent cone
        left_angle = self.facing - math.radians(ENEMY_FOV_DEG/2)
        right_angle = self.facing + math.radians(ENEMY_FOV_DEG/2)
        p1 = (self.x, self.y)
        p2 = (self.x + math.cos(left_angle)*ENEMY_VIEW_DISTANCE, self.y + math.sin(left_angle)*ENEMY_VIEW_DISTANCE)
        p3 = (self.x + math.cos(right_angle)*ENEMY_VIEW_DISTANCE, self.y + math.sin(right_angle)*ENEMY_VIEW_DISTANCE)
        pts = [p1, p2, p3]
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        color = (255,180,60,40) if self.state!="chase" else (255,40,40,80)
        pygame.draw.polygon(s, color, pts)
        surf.blit(s, (0,0))

# --- Game state & logic ---
def run_game():
    player = Player()
    bullets = []
    enemies = []
    particles = []
    now = pygame.time.get_ticks()
    # spawn enemies with simple waypoints
    enemies.append(Enemy(140, 120, [(140,120),(320,120),(320,220)]))
    enemies.append(Enemy(540, 180, [(540,180),(640,180),(740,260)]))
    enemies.append(Enemy(760, 520, [(760,520),(560,520),(560,420)]))
    enemies.append(Enemy(360, 480, [(360,480),(460,480),(460,380)]))

    state = "menu"
    last_time = pygame.time.get_ticks()
    running = True

    while running:
        dt_ms = clock.tick(FPS)
        dt = dt_ms / (1000/60)  # normalized to 60fps units
        now = pygame.time.get_ticks()
        mouse_x, mouse_y = pygame.mouse.get_pos()
        keys = pygame.key.get_pressed()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            if ev.type == pygame.KEYDOWN:
                if state == "menu" and ev.key == pygame.K_RETURN:
                    state = "playing"
                elif state == "gameover" and ev.key == pygame.K_RETURN:
                    # restart
                    return True  # signal restart
                elif ev.key == pygame.K_1:
                    player.weapon = "pistol"
                elif ev.key == pygame.K_2:
                    player.weapon = "knife"
                elif ev.key == pygame.K_r:
                    if player.weapon=="pistol":
                        player.reloading = True; player.reload_start = now
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if state == "playing" and ev.button == 1:
                    proj = player.shoot(mouse_x, mouse_y, now)
                    if proj:
                        bullets.append(proj)
                if state == "menu" and ev.button == 1:
                    state = "playing"

        if state == "playing":
            player.crouch = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
            player.update(dt, keys)
            player.reload(now)

            # knife attack
            if player.weapon == "knife" and pygame.mouse.get_pressed()[0]:
                # melee, basic cooldown enforcement via last_shot
                if now - player.last_shot >= KNIFE_COOLDOWN_MS:
                    player.last_shot = now
                    for e in enemies:
                        if vec_len(e.x - player.x, e.y - player.y) <= KNIFE_RANGE:
                            e.health = 0
                            player.kills += 1
                            player.score += 150
                            # spawn particles
                            for _ in range(8):
                                particles.append(Particle(e.x, e.y, RED))
            # update bullets
            for b in bullets:
                b.update(1.0)
            bullets = [b for b in bullets if b.alive]

            # bullet collisions with obstacles / enemies
            for b in bullets:
                # obstacles
                for obs in OBSTACLES:
                    if obs.colliderect(b.rect):
                        b.alive = False
                        for _ in range(6):
                            particles.append(Particle(b.x, b.y, GRAY))
                # enemies
                for e in enemies:
                    if e.rect().colliderect(b.rect) and b.owner=="player":
                        e.health -= 40
                        b.alive = False
                        for _ in range(10):
                            particles.append(Particle(b.x, b.y, YELLOW))
                        if e.health <= 0:
                            player.score += 100
                            player.kills += 1

            # update enemies
            for e in enemies:
                e.update(dt, player, OBSTACLES, now)
                if e.state == "chase":
                    # if close, damage player
                    if vec_len(e.x - player.x, e.y - player.y) < 18 and now - getattr(e, "last_hit",0) > 500:
                        player.health -= 18
                        e.last_hit = now
                        for _ in range(6):
                            particles.append(Particle(player.x, player.y, RED))
                # enemy line of fire: simple chance to fire pistol when chasing (not implemented projectiles from enemy to keep it simple)
            enemies = [e for e in enemies if e.health > 0]

            # spawn small particles and update
            for p in particles:
                p.update()
            particles = [p for p in particles if p.life > 0]

            # check player death
            if player.health <= 0:
                state = "gameover"

        # -- Drawing --
        screen.fill(SHADOW)
        # Draw world grid / floor
        for y in range(0, SCREEN_HEIGHT, 64):
            pygame.draw.line(screen, (24,24,28), (0,y), (SCREEN_WIDTH,y), 1)
        for x in range(0, SCREEN_WIDTH, 64):
            pygame.draw.line(screen, (24,24,28), (x,0), (x,SCREEN_HEIGHT), 1)

        # Draw obstacles (cover)
        for obs in OBSTACLES:
            pygame.draw.rect(screen, (60,60,60), obs)
            pygame.draw.rect(screen, (40,40,40), obs, 2)

        # Draw enemies vision cones first (so it's under enemy)
        for e in enemies:
            e.draw_vision(screen)

        # Draw enemies
        for e in enemies:
            e.draw(screen)

        # Draw player
        if state == "playing":
            player.draw(screen, (mouse_x, mouse_y))

        # Draw bullets and particles
        for b in bullets:
            b.draw(screen)
        for p in particles:
            p.draw(screen)

        # HUD
        draw_text(screen, f"Weapon: {player.weapon} (1: pistol, 2: knife)", 10, 8)
        if player.weapon=="pistol":
            draw_text(screen, f"Ammo: {player.mag}/{PISTOL_MAG}" + (" (reloading)" if player.reloading else ""), 10, 28)
        draw_text(screen, f"Health: {player.health}", 10, 48)
        draw_text(screen, f"Score: {player.score}  Kills: {player.kills}", SCREEN_WIDTH - 220, 8)
        draw_text(screen, "Hold Shift to crouch (reduces detection). Mouse to aim. LMB to fire. R to reload.", 10, SCREEN_HEIGHT-26, color=GRAY, size=14)

        # State overlays
        if state == "menu":
            pygame.draw.rect(screen, (0,0,0,160), (0,0,SCREEN_WIDTH,SCREEN_HEIGHT))
            draw_text(screen, "ASSASSIN HUNT", SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 60, center=True, size=48, color=WHITE)
            draw_text(screen, "Click or press Enter to start", SCREEN_WIDTH//2, SCREEN_HEIGHT//2, center=True, size=22)
            draw_text(screen, "Controls: WASD / Arrow keys to move, Shift to crouch, Mouse to aim, 1/2 switch, R reload", SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 40, center=True, size=18, color=GRAY)
        if state == "gameover":
            pygame.draw.rect(screen, (0,0,0,180), (0,0,SCREEN_WIDTH,SCREEN_HEIGHT))
            draw_text(screen, "GAME OVER", SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 40, center=True, size=44, color=RED)
            draw_text(screen, f"Score: {player.score}   Kills: {player.kills}", SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 6, center=True, size=20)
            draw_text(screen, "Press Enter to restart", SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 48, center=True, size=18)

        pygame.display.flip()

    return False

if __name__ == "__main__":
    # loop to allow restart
    while True:
        restart = run_game()
        if not restart:
            break
    pygame.quit()
    sys.exit()