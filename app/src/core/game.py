# core/game.py
# ─────────────────────────────────────────────────────────────────────────────
# Central Game class — owns state machine, connects maze/player/renderer/
# screens.  All six architectural fixes are wired here:
#
#   FIX #1 — Circular movement directions passed correctly to CircularMaze
#   FIX #2 — Ultimate mode uses Renderer(cell=ULT_CELL_SIZE); camera handled
#             inside Renderer._update_camera()
#   FIX #3 — Lights-Out: S_PREVIEW state holds for LIGHTS_OUT_PREVIEW_S secs,
#             then renderer draws fog mask
#   FIX #4 — Quiz: QuizPopup.update(dt) drives countdown + timeout + result
#             timers; verdicts handled here
#   FIX #5 — Maze generated with high confusion (dead-end stubs) via
#             Maze._add_confusion()
#   FIX #6 — Pause menu: ESC key + HUD button both toggle S_PAUSED; pause
#             screen exposes Resume / Restart / Quit
# ─────────────────────────────────────────────────────────────────────────────

import random
import pygame

from core.config import (
    MODE_TIME_ATTACK, MODE_LIGHTS_OUT, MODE_ULTIMATE, MODE_CIRCULAR,
    TIMER_TIME_ATTACK, TIMER_LIGHTS_OUT, TIMER_ULTIMATE, TIMER_CIRCULAR,
    ROWS, COLS, ULT_ROWS, ULT_COLS, ULT_CELL_SIZE, CELL_SIZE,
    CIRCULAR_RINGS, CIRCULAR_BASE_SECTORS,
    LIGHTS_OUT_PREVIEW_S,
    BONUS_EASY, BONUS_HARD,
)
from models.maze   import Maze, CircularMaze
from models.player import Player, CircularPlayer
from views.renderer import Renderer, CircularRenderer
from views.screens  import (
    QuizPopup, PauseScreen, GameOverScreen, VictoryScreen,
)
from data.questions import QUESTIONS


# ── State constants ───────────────────────────────────────────────────────────
S_PREVIEW  = "preview"    # FIX #3 — lights-out 3-second full-view phase
S_PLAYING  = "playing"
S_QUIZ     = "quiz"       # FIX #4 — quiz popup active
S_PAUSED   = "paused"     # FIX #6 — pause menu open
S_GAMEOVER = "gameover"
S_VICTORY  = "victory"


class Game:
    """
    One complete game session for a given mode.
    Instantiate a fresh Game() each time the player restarts.
    """

    # ── construction ─────────────────────────────────────────────────────────

    def __init__(self, mode: str):
        self.mode        = mode
        self.is_circular = (mode == MODE_CIRCULAR)

        # ── Maze + Player ─────────────────────────────────────────────────
        # FIX #2: Ultimate uses oversized grid; camera scroll lives in Renderer
        if mode == MODE_ULTIMATE:
            self.maze     = Maze(rows=ULT_ROWS, cols=ULT_COLS)
            self.player   = Player(*self.maze.start)
            self.renderer = Renderer(cell_size=ULT_CELL_SIZE)

        elif mode == MODE_CIRCULAR:
            # FIX #1: CircularMaze.can_move() now has correct direction logic
            self.maze     = CircularMaze(rings=CIRCULAR_RINGS,
                                         base_sectors=CIRCULAR_BASE_SECTORS)
            self.player   = CircularPlayer(*self.maze.start)
            self.renderer = CircularRenderer()

        else:
            # Time Attack or Lights Out — standard grid
            self.maze     = Maze(rows=ROWS, cols=COLS)
            self.player   = Player(*self.maze.start)
            self.renderer = Renderer(cell_size=CELL_SIZE)

        # ── Countdown timer ───────────────────────────────────────────────
        _timers = {
            MODE_TIME_ATTACK: TIMER_TIME_ATTACK,
            MODE_LIGHTS_OUT:  TIMER_LIGHTS_OUT,
            MODE_ULTIMATE:    TIMER_ULTIMATE,
            MODE_CIRCULAR:    TIMER_CIRCULAR,
        }
        self.timer = float(_timers.get(mode, TIMER_TIME_ATTACK))

        # ── Lights-Out state  (FIX #3) ───────────────────────────────────
        self.lights_out    = (mode == MODE_LIGHTS_OUT)
        self.preview_timer = LIGHTS_OUT_PREVIEW_S if self.lights_out else 0.0
        self.state         = S_PREVIEW if self.lights_out else S_PLAYING

        # ── Quiz state  (FIX #4) ─────────────────────────────────────────
        self.quiz_popup  = None
        self._asked_pool = []       # shuffled index pool; refilled when empty

        # ── Overlay screens  (FIX #6) ────────────────────────────────────
        self.pause_screen    = PauseScreen()
        self.gameover_screen = None
        self.victory_screen  = None

    # ── per-frame update ──────────────────────────────────────────────────────

    def update(self, dt: float):
        """Advance simulation by dt seconds.  Paused state skips everything."""

        # FIX #3 — preview countdown
        if self.state == S_PREVIEW:
            self.preview_timer -= dt
            if self.preview_timer <= 0:
                self.state = S_PLAYING
            return

        # FIX #4 — quiz drives its own internal timer
        if self.state == S_QUIZ and self.quiz_popup:
            verdict = self.quiz_popup.update(dt)
            if verdict is True:
                # Correct answer → grant time bonus
                diff  = self.quiz_popup.data.get("diff", "easy")
                bonus = BONUS_HARD if diff == "hard" else BONUS_EASY
                self.timer += bonus
                self.player.add_bonus(bonus)
            elif verdict is False:
                # Wrong answer → lose a life; check game-over
                dead = self.player.lose_life()
                if dead:
                    self.quiz_popup = None
                    self._trigger_game_over("out_of_lives")
                    return

            # verdict is None while timer is still running (no action needed)
            if self.quiz_popup and self.quiz_popup.should_close():
                self.quiz_popup = None
                self.state = S_PLAYING
            return

        # FIX #6 — paused: freeze everything
        if self.state == S_PAUSED:
            return

        if self.state != S_PLAYING:
            return

        # ── Normal playing ────────────────────────────────────────────────
        self.timer -= dt
        if self.timer <= 0:
            self.timer = 0
            self._trigger_game_over("time_up")
            return

        if self._at_goal():
            self._trigger_victory()

    # ── event handling ────────────────────────────────────────────────────────

    def handle_event(self, event):
        """
        Returns "menu" or "retry" routing tokens, or None to continue.
        """

        # ── Pause button click (HUD ⏸ button) — FIX #6 ──────────────────
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pb = self.renderer.pause_btn_rect()
            if pb and pb.collidepoint(event.pos):
                if self.state == S_PLAYING:
                    self.state = S_PAUSED
                    return
                elif self.state == S_PAUSED:
                    self.state = S_PLAYING
                    return

        # ── Quiz popup — FIX #4 ──────────────────────────────────────────
        if self.state == S_QUIZ and self.quiz_popup:
            # handle_event returns a verdict only on immediate click;
            # the bonus/penalty is applied in update() so timing is frame-accurate
            self.quiz_popup.handle_event(event)
            return

        # ── Pause menu — FIX #6 ──────────────────────────────────────────
        if self.state == S_PAUSED:
            action = self.pause_screen.handle_event(event)
            if action == "resume":
                self.state = S_PLAYING
            elif action == "restart":
                return "retry"
            elif action == "quit":
                return "menu"
            return

        # ── Game-over screen ──────────────────────────────────────────────
        if self.state == S_GAMEOVER and self.gameover_screen:
            action = self.gameover_screen.handle_event(event)
            if action == "retry":
                return "retry"
            elif action == "menu":
                return "menu"
            return

        # ── Victory screen ────────────────────────────────────────────────
        if self.state == S_VICTORY and self.victory_screen:
            action = self.victory_screen.handle_event(event)
            if action == "retry":
                return "retry"
            elif action == "menu":
                return "menu"
            return

        # ── Keyboard — movement + ESC pause ──────────────────────────────
        if self.state == S_PLAYING:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = S_PAUSED                  # FIX #6

                # FIX #1 — circular directions are explicit strings;
                # rectangular uses (dr, dc) offsets.
                # UP   → outward  (ring index +1) for circular,
                #         row-1 for rectangular.
                # DOWN → inward   (ring index -1) for circular,
                #         row+1 for rectangular.
                elif event.key in (pygame.K_UP,    pygame.K_w):
                    self._move(-1,  0, "out")
                elif event.key in (pygame.K_DOWN,  pygame.K_s):
                    self._move( 1,  0, "in")
                elif event.key in (pygame.K_LEFT,  pygame.K_a):
                    self._move( 0, -1, "ccw")
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._move( 0,  1, "cw")

    # ── movement helper ───────────────────────────────────────────────────────

    def _move(self, dr: int, dc: int, circ_dir: str):
        """Apply one move; check goal and junction after."""
        if self.state != S_PLAYING:
            return

        if self.is_circular:
            moved = self.player.move(circ_dir, self.maze)
        else:
            moved = self.player.move(dr, dc, self.maze)

        if moved:
            if self._at_goal():
                self._trigger_victory()
            elif self.player.at_junction(self.maze):
                self._trigger_quiz()

    # ── state transitions ─────────────────────────────────────────────────────

    def _at_goal(self) -> bool:
        if self.is_circular:
            return (self.player.ring   == self.maze.goal[0] and
                    self.player.sector == self.maze.goal[1])
        return (self.player.row == self.maze.goal[0] and
                self.player.col == self.maze.goal[1])

    def _trigger_quiz(self):
        """Open a quiz popup; suspend main timer via S_QUIZ state."""
        q = self._pick_question()
        self.quiz_popup = QuizPopup(q)
        self.state = S_QUIZ

    def _trigger_game_over(self, reason: str):
        self.gameover_screen = GameOverScreen(reason)
        self.state = S_GAMEOVER

    def _trigger_victory(self):
        self.victory_screen = VictoryScreen(
            time_left=self.timer, mode=self.mode)
        self.state = S_VICTORY

    def _pick_question(self) -> dict:
        """Return a random question; refill + reshuffle pool when exhausted."""
        if not self._asked_pool:
            self._asked_pool = list(range(len(QUESTIONS)))
            random.shuffle(self._asked_pool)
        return QUESTIONS[self._asked_pool.pop()]

    # ── draw ──────────────────────────────────────────────────────────────────

    def draw(self, screen):
        is_preview = (self.state == S_PREVIEW)

        if self.is_circular:
            self.renderer.draw(
                screen, self.maze, self.player,
                timer=self.timer, mode=self.mode,
            )
        else:
            # FIX #3 — renderer receives lights_out + preview flags
            self.renderer.draw(
                screen, self.maze, self.player,
                timer=self.timer, mode=self.mode,
                lights_out=self.lights_out,
                preview=is_preview,
                preview_timer=self.preview_timer,
            )

        # ── Overlay layers ────────────────────────────────────────────────
        if self.state == S_QUIZ and self.quiz_popup:
            self.quiz_popup.draw(screen)

        elif self.state == S_PAUSED:               # FIX #6
            self.pause_screen.draw(screen)

        elif self.state == S_GAMEOVER and self.gameover_screen:
            self.gameover_screen.draw(screen)

        elif self.state == S_VICTORY and self.victory_screen:
            self.victory_screen.draw(screen)