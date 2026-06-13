# core/config.py
# ─────────────────────────────────────────────────────────────────────────────
# Central constants for Maze Quest.
# Every tunable value lives here so other modules never use magic numbers.
# ─────────────────────────────────────────────────────────────────────────────

# ── Window ────────────────────────────────────────────────────────────────────
SCREEN_WIDTH  = 900          # fixed — never force-resize the desktop
SCREEN_HEIGHT = 700
HUD_HEIGHT    = 60           # top bar reserved for timer / lives / pause btn
FPS           = 60

# ── Normal rectangular grid ───────────────────────────────────────────────────
CELL_SIZE = 28
ROWS      = 21
COLS      = 21

# ── Ultimate Challenge — large scrolling map ──────────────────────────────────
# FIX #2 — camera scroll: the map is much larger than the window.
# The renderer uses cam_x/cam_y to show only the visible slice.
ULT_ROWS      = 41
ULT_COLS      = 41
ULT_CELL_SIZE = 22           # slightly smaller cell so density feels right

# ── Circular maze ─────────────────────────────────────────────────────────────
# FIX #1 — polar movement is corrected in CircularMaze.can_move()
CIRCULAR_RINGS        = 7
CIRCULAR_BASE_SECTORS = 12
CIRCULAR_RING_WIDTH   = 42   # pixel width of each concentric band

# ── FPS ───────────────────────────────────────────────────────────────────────

# ── Colour palette — dark teal theme ─────────────────────────────────────────
BG_COLOR       = (15,  28,  38)
WALL_COLOR     = (55, 120, 175)
PATH_COLOR     = (20,  40,  55)
PLAYER_COLOR   = (220, 190,  55)
GOAL_COLOR     = (50,  200, 100)
START_COLOR    = (80,  160, 220)
HUD_BG         = ( 8,  18,  28)
HEART_COLOR    = (220,  65,  85)
TEXT_COLOR     = (215, 232, 245)
ACCENT         = ( 75, 205, 178)
CORRECT_COLOR  = (50,  200, 100)
WRONG_COLOR    = (220,  65,  85)
CHECKPOINT_DOT = (220, 190,  55)
CARD_BG        = ( 22,  46,  62)
CARD_BORDER    = ( 55, 120, 175)
GRAY           = (100, 118, 130)
DARK_GRAY      = ( 38,  55,  65)
PAUSE_COLOR    = ( 55, 185, 220)

WHITE = (255, 255, 255)
BLACK = (  0,   0,   0)
GREEN = ( 50, 200, 100)
RED   = (220,  65,  85)
BLUE  = ( 60, 130, 180)

# ── Game mode IDs ─────────────────────────────────────────────────────────────
MODE_TIME_ATTACK = "Time Attack"
MODE_LIGHTS_OUT  = "Lights Out"
MODE_ULTIMATE    = "Ultimate Challenge"
MODE_CIRCULAR    = "Circular Maze"

# ── Per-mode countdown timers (seconds) ──────────────────────────────────────
TIMER_TIME_ATTACK = 180
TIMER_LIGHTS_OUT  = 180
TIMER_ULTIMATE    = 300
TIMER_CIRCULAR    = 240

# ── Player ────────────────────────────────────────────────────────────────────
PLAYER_LIVES  = 5
PLAYER_RADIUS = CELL_SIZE // 2 - 3   # visual radius for rectangular mode

# ── Quiz — FIX #4 ─────────────────────────────────────────────────────────────
# Countdown inside popup scaled by difficulty.
QUIZ_TIME_EASY   = 10.0   # seconds before auto-close
QUIZ_TIME_MEDIUM = 15.0
QUIZ_TIME_HARD   = 20.0
QUIZ_RESULT_SHOW = 3.0    # seconds the correct/wrong banner stays visible
QUIZ_TIMEOUT_SHOW= 2.0    # seconds the "Time Out!" overlay stays visible

# Bonus time awarded for a correct answer
BONUS_EASY = 10
BONUS_HARD = 20

# ── Lights-Out — FIX #3 ───────────────────────────────────────────────────────
LIGHTS_OUT_PREVIEW_S = 3.0    # full-visibility preview duration
LIGHTS_OUT_RADIUS_PX = 110    # pixel radius of the light circle around player

# ── Maze confusion — FIX #5 ───────────────────────────────────────────────────
# Fraction of eligible wall cells converted into dead-end stubs.
CONFUSION_STUB_RATIO = 0.28



# ── App Version ───────────────────────────────────────────
# NOTE: This value is auto-managed by scripts/version_sync.py.
# Do not edit by hand — run `task version:sync` (or
# `task version:patch` / `:minor` / `:major`) to update it
# everywhere at once (VERSION file, pyproject.toml, here).
APP_VERSION = "1.0.1"