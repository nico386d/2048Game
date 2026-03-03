# main.py
import sys
import random
import pygame

from game_engine import (
    SIZE, new_grid, add_random_tile, can_move,
    apply_move
)
from ai_player import AIConfig, best_move

# ---------- UI / Layout ----------
TILE_SIZE = 110
PADDING = 14

SIDE_PANEL_WIDTH = 260  # wider window
PANEL_BG = (235, 229, 221)

HEADER_PAD_TOP = 16
HEADER_GAP = 10
HELP_H = 28

FPS = 60

BG_COLOR = (250, 248, 239)
BOARD_BG = (187, 173, 160)
EMPTY_COLOR = (205, 193, 180)
TEXT_DARK = (119, 110, 101)
TEXT_LIGHT = (249, 246, 242)

TILE_COLORS = {
    2: (238, 228, 218),
    4: (237, 224, 200),
    8: (242, 177, 121),
    16: (245, 149, 99),
    32: (246, 124, 95),
    64: (246, 94, 59),
    128: (237, 207, 114),
    256: (237, 204, 97),
    512: (237, 200, 80),
    1024: (237, 197, 63),
    2048: (237, 194, 46),
}


def tile_color(v: int):
    return TILE_COLORS.get(v, (60, 58, 50))


def tile_text_color(v: int):
    return TEXT_DARK if v in (2, 4) else TEXT_LIGHT


def rounded_rect(surface, color, rect, radius=10):
    pygame.draw.rect(surface, color, rect, border_radius=radius)


def draw_text(surface, text, font, color, rect, center=True):
    img = font.render(text, True, color)
    if center:
        surface.blit(img, img.get_rect(center=rect.center))
    else:
        surface.blit(img, rect.topleft)


def compute_layout():
    # Header: score row + help row + gaps (spacing fixed)
    box_h = 64
    header_h = HEADER_PAD_TOP + box_h + HEADER_GAP + HELP_H + HEADER_GAP

    board_y = header_h
    board_h = PADDING + SIZE * (TILE_SIZE + PADDING)
    window_h = board_y + board_h

    board_w = PADDING + SIZE * (TILE_SIZE + PADDING)
    window_w = board_w + SIDE_PANEL_WIDTH

    return board_y, board_h, board_w, window_w, window_h


# ---------- Simple Dropdown ----------
class Dropdown:
    def __init__(self, x, y, w, h, options, initial, font, label=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.options = options
        self.value = initial
        self.open = False
        self.font = font
        self.label = label

    def handle_mouse(self, pos):
        mx, my = pos
        if self.rect.collidepoint(mx, my):
            self.open = not self.open
            return True, None

        if self.open:
            for i, opt in enumerate(self.options):
                opt_rect = pygame.Rect(self.rect.x, self.rect.y + self.rect.height * (i + 1),
                                       self.rect.w, self.rect.h)
                if opt_rect.collidepoint(mx, my):
                    self.value = opt
                    self.open = False
                    return True, opt

            # click outside closes
            self.open = False
            return True, None

        return False, None

    def draw(self, screen):
        # main box
        rounded_rect(screen, (180, 160, 140), self.rect, radius=8)
        txt = self.font.render(f"Depth: {self.value}", True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=self.rect.center))

        # arrow
        pygame.draw.polygon(
            screen,
            (255, 255, 255),
            [
                (self.rect.right - 18, self.rect.centery - 4),
                (self.rect.right - 8, self.rect.centery - 4),
                (self.rect.right - 13, self.rect.centery + 4),
            ],
        )

        # options
        if self.open:
            for i, opt in enumerate(self.options):
                opt_rect = pygame.Rect(self.rect.x, self.rect.y + self.rect.height * (i + 1),
                                       self.rect.w, self.rect.h)
                rounded_rect(screen, (205, 193, 180), opt_rect, radius=6)
                t = self.font.render(str(opt), True, TEXT_DARK)
                screen.blit(t, t.get_rect(center=opt_rect.center))


# ---------- Game ----------
def main():
    pygame.init()
    pygame.display.set_caption("2048 + Expectimax AI")

    board_y, board_h, board_w, window_w, window_h = compute_layout()
    screen = pygame.display.set_mode((window_w, window_h))
    clock = pygame.time.Clock()

    font_title = pygame.font.SysFont("arial", 48, bold=True)
    font_small = pygame.font.SysFont("arial", 20, bold=True)
    font_medium = pygame.font.SysFont("arial", 22, bold=True)
    font_tile = pygame.font.SysFont("arial", 44, bold=True)
    font_tile_small = pygame.font.SysFont("arial", 34, bold=True)

    # Best score persistence
    best = 0
    best_path = "best_2048.txt"
    try:
        with open(best_path, "r", encoding="utf-8") as f:
            best = int(f.read().strip() or "0")
    except Exception:
        best = 0

    rng = random.Random()
    grid = new_grid()
    grid = add_random_tile(grid, rng)
    grid = add_random_tile(grid, rng)
    score = 0

    undo_stack = []  # one-step undo: (grid, score)

    # AI
    cfg = AIConfig(depth=3)
    ai_mode = True      # True = AI controls
    autoplay = False    # True = AI moves continuously

    # Side panel geometry
    panel_x = board_w
    panel_rect = pygame.Rect(panel_x, 0, SIDE_PANEL_WIDTH, window_h)

    # Dropdown
    dd = Dropdown(
        x=panel_x + 30,
        y=150,
        w=SIDE_PANEL_WIDTH - 60,
        h=44,
        options=[1, 2, 3, 4, 5, 6],
        initial=cfg.depth,
        font=font_medium,
        label="Search Depth"
    )

    def push_undo():
        nonlocal undo_stack
        undo_stack = [(grid, score)]

    def pop_undo():
        nonlocal grid, score, undo_stack
        if undo_stack:
            grid, score = undo_stack.pop()

    def restart():
        nonlocal grid, score, undo_stack, autoplay
        grid = new_grid()
        grid = add_random_tile(grid, rng)
        grid = add_random_tile(grid, rng)
        score = 0
        undo_stack = []
        autoplay = False

    def do_player_move(m):
        nonlocal grid, score, best
        res = apply_move(grid, m)
        if not res.changed:
            return
        push_undo()
        grid = res.grid
        score += res.score_gain
        best = max(best, score)
        grid = add_random_tile(grid, rng)

    def ai_step():
        if not can_move(grid):
            return
        m = best_move(grid, cfg)
        do_player_move(m)

    def draw():
        screen.fill(BG_COLOR)

        # --- Header (title + score boxes) over the BOARD area only ---
        box_w = 140
        box_h = 64

        title_rect = pygame.Rect(PADDING, HEADER_PAD_TOP, 240, box_h)
        draw_text(screen, "2048", font_title, TEXT_DARK, title_rect, center=False)

        score_rect = pygame.Rect(board_w - PADDING - 2 * box_w - PADDING, HEADER_PAD_TOP, box_w, box_h)
        best_rect = pygame.Rect(board_w - PADDING - box_w, HEADER_PAD_TOP, box_w, box_h)

        for rect, label, val in [(score_rect, "SCORE", score), (best_rect, "BEST", best)]:
            rounded_rect(screen, (187, 173, 160), rect, radius=10)
            label_img = font_small.render(label, True, (238, 228, 218))
            val_img = font_small.render(str(val), True, (255, 255, 255))
            screen.blit(label_img, label_img.get_rect(center=(rect.centerx, rect.y + 18)))
            screen.blit(val_img, val_img.get_rect(center=(rect.centerx, rect.y + 44)))

        help_y = HEADER_PAD_TOP + box_h + HEADER_GAP
        help_rect = pygame.Rect(PADDING, help_y, board_w - 2 * PADDING, HELP_H)
        mode = "AI" if ai_mode else "HUMAN"
        ap = "ON" if autoplay else "OFF"
        help_text = f"Mode: {mode} | H toggle  SPACE step  A autoplay({ap})  U undo  R restart  ESC quit"
        draw_text(screen, help_text, font_small, TEXT_DARK, help_rect, center=False)

        # --- Board ---
        board_rect = pygame.Rect(PADDING, board_y, board_w - 2 * PADDING, board_h - PADDING)
        rounded_rect(screen, BOARD_BG, board_rect, radius=14)

        for r in range(SIZE):
            for c in range(SIZE):
                x = PADDING + c * (TILE_SIZE + PADDING)
                y = board_y + PADDING + r * (TILE_SIZE + PADDING)
                rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                v = grid[r][c]
                if v == 0:
                    rounded_rect(screen, EMPTY_COLOR, rect, radius=10)
                else:
                    rounded_rect(screen, tile_color(v), rect, radius=10)
                    txt = str(v)
                    f = font_tile if len(txt) <= 4 else font_tile_small
                    draw_text(screen, txt, f, tile_text_color(v), rect, center=True)

        # --- Side panel ---
        rounded_rect(screen, PANEL_BG, panel_rect, radius=0)

        # Panel title
        panel_title = pygame.Rect(panel_x + 30, 90, SIDE_PANEL_WIDTH - 60, 28)
        draw_text(screen, "Search Depth", font_medium, TEXT_DARK, panel_title, center=False)

        dd.draw(screen)

        # Small status
        s1 = pygame.Rect(panel_x + 30, 240, SIDE_PANEL_WIDTH - 60, 22)
        draw_text(screen, f"Autoplay: {ap}", font_small, TEXT_DARK, s1, center=False)
        s2 = pygame.Rect(panel_x + 30, 265, SIDE_PANEL_WIDTH - 60, 22)
        draw_text(screen, f"Control: {mode}", font_small, TEXT_DARK, s2, center=False)

        pygame.display.flip()

    running = True
    while running:
        clock.tick(FPS)

        # autoplay AI (stops automatically if stuck)
        if ai_mode and autoplay and can_move(grid):
            ai_step()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handled, new_val = dd.handle_mouse(pygame.mouse.get_pos())
                if handled and new_val is not None:
                    cfg.depth = int(new_val)

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_r:
                    restart()
                elif event.key == pygame.K_u:
                    pop_undo()
                elif event.key == pygame.K_h:
                    ai_mode = not ai_mode
                    autoplay = False
                elif event.key == pygame.K_a:
                    if ai_mode:
                        autoplay = not autoplay
                elif event.key == pygame.K_SPACE:
                    if ai_mode:
                        ai_step()

                # Human moves (only in human mode)
                if not ai_mode:
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        do_player_move("L")
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        do_player_move("R")
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        do_player_move("U")
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        do_player_move("D")

        draw()

    # Save best
    try:
        with open(best_path, "w", encoding="utf-8") as f:
            f.write(str(best))
    except Exception:
        pass

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()