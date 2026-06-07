# models/maze.py
# ─────────────────────────────────────────────────────────────────────────────
# Two maze classes:
#
#   Maze          — rectangular grid, DFS-generated.
#                   FIX #5: _add_confusion() carves extra dead-end stubs so
#                   the layout has many false turns but only ONE solution path.
#
#   CircularMaze  — polar/concentric maze, DFS-generated.
#                   FIX #1: can_move() has correct directional semantics:
#                     'out'  → ring index increases (toward outer boundary)
#                     'in'   → ring index decreases (toward centre)
#                     'cw'   → sector index increases (clockwise)
#                     'ccw'  → sector index decreases (counter-clockwise)
#                   Visual wall drawing is handled by CircularRenderer;
#                   this class only stores which walls exist.
# ─────────────────────────────────────────────────────────────────────────────

import random
import math
from core.config import CONFUSION_STUB_RATIO


# ════════════════════════════════════════════════════════════════════════════
#  RECTANGULAR MAZE
# ════════════════════════════════════════════════════════════════════════════

class Maze:
    """
    Rectangular grid maze.
    grid[r][c] == 1  →  wall
    grid[r][c] == 0  →  open path

    Generation strategy (FIX #5 — high confusion):
      1. Standard recursive DFS carver — guarantees exactly ONE solution path
         from start to goal.
      2. _add_confusion(): finds wall cells that touch exactly one open cell
         (dead-end-stub candidates) and opens a fraction of them.  Because
         these stubs are single-cell cul-de-sacs they NEVER create an
         alternative route to the goal — they only mislead the player.
    """

    def __init__(self, rows: int = 21, cols: int = 21, seed=None):
        self.rows  = rows
        self.cols  = cols
        self._rng  = random.Random(seed)
        self.grid  = [[1] * cols for _ in range(rows)]
        self.start = (1, 1)
        self.goal  = (rows - 2, cols - 2)
        self.junctions: set = set()

        self._dfs_generate()
        self._add_confusion()        # FIX #5
        self._find_junctions()

    # ── generation ───────────────────────────────────────────────────────────

    def _dfs_generate(self):
        """
        Iterative DFS (recursive back-tracker).
        Moves in steps of 2 so every carved cell is surrounded by wall cells
        — this preserves the guarantee of a single solution path.
        """
        sr, sc = self.start
        self.grid[sr][sc] = 0
        stack   = [(sr, sc)]
        visited = {(sr, sc)}

        while stack:
            r, c = stack[-1]
            nbrs = self._unvisited_neighbors(r, c, visited)
            if nbrs:
                nr, nc = self._rng.choice(nbrs)
                # Carve the wall cell between current and chosen neighbor
                self.grid[(r + nr) // 2][(c + nc) // 2] = 0
                self.grid[nr][nc] = 0
                visited.add((nr, nc))
                stack.append((nr, nc))
            else:
                stack.pop()

        # Make sure goal cell is open
        self.grid[self.goal[0]][self.goal[1]] = 0

    def _unvisited_neighbors(self, r: int, c: int, visited: set):
        neighbors = []
        for dr, dc in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            nr, nc = r + dr, c + dc
            if (1 <= nr < self.rows - 1 and
                    1 <= nc < self.cols - 1 and
                    (nr, nc) not in visited):
                neighbors.append((nr, nc))
        return neighbors

    # ── FIX #5 — confusion stubs ──────────────────────────────────────────────

    def _add_confusion(self):
        """
        Carve a fraction of wall cells that have exactly one open neighbour
        into open path cells.  Each new cell is a dead-end — it has no
        further open exits — so it can never form an alternative route.
        The player is tricked into entering dead alleys.
        """
        candidates = []
        for r in range(1, self.rows - 1):
            for c in range(1, self.cols - 1):
                if self.grid[r][c] == 1:
                    open_nbr = self._count_open_neighbors(r, c)
                    if open_nbr == 1:
                        candidates.append((r, c))

        self._rng.shuffle(candidates)
        quota = int(len(candidates) * CONFUSION_STUB_RATIO)
        for r, c in candidates[:quota]:
            self.grid[r][c] = 0   # open the dead-end stub

    # ── junction detection ────────────────────────────────────────────────────

    def _find_junctions(self):
        """
        A junction is any open cell with ≥3 open cardinal neighbours,
        excluding the start and goal cells.
        """
        self.junctions = set()
        for r in range(self.rows):
            for c in range(self.cols):
                if (self.grid[r][c] == 0
                        and (r, c) not in (self.start, self.goal)
                        and self._count_open_neighbors(r, c) >= 3):
                    self.junctions.add((r, c))

    def _count_open_neighbors(self, r: int, c: int) -> int:
        count = 0
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                if self.grid[nr][nc] == 0:
                    count += 1
        return count

    # ── public queries ────────────────────────────────────────────────────────

    def is_walkable(self, row: int, col: int) -> bool:
        return (0 <= row < self.rows and
                0 <= col < self.cols and
                self.grid[row][col] == 0)

    def is_junction(self, row: int, col: int) -> bool:
        return (row, col) in self.junctions


# ════════════════════════════════════════════════════════════════════════════
#  CIRCULAR MAZE
# ════════════════════════════════════════════════════════════════════════════

class CircularMaze:
    """
    Radial labyrinth built from concentric rings divided into sectors.

    Ring 0        = innermost (centre) — this is the GOAL.
    Ring rings-1  = outermost           — this is the START.

    Wall representation (two sets of frozensets):
      radial_walls   : (ring, sec)  — wall on the CW edge of sector `sec`
                                      i.e. between sec and sec+1
      circular_walls : (ring, sec)  — wall on the OUTER edge of (ring, sec)
                                      i.e. between ring and ring+1

    FIX #1 — can_move() direction mapping:
      'out'  →  ring+1   (away from centre, visually outward)
      'in'   →  ring-1   (toward centre)
      'cw'   →  sec+1    (clockwise)
      'ccw'  →  sec-1    (counter-clockwise)
    """

    def __init__(self, rings: int = 7, base_sectors: int = 12, seed=None):
        self.rings        = rings
        self.base_sectors = base_sectors
        self._rng         = random.Random(seed)

        # Sectors per ring — inner rings have fewer sectors so cells
        # stay roughly the same angular size across rings.
        self.spr = []     # sectors_per_ring
        for i in range(rings):
            if i == 0:
                self.spr.append(max(4, base_sectors // 4))
            elif i < 2:
                self.spr.append(max(6, base_sectors // 2))
            elif i < 4:
                self.spr.append(base_sectors)
            else:
                self.spr.append(base_sectors * 2)

        self.radial_walls   = set()   # (ring, sec)
        self.circular_walls = set()   # (ring, sec)
        self.junctions      = set()

        self._init_all_walls()
        self._dfs_generate()
        self._find_junctions()

        self.start = (rings - 1, 0)   # outermost ring, sector 0
        self.goal  = (0, 0)           # centre cell

    # ── wall initialisation ───────────────────────────────────────────────────

    def _init_all_walls(self):
        """Begin with every wall present; DFS will selectively remove them."""
        for ring in range(self.rings):
            for sec in range(self.spr[ring]):
                self.radial_walls.add((ring, sec))
                if ring < self.rings - 1:
                    self.circular_walls.add((ring, sec))

    # ── neighbor enumeration ──────────────────────────────────────────────────

    def _neighbors(self, ring: int, sec: int):
        """
        Return list of (new_ring, new_sec, wall_type, wall_key) tuples
        for all four logical directions from (ring, sec).

        wall_type: 'r' = radial wall separating two sectors on the same ring
                   'c' = circular wall separating two adjacent rings
        wall_key : the (ring, sec) tuple that indexes the relevant wall set
        """
        s = self.spr[ring]
        result = []

        # ── Clockwise (same ring, sec+1) ──────────────────────────────
        right = (sec + 1) % s
        result.append((ring, right, 'r', (ring, sec)))

        # ── Counter-clockwise (same ring, sec-1) ──────────────────────
        left = (sec - 1) % s
        result.append((ring, left, 'r', (ring, left)))

        # ── Inward (ring-1, toward centre) ────────────────────────────
        # The inner ring has fewer sectors; map proportionally.
        if ring > 0:
            si = self.spr[ring - 1]
            inner_sec = int(sec * si / s) % si
            # Wall key: the OUTER edge of the inner cell = (ring-1, inner_sec)
            result.append((ring - 1, inner_sec, 'c', (ring - 1, inner_sec)))

        # ── Outward (ring+1, away from centre) ────────────────────────
        if ring < self.rings - 1:
            so = self.spr[ring + 1]
            outer_sec = int(sec * so / s) % so
            # Wall key: the OUTER edge of the current cell = (ring, sec)
            result.append((ring + 1, outer_sec, 'c', (ring, sec)))

        return result

    # ── DFS generation ────────────────────────────────────────────────────────

    def _dfs_generate(self):
        """
        Iterative DFS from the start cell (outermost ring, sector 0).
        Removes walls as it carves — guarantees a single spanning tree
        (exactly ONE path between any two cells).
        """
        start   = (self.rings - 1, 0)
        visited = {start}
        stack   = [start]

        while stack:
            ring, sec = stack[-1]
            nbrs = self._neighbors(ring, sec)
            self._rng.shuffle(nbrs)
            moved = False
            for nr, ns, wtype, wkey in nbrs:
                if (nr, ns) not in visited:
                    # Remove the wall between current cell and neighbor
                    if wtype == 'r':
                        self.radial_walls.discard(wkey)
                    else:
                        self.circular_walls.discard(wkey)
                    visited.add((nr, ns))
                    stack.append((nr, ns))
                    moved = True
                    break
            if not moved:
                stack.pop()

    # ── junction detection ────────────────────────────────────────────────────

    def _count_open(self, ring: int, sec: int) -> int:
        """Count open passages (no wall) out of (ring, sec)."""
        count = 0
        for nr, ns, wtype, wkey in self._neighbors(ring, sec):
            wall_set = (self.radial_walls if wtype == 'r'
                        else self.circular_walls)
            if wkey not in wall_set:
                count += 1
        return count

    def _find_junctions(self):
        self.junctions = set()
        for ring in range(self.rings):
            for sec in range(self.spr[ring]):
                if self._count_open(ring, sec) >= 3:
                    self.junctions.add((ring, sec))

    def is_junction(self, ring: int, sec: int) -> bool:
        return (ring, sec) in self.junctions

    # ── FIX #1 — corrected movement ───────────────────────────────────────────

    def can_move(self, ring: int, sec: int, direction: str):
        """
        Check whether the player can move from (ring, sec) in `direction`.
        Returns (new_ring, new_sec) if the passage is open, else None.

        Direction semantics (corrected from original — FIX #1):
          'out'  → ring increases  (UP key   → move toward outer edge)
          'in'   → ring decreases  (DOWN key → move toward centre / goal)
          'cw'   → sec increases   (RIGHT key → clockwise along arc)
          'ccw'  → sec decreases   (LEFT key  → counter-clockwise)
        """
        s = self.spr[ring]

        if direction == 'cw':
            ns = (sec + 1) % s
            # Wall on CW edge of current sector
            if (ring, sec) not in self.radial_walls:
                return (ring, ns)
            return None

        if direction == 'ccw':
            ns = (sec - 1) % s
            # Wall on CW edge of LEFT sector (which is the CCW boundary of sec)
            if (ring, ns) not in self.radial_walls:
                return (ring, ns)
            return None

        if direction == 'out':   # UP key — move AWAY from centre
            if ring < self.rings - 1:
                so = self.spr[ring + 1]
                outer_sec = int(sec * so / s) % so
                # Wall: outer edge of current cell
                if (ring, sec) not in self.circular_walls:
                    return (ring + 1, outer_sec)
            return None

        if direction == 'in':    # DOWN key — move TOWARD centre
            if ring > 0:
                si = self.spr[ring - 1]
                inner_sec = int(sec * si / s) % si
                # Wall: outer edge of the inner cell (which borders us)
                if (ring - 1, inner_sec) not in self.circular_walls:
                    return (ring - 1, inner_sec)
            return None

        return None