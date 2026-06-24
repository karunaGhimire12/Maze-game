"""Question engine and generated internal question bank for Maze Quest.

The public API intentionally stays small:
    QUESTIONS             -> full 700-question list
    QuestionDeck          -> shuffled, non-repeating question source
    bonus_for_difficulty  -> reward-time lookup
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from core.config import (
    DIFF_EASY, DIFF_MEDIUM, DIFF_HARD, DIFFICULTIES,
    BONUS_BY_DIFFICULTY,
)


def _question(q: str, a: str, opts: list[str], diff: str, category: str) -> dict:
    opts = [str(x) for x in opts]
    if a not in opts:
        opts = [a, *opts[:3]]
    return {"q": q, "a": str(a), "opts": opts[:4], "diff": diff, "category": category}


def _math_easy() -> list[dict]:
    items = []
    for i in range(1, 126):
        a = 2 + (i * 3) % 18
        b = 1 + (i * 5) % 16
        ans = a + b
        opts = [ans, ans + 1, max(0, ans - 2), ans + 3]
        items.append(_question(f"{a} + {b} = ?", str(ans), [str(o) for o in opts], DIFF_EASY, "math"))
    return items


def _math_medium() -> list[dict]:
    items = []
    for i in range(1, 126):
        a = 6 + (i * 7) % 24
        b = 2 + (i * 5) % 11
        if i % 3 == 0:
            ans = a * b
            q = f"{a} x {b} = ?"
            opts = [ans, ans + b, ans - b, ans + a]
        elif i % 3 == 1:
            ans = a * b + b
            q = f"{a * b} + {b} = ?"
            opts = [ans, ans - a, ans + a, ans + 2]
        else:
            ans = a
            q = f"{a * b} / {b} = ?"
            opts = [ans, ans + 1, max(1, ans - 1), ans + 3]
        items.append(_question(q, str(ans), [str(o) for o in opts], DIFF_MEDIUM, "math"))
    return items


def _math_hard() -> list[dict]:
    items = []
    for i in range(1, 101):
        n = 3 + (i % 14)
        if i % 4 == 0:
            ans = n * n
            q = f"{n}^2 = ?"
            opts = [ans, ans + n, ans - n, ans + 2 * n]
        elif i % 4 == 1:
            ans = n
            q = f"sqrt({n * n}) = ?"
            opts = [ans, ans + 1, max(1, ans - 2), ans + 3]
        elif i % 4 == 2:
            ans = 2 ** (3 + i % 5)
            q = f"2^{3 + i % 5} = ?"
            opts = [ans, ans // 2, ans * 2, ans + 8]
        else:
            ans = (n * (n + 1)) // 2
            q = f"Sum of 1 to {n} = ?"
            opts = [ans, ans + n, ans - 1, ans + 2]
        items.append(_question(q, str(ans), [str(o) for o in opts], DIFF_HARD, "math"))
    return items


_GK_EASY = [
    ("Capital of France?", "Paris", ["Paris", "Rome", "Berlin", "Madrid"]),
    ("Largest planet?", "Jupiter", ["Mars", "Jupiter", "Venus", "Mercury"]),
    ("H2O is commonly called?", "Water", ["Water", "Salt", "Oxygen", "Sugar"]),
    ("How many continents are there?", "7", ["5", "6", "7", "8"]),
    ("Which animal is known as man's best friend?", "Dog", ["Dog", "Cat", "Horse", "Cow"]),
    ("What color do you get by mixing red and white?", "Pink", ["Pink", "Green", "Black", "Blue"]),
    ("Which day comes after Friday?", "Saturday", ["Sunday", "Monday", "Saturday", "Thursday"]),
    ("How many hours are in a day?", "24", ["12", "18", "24", "30"]),
    ("Which shape has three sides?", "Triangle", ["Square", "Circle", "Triangle", "Hexagon"]),
    ("Which ocean is the largest?", "Pacific", ["Atlantic", "Pacific", "Indian", "Arctic"]),
]

_GK_MEDIUM = [
    ("Chemical symbol for gold?", "Au", ["Ag", "Au", "Fe", "Go"]),
    ("Year World War II ended?", "1945", ["1943", "1944", "1945", "1946"]),
    ("Who invented the telephone?", "Bell", ["Edison", "Tesla", "Bell", "Morse"]),
    ("What gas do plants absorb?", "Carbon dioxide", ["Oxygen", "Nitrogen", "Carbon dioxide", "Helium"]),
    ("Smallest prime number?", "2", ["0", "1", "2", "3"]),
    ("Boiling point of water in Celsius?", "100", ["90", "95", "100", "110"]),
    ("Which planet is known as the Red Planet?", "Mars", ["Mars", "Venus", "Saturn", "Neptune"]),
    ("What is the hardest natural substance?", "Diamond", ["Iron", "Diamond", "Quartz", "Copper"]),
    ("How many bones are in an adult human body?", "206", ["196", "206", "216", "226"]),
    ("Which instrument measures earthquakes?", "Seismograph", ["Barometer", "Seismograph", "Thermometer", "Compass"]),
]

_GK_HARD = [
    ("DNA stands for?", "Deoxyribonucleic Acid", ["Deoxyribonucleic Acid", "Digital Nucleic Acid", "Dense Neural Array", "Dynamic Numeric Acid"]),
    ("Who proposed general relativity?", "Einstein", ["Newton", "Einstein", "Curie", "Darwin"]),
    ("What is the SI unit of electric current?", "Ampere", ["Volt", "Ohm", "Ampere", "Watt"]),
    ("Which empire built Machu Picchu?", "Inca", ["Maya", "Aztec", "Inca", "Roman"]),
    ("What is the pH of a neutral solution?", "7", ["5", "6", "7", "8"]),
    ("Which layer of Earth is liquid iron and nickel?", "Outer core", ["Crust", "Mantle", "Outer core", "Inner core"]),
    ("What is the study of fungi called?", "Mycology", ["Botany", "Mycology", "Zoology", "Geology"]),
    ("Which language family includes Sanskrit?", "Indo-European", ["Sino-Tibetan", "Indo-European", "Afroasiatic", "Austronesian"]),
    ("What is Avogadro's number approximately?", "6.02 x 10^23", ["3.14", "9.81", "6.02 x 10^23", "1.60 x 10^-19"]),
    ("Which theorem relates sides of a right triangle?", "Pythagorean theorem", ["Bayes theorem", "Pythagorean theorem", "Fermat theorem", "Euler theorem"]),
]


def _expand_gk(seed_items: list[tuple[str, str, list[str]]], diff: str, target: int) -> list[dict]:
    items = []
    n = 0
    while len(items) < target:
        q, a, opts = seed_items[n % len(seed_items)]
        suffix = "" if n < len(seed_items) else f" #{n // len(seed_items) + 1}"
        items.append(_question(f"{q}{suffix}", a, opts, diff, "general"))
        n += 1
    return items


def _build_questions() -> list[dict]:
    questions = []
    questions.extend(_math_easy())
    questions.extend(_math_medium())
    questions.extend(_math_hard())
    questions.extend(_expand_gk(_GK_EASY, DIFF_EASY, 109))
    questions.extend(_expand_gk(_GK_MEDIUM, DIFF_MEDIUM, 109))
    questions.extend(_expand_gk(_GK_HARD, DIFF_HARD, 132))
    assert len(questions) == 700
    return questions


QUESTIONS = _build_questions()


def bonus_for_difficulty(diff: str) -> int:
    return BONUS_BY_DIFFICULTY.get(diff, BONUS_BY_DIFFICULTY[DIFF_EASY])


@dataclass
class QuestionDeck:
    """Shuffled non-repeating source, optionally pinned to one difficulty."""

    difficulty: str | None = None
    rng: random.Random = field(default_factory=random.Random)
    _pool: list[dict] = field(default_factory=list)

    def _eligible(self) -> list[dict]:
        if self.difficulty in DIFFICULTIES:
            return [q for q in QUESTIONS if q["diff"] == self.difficulty]
        return list(QUESTIONS)

    def next(self) -> dict:
        if not self._pool:
            self._pool = self._eligible()
            self.rng.shuffle(self._pool)
        q = dict(self._pool.pop())
        opts = list(q["opts"])
        self.rng.shuffle(opts)
        q["opts"] = opts
        return q
