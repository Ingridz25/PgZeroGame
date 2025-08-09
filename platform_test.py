import pgzrun
from pgzero.builtins import Actor, Rect, music, sounds

# —————————————————————————————————————————————————————————————————
# Window & game states
WIDTH, HEIGHT = 800, 600
MENU, PLAYING, GAME_OVER, LEVEL_COMPLETE = 0, 1, 2, 3
game_state = MENU
audio_enabled = True

# Animation FPS
IDLE_FPS, RUN_FPS, JUMP_FPS = 2, 6, 5
FALL_FPS, ATTACK_FPS, AIR_ATTACK_FPS = 4, 8, 12
HIT_FPS = 6

# —————————————————————————————————————————————————————————————————
def set_game_state(s):
    global game_state
    game_state = s

    if s == MENU:
        if audio_enabled:
            music.play('starlight_city')
            music.set_volume(0.5)
        else:
            music.stop()
    elif s == PLAYING:
        music.stop()
    elif s == LEVEL_COMPLETE and audio_enabled:
        sounds.coin.play()

def toggle_audio():
    global audio_enabled
    audio_enabled = not audio_enabled
    if game_state == MENU:
        if audio_enabled:
            music.play('starlight_city'); music.set_volume(0.5)
        else:
            music.stop()

def quit_game():
    exit()

def reload_level():
    global player, enemies, platforms, flag_rect

    # 1) platforms
    platforms[:] = [
        Rect(  0, 501, 166, 99),  # p1
        Rect(188, 450, 212,  15),  # p2
        Rect(  0, 314, 166,  14),  # p3
        Rect(200, 241,  39,  16),  # p4
        Rect(256, 153, 248,  17),  # p5
        Rect(592, 257, 127,  15),  # p6
        Rect(547, 489, 253, 111),  # p7
    ]

    # 2) player spawn
    player = Player((10, 439))

    # 3) enemies with patrol ranges
    enemies[:] = []
    e1 = Enemy((360, 415)); e1.range = (241, 360); enemies.append(e1)
    e2 = Enemy((656, 458)); e2.range = (615, 656); enemies.append(e2)
    e3 = Enemy((461, 111)); e3.range = (323, 461); enemies.append(e3)

    # 4) flag
    flag_rect = Rect(719, 425, 20, 40)

    set_game_state(PLAYING)

# —————————————————————————————————————————————————————————————————
class Player(Actor):
    def __init__(self, pos):
        super().__init__('idle_0', pos)
        self.vx = self.vy = 0
        self.gravity, self.max_fall = 0.8, 15
        self.on_ground = False
        self.coyote = 0
        self.facing = 1
        self.attacking = False
        self.attack_timer = 0
        self.timer = self.frame = 0
        self.anim = {
            'idle':       ([f'idle_{i}' for i in range(2)],     IDLE_FPS),
            'run':        ([f'run_{i}'  for i in range(6)],     RUN_FPS),
            'jump':       (['jump_0'],                          JUMP_FPS),
            'fall':       (['fall_0'],                          FALL_FPS),
            'attack':     ([f'attack_{i}' for i in range(3)],   ATTACK_FPS),
            'air_attack': ([f'air_attack_{i}' for i in range(3)], AIR_ATTACK_FPS),
            'hit':        ([f'hit_{i}'  for i in range(3)],      HIT_FPS),
        }
        self.w, self.h = 30, 60
        self.hitbox = Rect(self.x - self.w/2, self.y - self.h/2, self.w, self.h)

    def update(self, platforms, enemies):
        # controls
        run = keyboard.lshift or keyboard.rshift
        speed, ms = (0.8,7) if run else (0.5,5)
        if keyboard.left:
            self.vx = max(self.vx - speed, -ms); self.facing = -1
        elif keyboard.right:
            self.vx = min(self.vx + speed,  ms); self.facing = 1
        else:
            self.vx *= 0.8

        # gravity
        self.vy = min(self.vy + self.gravity, self.max_fall)
        self.on_ground = False

        # move X + collide
        self.x += self.vx
        self.hitbox.x = self.x - self.w/2
        for p in platforms:
            if self.hitbox.colliderect(p):
                if self.vx > 0:
                    self.x = p.left - self.w/2
                else:
                    self.x = p.right + self.w/2
                self.vx = 0
                self.hitbox.x = self.x - self.w/2

        # move Y + collide
        self.y += self.vy
        self.hitbox.y = self.y - self.h/2
        for p in platforms:
            if self.hitbox.colliderect(p):
                if self.vy > 0:
                    self.y = p.top - self.h/2
                    self.vy = 0
                    self.on_ground = True
                    self.coyote = 10
                else:
                    self.y = p.bottom + self.h/2
                    self.vy = 0
                self.hitbox.y = self.y - self.h/2

        # state & animation
        if self.attacking:
            self.state = 'air_attack' if not self.on_ground else 'attack'
        elif not self.on_ground:
            self.state = 'jump' if self.vy < 0 else 'fall'
        elif keyboard.left or keyboard.right:
            self.state = 'run'
        else:
            self.state = 'idle'

        imgs, fps = self.anim[self.state]
        self.timer += 1
        if self.timer >= 60//fps:
            self.timer = 0
            self.frame = (self.frame + 1) % len(imgs)
            self.image = imgs[self.frame]
        self.flip_x = (self.facing < 0)            # ← use flip_x

        # enemy collisions & SFX
        for e in enemies[:]:
            if self.hitbox.colliderect(e.hitbox):
                if self.attacking:
                    if audio_enabled: sounds.hit.play()
                    enemies.remove(e)
                else:
                    if audio_enabled: sounds.damage.play()
                    self.take_damage()

        if self.attacking:
            self.attack_timer -= 1
            if self.attack_timer <= 0:
                self.attacking = False
        if self.coyote > 0:
            self.coyote -= 1

        # fell off
        if self.y > HEIGHT + 100:
            set_game_state(GAME_OVER)

        # clamp X
        self.x = max(self.w/2, min(WIDTH - self.w/2, self.x))

    def jump(self):
        if audio_enabled: sounds.jump.play()
        if self.on_ground or self.coyote > 0:
            self.vy = -16
            self.on_ground = False
            self.coyote = 0
            self.state = 'jump'

    def attack(self):
        if audio_enabled: sounds.attack.play()
        if not self.attacking:
            self.attacking = True
            self.attack_timer = 10

    def take_damage(self):
        self.state = 'hit'
        self.attacking = False
        self.x, self.y, self.vx, self.vy = 10, 439, 0, 0
        self.timer = self.frame = 0

# —————————————————————————————————————————————————————————————————
class Enemy(Actor):
    def __init__(self, pos):
        super().__init__('enemy_walk_0', pos)
        self.w, self.h = 50, 70
        self.velocity_x = -1
        self.velocity_y = 0
        self.gravity = 0.5
        self.walk = [f'enemy_walk_{i}' for i in range(3)]
        self.timer = self.frame = 0
        self.fps = 3
        self.range = (pos[0]-100, pos[0]+100)
        # hitbox just under feet
        self.hitbox = Rect(0, 0, 30, 20)
        self.hitbox.midbottom = self.midbottom

    def update(self, platforms):
        # animation
        self.timer += 1
        if self.timer >= 60//self.fps:
            self.timer = 0
            self.frame = (self.frame + 1) % len(self.walk)
            self.image = self.walk[self.frame]
            self.flip_x = (self.velocity_x < 0)    # ← unify here

        # physics
        self.velocity_y = min(self.velocity_y + self.gravity, 10)
        self.y += self.velocity_y
        self.x += self.velocity_x

        # reposition hitbox
        self.hitbox.midbottom = self.midbottom

        # ground collision
        on_ground = False
        for p in platforms:
            if self.hitbox.colliderect(p) and self.velocity_y > 0:
                self.velocity_y = 0
                self.bottom = p.top
                self.hitbox.midbottom = self.midbottom
                on_ground = True
                break

        # patrol
        if on_ground and (self.x < self.range[0] or self.x > self.range[1]):
            self.velocity_x *= -1

# —————————————————————————————————————————————————————————————————
class Button:
    def __init__(self, txt, pos, act):
        self.txt, self.pos, self.act = txt, pos, act
        self.rect = Rect(pos[0]-80, pos[1]-20, 160, 40)
    def draw(self):
        screen.draw.filled_rect(self.rect, (70,130,200))
        screen.draw.text(self.txt, center=self.pos, fontsize=30, color='white')
    def check_click(self, p):
        if self.rect.collidepoint(p): self.act()

# —————————————————————————————————————————————————————————————————
# globals
player    = None
enemies   = []
platforms = []
flag_rect = None

buttons = [
    Button('Start',        (400,300), reload_level),
    Button('Music On/Off', (400,360), toggle_audio),
    Button('Quit',         (400,420), quit_game),
]
complete_buttons = [
    Button('Play Again', (400,360), reload_level),
    Button('Main Menu',  (400,420), lambda:set_game_state(MENU)),
]

def update():
    if game_state == PLAYING:
        player.update(platforms, enemies)
        for e in enemies:
            e.update(platforms)
        if not enemies and player.hitbox.colliderect(flag_rect):
            set_game_state(LEVEL_COMPLETE)

def draw():
    screen.clear()
    if game_state == MENU:
        screen.fill('black')
        screen.draw.text('PLATFORM ADVENTURE', center=(400,200), fontsize=60, color='white')
        for b in buttons: b.draw()

    elif game_state == PLAYING:
        screen.fill((135,206,235))
        for p in platforms: screen.draw.filled_rect(p, 'saddlebrown')
        screen.draw.filled_rect(flag_rect, 'red')
        player.draw()
        for e in enemies: e.draw()
        screen.draw.text(f'Enemies left: {len(enemies)}', topleft=(10,10), fontsize=30, color='white')

    elif game_state == LEVEL_COMPLETE:
        screen.fill('darkgreen')
        screen.draw.text('CONGRATULATIONS!', center=(400,200), fontsize=70, color='gold')
        screen.draw.text('You completed the level', center=(400,300), fontsize=40, color='white')
        for b in complete_buttons: b.draw()

    else:
        screen.fill('darkred')
        screen.draw.text('GAME OVER', center=(400,200), fontsize=70, color='white')
        for b in complete_buttons: b.draw()

def on_key_down(key):
    if game_state == PLAYING:
        if key == keys.SPACE: player.jump()
        elif key == keys.Z:   player.attack()

def on_mouse_down(pos):
    grp = buttons if game_state == MENU else complete_buttons
    if game_state in (MENU, LEVEL_COMPLETE, GAME_OVER):
        for b in grp: b.check_click(pos)

# start on menu
set_game_state(MENU)
pgzrun.go()
