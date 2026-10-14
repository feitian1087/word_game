import array
import json
import math
import os
import random

import pygame

W, H = 800, 600
FPS = 60
R = 30
LIVES = 20
HIT_SCORE = 10
BANNER_MS = 1500
HS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.json")

BG = (22, 26, 56)
WHITE = (255, 255, 255)
BUBBLE = [(239, 83, 80), (255, 167, 38), (255, 238, 88), (102, 187, 106), (66, 165, 245), (171, 71, 188)]

LEVELS = [
    (0, "ASDFJKL", (50, 70), 2400, 3),
    (10, "ASDFGHJKL", (60, 85), 2100, 4),
    (25, "ASDFGHJKLQWERTYUIOP", (70, 100), 1800, 4),
    (45, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", (80, 115), 1500, 5),
    (70, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", (100, 140), 1200, 6),
]


def make_sound(sweeps):
    init = pygame.mixer.get_init()
    if not init:
        return None
    rate, _, channels = init
    buf = array.array("h")
    for f0, f1, dur in sweeps:
        n = int(rate * dur)
        phase = 0.0
        for i in range(n):
            phase += 2 * math.pi * (f0 + (f1 - f0) * i / n) / rate
            env = min(1.0, i / (0.005 * rate), (n - i) / (0.02 * rate))
            buf.extend([int(12000 * env * math.sin(phase))] * channels)
    return pygame.mixer.Sound(buffer=buf.tobytes())


def load_best():
    try:
        with open(HS_FILE, encoding="utf-8") as f:
            return int(json.load(f)["best"])
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def save_best(best):
    try:
        with open(HS_FILE, "w", encoding="utf-8") as f:
            json.dump({"best": best}, f)
    except OSError:
        pass


def level_for(score):
    return max(i for i, lv in enumerate(LEVELS) if score >= lv[0])


class Drop:
    def __init__(self, letter, x, speed):
        self.letter = letter
        self.x = x
        self.y = -R
        self.speed = speed
        self.color = random.choice(BUBBLE)

    def update(self, dt):
        self.y += self.speed * dt

    def draw(self, surf, font):
        center = (int(self.x), int(self.y))
        pygame.draw.circle(surf, self.color, center, R)
        pygame.draw.circle(surf, WHITE, center, R, 3)
        txt = font.render(self.letter, True, WHITE)
        surf.blit(txt, txt.get_rect(center=center))


class Game:
    def __init__(self, screen, fonts, sounds):
        self.screen = screen
        self.big, self.mid, self.small = fonts
        self.ok, self.bad = sounds
        self.best = load_best()
        self.reset()

    def reset(self):
        self.drops = []
        self.score = 0
        self.lives = LIVES
        self.level = 0
        self.over = False
        self.last_spawn = pygame.time.get_ticks()
        self.banner_until = self.last_spawn + BANNER_MS

    def spawn(self):
        _, pool, speed, interval, cap = LEVELS[self.level]
        now = pygame.time.get_ticks()
        if len(self.drops) >= cap or now - self.last_spawn < interval:
            return
        self.last_spawn = now
        candidates = [random.randint(R + 10, W - R - 10) for _ in range(8)]
        x = max(candidates, key=lambda c: min([abs(c - d.x) for d in self.drops] or [W]))
        self.drops.append(Drop(random.choice(pool), x, random.uniform(*speed)))

    def key(self, letter):
        hits = [d for d in self.drops if d.letter == letter]
        if not hits:
            self.bad and self.bad.play()
            return
        drop = max(hits, key=lambda d: d.y)
        self.drops.remove(drop)
        self.score += HIT_SCORE
        self.ok and self.ok.play()
        level = level_for(self.score)
        if level != self.level:
            self.level = level
            self.lives = LIVES
            self.banner_until = pygame.time.get_ticks() + BANNER_MS

    def update(self, dt):
        if self.over:
            return
        self.spawn()
        for d in self.drops:
            d.update(dt)
        missed = [d for d in self.drops if d.y - R > H]
        if missed:
            self.drops = [d for d in self.drops if d not in missed]
            self.lives -= len(missed)
            self.bad and self.bad.play()
        if self.lives <= 0:
            self.over = True
            if self.score > self.best:
                self.best = self.score
                save_best(self.best)

    def draw(self):
        self.screen.fill(BG)
        for d in self.drops:
            d.draw(self.screen, self.mid)
        hud = f"Score {self.score}    Best {self.best}    Level {self.level + 1}    Lives {self.lives}"
        self.screen.blit(self.small.render(hud, True, WHITE), (12, 10))
        if pygame.time.get_ticks() < self.banner_until and not self.over:
            txt = self.big.render(f"LEVEL {self.level + 1}", True, WHITE)
            self.screen.blit(txt, txt.get_rect(center=(W // 2, H // 2)))
        if self.over:
            shade = pygame.Surface((W, H), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 170))
            self.screen.blit(shade, (0, 0))
            lines = [
                (self.big, "GAME OVER"),
                (self.mid, f"Score: {self.score}     Best: {self.best}"),
                (self.small, "Press SPACE or ENTER to play again"),
                (self.small, "Press ESC to quit"),
            ]
            y = H // 2 - 120
            for font, text in lines:
                txt = font.render(text, True, WHITE)
                self.screen.blit(txt, txt.get_rect(center=(W // 2, y)))
                y += 80


def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Letter Rain")
    fonts = (pygame.font.Font(None, 96), pygame.font.Font(None, 48), pygame.font.Font(None, 36))
    sounds = (make_sound([(523, 523, 0.08), (784, 784, 0.12)]), make_sound([(220, 140, 0.25)]))
    game = Game(screen, fonts, sounds)
    clock = pygame.time.Clock()
    while True:
        dt = clock.tick(FPS) / 1000
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                pygame.quit()
                return
            if e.type != pygame.KEYDOWN:
                continue
            if game.over:
                if e.key in (pygame.K_SPACE, pygame.K_RETURN):
                    game.reset()
                continue
            name = pygame.key.name(e.key).upper()
            if len(name) == 1 and name.isalpha():
                game.key(name)
        game.update(dt)
        game.draw()
        pygame.display.flip()


if __name__ == "__main__":
    main()
