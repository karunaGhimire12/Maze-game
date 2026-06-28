# views/screens.py
# ─────────────────────────────────────────────────────────────────────────────
# All overlay and full-screen UI classes.
#
#   MainMenuScreen  — mode selection with 4 animated cards.
#
#   QuizPopup       — FIX #4 (complete rewrite):
#     • Countdown timer bar inside the card, scaled by difficulty.
#     • If timer → 0: STATE_TIMEDOUT → 2-second full-screen "TIME OUT!" overlay,
#       no answer revealed, no life lost, popup closes automatically.
#     • If player answers: STATE_ANSWERED → 3-second result banner (✓ or ✗),
#       then popup closes; bonus/penalty applied in game.py update().
#     • update(dt) drives all internal timers and returns a verdict token
#       (True / False / None) exactly once to the caller (game.py).
#
#   PauseScreen     — FIX #6:
#     • Three buttons: RESUME, RESTART, QUIT.
#     • handle_event returns "resume" / "restart" / "quit".
#
#   GameOverScreen  — Retry / Menu buttons.
#   VictoryScreen   — Play Again / Menu buttons, animated particles.
# ─────────────────────────────────────────────────────────────────────────────

import pygame
import math
import random

from core.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    PLAYER_LIVES,
    QUIZ_TIME_EASY, QUIZ_TIME_MEDIUM, QUIZ_TIME_HARD,
    QUIZ_RESULT_SHOW, QUIZ_TIMEOUT_SHOW,
    BONUS_EASY, BONUS_MEDIUM, BONUS_HARD,
    MODE_TIME_ATTACK, MODE_LIGHTS_OUT, MODE_ULTIMATE, MODE_CIRCULAR,
    DIFF_EASY, DIFF_MEDIUM, DIFF_HARD, DIFFICULTY_LABELS,
    BG_COLOR, WALL_COLOR, TEXT_COLOR, ACCENT, CORRECT_COLOR, WRONG_COLOR,
    CARD_BG, CARD_BORDER, DARK_GRAY, GRAY, WHITE, PAUSE_COLOR, GOAL_COLOR,
    PLAYER_COLOR,
)


# ── shared helpers ────────────────────────────────────────────────────────────

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
#  MAIN MENU
# ════════════════════════════════════════════════════════════════════════════

_MODES_DEF = [
    {
        "id":    MODE_TIME_ATTACK,
        "icon":  "⏱",
        "color": (75, 205, 178),
        "sub":   "Race against the clock",
        "desc":  "Visible maze • 3 min timer • Quiz checkpoints",
    },
    {
        "id":    MODE_LIGHTS_OUT,
        "icon":  "🌑",
        "color": (220, 160, 55),
        "sub":   "Memory & darkness challenge",
        "desc":  "3-second preview • Fog of war • Test your memory!",
    },
    {
        "id":    MODE_ULTIMATE,
        "icon":  "⚡",
        "color": (220, 75, 75),
        "sub":   "Massive scrolling labyrinth",
        "desc":  "41×41 map • Camera scrolls • Expert difficulty",
    },
    {
        "id":    MODE_CIRCULAR,
        "icon":  "◎",
        "color": (155, 95, 220),
        "sub":   "Radial concentric maze",
        "desc":  "Navigate inward to the goal • Unique geometry",
    },
]


class MainMenuScreen:

    def __init__(self):
        self._card_rects = []
        self._diff_rects = []
        self._difficulty_mode = None
        self._tick       = 0
        self._fonts      = {}

    def _ensure_fonts(self):
        if not self._fonts:
            self._fonts = {
                "title": _font(50, bold=True),
                "sub":   _font(16),
                "mode":  _font(20, bold=True),
                "desc":  _font(13),
                "label": _font(12, bold=True),
                "back":  _font(15, bold=True),
            }

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self._difficulty_mode:
                for diff, rect in self._diff_rects:
                    if rect.collidepoint(mx, my):
                        mode = self._difficulty_mode
                        self._difficulty_mode = None
                        return (mode, diff)
                if pygame.Rect(24, 112, 96, 34).collidepoint(mx, my):
                    self._difficulty_mode = None
                return None

            for i, rect in enumerate(self._card_rects):
                if rect.collidepoint(mx, my):
                    mode = _MODES_DEF[i]["id"]
                    if mode in (MODE_TIME_ATTACK, MODE_CIRCULAR):
                        self._difficulty_mode = mode
                        return None
                    return (mode, None)

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._difficulty_mode = None
        return None

    def draw(self, screen):
        self._ensure_fonts()
        self._tick += 1
        W, H = screen.get_size()
        screen.fill(BG_COLOR)

        # Subtle grid background
        for x in range(0, W, 40):
            pygame.draw.line(screen, (22, 42, 56), (x, 0), (x, H))
        for y in range(0, H, 40):
            pygame.draw.line(screen, (22, 42, 56), (0, y), (W, y))

        # Title
        ts = self._fonts["title"].render("MAZE QUEST", True, TEXT_COLOR)
        screen.blit(ts, (W // 2 - ts.get_width() // 2, 24))
        self._draw_logo(screen, W // 2 + ts.get_width() // 2 + 14, 36)
        ss = self._fonts["sub"].render(
            "Navigate  •  Answer  •  Conquer", True, GRAY)
        screen.blit(ss, (W // 2 - ss.get_width() // 2, 82))

        if self._difficulty_mode:
            self._draw_difficulty_picker(screen, W, H)
            return

        lbl = self._fonts["label"].render("SELECT GAME MODE", True, GRAY)
        screen.blit(lbl, (28, 118))

        # Mode cards
        card_y, card_h, gap = 140, 108, 10
        mx_pos, my_pos = pygame.mouse.get_pos()
        self._card_rects = []

        for i, mode in enumerate(_MODES_DEF):
            cy   = card_y + i * (card_h + gap)
            rect = pygame.Rect(20, cy, W - 40, card_h)
            self._card_rects.append(rect)
            hov  = rect.collidepoint(mx_pos, my_pos)

            _draw_rr(screen,
                     (32, 58, 74) if hov else CARD_BG,
                     rect, r=12, border=2,
                     bc=mode["color"] if hov else CARD_BORDER)

            # Icon circle
            ix, iy = rect.x + 30, rect.centery
            pygame.draw.circle(screen, mode["color"], (ix, iy), 22, 2)
            ic = self._fonts["mode"].render(mode["icon"], True, mode["color"])
            screen.blit(ic, (ix - ic.get_width() // 2,
                             iy - ic.get_height() // 2))

            # Text
            ns = self._fonts["mode"].render(mode["id"], True, TEXT_COLOR)
            screen.blit(ns, (rect.x + 62, rect.y + 14))
            sub_s = self._fonts["desc"].render(mode["sub"], True, GRAY)
            screen.blit(sub_s, (rect.x + 62, rect.y + 38))
            ds = self._fonts["desc"].render(mode["desc"], True, (132, 155, 170))
            screen.blit(ds, (rect.x + 62, rect.y + 58))

        # How-to footer
        hy = card_y + 4 * (card_h + gap) + 10
        how = [
            ("HOW TO PLAY", ACCENT, self._fonts["label"]),
            ("Move with arrow keys / WASD.  Reach the goal to win.",
             GRAY, self._fonts["desc"]),
            ("Answer quiz questions at junctions for time bonuses.",
             GRAY, self._fonts["desc"]),
            ("Wrong answers cost a life.  ESC or ⏸ PAUSE to pause.",
             GRAY, self._fonts["desc"]),
        ]
        for text, color, fnt in how:
            s = fnt.render(text, True, color)
            screen.blit(s, (28, hy))
            hy += 18

    def _draw_logo(self, screen, x, y):
        rect = pygame.Rect(min(x, screen.get_width() - 90), y, 42, 42)
        pygame.draw.circle(screen, ACCENT, rect.center, 19, 2)
        pygame.draw.arc(screen, PLAYER_COLOR, rect.inflate(-10, -10), 0.2, 4.9, 4)
        pygame.draw.circle(screen, PLAYER_COLOR, (rect.centerx + 8, rect.centery - 8), 5)

    def _draw_difficulty_picker(self, screen, W, H):
        back = pygame.Rect(24, 112, 96, 34)
        _draw_rr(screen, DARK_GRAY, back, r=8, border=1, bc=GRAY)
        _center_text(screen, "BACK", self._fonts["back"], GRAY, back.centerx, back.y + 8)

        label = self._fonts["label"].render(f"{self._difficulty_mode.upper()} DIFFICULTY", True, GRAY)
        screen.blit(label, (28, 164))
        desc = self._fonts["desc"].render("Choose question pool and reward timing.", True, (132, 155, 170))
        screen.blit(desc, (28, 184))

        defs = [
            (DIFF_EASY, "Only Easy Questions", "+5s per correct answer", CORRECT_COLOR),
            (DIFF_MEDIUM, "Only Medium/Average Questions", "+8s per correct answer", (220, 180, 55)),
            (DIFF_HARD, "Only Hard Questions", "+15s per correct answer", WRONG_COLOR),
        ]
        self._diff_rects = []
        y = 220
        for diff, sub, reward, color in defs:
            rect = pygame.Rect(28, y, W - 56, 96)
            self._diff_rects.append((diff, rect))
            hov = rect.collidepoint(pygame.mouse.get_pos())
            _draw_rr(screen, (32, 58, 74) if hov else CARD_BG, rect, r=12, border=2, bc=color if hov else CARD_BORDER)
            name = self._fonts["mode"].render(DIFFICULTY_LABELS[diff], True, TEXT_COLOR)
            screen.blit(name, (rect.x + 22, rect.y + 16))
            s1 = self._fonts["desc"].render(sub, True, GRAY)
            s2 = self._fonts["desc"].render(reward, True, color)
            screen.blit(s1, (rect.x + 22, rect.y + 43))
            screen.blit(s2, (rect.x + 22, rect.y + 64))
            y += 112


# ════════════════════════════════════════════════════════════════════════════
#  QUIZ POPUP  — FIX #4 complete rewrite
# ════════════════════════════════════════════════════════════════════════════

# Internal quiz states
_QS_WAITING  = "waiting"    # timer running, waiting for player click
_QS_ANSWERED = "answered"   # player clicked; showing result for QUIZ_RESULT_SHOW s
_QS_TIMEDOUT = "timedout"   # timer ran out; showing "Time Out!" for QUIZ_TIMEOUT_SHOW s
_QS_DONE     = "done"       # ready to be closed by game.py


class QuizPopup:
    """
    FIX #4 — Full quiz popup with:
      • Per-difficulty countdown timer (rendered as a progress bar).
      • Time-out path: 2-second "TIME OUT!" overlay, no life lost, no answer shown.
      • Answer path: 3-second result flash (correct=green / wrong=red), then done.

    Interaction protocol with game.py:
      handle_event(event) → returns True (correct) / False (wrong) / None (no click yet)
      update(dt)          → drives timers; returns the SAME verdict token
                            exactly once when STATE transitions from WAITING,
                            then returns None on subsequent calls.
      should_close()      → True once internal state reaches _QS_DONE.
    """

    def __init__(self, question_data: dict):
        self.data     = question_data
        self._state   = _QS_WAITING
        self.selected = None         # index of clicked option
        self.correct  = None         # True / False once answered

        diff = question_data.get("diff", "easy")
        self.time_limit = {
            "easy":   QUIZ_TIME_EASY,
            "medium": QUIZ_TIME_MEDIUM,
            "hard":   QUIZ_TIME_HARD,
        }.get(diff, QUIZ_TIME_EASY)
        self.countdown = self.time_limit

        self._result_timer  = 0.0
        self._timeout_timer = 0.0
        self._verdict_sent  = False   # ensure verdict emitted only once

        self._btn_rects = []
        self._fonts = {
            "hdr":    _font(14, bold=True),
            "q":      _font(19, bold=True),
            "opt":    _font(16),
            "result": _font(22, bold=True),
            "timer":  _font(17, bold=True),
            "big":    _font(58, bold=True),
            "sub":    _font(22),
        }

    # ── update (drives internal timers) ──────────────────────────────────────

    def update(self, dt: float):
        """
        Call every frame while state is S_QUIZ.
        Returns verdict token (True/False) exactly once, then None.
        game.py applies the bonus/penalty in response to the token.
        """
        if self._state == _QS_WAITING:
            self.countdown -= dt
            if self.countdown <= 0:
                self.countdown    = 0
                self._state       = _QS_TIMEDOUT
                self._timeout_timer = QUIZ_TIMEOUT_SHOW
                # Timed out — no verdict
            return None

        if self._state == _QS_ANSWERED:
            self._result_timer -= dt
            if self._result_timer <= 0:
                self._state = _QS_DONE
            # Emit verdict exactly once
            if not self._verdict_sent:
                self._verdict_sent = True
                return self.correct   # True or False
            return None

        if self._state == _QS_TIMEDOUT:
            self._timeout_timer -= dt
            if self._timeout_timer <= 0:
                self._state = _QS_DONE
            return None

        return None   # _QS_DONE

    # ── event handling ────────────────────────────────────────────────────────

    def handle_event(self, event):
        """
        Only active in _QS_WAITING.  Returns True/False on click, else None.
        Note: game.py also receives the verdict through update() — the click
        here sets the state but the bonus/penalty is applied in update() to
        keep timing frame-accurate.
        """
        if self._state != _QS_WAITING:
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, rect in enumerate(self._btn_rects):
                if rect.collidepoint(mx, my):
                    self.selected        = i
                    self.correct         = (self.data["opts"][i] == self.data["a"])
                    self._state          = _QS_ANSWERED
                    self._result_timer   = QUIZ_RESULT_SHOW
                    return self.correct
        return None

    def should_close(self) -> bool:
        return self._state == _QS_DONE

    def timed_out(self) -> bool:
        """True if the player ran out of time (no life should be deducted)."""
        return self._state in (_QS_TIMEDOUT, _QS_DONE) and self.correct is None

    # ── draw ──────────────────────────────────────────────────────────────────

    def draw(self, screen):
        W, H = screen.get_size()

        # Dim background
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((4, 12, 22, 215))
        screen.blit(ov, (0, 0))

        # Time-out overlay — replaces the card entirely
        if self._state == _QS_TIMEDOUT:
            self._draw_timeout(screen, W, H)
            return

        # ── Quiz card ─────────────────────────────────────────────────────
        cw, ch = 548, 350
        cx_c   = W // 2 - cw // 2
        cy_c   = H // 2 - ch // 2

        _draw_rr(screen, CARD_BG, (cx_c, cy_c, cw, ch),
                 r=18, border=2, bc=WALL_COLOR)

        # Difficulty label
        diff = self.data.get("diff", "easy").upper()
        diff_color = {
            "EASY":   CORRECT_COLOR,
            "MEDIUM": (220, 180, 55),
            "HARD":   WRONG_COLOR,
        }.get(diff, ACCENT)
        hdr = self._fonts["hdr"].render(
            f"JUNCTION CHECKPOINT  [{diff}]", True, diff_color)
        screen.blit(hdr, (cx_c + 20, cy_c + 14))
        pygame.draw.line(screen, WALL_COLOR,
                         (cx_c + 20, cy_c + 36),
                         (cx_c + cw - 20, cy_c + 36), 1)

        # ── Countdown progress bar (FIX #4) ──────────────────────────────
        bar_x = cx_c + 20
        bar_y = cy_c + 44
        bar_w = cw - 40
        bar_h = 8
        ratio = max(0.0, self.countdown / self.time_limit)
        bar_color = _lerp_color(WRONG_COLOR, CORRECT_COLOR, ratio)
        pygame.draw.rect(screen, DARK_GRAY, (bar_x, bar_y, bar_w, bar_h),
                         border_radius=4)
        if ratio > 0:
            pygame.draw.rect(screen, bar_color,
                             (bar_x, bar_y, int(bar_w * ratio), bar_h),
                             border_radius=4)
        ts = self._fonts["timer"].render(f"{self.countdown:.1f}s", True, bar_color)
        screen.blit(ts, (cx_c + cw - 20 - ts.get_width(), bar_y - 1))

        # Question text
        q_s = self._fonts["q"].render(self.data["q"], True, TEXT_COLOR)
        screen.blit(q_s, (W // 2 - q_s.get_width() // 2, cy_c + 62))

        # Option buttons (2 × 2 grid)
        opts  = self.data["opts"][:4]
        btn_w = (cw - 60) // 2
        btn_h = 46
        self._btn_rects = []

        for i, opt in enumerate(opts):
            bx   = cx_c + 20 + (i % 2) * (btn_w + 20)
            by   = cy_c + 112 + (i // 2) * (btn_h + 12)
            rect = pygame.Rect(bx, by, btn_w, btn_h)
            self._btn_rects.append(rect)

            if self._state == _QS_ANSWERED:
                if opt == self.data["a"]:
                    bg, bc = (28, 90, 54), CORRECT_COLOR
                elif i == self.selected:
                    bg, bc = (90, 28, 28), WRONG_COLOR
                else:
                    bg, bc = DARK_GRAY, GRAY
            else:
                hov   = rect.collidepoint(pygame.mouse.get_pos())
                bg, bc = ((38, 70, 85) if hov else (26, 50, 66)), \
                         (ACCENT if hov else WALL_COLOR)

            _draw_rr(screen, bg, rect, r=10, border=2, bc=bc)
            os_ = self._fonts["opt"].render(str(opt), True, TEXT_COLOR)
            screen.blit(os_, (rect.centerx - os_.get_width() // 2,
                              rect.centery - os_.get_height() // 2))

        # Result banner (shown during _QS_ANSWERED) — FIX #4
        if self._state == _QS_ANSWERED:
            if self.correct:
                diff_key = self.data.get("diff", "easy")
                bonus = {
                    "hard": BONUS_HARD,
                    "medium": BONUS_MEDIUM,
                }.get(diff_key, BONUS_EASY)
                rt, rc   = f"✓  Correct!  +{bonus}s bonus", CORRECT_COLOR
            else:
                rt, rc = f"✗  Wrong!   Answer: {self.data['a']}", WRONG_COLOR
            rs = self._fonts["result"].render(rt, True, rc)
            # Pulsing alpha for visual feedback
            screen.blit(rs, (W // 2 - rs.get_width() // 2, cy_c + ch - 52))

    # ── time-out full-screen overlay ──────────────────────────────────────────

    def _draw_timeout(self, screen, W, H):
        """
        FIX #4 — 2-second red overlay: "TIME OUT!" message, no answer shown,
        no life deducted.  Fades alpha proportionally to remaining time.
        """
        alpha = int(210 * min(1.0, self._timeout_timer / QUIZ_TIMEOUT_SHOW))
        ov2   = pygame.Surface((W, H), pygame.SRCALPHA)
        ov2.fill((70, 8, 8, max(0, alpha)))
        screen.blit(ov2, (0, 0))

        center_y = H // 2 - 40
        _center_text(screen, "TIME OUT!", self._fonts["big"], WRONG_COLOR, W // 2, center_y)
        _center_text(screen, "No answer given — quiz skipped.",
                     self._fonts["sub"], GRAY, W // 2, center_y + 72)


# ── colour lerp helper (needed inside this module) ────────────────────────────

def _lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ════════════════════════════════════════════════════════════════════════════
#  PAUSE SCREEN  — FIX #6
# ════════════════════════════════════════════════════════════════════════════

class PauseScreen:
    """
    FIX #6 — Full pause menu with three working buttons.

    handle_event() returns one of:
      "resume"  — close menu, continue playing
      "restart" — game.py maps this to "retry" routing token
      "quit"    — game.py maps this to "menu" routing token
    """

    def __init__(self):
        self._btns  = {}   # label → Rect
        self._fonts = {}

    def _ensure_fonts(self):
        if not self._fonts:
            self._fonts = {
                "title": _font(38, bold=True),
                "btn":   _font(20, bold=True),
                "sub":   _font(14),
            }

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for label, rect in self._btns.items():
                if rect.collidepoint(mx, my):
                    return label          # "resume" / "restart" / "quit"

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "resume"

        return None

    def draw(self, screen):
        self._ensure_fonts()
        W, H = screen.get_size()

        # Semi-transparent dark overlay
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((4, 14, 24, 205))
        screen.blit(ov, (0, 0))

        # Panel card
        pw, ph = 320, 300
        px, py = W // 2 - pw // 2, H // 2 - ph // 2
        _draw_rr(screen, CARD_BG, (px, py, pw, ph),
                 r=18, border=2, bc=PAUSE_COLOR)

        _center_text(screen, "⏸  PAUSED",
                     self._fonts["title"], PAUSE_COLOR, W // 2, py + 22)
        pygame.draw.line(screen, WALL_COLOR,
                         (px + 24, py + 70), (px + pw - 24, py + 70), 1)

        # Buttons — RESUME / RESTART / QUIT
        _BTN_DEFS = [
            ("resume",  "RESUME",  CORRECT_COLOR, py + 88),
            ("restart", "RESTART", ACCENT,        py + 150),
            ("quit",    "QUIT",    WRONG_COLOR,   py + 212),
        ]
        self._btns = {}
        for key, label, color, by in _BTN_DEFS:
            rect = pygame.Rect(px + 40, by, pw - 80, 46)
            self._btns[key] = rect
            _draw_rr(screen, DARK_GRAY, rect, r=10, border=2, bc=color)
            _center_text(screen, label, self._fonts["btn"], color, W // 2, by + 12)

        # Hint
        hint = self._fonts["sub"].render("ESC also resumes", True, GRAY)
        screen.blit(hint, (W // 2 - hint.get_width() // 2, py + ph - 28))


# ════════════════════════════════════════════════════════════════════════════
#  GAME OVER SCREEN
# ════════════════════════════════════════════════════════════════════════════

class GameOverScreen:

    def __init__(self, reason: str = "out_of_lives"):
        self.reason = reason
        self._btns  = {}
        self._fonts = {}

    def _ensure_fonts(self):
        if not self._fonts:
            self._fonts = {
                "big": _font(56, bold=True),
                "med": _font(24),
                "sub": _font(18),
            }

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for label, rect in self._btns.items():
                if rect.collidepoint(mx, my):
                    return label   # "retry" / "menu"
        return None

    def draw(self, screen):
        self._ensure_fonts()
        W, H = screen.get_size()
        screen.fill(BG_COLOR)
        for x in range(0, W, 40):
            pygame.draw.line(screen, (22, 38, 50), (x, 0), (x, H))
        for y in range(0, H, 40):
            pygame.draw.line(screen, (22, 38, 50), (0, y), (W, y))

        _center_text(screen, "GAME  OVER",
                     self._fonts["big"], WRONG_COLOR, W // 2, H // 2 - 130)

        msg = ("You ran out of lifelines!"
               if self.reason == "out_of_lives" else "Time's up!")
        _center_text(screen, msg, self._fonts["sub"], GRAY, W // 2, H // 2 - 58)

        buttons = [("retry", "Try Again", ACCENT, H // 2 + 18),
                   ("menu",  "Main Menu", GRAY,   H // 2 + 88)]
        self._btns = {}
        for key, label, color, by in buttons:
            rect = pygame.Rect(W // 2 - 110, by, 220, 52)
            self._btns[key] = rect
            _draw_rr(screen, CARD_BG, rect, r=12, border=2, bc=color)
            _center_text(screen, label, self._fonts["med"], color, W // 2, by + 14)


# ════════════════════════════════════════════════════════════════════════════
#  VICTORY SCREEN
# ════════════════════════════════════════════════════════════════════════════

class VictoryScreen:

    def __init__(self, time_left: float = 0, mode: str = ""):
        self.time_left = time_left
        self.mode      = mode
        self._btns     = {}
        self._tick     = 0
        self._fonts    = {}

    def _ensure_fonts(self):
        if not self._fonts:
            self._fonts = {
                "big":   _font(52, bold=True),
                "score": _font(28, bold=True),
                "med":   _font(22),
                "small": _font(16),
            }

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for label, rect in self._btns.items():
                if rect.collidepoint(mx, my):
                    return label   # "retry" / "menu"
        return None

    def draw(self, screen):
        self._ensure_fonts()
        self._tick += 1
        W, H = screen.get_size()
        screen.fill(BG_COLOR)

        # Animated background particles
        rng2 = random.Random(77)
        for _ in range(32):
            x = rng2.randint(0, W)
            y = rng2.randint(0, H)
            r = rng2.randint(2, 5)
            a = int(90 + 80 * math.sin(self._tick * 0.04 + rng2.random() * 6))
            pygame.draw.circle(screen, (a, 210, 110), (x, y), r)

        _center_text(screen, "YOU  WIN! 🎉",
                     self._fonts["big"], GOAL_COLOR, W // 2, H // 2 - 138)
        _center_text(screen, f"Mode: {self.mode}",
                     self._fonts["small"], GRAY, W // 2, H // 2 - 72)

        mins = int(self.time_left) // 60
        secs = int(self.time_left) % 60
        _center_text(screen, f"Time Remaining: {mins}:{secs:02d}",
                     self._fonts["score"], ACCENT, W // 2, H // 2 - 36)

        buttons = [("continue", "Play Continue", GOAL_COLOR, H // 2 + 42),
                   ("menu",  "Main Menu",  GRAY,       H // 2 + 110)]
        self._btns = {}
        for key, label, color, by in buttons:
            rect = pygame.Rect(W // 2 - 110, by, 220, 52)
            self._btns[key] = rect
            _draw_rr(screen, CARD_BG, rect, r=12, border=2, bc=color)
            _center_text(screen, label, self._fonts["med"], color, W // 2, by + 14)
