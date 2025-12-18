import json
import os
import random
import sys
import math
from array import array
from collections import deque
from datetime import datetime

import pygame

# ---------------- Config ----------------
CELL = 40
HUD_H = 56
FPS = 60

# Maze size (odd numbers work best)
MAZE_W = 21
MAZE_H = 15

# Make mazes easier / more open
EXTRA_WALL_REMOVALS = 0.10   # remove ~10% interior walls if it increases connectivity
BRAID_DEADENDS_PROB = 0.80   # reduce dead ends
ROOMS_COUNT = 5              # carve a few 3x3 rooms

# Speed presets: (label, player_step_ms, ghost_step_ms)
SPEEDS = [
    ("Slow",      170, 200),
    ("Normal",    130, 160),
    ("Fast",      95,  125),
    ("SuperFast", 70,  95),
]

# Fruits (special pellets)
FRUIT_SCORES = {
    "cherry": 50,
    "strawberry": 100,
    "banana": 150,
    "watermelon": 200,
}
FRUIT_TYPES = list(FRUIT_SCORES.keys())

LEADERBOARD_FILE = "leaderboard.json"
LEADERBOARD_MAX = 20

# Auto-start demo if no name is entered on the menu
DEMO_IDLE_MS = 30000
DEMO_RESTART_MS = 30000  # demo restarts 30s after win/lose

# Colors
BLACK = (0, 0, 0)
BLUE = (30, 60, 220)
YELLOW = (250, 230, 40)
WHITE = (245, 245, 245)
RED = (220, 60, 60)
PINK = (255, 120, 200)
CYAN = (80, 220, 220)
ORANGE = (255, 160, 70)
GRAY = (150, 150, 150)
GREEN = (70, 230, 110)
MAGENTA = (255, 80, 220)
GOLD = (255, 215, 0)
SILVER = (200, 200, 220)
BRONZE = (205, 127, 50)

BALLOON_COLORS = [
    (255, 90, 90),
    (90, 255, 160),
    (90, 200, 255),
    (255, 220, 90),
    (255, 120, 220),
    (180, 120, 255),
]

# Directions
DIRS = {
    "LEFT":  (-1, 0),
    "RIGHT": (1, 0),
    "UP":    (0, -1),
    "DOWN":  (0, 1),
}
OPPOSITE = {"LEFT": "RIGHT", "RIGHT": "LEFT", "UP": "DOWN", "DOWN": "UP"}
DIR_ORDER = ["UP", "LEFT", "DOWN", "RIGHT"]  # for auto-mode BFS (stable)

# ---------------- Helpers ----------------
def quit_game():
    pygame.quit()
    sys.exit()

def is_wall(grid, x, y):
    if x < 0 or y < 0 or y >= len(grid) or x >= len(grid[0]):
        return True
    return grid[y][x] == "#"

def neighbors4(x, y):
    return [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]

# ---------------- Sound ----------------
def make_tone(frequency_hz, duration_ms=120, volume=0.25, sample_rate=44100):
    """Generate a sine-wave Sound. Returns None if mixer isn't available."""
    if not pygame.mixer.get_init():
        return None

    n_samples = int(sample_rate * (duration_ms / 1000.0))
    amp = int(32767 * max(0.0, min(volume, 1.0)))
    buf = array("h")

    fade = max(1, int(sample_rate * 0.005))
    for i in range(n_samples):
        t = i / sample_rate
        s = int(amp * math.sin(2.0 * math.pi * frequency_hz * t))
        if i < fade:
            s = int(s * (i / fade))
        elif i > n_samples - fade:
            s = int(s * ((n_samples - i) / fade))
        buf.append(s)

    return pygame.mixer.Sound(buffer=buf.tobytes())

def make_music_loop(duration_ms=3800, volume=0.10, sample_rate=44100):
    """Generate a simple looping leaderboard music (no external files)."""
    if not pygame.mixer.get_init():
        return None

    n_samples = int(sample_rate * (duration_ms / 1000.0))
    amp = int(32767 * max(0.0, min(volume, 1.0)))
    notes = [523.25, 659.25, 783.99, 659.25, 587.33, 698.46, 880.00, 698.46]
    step = max(1, n_samples // len(notes))

    buf = array("h")
    fade = max(1, int(sample_rate * 0.008))

    for i in range(n_samples):
        idx = min(len(notes) - 1, i // step)
        f = notes[idx]
        t0 = i / sample_rate
        s = math.sin(2.0 * math.pi * f * t0) + 0.35 * math.sin(2.0 * math.pi * (f * 2.0) * t0)
        sample = int(amp * 0.65 * s)

        if i < fade:
            sample = int(sample * (i / fade))
        elif i > n_samples - fade:
            sample = int(sample * ((n_samples - i) / fade))

        buf.append(sample)

    return pygame.mixer.Sound(buffer=buf.tobytes())

def load_sound_file(filename, volume=0.40):
    """
    Load a sound file from the same folder as this script.
    Example: put 'cheer.wav' and/or 'bang.wav' next to this .py.
    Returns None if missing/unloadable or if the mixer isn't initialized.
    """
    if not pygame.mixer.get_init():
        return None
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        p = os.path.join(base, filename)
        if not os.path.exists(p):
            return None
        snd = pygame.mixer.Sound(p)
        snd.set_volume(max(0.0, min(1.0, volume)))
        return snd
    except Exception:
        return None


def make_bang(duration_ms=420, volume=0.55, sample_rate=44100, seed=123):
    """
    Synthesize a short 'bang' explosion sound (noise burst + low boom), no external files.
    """
    if not pygame.mixer.get_init():
        return None

    rnd = random.Random(seed)
    n_samples = int(sample_rate * (duration_ms / 1000.0))
    amp = int(32767 * max(0.0, min(volume, 1.0)))
    buf = array("h")

    # One-pole lowpass for a "boom"
    lp = 0.0
    a = 0.02

    for i in range(n_samples):
        t0 = i / sample_rate
        # White noise burst
        n = (rnd.random() * 2.0 - 1.0)
        # Low boom (60 Hz) + filtered noise
        lp += a * (n - lp)
        boom = math.sin(2.0 * math.pi * 60.0 * t0) * (1.0 - i / max(1, n_samples - 1))
        s = 0.70 * lp + 0.55 * boom + 0.15 * n

        # Fast attack, exponential-ish decay
        env = 1.0 - (i / max(1, n_samples - 1))
        env = env * env * env
        sample = int(amp * env * s)

        buf.append(max(-32767, min(32767, sample)))

    return pygame.mixer.Sound(buffer=buf.tobytes())

def make_lose_sting(volume=0.55, sample_rate=44100, seed=99):
    """
    Synthesize a short 'lose' sting for when the chaser catches Pac-Man.
    Uses a descending tone + gritty noise. No external files required.
    """
    if not pygame.mixer.get_init():
        return None

    rnd = random.Random(seed)
    duration_s = 0.55
    n_samples = int(sample_rate * duration_s)
    amp = int(32767 * max(0.0, min(volume, 1.0)))
    buf = array("h")

    # Simple lowpass for thump
    lp = 0.0
    a = 0.04

    for i in range(n_samples):
        t = i / sample_rate
        x = i / max(1, n_samples - 1)

        # Descending tone (A3 -> A2)
        f = 220.0 * (2 ** (-1.0 * x))
        tone = math.sin(2.0 * math.pi * f * t) + 0.35 * math.sin(2.0 * math.pi * (2.0 * f) * t)

        # Gritty noise / "laugh" texture
        n = rnd.random() * 2.0 - 1.0
        lp += a * (n - lp)
        grit = (n - lp) * 0.8 + lp * 0.5

        # Envelope: fast attack, strong decay
        env = (1.0 - x)
        env = env * env * env

        s = env * (0.80 * tone + 0.55 * grit)
        # Soft clip
        s = max(-1.2, min(1.2, s)) / 1.2

        buf.append(int(amp * s))

    return pygame.mixer.Sound(buffer=buf.tobytes())


# ---------------- Leaderboard ----------------
def lb_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, LEADERBOARD_FILE)

def load_leaderboard():
    try:
        with open(lb_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []

def save_leaderboard(entries):
    try:
        with open(lb_path(), "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
    except Exception:
        pass

def add_score(name, score, speed_label, result):
    entries = load_leaderboard()
    entries.append({
        "name": (name[:16] if name else "Player"),
        "score": int(score),
        "speed": speed_label,
        "result": result,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    entries.sort(key=lambda e: e.get("score", 0), reverse=True)
    entries = entries[:LEADERBOARD_MAX]
    save_leaderboard(entries)
    return entries

# ---------------- Maze generation ----------------
def generate_maze(width, height):
    """Generate an easier maze with more openings."""
    if width % 2 == 0:
        width -= 1
    if height % 2 == 0:
        height -= 1
    width = max(width, 9)
    height = max(height, 9)

    grid = [["#" for _ in range(width)] for _ in range(height)]

    def carve(x, y):
        grid[y][x] = " "
        dirs = [(2, 0), (-2, 0), (0, 2), (0, -2)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if 1 <= nx < width - 1 and 1 <= ny < height - 1 and grid[ny][nx] == "#":
                grid[y + dy // 2][x + dx // 2] = " "
                carve(nx, ny)

    carve(1, 1)

    # Add loops
    loop_picks = (width * height) // 22
    for _ in range(loop_picks):
        x = random.randrange(1, width - 1)
        y = random.randrange(1, height - 1)
        if grid[y][x] == "#":
            open_neighbors = sum(1 for nx, ny in neighbors4(x, y) if grid[ny][nx] == " ")
            if open_neighbors >= 2:
                grid[y][x] = " "

    def is_open(x, y):
        return 0 <= x < width and 0 <= y < height and grid[y][x] == " "

    def open_degree(x, y):
        return sum(1 for nx, ny in neighbors4(x, y) if is_open(nx, ny))

    # Braid dead ends
    dead_ends = [(x, y) for y in range(1, height - 1) for x in range(1, width - 1)
                if is_open(x, y) and open_degree(x, y) == 1]
    random.shuffle(dead_ends)
    for x, y in dead_ends:
        if random.random() > BRAID_DEADENDS_PROB:
            continue
        candidates = []
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            wx, wy = x + dx, y + dy
            tx, ty = x + 2*dx, y + 2*dy
            if 1 <= tx < width - 1 and 1 <= ty < height - 1:
                if grid[wy][wx] == "#" and is_open(tx, ty):
                    candidates.append((wx, wy))
        if candidates:
            wx, wy = random.choice(candidates)
            grid[wy][wx] = " "

    # Rooms
    for _ in range(ROOMS_COUNT):
        cx = random.randrange(2, width - 2)
        cy = random.randrange(2, height - 2)
        if grid[cy][cx] == " ":
            for ry in range(cy - 1, cy + 2):
                for rx in range(cx - 1, cx + 2):
                    if 1 <= rx < width - 1 and 1 <= ry < height - 1:
                        grid[ry][rx] = " "

    # Extra random wall removals
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if grid[y][x] == "#" and random.random() < EXTRA_WALL_REMOVALS:
                open_neighbors = sum(1 for nx, ny in neighbors4(x, y) if grid[ny][nx] == " ")
                if open_neighbors >= 2:
                    grid[y][x] = " "

    start = (1, 1)

    # BFS distances
    def bfs_dist(sx, sy):
        dist = [[-1] * width for _ in range(height)]
        q = deque()
        dist[sy][sx] = 0
        q.append((sx, sy))
        while q:
            x, y = q.popleft()
            for nx, ny in neighbors4(x, y):
                if 0 <= nx < width and 0 <= ny < height and dist[ny][nx] == -1 and grid[ny][nx] == " ":
                    dist[ny][nx] = dist[y][x] + 1
                    q.append((nx, ny))
        return dist

    dist = bfs_dist(*start)

    # Choose farthest tile as exit, and a far-ish tile as ghost start
    open_tiles = []
    far = start
    far_d = -1
    for y in range(height):
        for x in range(width):
            if grid[y][x] == " " and dist[y][x] != -1:
                open_tiles.append((x, y))
                if dist[y][x] > far_d:
                    far_d = dist[y][x]
                    far = (x, y)

    if len(open_tiles) < (width * height) // 6:
        return generate_maze(width, height)

    exit_pos = far
    candidates = [t for t in open_tiles if t != start and t != exit_pos and dist[t[1]][t[0]] >= max(6, far_d // 2)]
    ghost_start = random.choice(candidates) if candidates else open_tiles[-1]

    # Pellets: all open tiles except start, ghost, exit and near-start padding
    blocked = {start, ghost_start, exit_pos}
    sx, sy = start
    for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
        blocked.add((sx + dx, sy + dy))

    pellets = {t for t in open_tiles if t not in blocked}
    if len(pellets) < 10:
        pellets = {t for t in open_tiles if t not in {start, ghost_start, exit_pos}}

    return ["".join(row) for row in grid], start, ghost_start, exit_pos, pellets

# ---------------- Auto mode pathfinding ----------------
def bfs_first_move(grid, start, targets, blocked=None):
    """Return the first direction along a shortest path to the nearest target."""
    if not targets:
        return None
    sx, sy = start
    if (sx, sy) in targets:
        return None

    q = deque([(sx, sy)])
    prev = {(sx, sy): None}  # (x,y)->(px,py,dir)

    while q:
        x, y = q.popleft()
        for d in DIR_ORDER:
            dx, dy = DIRS[d]
            nx, ny = x + dx, y + dy
            if ((blocked(nx, ny) if blocked else is_wall(grid, nx, ny))) or (nx, ny) in prev:
                continue
            prev[(nx, ny)] = (x, y, d)
            if (nx, ny) in targets:
                cur = (nx, ny)
                while prev[cur] is not None:
                    px, py, dir_used = prev[cur]
                    if (px, py) == (sx, sy):
                        return dir_used
                    cur = (px, py)
                return None
            q.append((nx, ny))
    return None

# ---------------- Entities ----------------
class Ghost:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.dir = random.choice(list(DIRS.keys()))

    def step(self, grid, blocked=None):
        options = []
        for d, (dx, dy) in DIRS.items():
            nx, ny = self.x + dx, self.y + dy
            if not ((blocked(nx, ny) if blocked else is_wall(grid, nx, ny))):
                options.append(d)
        if not options:
            return

        if len(options) > 1 and OPPOSITE.get(self.dir) in options:
            options.remove(OPPOSITE[self.dir])

        chosen = self.dir if (self.dir in options and random.random() < 0.60) else random.choice(options)
        dx, dy = DIRS[chosen]
        self.x += dx
        self.y += dy
        self.dir = chosen

def pacman_dir_angle(dir_name):
    if dir_name == "RIGHT":
        return 0.0
    if dir_name == "LEFT":
        return math.pi
    if dir_name == "UP":
        return -math.pi / 2
    return math.pi / 2

def draw_pacman(surface, center, radius, dir_name, mouth_open_amount):
    pygame.draw.circle(surface, YELLOW, center, radius)

    # Eyes (simple cartoon eyes that face the movement direction)
    cx, cy = center
    ang = pacman_dir_angle(dir_name)
    ca = math.cos(ang)
    sa = math.sin(ang)

    def rot(local_x, local_y):
        return (local_x * ca - local_y * sa, local_x * sa + local_y * ca)

    # Two eyes positioned slightly forward and above the center (in local +X facing RIGHT)
    eye_positions_local = [
        (radius * 0.06, -radius * 0.34),
        (radius * 0.30, -radius * 0.24),
    ]
    eye_r = max(5, int(radius * 0.22))
    pupil_r = max(2, int(radius * 0.09))
    # Pupils look forward
    look_dx = math.cos(ang) * radius * 0.08
    look_dy = math.sin(ang) * radius * 0.08

    for ex_l, ey_l in eye_positions_local:
        rx, ry = rot(ex_l, ey_l)
        ex = int(cx + rx)
        ey = int(cy + ry)
        pygame.draw.circle(surface, WHITE, (ex, ey), eye_r)
        pygame.draw.circle(surface, BLACK, (int(ex + look_dx), int(ey + look_dy)), pupil_r)

    min_span = math.radians(10)
    max_span = math.radians(70)
    span = min_span + (max_span - min_span) * max(0.0, min(mouth_open_amount, 1.0))
    a0 = pacman_dir_angle(dir_name) - span / 2
    a1 = pacman_dir_angle(dir_name) + span / 2

    points = [center]
    steps = 18
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * (i / steps)
        px = center[0] + int(radius * math.cos(a))
        py = center[1] + int(radius * math.sin(a))
        points.append((px, py))
    pygame.draw.polygon(surface, BLACK, points)


def draw_fruit(surface, center, size, fruit_type):
    """Draw a tiny cherry or strawberry at a pellet cell center."""
    cx, cy = center
    s = max(6, int(size))

    if fruit_type == "cherry":
        r = max(3, s // 3)
        # two cherries
        left = (cx - r, cy + r // 2)
        right = (cx + r, cy + r // 2)
        pygame.draw.circle(surface, (200, 30, 30), left, r)
        pygame.draw.circle(surface, (200, 30, 30), right, r)
        pygame.draw.circle(surface, (255, 210, 210), (left[0] - 1, left[1] - 1), max(1, r // 3))
        pygame.draw.circle(surface, (255, 210, 210), (right[0] - 1, right[1] - 1), max(1, r // 3))
        # stems
        stem_top = (cx, cy - r)
        pygame.draw.line(surface, (40, 170, 60), stem_top, (left[0], left[1] - r), 2)
        pygame.draw.line(surface, (40, 170, 60), stem_top, (right[0], right[1] - r), 2)
        # leaf
        pygame.draw.ellipse(surface, (40, 190, 70), (cx - r // 2, cy - r - r // 2, r + 4, r))
        return

    if fruit_type == "banana":
        # curved banana
        w = int(s * 1.25)
        h = int(s * 0.65)
        rect = pygame.Rect(0, 0, w, h)
        rect.center = (cx, cy + 1)
        pygame.draw.arc(surface, (255, 230, 60), rect, math.radians(200), math.radians(340), 6)
        pygame.draw.arc(surface, (210, 170, 30), rect.inflate(-4, -4), math.radians(200), math.radians(340), 3)
        # tips
        pygame.draw.circle(surface, (90, 70, 20), (rect.left + 6, rect.centery + 2), 2)
        pygame.draw.circle(surface, (90, 70, 20), (rect.right - 6, rect.centery), 2)
        return

    if fruit_type == "watermelon":
        # watermelon slice
        r = max(6, int(s * 0.70))
        pygame.draw.circle(surface, (40, 170, 60), (cx, cy), r)  # rind
        pygame.draw.circle(surface, (230, 60, 80), (cx, cy), max(3, r - 4))  # flesh
        # seeds
        for dx, dy in [(-0.20, 0.05), (-0.05, 0.15), (0.10, 0.06), (0.22, 0.16), (0.06, -0.05)]:
            pygame.draw.circle(surface, (30, 30, 30), (int(cx + dx * r), int(cy + dy * r)), 2)
        return

    # strawberry (default)
    w = s
    h = int(s * 1.2)
    body = pygame.Rect(0, 0, w, h)
    body.center = (cx, cy + 1)

    # body: rounded triangle-ish
    pygame.draw.ellipse(surface, (210, 40, 50), body)
    tip = (cx, body.bottom)
    left = (body.left + 1, cy)
    right = (body.right - 1, cy)
    pygame.draw.polygon(surface, (210, 40, 50), [left, right, tip])

    # seeds
    for dx, dy in [(-0.18, -0.10), (0.0, -0.12), (0.18, -0.08),
                   (-0.10, 0.08), (0.10, 0.10), (0.0, 0.02)]:
        pygame.draw.circle(surface, (240, 220, 90),
                           (int(cx + dx * w), int(cy + dy * h)), 1)

    # leaf
    leaf_w = int(w * 0.75)
    leaf_h = int(h * 0.35)
    leaf = pygame.Rect(0, 0, leaf_w, leaf_h)
    leaf.center = (cx, body.top + leaf_h // 3)
    pygame.draw.ellipse(surface, (40, 170, 60), leaf)
    pygame.draw.line(surface, (30, 130, 50), (leaf.left + 2, leaf.centery), (leaf.right - 2, leaf.centery), 2)


def rotate_point(x, y, ang):
    ca = math.cos(ang)
    sa = math.sin(ang)
    return (x * ca - y * sa, x * sa + y * ca)

def draw_ghost(surface, center, radius, dir_name, mouth_open_amount, color):
    """
    Chaser with angry eyes + Pac-Man-like mouth with sharp teeth.
    Eyes/mouth face movement direction. Tail is a wiggly "comet" trail behind.
    """
    cx, cy = center
    ang = pacman_dir_angle(dir_name)
    tsec = pygame.time.get_ticks() / 1000.0

    # --- Tail: wiggly blob trail behind the body (very visible) ---
    # Tail direction is opposite movement
    back_dx = -math.cos(ang)
    back_dy = -math.sin(ang)
    perp_dx = -math.sin(ang)
    perp_dy =  math.cos(ang)

    tail_len = radius * 2.8
    n_blobs = 8

    # darker tail color
    tr = max(0, int(color[0] * 0.75))
    tg = max(0, int(color[1] * 0.55))
    tb = max(0, int(color[2] * 0.55))
    tail_color = (tr, tg, tb)

    for k in range(n_blobs):
        frac = k / (n_blobs - 1)
        dist = radius * 0.55 + frac * tail_len

        # Wiggle sideways, decreasing toward the tip
        wig = math.sin(tsec * 8.0 + frac * 5.0 + (cx + cy) * 0.004) * (radius * 0.40) * (1.0 - frac)

        x = cx + back_dx * dist + perp_dx * wig
        y = cy + back_dy * dist + perp_dy * wig

        rr = int(radius * (0.55 * (1.0 - frac) + 0.18))
        pygame.draw.circle(surface, (10, 10, 10), (int(x), int(y)), rr + 2)     # outline
        pygame.draw.circle(surface, tail_color, (int(x), int(y)), rr)

    # --- Body ---
    pygame.draw.circle(surface, color, center, radius)

    # --- Mouth wedge (evil Pac-Man) ---
    min_span = math.radians(14)
    max_span = math.radians(80)
    span = min_span + (max_span - min_span) * max(0.0, min(mouth_open_amount, 1.0))
    a0 = ang - span / 2
    a1 = ang + span / 2

    points = [center]
    steps = 18
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * (i / steps)
        px = cx + int(radius * math.cos(a))
        py = cy + int(radius * math.sin(a))
        points.append((px, py))
    pygame.draw.polygon(surface, BLACK, points)

    # Teeth along the mouth edge
    teeth_n = 7
    inward = max(6, int(radius * 0.35))
    for i in range(teeth_n):
        ta0 = a0 + (a1 - a0) * (i / teeth_n)
        ta1 = a0 + (a1 - a0) * ((i + 1) / teeth_n)
        tm = (ta0 + ta1) / 2

        p0 = (cx + int(radius * math.cos(ta0)), cy + int(radius * math.sin(ta0)))
        p1 = (cx + int(radius * math.cos(ta1)), cy + int(radius * math.sin(ta1)))
        tip = (cx + int((radius - inward) * math.cos(tm)), cy + int((radius - inward) * math.sin(tm)))
        pygame.draw.polygon(surface, WHITE, [p0, tip, p1])

    # --- Eyes (rotate with direction) ---
    eye_dx = radius * 0.28
    eye_dy = -radius * 0.20
    eye_w = max(6, int(radius * 0.22))
    eye_h = max(6, int(radius * 0.26))
    pupil_r = max(2, int(radius * 0.075))

    # pupil looks forward
    look_dx = math.cos(ang) * radius * 0.12
    look_dy = math.sin(ang) * radius * 0.12

    for side in (-1, 1):
        lx = side * eye_dx
        ly = eye_dy
        rx, ry = rotate_point(lx, ly, ang)

        ex = int(cx + rx)
        ey = int(cy + ry)

        eye_rect = pygame.Rect(0, 0, eye_w, eye_h)
        eye_rect.center = (ex, ey)
        pygame.draw.ellipse(surface, WHITE, eye_rect)

        inward_eye = -side * radius * 0.03
        ix, iy = rotate_point(inward_eye, 0.0, ang)
        pygame.draw.circle(surface, (10, 10, 10), (int(ex + look_dx + ix), int(ey + look_dy + iy)), pupil_r)

        # Eyebrows: slant toward center, rotate with direction
        brow_len = eye_w + 8
        brow_y = -eye_h // 2 - 3
        tilt = -1 if side == -1 else 1

        b0l = (lx - brow_len * 0.55, ly + brow_y - tilt * 3)
        b1l = (lx + brow_len * 0.55, ly + brow_y + tilt * 3)
        b0x, b0y = rotate_point(b0l[0], b0l[1], ang)
        b1x, b1y = rotate_point(b1l[0], b1l[1], ang)
        pygame.draw.line(surface, (20, 20, 20), (int(cx + b0x), int(cy + b0y)), (int(cx + b1x), int(cy + b1y)), 3)

# ---------------- UI helpers ----------------
def draw_text_center(screen, text, font, y, color=WHITE):
    surf = font.render(text, True, color)
    screen.blit(surf, (screen.get_width() // 2 - surf.get_width() // 2, y))
    return surf.get_height()

def draw_rainbow_text(screen, text, font, center_x, y, tick, letter_spacing=2):
    """Draw text with per-letter cycling colors."""
    palette = [RED, ORANGE, YELLOW, GREEN, CYAN, BLUE, MAGENTA]
    widths = [font.size(ch)[0] for ch in text]
    total_w = sum(widths) + letter_spacing * (len(text) - 1)
    x = center_x - total_w // 2
    shift = (tick // 6)
    for i, ch in enumerate(text):
        c = palette[(i + shift) % len(palette)]
        surf = font.render(ch, True, c)
        screen.blit(surf, (x, y))
        x += widths[i] + letter_spacing

def hsv_to_rgb(h, s, v):
    """Convert HSV (0..1) to RGB tuple (0..255) for cycling rainbow colors."""
    h = h % 1.0
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    i = i % 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return (int(r * 255), int(g * 255), int(b * 255))

def draw_button(screen, rect, text, font, *, hovered=False):
    bg = (55, 55, 55) if not hovered else (85, 85, 85)
    pygame.draw.rect(screen, bg, rect, border_radius=10)
    pygame.draw.rect(screen, (130, 130, 130), rect, width=2, border_radius=10)
    label = font.render(text, True, WHITE)
    screen.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))

def draw_balloon(screen, x, y, radius, color):
    pygame.draw.circle(screen, color, (int(x), int(y)), radius)
    pygame.draw.circle(screen, (255, 255, 255), (int(x - radius * 0.25), int(y - radius * 0.25)), max(2, radius // 4))
    pygame.draw.circle(screen, (40, 40, 40), (int(x), int(y + radius - 2)), max(1, radius // 6))
    pygame.draw.line(screen, (220, 220, 220), (int(x), int(y + radius)), (int(x), int(y + radius + radius * 2)), 1)

# ---------------- Main ----------------
def main():
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.init()
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
    except pygame.error:
        pass

    screen = pygame.display.set_mode((MAZE_W * CELL, MAZE_H * CELL + HUD_H))
    pygame.display.set_caption("Mini Pac-Man (Python) - Auto/Manual")
    clock = pygame.time.Clock()

    font = pygame.font.SysFont(None, 30)
    big_font = pygame.font.SysFont(None, 66)
    title_font = pygame.font.SysFont(None, 74)
    lb_font = pygame.font.SysFont("consolas", 28) or font

    subtitle_font = pygame.font.SysFont("consolas", 24, bold=True) or font
    info_font = pygame.font.SysFont("consolas", 20) or font
    # SFX
    sfx_pellet = make_tone(980, 70, 0.24)

    # Fruit chomp (special pellet). Optional: put 'fruit.wav' next to this .py.
    sfx_fruit = load_sound_file("fruit.wav", volume=0.60)
    if sfx_fruit is None:
        sfx_fruit = make_tone(880, 120, 0.40)
    sfx_chomp_a = make_tone(620, 55, 0.18)
    sfx_chomp_b = make_tone(520, 55, 0.18)
    sfx_win = make_tone(1250, 240, 0.25)
    sfx_die = make_tone(220, 450, 0.28)

    # Chaser win (Pac-Man caught). Optional: put 'lose.wav' next to this .py.
    sfx_lose = load_sound_file("lose.wav", volume=0.70)
    if sfx_lose is None:
        sfx_lose = make_lose_sting()


    # Explosion 'bang' for chaser when Pac-Man exits.
    # Optional: put 'bang.wav' next to this .py for a more realistic sound.
    sfx_bang = load_sound_file("bang.wav", volume=0.70)
    if sfx_bang is None:
        sfx_bang = make_bang()

    # Exit cheer/hurrah: external file (recommended). Put 'cheer.wav' next to this .py.
    sfx_cheer = load_sound_file("cheer.wav", volume=0.45)

    # Channels
    music_channel = None
    cheer_channel = None
    if pygame.mixer.get_init():
        try:
            pygame.mixer.set_num_channels(8)
            music_channel = pygame.mixer.Channel(1)  # leaderboard music
            cheer_channel = pygame.mixer.Channel(2)  # exit cheer loop
        except Exception:
            music_channel = None
            cheer_channel = None

    # Leaderboard music
    lb_music = make_music_loop()
    lb_music_playing = False

    # Exit cheer loop flag
    cheer_playing = False

    def stop_cheer():
        nonlocal cheer_playing
        if cheer_playing:
            try:
                if cheer_channel:
                    cheer_channel.stop()
                elif sfx_cheer:
                    sfx_cheer.stop()
            except Exception:
                pass
            cheer_playing = False

    def start_cheer():
        nonlocal cheer_playing
        if (not sfx_cheer) or cheer_playing:
            return
        try:
            if cheer_channel:
                cheer_channel.play(sfx_cheer, loops=-1)
            else:
                sfx_cheer.play(loops=-1)
            cheer_playing = True
        except Exception:
            cheer_playing = False

    def new_game_state(speed_idx):
        speed_label, step_ms, ghost_step_ms = SPEEDS[speed_idx]
        base_grid, start, ghost_start, exit_pos, pellets = generate_maze(MAZE_W, MAZE_H)

        px, py = start
        gx, gy = ghost_start
        ghosts = [Ghost(gx, gy, random.choice([RED, PINK, CYAN, ORANGE]))]

        # Assign some pellets as fruits (cherry/strawberry) for bonus points
        fruits = {}
        pellet_list = list(pellets)
        if pellet_list:
            # ~4% of pellets become fruits, minimum 4, maximum 14
            k = max(4, min(14, len(pellet_list) // 25))
            picks = random.sample(pellet_list, k=min(k, len(pellet_list)))
            for i, pos in enumerate(picks):
                # mix fruit types (more cherries, some strawberries, fewer bananas/watermelons)
                r = random.random()
                if r < 0.60:
                    ftype = "cherry"
                elif r < 0.85:
                    ftype = "strawberry"
                elif r < 0.95:
                    ftype = "banana"
                else:
                    ftype = "watermelon"
                fruits[pos] = ftype


        return {
            "base_grid": base_grid,
            "px": px, "py": py,
            "pellets": set(pellets),
            "fruits": dict(fruits),
            "score": 0,
            "game_over": False,
            "win": False,
            "move_dir": "RIGHT",
            "next_dir": "RIGHT",
            "ghosts": ghosts,
            "exit": exit_pos,
            "exit_open": False,
            "celebrating": False,
            "balloons": [],
            "confetti": [],
            "explosions": [],
            "ghosts_exploded": False,
            "bang_played": False,
            "last_step": pygame.time.get_ticks(),
            "last_ghost_step": pygame.time.get_ticks(),
            "mouth_phase": 0,
            "chomp_toggle": False,
            "STEP_MS": step_ms,
            "GHOST_STEP_MS": ghost_step_ms,
            "speed_label": speed_label,
            "auto_mode": False,
            "demo": False,
            "demo_ended": False,
            "demo_restart_at": 0,
            "turn_buffer_dir": None,
            "turn_buffer_until": 0,
        "popups": [],
        }

    def is_blocked_cell(grid, x, y):
        if is_wall(grid, x, y):
            return True
        # Locked exit: you can only enter it after all food is eaten.
        if (not game.get('exit_open', False)) and (x, y) == game.get('exit'):
            return True
        return False

    def can_move(grid, x, y, d):
        dx, dy = DIRS[d]
        return not is_blocked_cell(grid, x + dx, y + dy)

    def center_of_cell(x, y):
        return (x * CELL + CELL // 2, HUD_H + y * CELL + CELL // 2)

    # ---------------- Exit celebration particles ----------------
    def seed_balloons(game):
        ex, ey = game["exit"]
        cx, cy = center_of_cell(ex, ey)
        balloons = []
        for _ in range(12):
            balloons.append({
                "x": cx + random.uniform(-CELL * 1.2, CELL * 1.2),
                "y": cy + random.uniform(CELL * 0.4, CELL * 3.0),
                "vx": random.uniform(-18.0, 18.0),
                "vy": random.uniform(-55.0, -30.0),
                "r": random.randint(8, 14),
                "c": random.choice(BALLOON_COLORS),
                "phase": random.uniform(0.0, 6.28),
            })
        game["balloons"] = balloons

    def seed_confetti(game):
        ex, ey = game["exit"]
        cx, cy = center_of_cell(ex, ey)
        pieces = []
        for _ in range(55):
            ang = random.uniform(-math.pi * 0.95, -math.pi * 0.05)  # mostly upward
            spd = random.uniform(80.0, 160.0)
            vx = math.cos(ang) * spd * random.uniform(0.55, 1.0)
            vy = math.sin(ang) * spd
            pieces.append({
                "x": cx + random.uniform(-CELL * 0.6, CELL * 0.6),
                "y": cy + random.uniform(-CELL * 0.2, CELL * 0.6),
                "vx": vx,
                "vy": vy,
                "s": random.randint(3, 6),
                "c": random.choice(BALLOON_COLORS),
                "spin": random.uniform(-8.0, 8.0),
                "a": random.uniform(0.0, 6.28),
            })
        game["confetti"] = pieces

    def update_balloons(game, dt):
        if not game["exit_open"] or not game["balloons"]:
            return
        ex, ey = game["exit"]
        cx, cy = center_of_cell(ex, ey)

        for b in game["balloons"]:
            b["phase"] += dt * 1.6
            sway = math.sin(b["phase"]) * 12.0
            b["x"] += (b["vx"] + sway) * dt
            b["y"] += b["vy"] * dt

            if b["y"] < HUD_H - 40:
                b["y"] = cy + random.uniform(CELL * 1.0, CELL * 3.2)
                b["x"] = cx + random.uniform(-CELL * 1.3, CELL * 1.3)
                b["vx"] = random.uniform(-18.0, 18.0)
                b["vy"] = random.uniform(-55.0, -30.0)
                b["r"] = random.randint(8, 14)
                b["c"] = random.choice(BALLOON_COLORS)

    def update_confetti(game, dt):
        if not game["exit_open"] or not game["confetti"]:
            return
        ex, ey = game["exit"]
        cx, cy = center_of_cell(ex, ey)

        for p in game["confetti"]:
            p["a"] += p["spin"] * dt
            p["vx"] += math.sin(p["a"]) * 4.0 * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt

            if p["y"] < HUD_H - 30 or p["x"] < -40 or p["x"] > screen.get_width() + 40:
                ang = random.uniform(-math.pi * 0.95, -math.pi * 0.05)
                spd = random.uniform(80.0, 160.0)
                p["vx"] = math.cos(ang) * spd * random.uniform(0.55, 1.0)
                p["vy"] = math.sin(ang) * spd
                p["x"] = cx + random.uniform(-CELL * 0.6, CELL * 0.6)
                p["y"] = cy + random.uniform(-CELL * 0.2, CELL * 0.8)
                p["s"] = random.randint(3, 6)
                p["c"] = random.choice(BALLOON_COLORS)
                p["spin"] = random.uniform(-8.0, 8.0)
                p["a"] = random.uniform(0.0, 6.28)


    def seed_explosions(game):
        """Create explosion particles at each ghost location."""
        parts = []
        for g in game.get("ghosts", []):
            cx, cy = center_of_cell(g.x, g.y)
            for _ in range(65):
                ang = random.uniform(0.0, math.tau)
                spd = random.uniform(120.0, 260.0)
                parts.append({
                    "x": float(cx),
                    "y": float(cy),
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd,
                    "life": random.uniform(0.35, 0.75),
                    "r": random.randint(2, 5),
                    "c": random.choice([(255, 70, 70), (255, 120, 60), (255, 200, 80), (255, 255, 255)]),
                })
        game["explosions"] = parts


    # ---------------- Score popups (fruit bonus) ----------------
    def add_score_popup(cell_xy, points, fruit_type):
        """Create a floating +points popup above a cell."""
        x, y = cell_xy
        cx, cy = center_of_cell(x, y)

        # Fruit-themed colors
        col = WHITE
        if fruit_type == "cherry":
            col = (255, 90, 90)
        elif fruit_type == "strawberry":
            col = (255, 120, 200)
        elif fruit_type == "banana":
            col = (255, 230, 60)
        elif fruit_type == "watermelon":
            col = (90, 255, 160)

        game.setdefault("popups", []).append({
            "x": float(cx),
            "y": float(cy - 10),
            "vy": -55.0,
            "life": 0.85,
            "max_life": 0.85,
            "text": f"+{int(points)}",
            "c": col,
        })

    def update_popups(game, dt):
        pops = game.get("popups", [])
        if not pops:
            return
        alive = []
        for p in pops:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            p["y"] += p["vy"] * dt
            alive.append(p)
        game["popups"] = alive

    def draw_popups(game):
        pops = game.get("popups", [])
        if not pops:
            return
        for p in pops:
            # fade out
            a = max(0.0, min(1.0, p["life"] / max(0.001, p.get("max_life", 1.0))))
            alpha = int(255 * a)
            surf = font.render(p["text"], True, p["c"])
            surf.set_alpha(alpha)
            screen.blit(surf, (int(p["x"] - surf.get_width() // 2), int(p["y"] - surf.get_height() // 2)))


    def update_explosions(game, dt):
        parts = game.get("explosions", [])
        if not parts:
            return
        g = 520.0  # gravity-ish pull
        drag = 0.92
        alive = []
        for p in parts:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            p["vx"] *= (drag ** (dt * 60.0))
            p["vy"] = p["vy"] * (drag ** (dt * 60.0)) + g * dt * 0.25
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            alive.append(p)
        game["explosions"] = alive

    def draw_explosions(game):
        parts = game.get("explosions", [])
        if not parts:
            return
        for p in parts:
            pygame.draw.circle(screen, p["c"], (int(p["x"]), int(p["y"])), p["r"])

    def draw_exit(game):
        ex, ey = game["exit"]
        cx = ex * CELL + CELL // 2
        cy = HUD_H + ey * CELL + CELL // 2
        t = pygame.time.get_ticks() / 1000.0

        # Confetti/graffiti pieces flying out
        if game["exit_open"] and game["confetti"]:
            for p in game["confetti"]:
                s = p["s"]
                rect = pygame.Rect(int(p["x"] - s // 2), int(p["y"] - s // 2), s, s)
                pygame.draw.rect(screen, p["c"], rect, border_radius=2)

        # Balloons
        if game["exit_open"] and game["balloons"]:
            for b in game["balloons"]:
                draw_balloon(screen, b["x"], b["y"], b["r"], b["c"])

        if not game["exit_open"]:
            # Locked exit: colorful + animated, but still blocked until food is gone
            palette = [RED, ORANGE, YELLOW, GREEN, CYAN, BLUE, MAGENTA] + BALLOON_COLORS
            idx = int((pygame.time.get_ticks() // 120) % len(palette))
            c1 = palette[idx]
            c2 = palette[(idx + 6) % len(palette)]

            pulse = 1.0 + 0.06 * math.sin(t * 4.2)
            w = int((CELL * 0.82) * pulse)
            h = int((CELL * 0.82) * pulse)
            r = pygame.Rect(0, 0, w, h)
            r.center = (cx, cy)

            # Base door
            pygame.draw.rect(screen, (45, 45, 55), r, border_radius=10)
            pygame.draw.rect(screen, c1, r, width=4, border_radius=10)
            pygame.draw.rect(screen, c2, r.inflate(-10, -10), width=2, border_radius=8)

            # Subtle "scan" line
            scan_y = r.top + int((math.sin(t * 3.0) * 0.5 + 0.5) * (r.height - 6)) + 3
            pygame.draw.line(screen, c1, (r.left + 6, scan_y), (r.right - 6, scan_y), 2)

            # Lock icon
            lock_w = max(10, CELL // 4)
            lock_h = max(12, CELL // 4 + 2)
            lock = pygame.Rect(0, 0, lock_w, lock_h)
            lock.center = (cx, cy + 2)
            pygame.draw.rect(screen, (15, 15, 18), lock, border_radius=4)
            pygame.draw.rect(screen, WHITE, lock, width=2, border_radius=4)

            shackle_r = max(6, lock_w // 2)
            shackle_center = (lock.centerx, lock.top + 1)
            pygame.draw.circle(screen, WHITE, shackle_center, shackle_r, width=2)
            pygame.draw.circle(screen, (45, 45, 55), shackle_center, shackle_r - 3)
            return

        # Open exit: animated rainbow portal
        palette = [RED, ORANGE, YELLOW, GREEN, CYAN, BLUE, MAGENTA] + BALLOON_COLORS
        idx = int((pygame.time.get_ticks() // 90) % len(palette))
        c1 = palette[idx]
        c2 = palette[(idx + 5) % len(palette)]
        c3 = palette[(idx + 11) % len(palette)]

        pulse = 1.0 + 0.10 * math.sin(t * 5.0)
        r_outer = int((CELL * 0.50) * pulse)
        r_mid = max(8, r_outer - 8)
        r_mid2 = max(6, r_outer - 16)
        r_inner = max(5, r_outer - 26)

        # Outer glow (bigger)
        pygame.draw.circle(screen, c1, (cx, cy), r_outer + 14)
        pygame.draw.circle(screen, BLACK, (cx, cy), r_outer + 9)

        # Portal body (more depth)
        pygame.draw.circle(screen, c2, (cx, cy), r_outer)
        pygame.draw.circle(screen, c3, (cx, cy), r_mid, width=5)
        pygame.draw.circle(screen, BLACK, (cx, cy), r_mid2, width=3)
        pygame.draw.circle(screen, (20, 20, 30), (cx, cy), r_inner)
        pygame.draw.circle(screen, (35, 35, 55), (cx, cy), max(3, r_inner - 8), width=2)

        # Rotating sparkles around the portal
        for i in range(14):
            ang = t * 2.6 + (i / 14.0) * math.tau
            rr = CELL * 0.70 + 6.0 * math.sin(t * 3.3 + i)
            sx = cx + int(math.cos(ang) * rr)
            sy = cy + int(math.sin(ang) * rr)
            col = palette[(idx + i) % len(palette)]
            pygame.draw.circle(screen, col, (sx, sy), 3)

    # -------- App states --------
    app_mode = "MENU"  # MENU | PLAY | RESULTS | LEADERBOARD
    name = ""
    speed_idx = 1  # Normal
    game = new_game_state(speed_idx)
    last_entries = load_leaderboard()
    lb_confetti = []
    menu_idle_start = pygame.time.get_ticks()

    quit_btn = pygame.Rect(screen.get_width() - 140, 12, 120, 34)

    while True:
        dt_ms = clock.tick(FPS)
        dt = dt_ms / 1000.0
        mouse_pos = pygame.mouse.get_pos()

        # --- Event handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                quit_game()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if app_mode == "LEADERBOARD":
                        app_mode = "MENU"
                        menu_idle_start = pygame.time.get_ticks()
                    else:
                        quit_game()
                    continue

                if app_mode == "MENU":
                    menu_idle_start = pygame.time.get_ticks()
                    if event.key == pygame.K_RETURN:
                        stop_cheer()
                        game = new_game_state(speed_idx)
                        game["demo"] = False
                        app_mode = "PLAY"
                    elif event.key == pygame.K_l:
                        last_entries = load_leaderboard()
                        app_mode = "LEADERBOARD"
                    elif event.key == pygame.K_LEFT:
                        speed_idx = (speed_idx - 1) % len(SPEEDS)
                    elif event.key == pygame.K_RIGHT:
                        speed_idx = (speed_idx + 1) % len(SPEEDS)
                    elif event.key == pygame.K_BACKSPACE:
                        name = name[:-1]
                    else:
                        ch = event.unicode
                        if ch and ch.isprintable() and ch not in "\r\n\t":
                            if len(name) < 16 and (ch.isalnum() or ch == " " or ch in "_-"):
                                name += ch

                elif app_mode == "LEADERBOARD":
                    if event.key in (pygame.K_m, pygame.K_RETURN, pygame.K_BACKSPACE, pygame.K_SPACE):
                        app_mode = "MENU"
                        menu_idle_start = pygame.time.get_ticks()

                elif app_mode == "RESULTS":
                    if event.key == pygame.K_RETURN:
                        app_mode = "LEADERBOARD"
                    elif event.key in (pygame.K_r, pygame.K_SPACE, pygame.K_n):
                        stop_cheer()
                        game = new_game_state(speed_idx)   # replay (same speed + name)
                        app_mode = "PLAY"
                    elif event.key in (pygame.K_m, pygame.K_BACKSPACE):
                        stop_cheer()
                        app_mode = "MENU"
                        menu_idle_start = pygame.time.get_ticks()

                elif app_mode == "PLAY":
                    # Demo mode: any key (except ESC) returns to menu so the user can start playing
                    if game.get("demo", False):
                        if event.key != pygame.K_ESCAPE:
                            stop_cheer()
                            app_mode = "MENU"
                            name = ""
                            menu_idle_start = pygame.time.get_ticks()
                            ch = event.unicode
                            if ch and ch.isprintable() and ch not in "\r\n\t":
                                if len(name) < 16 and (ch.isalnum() or ch == " " or ch in "_-"):
                                    name += ch
                            continue

                    if event.key == pygame.K_m:
                        stop_cheer()
                        app_mode = "MENU"
                        menu_idle_start = pygame.time.get_ticks()
                    elif event.key == pygame.K_a:
                        game["auto_mode"] = not game["auto_mode"]
                    elif not game["auto_mode"]:
                        if event.key == pygame.K_LEFT:
                            game["next_dir"] = "LEFT"
                            game["turn_buffer_dir"] = "LEFT"
                            game["turn_buffer_until"] = pygame.time.get_ticks() + 350
                        elif event.key == pygame.K_RIGHT:
                            game["next_dir"] = "RIGHT"
                            game["turn_buffer_dir"] = "RIGHT"
                            game["turn_buffer_until"] = pygame.time.get_ticks() + 350
                        elif event.key == pygame.K_UP:
                            game["next_dir"] = "UP"
                            game["turn_buffer_dir"] = "UP"
                            game["turn_buffer_until"] = pygame.time.get_ticks() + 350
                        elif event.key == pygame.K_DOWN:
                            game["next_dir"] = "DOWN"
                            game["turn_buffer_dir"] = "DOWN"
                            game["turn_buffer_until"] = pygame.time.get_ticks() + 350


            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if app_mode == "PLAY" and game.get("demo", False):
                    stop_cheer()
                    app_mode = "MENU"
                    name = ""
                    menu_idle_start = pygame.time.get_ticks()
                elif app_mode == "MENU" and quit_btn.collidepoint(event.pos):
                    quit_game()

        
        # --- Auto-start demo (attract mode) ---
        if app_mode == "MENU" and (name.strip() == ""):
            now_ticks = pygame.time.get_ticks()
            if now_ticks - menu_idle_start >= DEMO_IDLE_MS:
                stop_cheer()
                name = "Demo"
                game = new_game_state(speed_idx)
                game["auto_mode"] = True
                game["demo"] = True
                app_mode = "PLAY"

# --- Leaderboard music control ---
        if app_mode == "LEADERBOARD":
            if lb_music and (not lb_music_playing):
                try:
                    if music_channel:
                        music_channel.play(lb_music, loops=-1)
                    else:
                        lb_music.play(loops=-1)
                    lb_music_playing = True
                except Exception:
                    lb_music_playing = False
        else:
            if lb_music_playing:
                try:
                    if music_channel:
                        music_channel.stop()
                    else:
                        lb_music.stop()
                except Exception:
                    pass
                lb_music_playing = False
                try:
                    lb_confetti.clear()
                except Exception:
                    pass

        # --- Exit cheer control (continuous while exit is open) ---
        if app_mode in ("PLAY", "RESULTS") and game.get("celebrating", False):
            start_cheer()
        else:
            stop_cheer()

        # --- Particle updates ---
        update_balloons(game, dt)
        update_confetti(game, dt)
        update_explosions(game, dt)

        # --- Update PLAY ---
        if app_mode == "PLAY":
            now = pygame.time.get_ticks()

            # Demo timed restart check
            demo_frozen = False
            if game.get("demo", False) and game.get("demo_ended", False):
                demo_frozen = True
                if now >= int(game.get("demo_restart_at", 0)):
                    stop_cheer()
                    name = "Demo"
                    game = new_game_state(speed_idx)
                    game["auto_mode"] = True
                    game["demo"] = True
                    demo_frozen = False
                    app_mode = "PLAY"

            moved_this_tick = False
            grid = game["base_grid"]

            if (not demo_frozen) and (not game["game_over"]) and (not game["win"]):
                # Auto picks direction
                if game["auto_mode"]:
                    targets = {game["exit"]} if game["exit_open"] else set(game["pellets"])
                    choice = bfs_first_move(grid, (game["px"], game["py"]), targets, blocked=lambda x, y: is_blocked_cell(grid, x, y))
                    if choice and can_move(grid, game["px"], game["py"], choice):
                        game["next_dir"] = choice
                    else:
                        valids = [d for d in DIR_ORDER if can_move(grid, game["px"], game["py"], d)]
                        if valids:
                            game["next_dir"] = random.choice(valids)

                
                # Manual steering (poll keys so holding arrows works, similar to auto updating next_dir continuously)
                if not game["auto_mode"]:
                    keys = pygame.key.get_pressed()
                    if keys[pygame.K_LEFT]:
                        game["next_dir"] = "LEFT"
                    elif keys[pygame.K_RIGHT]:
                        game["next_dir"] = "RIGHT"
                    elif keys[pygame.K_UP]:
                        game["next_dir"] = "UP"
                    elif keys[pygame.K_DOWN]:
                        game["next_dir"] = "DOWN"
                    if game["next_dir"]:
                        game["turn_buffer_dir"] = game["next_dir"]
                        game["turn_buffer_until"] = pygame.time.get_ticks() + 350

# Player step
                if now - game["last_step"] >= game["STEP_MS"]:
                    game["last_step"] = now

                    desired_dir = game["next_dir"]
                    # Turning assist: keep a short buffer so quick taps still turn at the next opening.
                    if (not game["auto_mode"]) and pygame.time.get_ticks() <= game.get("turn_buffer_until", 0) and game.get("turn_buffer_dir"):
                        desired_dir = game["turn_buffer_dir"]
                    if can_move(grid, game["px"], game["py"], desired_dir):
                        game["move_dir"] = desired_dir
                        # Clear buffer once used
                        if desired_dir == game.get("turn_buffer_dir"):
                            game["turn_buffer_dir"] = None
                            game["turn_buffer_until"] = 0


                    if can_move(grid, game["px"], game["py"], game["move_dir"]):
                        dx, dy = DIRS[game["move_dir"]]
                        game["px"] += dx
                        game["py"] += dy
                        moved_this_tick = True

                    if moved_this_tick:
                        game["mouth_phase"] ^= 1
                        if sfx_chomp_a and sfx_chomp_b:
                            (sfx_chomp_b if game["chomp_toggle"] else sfx_chomp_a).play()
                            game["chomp_toggle"] = not game["chomp_toggle"]

                    pos = (game["px"], game["py"])
                    if pos in game["pellets"]:
                        game["pellets"].remove(pos)
                        ftype = game.get("fruits", {}).pop(pos, None)
                        points = FRUIT_SCORES.get(ftype, 10)
                        game["score"] += points
                        if ftype:
                            add_score_popup(pos, points, ftype)
                        if ftype:
                            if sfx_fruit:
                                sfx_fruit.play()
                        else:
                            if sfx_pellet:
                                sfx_pellet.play()

                    # Chomp reach assist: when only a few pellets remain, also eat the pellet directly in front
                    # (helps snag single/last pellets without pixel-perfect timing).
                    if len(game["pellets"]) <= 3 and moved_this_tick and game["mouth_phase"]:
                        dx, dy = DIRS[game["move_dir"]]
                        fpos = (game["px"] + dx, game["py"] + dy)
                        if fpos in game["pellets"] and (not is_wall(grid, fpos[0], fpos[1])):
                            game["pellets"].remove(fpos)
                            ftype = game.get("fruits", {}).pop(fpos, None)
                            points = FRUIT_SCORES.get(ftype, 10)
                            game["score"] += points
                            if ftype:
                                add_score_popup(fpos, points, ftype)
                            if ftype:
                                if sfx_fruit:
                                    sfx_fruit.play()
                            else:
                                if sfx_pellet:
                                    sfx_pellet.play()

                    # Open exit if all pellets cleared
                    if (not game["pellets"]) and (not game["exit_open"]):
                        game["exit_open"] = True

                    # Win by reaching the exit (only after open)
                    if game["exit_open"] and pos == game["exit"]:
                        # Celebrate only when Pac-Man actually exits
                        if not game.get("celebrating", False):
                            game["celebrating"] = True
                            seed_balloons(game)
                            seed_confetti(game)
                        # Make the chaser explode when Pac-Man exits
                        if not game.get("ghosts_exploded", False):
                            seed_explosions(game)
                            game["ghosts_exploded"] = True
                            if (not game.get("bang_played", False)) and sfx_bang:
                                try:
                                    sfx_bang.play()
                                except Exception:
                                    pass
                                game["bang_played"] = True
                        game["win"] = True
                        if sfx_win:
                            sfx_win.play()

                # Ghost step
                if now - game["last_ghost_step"] >= game["GHOST_STEP_MS"]:
                    game["last_ghost_step"] = now
                    for g in game["ghosts"]:
                        g.step(grid, blocked=lambda x, y: is_blocked_cell(grid, x, y))

                # Collision
                for g in game["ghosts"]:
                    if g.x == game["px"] and g.y == game["py"]:
                        game["game_over"] = True
                        if sfx_die:
                            sfx_die.play()
                        # Extra SFX when chaser wins
                        if sfx_lose:
                            try:
                                sfx_lose.play()
                            except Exception:
                                pass
                        if sfx_bang:
                            try:
                                sfx_bang.play()
                            except Exception:
                                pass
                        break

            if game["game_over"] or game["win"]:
                if game.get("demo", False):
                    # Demo: freeze on the outcome, then restart after a delay.
                    if not game.get("demo_ended", False):
                        game["demo_ended"] = True
                        game["demo_restart_at"] = pygame.time.get_ticks() + DEMO_RESTART_MS
                    # do not go to RESULTS / do not write leaderboard
                else:
                    result = "WIN" if game["win"] else "LOSE"
                    last_entries = add_score(name or "Player", game["score"], game["speed_label"], result)
                    app_mode = "RESULTS"

        # --- Draw ---
        screen.fill(BLACK)

        # HUD
        if app_mode in ("PLAY", "RESULTS"):
            pygame.draw.rect(screen, (18, 18, 18), pygame.Rect(0, 0, MAZE_W * CELL, HUD_H))
            if app_mode == "PLAY":
                exit_state = "OPEN" if game["exit_open"] else "LOCKED"
                mode_state = "AUTO" if game["auto_mode"] else "MANUAL"
                line1 = font.render(
                    f"Player: {name or 'Player'}   Score: {game['score']}   Speed: {game['speed_label']}   Mode: {mode_state}   Exit: {exit_state}",
                    True, WHITE
                )
                line2_text = "DEMO (Auto): Press any key/click to return to menu   ESC: Quit" if game.get("demo", False) else "A: Toggle AUTO/MANUAL   Arrows: Move (Manual)   M: Menu   ESC: Quit"
                line2 = font.render(
                    line2_text,
                    True, WHITE
                )
                screen.blit(line1, (12, 8))
                screen.blit(line2, (12, 32))
            else:
                hud_text = "ESC: Quit" if app_mode == "RESULTS" else "ESC: Quit    M: Back to Menu"
                hud = font.render(hud_text, True, WHITE)
                screen.blit(hud, (12, 14))

        # MENU
        if app_mode == "MENU":
            pygame.draw.rect(screen, (18, 18, 18), pygame.Rect(0, 0, screen.get_width(), HUD_H))
            screen.blit(font.render("ESC: Quit", True, WHITE), (12, 14))
            draw_button(screen, quit_btn, "Quit", font, hovered=quit_btn.collidepoint(mouse_pos))

            y = 90
            draw_text_center(screen, "PAC-MAN MINI", title_font, y, YELLOW)
            y += 90

            draw_text_center(screen, "Type your name:", font, y, WHITE)
            y += 36
            caret = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else " "
            draw_text_center(screen, f"[ {name}{caret} ]", big_font, y, WHITE)
            y += 84

            draw_text_center(screen, "Choose speed (Left/Right):", font, y, WHITE)
            y += 40
            parts = []
            for i, (lab, _, _) in enumerate(SPEEDS):
                parts.append(f"[{lab}]" if i == speed_idx else lab)
            draw_text_center(screen, "  |  ".join(parts), font, y, WHITE)
            y += 70

            draw_text_center(screen, "Enter: Start (new easier random maze)    L: Leaderboard", font, y, GRAY)
            y += 26
            draw_text_center(screen, "In-game: A toggles AUTO/MANUAL. (Manual uses arrow keys.)", font, y, GRAY)

        # PLAY / RESULTS board
        elif app_mode in ("PLAY", "RESULTS"):
            grid = game["base_grid"]

            def cell_center(x, y):
                return (x * CELL + CELL // 2, HUD_H + y * CELL + CELL // 2)

            # Walls
            for y0, row in enumerate(grid):
                for x0, ch in enumerate(row):
                    if ch == "#":
                        pygame.draw.rect(screen, BLUE, pygame.Rect(x0 * CELL, HUD_H + y0 * CELL, CELL, CELL))

            # Exit (with balloons + confetti)
            draw_exit(game)

            # Pellets / Fruits
            pellet_r = max(8, CELL // 7)
            pellet_col = (120, 220, 255)
            for (x0, y0) in game["pellets"]:
                ftype = game.get("fruits", {}).get((x0, y0))
                if ftype:
                    # fruits are bigger than pellets
                    draw_fruit(screen, cell_center(x0, y0), pellet_r * 4, ftype)
                else:
                    pygame.draw.circle(screen, pellet_col, cell_center(x0, y0), pellet_r)

            # Popups (+points for fruits)
            draw_popups(game)

            # Player
            pac_center = cell_center(game["px"], game["py"])
            pac_radius = CELL // 2 - 4
            mouth_amt = 0.90 if game["mouth_phase"] else 0.12
            draw_pacman(screen, pac_center, pac_radius, game["move_dir"], mouth_amt)

            # Explosions (when Pac-Man exits)
            draw_explosions(game)

            # Ghosts
            if not game.get("ghosts_exploded", False):
                ghost_mouth_amt = 0.92 if ((pygame.time.get_ticks() // 140) % 2 == 0) else 0.10
                reds = [(120, 10, 10), (160, 20, 20), (200, 30, 30), (240, 50, 50), (255, 80, 80)]
                tickr = (pygame.time.get_ticks() // 120)
                for gi, g in enumerate(game["ghosts"]):
                    ghost_color = reds[(tickr + gi) % len(reds)]
                    draw_ghost(screen, cell_center(g.x, g.y), CELL // 2 - 4, g.dir, ghost_mouth_amt, ghost_color)
            # Demo end overlay
            if game.get("demo", False) and game.get("demo_ended", False):
                remaining = max(0, int((game.get("demo_restart_at", 0) - pygame.time.get_ticks()) / 1000))
                msg = "DEMO: YOU WIN!" if game.get("win", False) else "DEMO: GAME OVER"
                draw_text_center(screen, msg, title_font, HUD_H + MAZE_H * CELL // 2 - 90, WHITE)
                draw_text_center(screen, f"Restarting in {remaining}s (press any key/click to exit demo)", font,
                                 HUD_H + MAZE_H * CELL // 2 - 30, GRAY)


            # Results overlay
            if app_mode == "RESULTS":
                msg = "YOU WIN!" if game["win"] else "GAME OVER"
                draw_text_center(screen, msg, title_font, HUD_H + MAZE_H * CELL // 2 - 90, WHITE)
                draw_text_center(screen, f"{name or 'Player'} scored {game['score']} on {game['speed_label']}", font,
                                 HUD_H + MAZE_H * CELL // 2 - 30, WHITE)
                draw_text_center(screen, "R/Space/N: Replay    M: Menu    Enter: Leaderboard    ESC: Quit", font,
                                 HUD_H + MAZE_H * CELL // 2 + 10, GRAY)

        
        # LEADERBOARD
        elif app_mode == "LEADERBOARD":
            # WORMGAME-style festive leaderboard: confetti + animated title + aligned columns
            W = screen.get_width()
            H = screen.get_height()
            t = pygame.time.get_ticks() / 1000.0

            # Init confetti once per entry into the leaderboard
            if not lb_confetti:
                for _ in range(140):
                    lb_confetti.append({
                        "x": random.uniform(0, W),
                        "y": random.uniform(0, H),
                        "vx": random.uniform(-0.25, 0.25),
                        "vy": random.uniform(0.8, 2.8),
                        "size": random.randint(2, 6),
                        "h": random.random(),
                    })

            # Background
            screen.fill((8, 8, 24))

            # Confetti (looping drift)
            for p in lb_confetti:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                if p["y"] > H + 10:
                    p["y"] = -10
                    p["x"] = random.uniform(0, W)
                    p["h"] = random.random()
                if p["x"] < -10:
                    p["x"] = W + 10
                if p["x"] > W + 10:
                    p["x"] = -10

                c = hsv_to_rgb((p["h"] + t * 0.10) % 1.0, 0.9, 1.0)
                pygame.draw.rect(
                    screen,
                    c,
                    pygame.Rect(int(p["x"]), int(p["y"]), p["size"], p["size"]),
                    border_radius=2,
                )

            # Title (color-cycling)
            title_color = hsv_to_rgb((t * 0.08) % 1.0, 0.7, 1.0)
            title_surf = title_font.render("LEADERBOARD", True, title_color)
            screen.blit(title_surf, title_surf.get_rect(center=(W // 2, 80)))

            subtitle_surf = subtitle_font.render("TOP 10 RUNS • BEST SCORES", True, (220, 220, 220))
            screen.blit(subtitle_surf, subtitle_surf.get_rect(center=(W // 2, 125)))

            # Table layout (center as a block so monospaced columns stay aligned)
            header_y = 170
            row_h = 34
            header_line = f"{'RK':>2}  {'PLAYER':<16}  {'SCORE':>6}  {'SPEED':<10}  {'RES':<4}"

            max_w = lb_font.size(header_line)[0]
            for idx, e in enumerate(last_entries[:10], start=1):
                nm = (e.get("name", "Player") or "Player")[:16]
                sc = int(e.get("score", 0))
                sp = (e.get("speed", "") or "")[:10]
                rs = (e.get("result", "") or "")[:4]
                line = f"{idx:>2}  {nm:<16}  {sc:>6}  {sp:<10}  {rs:<4}"
                max_w = max(max_w, lb_font.size(line)[0])

            table_x = max(20, (W - max_w) // 2)

            # Header
            header_surf = lb_font.render(header_line, True, WHITE)
            screen.blit(header_surf, (table_x, header_y))
            pygame.draw.line(
                screen,
                (220, 220, 220),
                (table_x, header_y + 30),
                (table_x + header_surf.get_width(), header_y + 30),
                2,
            )

            # Rows
            start_y = header_y + 44
            if not last_entries:
                msg = lb_font.render("No scores yet. Go play!", True, WHITE)
                screen.blit(msg, msg.get_rect(center=(W // 2, H // 2)))
            else:
                for idx, e in enumerate(last_entries[:10], start=1):
                    nm = (e.get("name", "Player") or "Player")[:16]
                    sc = int(e.get("score", 0))
                    sp = (e.get("speed", "") or "")[:10]
                    rs = (e.get("result", "") or "")[:4]
                    line = f"{idx:>2}  {nm:<16}  {sc:>6}  {sp:<10}  {rs:<4}"

                    # Each row cycles color with a slight phase offset
                    row_color = hsv_to_rgb((t * 0.12 + idx * 0.08) % 1.0, 0.95, 1.0)

                    # Give top 3 a little extra pop (slightly different hue/sat)
                    if idx == 1:
                        row_color = hsv_to_rgb((t * 0.10) % 1.0, 0.6, 1.0)
                    elif idx == 2:
                        row_color = hsv_to_rgb((t * 0.10 + 0.08) % 1.0, 0.5, 0.95)
                    elif idx == 3:
                        row_color = hsv_to_rgb((t * 0.10 + 0.16) % 1.0, 0.55, 0.90)

                    row_surf = lb_font.render(line, True, row_color)
                    screen.blit(row_surf, (table_x, start_y + (idx - 1) * row_h))

            info = info_font.render("Press Esc / Enter / Space / M to return", True, (200, 200, 200))
            screen.blit(info, info.get_rect(center=(W // 2, H - 40)))

        pygame.display.flip()

if __name__ == "__main__":
    main()
