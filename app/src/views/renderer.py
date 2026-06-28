# views/renderer.py
# ─────────────────────────────────────────────────────────────────────────────
# Two renderers:
#
#   Renderer        — rectangular maze.
#     FIX #2: Ultimate Challenge mode uses a dynamic camera (cam_x / cam_y)
#             so the large 41×41 map scrolls smoothly inside the fixed
#             900×700 window.  Other modes centre the whole maze statically.
#     FIX #3: lights_out flag triggers _draw_fog_mask() — a per-frame SRCALPHA
#             surface that blacks out everything except a smooth radial circle
#             around the player.  preview=True skips the mask so the player
#             can memorise the layout during the 3-second countdown.
#     FIX #6: A ⏸ PAUSE button is drawn on the HUD every frame; its Rect is
#             stored and exposed via pause_btn_rect() for hit-testing in Game.
#
#   CircularRenderer — polar/concentric maze.
#     FIX #1: Walls are drawn exactly where the maze data says they are;
#             visual openings correctly reflect the passages carved by DFS.
#             A legend is rendered at the bottom to orient the player.
#     FIX #6: Same ⏸ PAUSE button present.
# ─────────────────────────────────────────────────────────────────────────────

import pygame
import math
import pygame.gfxdraw

from core.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT,
    CELL_SIZE, ULT_CELL_SIZE,
    CIRCULAR_RING_WIDTH, MODE_ULTIMATE,
    BG_COLOR, WALL_COLOR, PATH_COLOR, PLAYER_COLOR, GOAL_COLOR,
    HUD_BG, HEART_COLOR, TEXT_COLOR, ACCENT, CORRECT_COLOR, WRONG_COLOR,
    CHECKPOINT_DOT, CARD_BG, DARK_GRAY, PAUSE_COLOR, WHITE, GRAY,
    LIGHTS_OUT_RADIUS_PX,
)


# ── utility ───────────────────────────────────────────────────────────────────

def _lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _font(size, bold=False):
    return pygame.font.SysFont("segoeui", size, bold=bold)


def _center_text(surf, text, fnt, color, cx, y):
    s = fnt.render(text, True, color)
    surf.blit(s, (cx - s.get_width() // 2, y))
    return s.get_height()


def _draw_rr(surf, color, rect, r=12, border=0, bc=None):
    pygame.draw.rect(surf, color, rect, border_radius=r)
    if border and bc:
        pygame.draw.rect(surf, bc, rect, border, border_radius=r)


# ════════════════════════════════════════════════════════════════════════════
#  RECTANGULAR RENDERER
# ════════════════════════════════════════════════════════════════════════════

class Renderer:
    """
    Draws a rectangular Maze onto the given screen surface.

    FIX #2 — Camera:
      _update_camera() computes cam_x / cam_y so the viewport follows the
      player.  For modes other than Ultimate Challenge the camera is set to
      centre the whole maze (cam values can be negative, meaning the maze
      starts before the screen edge — clipped by set_clip).

    FIX #3 — Lights-Out fog:
      _draw_fog_mask() builds an SRCALPHA surface each frame with a radial
      gradient hole centred on the player's screen position.
    """

    def __init__(self, cell_size: int = CELL_SIZE):
        self.cell     = cell_size
        self._fonts   = {}
        self.cam_x    = 0    # world-pixel X of the top-left of the viewport
        self.cam_y    = 0    # world-pixel Y of the top-left of the viewport
        self._pb_rect = None  # pause button Rect, set during draw
        self._screen_w = SCREEN_WIDTH
        self._screen_h = SCREEN_HEIGHT

    # ── font lazy init ────────────────────────────────────────────────────────

    def _ensure_fonts(self):
        if not self._fonts:
            self._fonts = {
                "hud": _font(21, bold=True),
                "btn": _font(14, bold=True),
                "title": _font(26, bold=True),
                "mode": _font(14, bold=True),
            }

    # ── camera ────────────────────────────────────────────────────────────────
    # FIX #2

    def _update_camera(self, maze, player, use_camera: bool):
        vp_w = self._screen_w
        vp_h = self._screen_h - HUD_HEIGHT

        if not use_camera:
            # Centre the entire maze in the viewport
            maze_w = maze.cols * self.cell
            maze_h = maze.rows * self.cell
            self.cam_x = -(vp_w - maze_w) // 2
            self.cam_y = -(vp_h - maze_h) // 2
            return

        # Ultimate Challenge — keep player centred
        target_x = player.col * self.cell + self.cell // 2 - vp_w // 2
        target_y = player.row * self.cell + self.cell // 2 - vp_h // 2

        # Clamp so we never scroll past the maze boundaries
        max_cam_x = max(0, maze.cols * self.cell - vp_w)
        max_cam_y = max(0, maze.rows * self.cell - vp_h)
        self.cam_x = max(0, min(target_x, max_cam_x))
        self.cam_y = max(0, min(target_y, max_cam_y))

    # ── coordinate helpers ────────────────────────────────────────────────────

    def world_to_screen(self, row: int, col: int):
        """Convert a grid cell (row, col) to the screen pixel of its top-left corner."""
        sx = col * self.cell - self.cam_x
        sy = row * self.cell - self.cam_y + HUD_HEIGHT
        return int(sx), int(sy)

    # ── main draw entry ───────────────────────────────────────────────────────

    def draw(self, screen, maze, player,
             timer=None, mode=None,
             lights_out: bool = False,
             preview: bool = False,
             preview_timer: float = 0):
        self._ensure_fonts()
        self._screen_w, self._screen_h = screen.get_size()
        use_camera = (mode == MODE_ULTIMATE)
        self._update_camera(maze, player, use_camera)

        screen.fill(BG_COLOR)
        self._draw_hud(screen, player, timer, mode)

        # Clip drawing to the game viewport (below HUD)
        vp = pygame.Rect(0, HUD_HEIGHT, self._screen_w, self._screen_h - HUD_HEIGHT)
        screen.set_clip(vp)

        self._draw_cells(screen, maze)
        self._draw_goal(screen, maze)
        self._draw_player(screen, player)

        screen.set_clip(None)

        # FIX #3 — fog mask after clip is released so it spans the whole window
        if lights_out and not preview:
            self._draw_fog_mask(screen, player)

        # FIX #6 — pause button always visible on HUD
        self._draw_pause_btn(screen)

        # FIX #3 — preview countdown banner
        if preview:
            self._draw_preview_banner(screen, preview_timer)

    # ── HUD ───────────────────────────────────────────────────────────────────

    def _draw_hud(self, screen, player, timer, mode):
        W = self._screen_w
        pygame.draw.rect(screen, HUD_BG, (0, 0, W, HUD_HEIGHT))
        pygame.draw.line(screen, WALL_COLOR, (0, HUD_HEIGHT), (W, HUD_HEIGHT), 2)
        f = self._fonts["hud"]

        # Timer (left)
        if timer is not None:
            mins = int(timer) // 60
            secs = int(timer) % 60
            color = CORRECT_COLOR if timer > 30 else WRONG_COLOR
            ts = f.render(f"⏱ {mins}:{secs:02d}", True, color)
            screen.blit(ts, (14, HUD_HEIGHT - ts.get_height() - 12))

        title = self._fonts["title"].render("Maze Quest", True, TEXT_COLOR)
        tx = W // 2 - title.get_width() // 2
        screen.blit(title, (tx, 10))
        self._draw_logo(screen, tx + title.get_width() + 12, 18)

        if mode:
            ms = self._fonts["mode"].render(mode, True, ACCENT)
            screen.blit(ms, (W // 2 - ms.get_width() // 2, 42))

        # Lives (right — hearts)
        for i in range(player.lives):
            hx = W - 220 - i * 30   # leave room for pause button
            hy = HUD_HEIGHT - 25
            pygame.draw.circle(screen, HEART_COLOR, (hx, hy), 10)
            pygame.draw.circle(screen, (255, 120, 138), (hx - 3, hy - 4), 4)
            pygame.draw.circle(screen, (255, 120, 138), (hx + 3, hy - 4), 4)

    # ── FIX #6 — pause button ─────────────────────────────────────────────────

    def _draw_pause_btn(self, screen):
        rect = pygame.Rect(self._screen_w - 100, HUD_HEIGHT - 48, 82, 34)
        _draw_rr(screen, DARK_GRAY, rect, r=8, border=1, bc=PAUSE_COLOR)
        s = self._fonts["btn"].render("⏸ PAUSE", True, PAUSE_COLOR)
        screen.blit(s, (rect.centerx - s.get_width() // 2,
                        rect.centery - s.get_height() // 2))
        self._pb_rect = rect

    def pause_btn_rect(self):
        """Return the last-drawn pause button Rect (or None before first draw)."""
        return self._pb_rect

    # ── maze cells ────────────────────────────────────────────────────────────

    def _draw_cells(self, screen, maze):
        cell = self.cell
        for r in range(maze.rows):
            for c in range(maze.cols):
                sx, sy = self.world_to_screen(r, c)
                # Skip cells entirely outside the viewport for performance
                if sx + cell < 0 or sx > self._screen_w:
                    continue
                if sy + cell < HUD_HEIGHT or sy > self._screen_h:
                    continue

                color = WALL_COLOR if maze.grid[r][c] == 1 else PATH_COLOR
                pygame.draw.rect(screen, color, (sx, sy, cell, cell))

                # Junction indicator dot
                if maze.is_junction(r, c):
                    pygame.draw.circle(screen, CHECKPOINT_DOT,
                                       (sx + cell // 2, sy + cell // 2), 3)

    def _draw_goal(self, screen, maze):
        gr, gc = maze.goal
        sx, sy = self.world_to_screen(gr, gc)
        cx_ = sx + self.cell // 2
        cy_ = sy + self.cell // 2
        r   = self.cell // 2 - 2

        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*GOAL_COLOR, 90), (r * 2, r * 2), r * 2)
        screen.blit(glow, (cx_ - r * 2, cy_ - r * 2))
        pygame.draw.circle(screen, GOAL_COLOR, (cx_, cy_), r)
        pygame.draw.circle(screen, (180, 255, 180), (cx_, cy_), max(1, r // 2))

    def _draw_player(self, screen, player):
        sx, sy = self.world_to_screen(player.visual_row, player.visual_col)
        cx_ = sx + self.cell // 2
        cy_ = sy + self.cell // 2
        r   = self.cell // 2 - 3

        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*PLAYER_COLOR, 70), (r * 2, r * 2), r * 2)
        screen.blit(glow, (cx_ - r * 2, cy_ - r * 2))
        pygame.draw.circle(screen, PLAYER_COLOR, (cx_, cy_), r)
        pygame.draw.circle(screen, WHITE,
                           (cx_ - r // 3, cy_ - r // 3), max(1, r // 4))

    # ── FIX #3 — lights-out fog mask ─────────────────────────────────────────

    def _draw_fog_mask(self, screen, player):
        """
        Draw a full-screen black mask with a smooth radial hole centred on
        the player's current screen position.

        Implementation uses an SRCALPHA surface.  Each pixel within the light
        radius gets an alpha proportional to (dist / radius)^2 so the edge
        fades naturally.  Pixels outside are fully opaque black.
        """
        sx, sy = self.world_to_screen(player.visual_row, player.visual_col)
        pcx = sx + self.cell // 2
        pcy = sy + self.cell // 2
        radius = LIGHTS_OUT_RADIUS_PX

        fog = pygame.Surface((self._screen_w, self._screen_h), pygame.SRCALPHA)
        fog.fill((0, 0, 0, 255))   # start fully black

        # Carve a smooth hole — iterate over the bounding square
        for dy in range(-radius, radius + 1):
            fy = pcy + dy
            if fy < HUD_HEIGHT or fy >= self._screen_h:
                continue
            for dx in range(-radius, radius + 1):
                dist = math.hypot(dx, dy)
                if dist > radius:
                    continue
                fx = pcx + dx
                if fx < 0 or fx >= self._screen_w:
                    continue
                # alpha=0 at centre, 255 at edge — smooth radial gradient
                alpha = int(255 * (dist / radius) ** 2)
                fog.set_at((fx, fy), (0, 0, 0, alpha))

        screen.blit(fog, (0, 0))

    # ── FIX #3 — preview banner ───────────────────────────────────────────────

    def _draw_preview_banner(self, screen, preview_timer: float):
        f   = _font(22, bold=True)
        t   = int(preview_timer) + 1
        txt = f"Memorise the maze!  Starting in {t}…"
        s   = f.render(txt, True, PLAYER_COLOR)
        ov  = pygame.Surface((s.get_width() + 40, 44), pygame.SRCALPHA)
        ov.fill((4, 14, 24, 215))
        bx  = self._screen_w // 2 - (s.get_width() + 40) // 2
        screen.blit(ov, (bx, HUD_HEIGHT + 8))
        screen.blit(s,  (self._screen_w // 2 - s.get_width() // 2, HUD_HEIGHT + 12))

    def _draw_logo(self, screen, x, y):
        x = min(x, self._screen_w - 138)
        rect = pygame.Rect(x, y, 34, 34)
        pygame.draw.circle(screen, ACCENT, rect.center, 16, 2)
        pygame.draw.arc(screen, PLAYER_COLOR, rect.inflate(-8, -8), 0.2, 4.9, 3)
        pygame.draw.circle(screen, PLAYER_COLOR, (rect.centerx + 7, rect.centery - 7), 4)


# ════════════════════════════════════════════════════════════════════════════
#  CIRCULAR RENDERER
# ════════════════════════════════════════════════════════════════════════════

class CircularRenderer:
    """
    Draws a CircularMaze as filled arc segments separated by wall lines.

    FIX #1:
      Walls are painted exactly where maze.radial_walls and
      maze.circular_walls say they should be.  Because the DFS generation
      now uses the corrected direction semantics, the visual openings
      correctly align with the passages the player can walk through.

    Wall drawing:
      radial wall   — a straight line from inner_r to outer_r at the CW edge
                      angle of the sector.
      circular wall — an arc drawn at outer_r spanning the sector's angular
                      range.
      A wall is drawn only if its key is PRESENT in the respective set
      (present = wall exists = passage blocked).

    FIX #6:
      Same ⏸ PAUSE button drawn on the HUD.
    """

    def __init__(self):
        self._fonts   = {}
        self._pb_rect = None
        self._rw      = CIRCULAR_RING_WIDTH
        self._screen_w = SCREEN_WIDTH
        self._screen_h = SCREEN_HEIGHT

    def _ensure_fonts(self):
        if not self._fonts:
            self._fonts = {
                "hud":  _font(21, bold=True),
                "btn":  _font(14, bold=True),
                "hint": _font(13),
                "title": _font(26, bold=True),
                "mode": _font(14, bold=True),
            }

    def _centre(self):
        return (self._screen_w // 2,
                HUD_HEIGHT + (self._screen_h - HUD_HEIGHT) // 2)

    # ── main entry ────────────────────────────────────────────────────────────

    def draw(self, screen, maze, player, timer=None, mode=None):
        self._ensure_fonts()
        self._screen_w, self._screen_h = screen.get_size()
        screen.fill(BG_COLOR)
        self._draw_hud(screen, player, timer, mode)
        self._draw_maze(screen, maze, player)
        self._draw_pause_btn(screen)

    # ── HUD ───────────────────────────────────────────────────────────────────

    def _draw_hud(self, screen, player, timer, mode):
        W = self._screen_w
        pygame.draw.rect(screen, HUD_BG, (0, 0, W, HUD_HEIGHT))
        pygame.draw.line(screen, WALL_COLOR, (0, HUD_HEIGHT), (W, HUD_HEIGHT), 2)
        f = self._fonts["hud"]

        if timer is not None:
            mins = int(timer) // 60
            secs = int(timer) % 60
            color = CORRECT_COLOR if timer > 30 else WRONG_COLOR
            ts = f.render(f"⏱ {mins}:{secs:02d}", True, color)
            screen.blit(ts, (14, HUD_HEIGHT - ts.get_height() - 12))

        title = self._fonts["title"].render("Maze Quest", True, TEXT_COLOR)
        tx = W // 2 - title.get_width() // 2
        screen.blit(title, (tx, 10))
        self._draw_logo(screen, tx + title.get_width() + 12, 18)

        if mode:
            ms = self._fonts["mode"].render(mode, True, ACCENT)
            screen.blit(ms, (W // 2 - ms.get_width() // 2, 42))

        for i in range(player.lives):
            hx = W - 220 - i * 30
            hy = HUD_HEIGHT - 25
            pygame.draw.circle(screen, HEART_COLOR, (hx, hy), 10)
            pygame.draw.circle(screen, (255, 120, 138), (hx - 3, hy - 4), 4)
            pygame.draw.circle(screen, (255, 120, 138), (hx + 3, hy - 4), 4)

    # ── FIX #6 ────────────────────────────────────────────────────────────────

    def _draw_pause_btn(self, screen):
        rect = pygame.Rect(self._screen_w - 100, HUD_HEIGHT - 48, 82, 34)
        _draw_rr(screen, DARK_GRAY, rect, r=8, border=1, bc=PAUSE_COLOR)
        s = self._fonts["btn"].render("⏸ PAUSE", True, PAUSE_COLOR)
        screen.blit(s, (rect.centerx - s.get_width() // 2,
                        rect.centery - s.get_height() // 2))
        self._pb_rect = rect

    def pause_btn_rect(self):
        return self._pb_rect

    # ── circular maze ─────────────────────────────────────────────────────────

    def _draw_maze(self, screen, maze, player):
        cx, cy = self._centre()
        rw = min(self._rw, max(22, int((min(self._screen_w, self._screen_h - HUD_HEIGHT) - 48) / (maze.rings * 2))))

        for ring in range(maze.rings):
            inner_r = ring * rw
            outer_r = (ring + 1) * rw
            s_count = maze.spr[ring]
            step    = 2 * math.pi / s_count

            for sec in range(s_count):
                a0 = sec * step - math.pi / 2    # start angle (top = -π/2)
                a1 = a0 + step                    # end angle

                is_goal   = (ring == maze.goal[0] and sec == maze.goal[1])

                # Fill cell arc
                cell_color = GOAL_COLOR if is_goal else PATH_COLOR
                self._fill_arc(screen, cx, cy, inner_r, outer_r,
                               a0, a1, cell_color)

                # Junction dot
                if maze.is_junction(ring, sec) and not is_goal:
                    mid_r = (inner_r + outer_r) / 2
                    mid_a = (a0 + a1) / 2
                    dx_ = cx + mid_r * math.cos(mid_a)
                    dy_ = cy + mid_r * math.sin(mid_a)
                    pygame.draw.circle(screen, CHECKPOINT_DOT,
                                       (int(dx_), int(dy_)), 4)

                # ── Wall lines — only where walls EXIST (FIX #1) ─────────
                # Circular wall: outer arc of this cell (ring → ring+1)
                if (ring, sec) in maze.circular_walls:
                    self._arc_line(screen, cx, cy, outer_r,
                                   a0, a1, WALL_COLOR, 2)

                # Radial wall: CW edge of this sector (sec → sec+1)
                if (ring, sec) in maze.radial_walls:
                    wx_out = cx + outer_r * math.cos(a1)
                    wy_out = cy + outer_r * math.sin(a1)
                    wx_in  = cx + inner_r * math.cos(a1)
                    wy_in  = cy + inner_r * math.sin(a1)
                    pygame.draw.line(screen, WALL_COLOR,
                                     (int(wx_in),  int(wy_in)),
                                     (int(wx_out), int(wy_out)), 2)
                    pygame.draw.aaline(screen, WALL_COLOR,
                                       (int(wx_in),  int(wy_in)),
                                       (int(wx_out), int(wy_out)))

        # Outer boundary circle
        pygame.draw.circle(screen, WALL_COLOR,
                           (cx, cy), maze.rings * rw, 2)

        self._draw_circular_player(screen, cx, cy, rw, maze, player)

        # Orientation hint
        hint = "↑ Outward  ↓ Inward  ← → Rotate  •  Goal = Centre"
        hs = self._fonts["hint"].render(hint, True, GRAY)
        screen.blit(hs, (self._screen_w // 2 - hs.get_width() // 2,
                         self._screen_h - 22))

    def _draw_circular_player(self, screen, cx, cy, rw, maze, player):
        ring = player.visual_ring
        logical_ring = max(0, min(maze.rings - 1, int(round(player.ring))))
        sectors = maze.spr[logical_ring]
        sec = player.visual_sector % sectors
        radius = (ring + 0.5) * rw
        angle = (sec + 0.5) * (2 * math.pi / sectors) - math.pi / 2
        px = int(cx + radius * math.cos(angle))
        py = int(cy + radius * math.sin(angle))
        r = max(6, rw // 4)
        glow = pygame.Surface((r * 5, r * 5), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*PLAYER_COLOR, 70), (r * 2, r * 2), r * 2)
        screen.blit(glow, (px - r * 2, py - r * 2))
        pygame.draw.circle(screen, PLAYER_COLOR, (px, py), r)
        pygame.draw.circle(screen, WHITE, (px - r // 3, py - r // 3), max(2, r // 3))

    def _draw_logo(self, screen, x, y):
        x = min(x, self._screen_w - 138)
        rect = pygame.Rect(x, y, 34, 34)
        pygame.draw.circle(screen, ACCENT, rect.center, 16, 2)
        pygame.draw.arc(screen, PLAYER_COLOR, rect.inflate(-8, -8), 0.2, 4.9, 3)
        pygame.draw.circle(screen, PLAYER_COLOR, (rect.centerx + 7, rect.centery - 7), 4)

    # ── arc helpers ───────────────────────────────────────────────────────────

    def _fill_arc(self, screen, cx, cy,
                  r_in, r_out, a0, a1, color):
        """Fill a ring segment (annular sector) with a polygon."""
        steps = max(10, int(r_out * abs(a1 - a0) * 1.5))
        pts   = []
        for i in range(steps + 1):
            a = a0 + (a1 - a0) * i / steps
            pts.append((cx + r_out * math.cos(a),
                        cy + r_out * math.sin(a)))
        for i in range(steps, -1, -1):
            a = a0 + (a1 - a0) * i / steps
            pts.append((cx + r_in * math.cos(a),
                        cy + r_in * math.sin(a)))
        if len(pts) >= 3:
            ipts = [(int(x), int(y)) for x, y in pts]
            pygame.gfxdraw.filled_polygon(screen, ipts, color)
            pygame.gfxdraw.aapolygon(screen, ipts, color)

    def _arc_line(self, screen, cx, cy, radius, a0, a1, color, width):
        """Draw a polyline approximating an arc at the given radius."""
        steps = max(8, int(radius * abs(a1 - a0)))
        pts   = [
            (int(cx + radius * math.cos(a0 + (a1 - a0) * i / steps)),
             int(cy + radius * math.sin(a0 + (a1 - a0) * i / steps)))
            for i in range(steps + 1)
        ]
        if len(pts) >= 2:
            pygame.draw.lines(screen, color, False, pts, width)
            pygame.draw.aalines(screen, color, False, pts)
