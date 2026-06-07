# models/player.py
# ─────────────────────────────────────────────────────────────────────────────
# Two player classes — one for rectangular grid mazes, one for circular mazes.
# Both share the same interface (lives, time_bonus, at_junction, lose_life).
#
# FIX #1 note:
#   CircularPlayer.move() simply forwards the direction string to
#   CircularMaze.can_move() which now contains the corrected logic.
#   No movement logic lives here — the maze is the single source of truth
#   for what moves are legal.
# ─────────────────────────────────────────────────────────────────────────────

from core.config import PLAYER_LIVES


# ════════════════════════════════════════════════════════════════════════════
#  Rectangular player
# ════════════════════════════════════════════════════════════════════════════

class Player:
    """Player navigating a rectangular grid Maze."""

    def __init__(self, row: int, col: int):
        self.row  = row
        self.col  = col
        self.lives = PLAYER_LIVES
        self.time_bonus = 0            # accumulated bonus seconds (cosmetic)
        self.visited_junctions: set = set()

    # ── movement ──────────────────────────────────────────────────────────────

    def move(self, dr: int, dc: int, maze) -> bool:
        """
        Attempt to move by (dr, dc).  Returns True if the move was legal.
        The maze is the authority on walkability.
        """
        nr, nc = self.row + dr, self.col + dc
        if maze.is_walkable(nr, nc):
            self.row, self.col = nr, nc
            return True
        return False

    # ── life management ───────────────────────────────────────────────────────

    def lose_life(self) -> bool:
        """Remove one life.  Returns True if the player is now dead (0 lives)."""
        self.lives = max(0, self.lives - 1)
        return self.lives <= 0

    # ── junction tracking ─────────────────────────────────────────────────────

    def at_junction(self, maze) -> bool:
        """
        Returns True once per junction cell — subsequent visits are ignored
        so the quiz popup is not re-triggered on the same cell.
        """
        pos = (self.row, self.col)
        if pos in self.visited_junctions:
            return False
        if maze.is_junction(self.row, self.col):
            self.visited_junctions.add(pos)
            return True
        return False

    # ── bonus ─────────────────────────────────────────────────────────────────

    def add_bonus(self, seconds: float):
        self.time_bonus += seconds


# ════════════════════════════════════════════════════════════════════════════
#  Circular player
# ════════════════════════════════════════════════════════════════════════════

class CircularPlayer:
    """
    Player navigating a CircularMaze.
    Position is (ring, sector).  Ring 0 = centre (goal), ring N-1 = outer start.

    FIX #1 — movement:
    Direction strings ('out', 'in', 'cw', 'ccw') are forwarded directly to
    CircularMaze.can_move() which now applies the corrected direction semantics.
    """

    def __init__(self, ring: int, sector: int):
        self.ring   = ring
        self.sector = sector
        self.lives  = PLAYER_LIVES
        self.time_bonus = 0
        self.visited_junctions: set = set()

    # ── movement ──────────────────────────────────────────────────────────────

    def move(self, direction: str, maze) -> bool:
        """
        Ask the maze whether movement in `direction` is possible.
        'out' / 'in' / 'cw' / 'ccw' — see CircularMaze.can_move() for details.
        Returns True if the move succeeded.
        """
        result = maze.can_move(self.ring, self.sector, direction)
        if result is not None:
            self.ring, self.sector = result
            return True
        return False

    # ── life management ───────────────────────────────────────────────────────

    def lose_life(self) -> bool:
        self.lives = max(0, self.lives - 1)
        return self.lives <= 0

    # ── junction tracking ─────────────────────────────────────────────────────

    def at_junction(self, maze) -> bool:
        pos = (self.ring, self.sector)
        if pos in self.visited_junctions:
            return False
        if maze.is_junction(self.ring, self.sector):
            self.visited_junctions.add(pos)
            return True
        return False

    # ── bonus ─────────────────────────────────────────────────────────────────

    def add_bonus(self, seconds: float):
        self.time_bonus += seconds