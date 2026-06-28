# core/game.py
# ─────────────────────────────────────────────────────────────────────────────
# Central Game class — owns state machine, connects maze/player/renderer/
# ─────────────────────────────────────────────────────────────────────────────
# Main Game Controller
#
# This file is the heart of the Maze Quest game.
#
# The Game class manages everything that happens during gameplay.
# It connects all other parts of the game together, such as:
#
# • Maze generation
# • Player movement
# • Renderer (drawing everything on the screen)
# • Timer and lives
# • Quiz popup system
# • Pause menu
# • Game Over screen
# • Victory screen
#
# It also controls the game's different states.
# ─────────────────────────────────────────────────────────────────────────────

import pygame

from core.config import (
    MODE_TIME_ATTACK, MODE_LIGHTS_OUT, MODE_ULTIMATE, MODE_CIRCULAR,
    TIMER_TIME_ATTACK, TIMER_LIGHTS_OUT, TIMER_ULTIMATE, TIMER_CIRCULAR,
    DIFFICULTY_TIMERS, DIFFICULTY_LABELS,
    ROWS, COLS, ULT_ROWS, ULT_COLS, ULT_CELL_SIZE, CELL_SIZE,
    CIRCULAR_RINGS, CIRCULAR_BASE_SECTORS,
    LIGHTS_OUT_PREVIEW_S,
    PLAYER_LIVES,
)
from models.maze   import Maze, CircularMaze
from models.player import Player, CircularPlayer
from views.renderer import Renderer, CircularRenderer
from views.screens  import (
    QuizPopup, PauseScreen, GameOverScreen, VictoryScreen,
)
from data.questions import QuestionDeck, bonus_for_difficulty


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

    def __init__(self, mode: str, difficulty: str | None = None):
        self.mode        = mode
        self.difficulty  = difficulty
        self.is_circular = (mode == MODE_CIRCULAR)
        self._auto_dir   = None
        self._touch_start = None
        self._missed_questions = 0

        self._build_maze()
        self._reset_run_state(reset_player=False)

    def _build_maze(self):
        if self.mode == MODE_ULTIMATE:
            self.maze     = Maze(rows=ULT_ROWS, cols=ULT_COLS)
            self.player   = Player(*self.maze.start)
            self.renderer = Renderer(cell_size=ULT_CELL_SIZE)

        elif self.mode == MODE_CIRCULAR:
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

    def _base_timer(self):
        if self.mode in DIFFICULTY_TIMERS and self.difficulty:
            return DIFFICULTY_TIMERS[self.mode].get(self.difficulty, TIMER_TIME_ATTACK)
        _timers = {
            MODE_TIME_ATTACK: TIMER_TIME_ATTACK,
            MODE_LIGHTS_OUT:  TIMER_LIGHTS_OUT,
            MODE_ULTIMATE:    TIMER_ULTIMATE,
            MODE_CIRCULAR:    TIMER_CIRCULAR,
        }
        return _timers.get(self.mode, TIMER_TIME_ATTACK)

    def _reset_run_state(self, reset_player: bool = True):
        if reset_player:
            self.player.reset_to(*self.maze.start)
            self.player.lives = PLAYER_LIVES
            self.player.time_bonus = 0

        # ── Countdown timer ───────────────────────────────────────────────
        self.timer = float(self._base_timer())

        # ── Lights-Out state  (FIX #3) ───────────────────────────────────
        self.lights_out    = (self.mode == MODE_LIGHTS_OUT)
        self.preview_timer = LIGHTS_OUT_PREVIEW_S if self.lights_out else 0.0
        self.state         = S_PREVIEW if self.lights_out else S_PLAYING

        # ── Quiz state  (FIX #4) ─────────────────────────────────────────
        self.quiz_popup  = None
        deck_diff = self.difficulty if self.mode in (MODE_TIME_ATTACK, MODE_CIRCULAR) else None
        self.question_deck = QuestionDeck(deck_diff)
        self._missed_questions = 0
        self._auto_dir = None

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
                bonus = bonus_for_difficulty(diff)
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
                if self.quiz_popup.timed_out():
                    self._missed_questions += 1
                    if self._missed_questions >= 2:
                        self._missed_questions = 0
                        if self.player.lose_life():
                            self.quiz_popup = None
                            self._trigger_game_over("out_of_lives")
                            return
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

        arrived = self.player.update(dt)
        if arrived:
            self._on_cell_arrival()
            if self.state != S_PLAYING:
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
                self._reset_run_state(reset_player=True)
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
            if action in ("continue", "retry"):
                self._build_maze()
                self._reset_run_state(reset_player=False)
            elif action == "menu":
                return "menu"
            return

        if self.state == S_PLAYING and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._touch_start = event.pos
            return

        if self.state == S_PLAYING and event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._touch_start:
                sx, sy = self._touch_start
                ex, ey = event.pos
                dx, dy = ex - sx, ey - sy
                if abs(dx) > 28 or abs(dy) > 28:
                    if abs(dx) > abs(dy):
                        self._request_move((0, 1), "cw") if dx > 0 else self._request_move((0, -1), "ccw")
                    else:
                        self._request_move((-1, 0), "out") if dy < 0 else self._request_move((1, 0), "in")
            self._touch_start = None
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
                    self._request_move((-1, 0), "out")
                elif event.key in (pygame.K_DOWN,  pygame.K_s):
                    self._request_move((1, 0), "in")
                elif event.key in (pygame.K_LEFT,  pygame.K_a):
                    self._request_move((0, -1), "ccw")
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._request_move((0, 1), "cw")

    # ── movement helper ───────────────────────────────────────────────────────

    def _request_move(self, rect_dir, circ_dir: str):
        """Start a move if the ball is idle; auto-glide continues after arrival."""
        if self.state != S_PLAYING or self.player.is_moving():
            return

        self._auto_dir = (rect_dir, circ_dir)
        self._move_one(rect_dir, circ_dir)

    def _move_one(self, rect_dir, circ_dir: str):
        if self.is_circular:
            moved = self.player.move(circ_dir, self.maze)
        else:
            dr, dc = rect_dir
            moved = self.player.move(dr, dc, self.maze)

        if not moved:
            self._auto_dir = None
        return moved

    def _on_cell_arrival(self):
        if self._at_goal():
            self._auto_dir = None
            self._trigger_victory()
            return

        if self.player.at_junction(self.maze):
            self._auto_dir = None
            self._trigger_quiz()
            return

        if self._auto_dir and self._should_continue_forward():
            rect_dir, circ_dir = self._auto_dir
            self._move_one(rect_dir, circ_dir)
        else:
            self._auto_dir = None

    def _should_continue_forward(self) -> bool:
        rect_dir, circ_dir = self._auto_dir
        if self.is_circular:
            openings = self.maze.open_directions(self.player.ring, self.player.sector)
            return len(openings) <= 2 and circ_dir in openings

        openings = self.maze.open_directions(self.player.row, self.player.col)
        return len(openings) <= 2 and rect_dir in openings

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
        label = self.mode
        if self.difficulty:
            label = f"{self.mode} - {DIFFICULTY_LABELS.get(self.difficulty, self.difficulty.title())}"
        self.victory_screen = VictoryScreen(
            time_left=self.timer, mode=label)
        self.state = S_VICTORY

    def _pick_question(self) -> dict:
        return self.question_deck.next()

    # ── draw ──────────────────────────────────────────────────────────────────

    def draw(self, screen):
        is_preview = (self.state == S_PREVIEW)

        if self.is_circular:
            self.renderer.draw(
                screen, self.maze, self.player,
                timer=self.timer, mode=self._display_mode(),
            )
        else:
            # FIX #3 — renderer receives lights_out + preview flags
            self.renderer.draw(
                screen, self.maze, self.player,
                timer=self.timer, mode=self._display_mode(),
                lights_out=self.lights_out,
                preview=is_preview,
                preview_timer=self.preview_timer,
            )

        # ── Overlay layers ────────────────────────────────────────────────
        if self.state == S_QUIZ and self.quiz_popup:
            self.quiz_popup.draw(screen)

        elif self.state == S_PAUSED:              
            self.pause_screen.draw(screen)

        elif self.state == S_GAMEOVER and self.gameover_screen:
            self.gameover_screen.draw(screen)

        elif self.state == S_VICTORY and self.victory_screen:
            self.victory_screen.draw(screen)

    def _display_mode(self):
        if self.difficulty:
            return f"{self.mode} - {DIFFICULTY_LABELS.get(self.difficulty, self.difficulty.title())}"
        return self.mode
