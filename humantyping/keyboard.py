import unicodedata

import numpy as np

from .config import FAR_KEY_THRESHOLD


class KeyboardLayout:
    def __init__(self, layout_name: str = "qwerty") -> None:
        self.layout_name = layout_name
        self.grid = self._load_layout(layout_name)
        self.pos_map = self._build_pos_map()

        if layout_name == "azerty":
            self.direct_accents: set[str] = set("éèàùç")
            self.composed_accents: set[str] = set("âêîôûäëïöü")
        else:
            # QWERTY has no direct accent keys
            self.direct_accents = set()
            self.composed_accents = set("âêîôûäëïöüéèàùç")

    def _load_layout(self, name: str) -> list[list[str]]:
        if name == "qwerty":
            return [
                list("`1234567890-="),
                list("qwertyuiop[]\\"),
                list("asdfghjkl;'"),
                list("zxcvbnm,./")
            ]
        elif name == "azerty":
            return [
                list("&é\"'(-è_çà)="),
                list("azertyuiop^$"),
                list("qsdfghjklmù*"),
                list("wxcvbn,;:!")
            ]
        else:
            raise ValueError(f"Unsupported layout: {name!r}. Use 'qwerty' or 'azerty'.")

    def _build_pos_map(self) -> dict[str, tuple[int, int]]:
        mapping: dict[str, tuple[int, int]] = {}
        for r, row in enumerate(self.grid):
            for c, char in enumerate(row):
                mapping[char] = (r, c)

        # AZERTY: map digits to the same positions as row 0 characters
        if self.layout_name == "azerty":
            azerty_row0 = "&é\"'(-è_çà)"
            azerty_digits = "1234567890"
            for digit, base_char in zip(azerty_digits, azerty_row0):
                if base_char in mapping and digit not in mapping:
                    mapping[digit] = mapping[base_char]

        return mapping

    def _normalize_char(self, char: str) -> str:
        """Normalize a character for keyboard position lookup."""
        char = char.lower()
        if char in self.composed_accents:
            return ''.join(
                c for c in unicodedata.normalize('NFD', char)
                if unicodedata.category(c) != 'Mn'
            )
        return char

    def has_key(self, char: str) -> bool:
        """Check if a character exists on this keyboard layout."""
        return self._normalize_char(char) in self.pos_map

    def get_neighbor_keys(self, char: str) -> list[str]:
        """Return the neighboring keys for a given character."""
        normalized = self._normalize_char(char)

        if normalized not in self.pos_map:
            return []

        r, c = self.pos_map[normalized]
        neighbors = []

        deltas = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]

        for dr, dc in deltas:
            nr, nc = r + dr, c + dc
            if 0 <= nr < len(self.grid) and 0 <= nc < len(self.grid[nr]):
                neighbors.append(self.grid[nr][nc])

        return neighbors

    def get_distance(self, char1: str, char2: str) -> float:
        """Calculate the Euclidean distance between two keys."""
        norm1 = self._normalize_char(char1)
        norm2 = self._normalize_char(char2)

        if norm1 not in self.pos_map or norm2 not in self.pos_map:
            return FAR_KEY_THRESHOLD

        r1, c1 = self.pos_map[norm1]
        r2, c2 = self.pos_map[norm2]

        return np.sqrt((r1 - r2) ** 2 + (c1 - c2) ** 2)

    def get_random_neighbor(self, char: str) -> str:
        """Return a random neighboring key, preserving case."""
        was_upper = char.isupper()
        neighbors = self.get_neighbor_keys(char)
        if not neighbors:
            flat_grid = [c for row in self.grid for c in row]
            result = np.random.choice(flat_grid)
        else:
            result = np.random.choice(neighbors)
        return result.upper() if was_upper else result

    def is_direct_accent(self, char: str) -> bool:
        return char.lower() in self.direct_accents

    def is_composed_accent(self, char: str) -> bool:
        return char.lower() in self.composed_accents
