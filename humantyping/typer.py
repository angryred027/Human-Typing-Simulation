from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field

from .config import (
    DEFAULT_WPM, WPM_STD, AVG_WORD_LENGTH,
    PROB_ERROR, PROB_SWAP_ERROR, PROB_NOTICE_ERROR,
    PROB_MISSED_SHIFT, PROB_SHIFT_HELD,
    PROB_OMISSION, PROB_INSERTION, PROB_DOUBLING,
    SPEED_BOOST_COMMON_WORD, SPEED_PENALTY_COMPLEX_WORD,
    SPEED_BOOST_CLOSE_KEYS, SPEED_BOOST_BIGRAM,
    TIME_KEYSTROKE_STD, TIME_BACKSPACE_MEAN, TIME_BACKSPACE_STD,
    TIME_REACTION_MEAN, TIME_REACTION_STD, TIME_ARROW_MEAN, TIME_ARROW_STD,
    TIME_DIRECT_ACCENT_PENALTY, TIME_COMPOSED_ACCENT_PENALTY,
    TIME_UPPERCASE_PENALTY, TIME_SPACE_PAUSE_MEAN, TIME_SPACE_PAUSE_STD,
    FATIGUE_FACTOR, FATIGUE_CAP,
    DRIFT_CORRECTION_PROB, PROB_WORD_LEVEL_CORRECTION, COMPLEX_WORD_ERROR_MULT,
    COMMON_WORD_ERROR_MULT, COMPOSED_ACCENT_ERROR_MULT, PUNCTUATION_ERROR_MULT,
    FAR_KEY_PENALTY, FAR_KEY_THRESHOLD, CLOSE_KEY_THRESHOLD,
    MIN_KEYSTROKE_TIME, MIN_REACTION_TIME, MIN_BACKSPACE_TIME, MIN_ARROW_TIME,
    MIN_SPEED_MULTIPLIER,
)
from .keyboard import KeyboardLayout
from .language import get_word_difficulty, is_common_bigram


@dataclass
class TypingState:
    current_text: str = ""
    target_text: str = ""
    total_time: float = 0.0
    history: list[tuple[float, str, str]] = field(default_factory=list)
    last_char_typed: str | None = None
    fatigue_multiplier: float = 1.0
    mental_cursor_pos: int = 0
    caret_pos: int = 0
    word_fix_pos: int | None = None
    word_fix_phase: str = "seek"


class MarkovTyper:
    def __init__(self, target_text: str, target_wpm: float = DEFAULT_WPM, layout: str = "qwerty"):
        if not isinstance(target_text, str) or len(target_text) == 0:
            raise ValueError("target_text must be a non-empty string")
        if not isinstance(target_wpm, (int, float)) or target_wpm <= 0:
            raise ValueError("target_wpm must be a positive number")

        self.target_text = target_text
        self.keyboard = KeyboardLayout(layout)
        self.state = TypingState(target_text=target_text)

        self.session_wpm = np.random.normal(target_wpm, WPM_STD)
        self.session_wpm = max(10, self.session_wpm)
        self.base_keystroke_time = 60 / (self.session_wpm * AVG_WORD_LENGTH)

        self.state.history.append((0.0, f"INIT (WPM: {self.session_wpm:.1f})", ""))

    def _get_current_word_context(self) -> str | None:
        idx = self.state.mental_cursor_pos
        if idx >= len(self.target_text):
            return None
        start = idx
        while start > 0 and self.target_text[start - 1] != ' ':
            start -= 1
        end = idx
        while end < len(self.target_text) and self.target_text[end] != ' ':
            end += 1
        return self.target_text[start:end]

    def _calculate_keystroke_time(self, char_to_type: str) -> float:
        keystroke_time = self.base_keystroke_time * self.state.fatigue_multiplier

        current_word = self._get_current_word_context()
        if current_word:
            difficulty = get_word_difficulty(current_word)
            if difficulty == "common":
                keystroke_time *= SPEED_BOOST_COMMON_WORD
            elif difficulty == "complex":
                keystroke_time *= SPEED_PENALTY_COMPLEX_WORD

        if self.state.last_char_typed:
            if is_common_bigram(self.state.last_char_typed, char_to_type):
                keystroke_time *= SPEED_BOOST_BIGRAM
            else:
                dist = self.keyboard.get_distance(self.state.last_char_typed, char_to_type)
                if 0 < dist < CLOSE_KEY_THRESHOLD:
                    keystroke_time *= SPEED_BOOST_CLOSE_KEYS
                elif dist > FAR_KEY_THRESHOLD:
                    keystroke_time *= FAR_KEY_PENALTY

        if char_to_type == ' ':
            keystroke_time += np.random.normal(TIME_SPACE_PAUSE_MEAN, TIME_SPACE_PAUSE_STD)
        elif self.keyboard.is_composed_accent(char_to_type):
            keystroke_time += TIME_COMPOSED_ACCENT_PENALTY
        elif self.keyboard.is_direct_accent(char_to_type):
            keystroke_time += TIME_DIRECT_ACCENT_PENALTY
        elif char_to_type.isupper():
            keystroke_time += TIME_UPPERCASE_PENALTY

        # Apply floor to prevent unrealistic stacking of boosts
        keystroke_time = max(MIN_SPEED_MULTIPLIER * self.base_keystroke_time, keystroke_time)

        dt = np.random.normal(keystroke_time, TIME_KEYSTROKE_STD)
        return max(MIN_KEYSTROKE_TIME, dt)

    def step(self) -> tuple[float, str, str] | None:
        # Continue an in-progress word-level (arrow-key) correction, if any.
        if self.state.word_fix_pos is not None:
            return self._word_correction_step()

        # 1. Check for completion
        if self.state.current_text == self.target_text:
            return None

        # --- MONITORING & CORRECTION PHASE ---

        # Calculate divergence point
        first_error_pos = len(self.target_text)
        min_len = min(len(self.state.current_text), len(self.target_text))
        for i in range(min_len):
            if self.state.current_text[i] != self.target_text[i]:
                first_error_pos = i
                break

        # Also consider over-typing as an error
        if len(self.state.current_text) > len(self.target_text) and first_error_pos == len(self.target_text):
            first_error_pos = len(self.target_text)

        # Do we have an error?
        if first_error_pos < len(self.state.current_text):
            should_correct = False

            last_action = self.state.history[-1][1] if self.state.history else ""

            # Case 0: CONTINUED BACKSPACING (Critical)
            if "BACKSPACE" in last_action:
                should_correct = True

            # Case A: End of text (Always correct)
            elif self.state.mental_cursor_pos >= len(self.target_text):
                should_correct = True

            # Case B: End of Word / Context Check
            elif len(self.state.current_text) > 0:
                last_char = self.state.current_text[-1]
                distance = len(self.state.current_text) - first_error_pos

                # Check at word boundaries (Strict)
                if last_char in ' \n\t.,;!?:()[]{}<>"\'':
                    should_correct = True

                # Drift Check (Don't let errors linger)
                elif distance >= 2:
                    if np.random.random() < DRIFT_CORRECTION_PROB:
                        should_correct = True

                # Immediate reaction (1 char past error)
                elif distance == 1:
                    if np.random.random() < PROB_NOTICE_ERROR:
                        should_correct = True

            if should_correct:
                # Reaction time (only if we weren't already backspacing)
                if "BACKSPACE" not in last_action:
                    dt = np.random.normal(TIME_REACTION_MEAN, TIME_REACTION_STD)
                    self.state.total_time += max(MIN_REACTION_TIME, dt)

                # Deferred (word-level) correction: if correct characters were
                # typed past the error and it is a lone substitution, navigate
                # back to it with arrow keys and fix it in place.
                distance = len(self.state.current_text) - first_error_pos
                if ("BACKSPACE" not in last_action and distance >= 2
                        and self._is_clean_substitution(first_error_pos)
                        and np.random.random() < PROB_WORD_LEVEL_CORRECTION):
                    self.state.word_fix_pos = first_error_pos
                    self.state.word_fix_phase = "seek"
                    self.state.caret_pos = len(self.state.current_text)
                    return self._word_correction_step()

                # Immediate (character-level) correction: backspace from the end.
                dt = max(MIN_BACKSPACE_TIME, np.random.normal(TIME_BACKSPACE_MEAN, TIME_BACKSPACE_STD))
                self.state.total_time += dt
                self.state.current_text = self.state.current_text[:-1]

                event = (self.state.total_time, "BACKSPACE", self.state.current_text)
                self.state.history.append(event)

                # Sync mental cursor immediately
                self.state.mental_cursor_pos = len(self.state.current_text)
                return event

        # --- TYPING PHASE ---

        # Sync mental cursor if we backspaced (redundant safety)
        if self.state.mental_cursor_pos > len(self.state.current_text):
            self.state.mental_cursor_pos = len(self.state.current_text)

        if self.state.mental_cursor_pos >= len(self.target_text):
            return None

        char_intended = self.target_text[self.state.mental_cursor_pos]

        # If the character is not on our keyboard, type it literally (no error modeling)
        if not self.keyboard.has_key(char_intended) and char_intended != ' ':
            self.state.fatigue_multiplier = min(FATIGUE_CAP, self.state.fatigue_multiplier * FATIGUE_FACTOR)
            dt = self.base_keystroke_time * self.state.fatigue_multiplier
            dt = max(MIN_KEYSTROKE_TIME, np.random.normal(dt, TIME_KEYSTROKE_STD))
            self.state.total_time += dt
            self.state.current_text += char_intended
            self.state.last_char_typed = char_intended
            event = (self.state.total_time, f"TYPED '{char_intended}'", self.state.current_text)
            self.state.history.append(event)
            self.state.mental_cursor_pos += 1
            return event

        self.state.fatigue_multiplier = min(FATIGUE_CAP, self.state.fatigue_multiplier * FATIGUE_FACTOR)

        # Swap Error (Anticipation)
        # Example: "the" -> "hte". We type char_after first, then char_intended.
        if len(self.target_text) > self.state.mental_cursor_pos + 1:
            char_after = self.target_text[self.state.mental_cursor_pos + 1]
            if char_after != ' ' and char_after != char_intended:
                if np.random.random() < PROB_SWAP_ERROR:
                    # Type the anticipated character first
                    dt1 = self._calculate_keystroke_time(char_after)
                    self.state.total_time += dt1
                    self.state.current_text += char_after

                    # Then type the intended character (producing a real swap)
                    dt2 = self._calculate_keystroke_time(char_intended)
                    self.state.total_time += dt2
                    self.state.current_text += char_intended

                    self.state.last_char_typed = char_intended
                    event = (self.state.total_time, f"TYPED_SWAP '{char_after}{char_intended}'", self.state.current_text)
                    self.state.history.append(event)
                    self.state.mental_cursor_pos += 2
                    return event

        # Omission (OX): skip a letter, typing the next one in its place ("major" -> "maor")
        if char_intended.isalpha() and self.state.mental_cursor_pos + 1 < len(self.target_text):
            char_after = self.target_text[self.state.mental_cursor_pos + 1]
            if char_after != ' ' and np.random.random() < PROB_OMISSION:
                dt = self._calculate_keystroke_time(char_after)
                self.state.total_time += dt
                self.state.current_text += char_after
                self.state.last_char_typed = char_after
                event = (self.state.total_time, f"TYPED_OMIT '{char_after}'", self.state.current_text)
                self.state.history.append(event)
                self.state.mental_cursor_pos += 2  # both the skipped and placed char are consumed
                return event

        # Insertion (XO): an extra neighbouring key before the intended letter ("this" -> "thjis")
        if char_intended != ' ' and np.random.random() < PROB_INSERTION:
            extra = self.keyboard.get_random_neighbor(char_intended)
            dt = self._calculate_keystroke_time(extra)
            self.state.total_time += dt
            self.state.current_text += extra
            self.state.last_char_typed = extra
            event = (self.state.total_time, f"TYPED_INSERT '{extra}'", self.state.current_text)
            self.state.history.append(event)
            return event

        # Doubling (DOUB12): type a single letter twice ("operation" -> "opperation")
        if char_intended.isalpha() and np.random.random() < PROB_DOUBLING:
            dt1 = self._calculate_keystroke_time(char_intended)
            self.state.total_time += dt1
            self.state.current_text += char_intended
            dt2 = self._calculate_keystroke_time(char_intended)
            self.state.total_time += dt2
            self.state.current_text += char_intended
            self.state.last_char_typed = char_intended
            event = (self.state.total_time, f"TYPED_DOUBLE '{char_intended}{char_intended}'", self.state.current_text)
            self.state.history.append(event)
            self.state.mental_cursor_pos += 1  # only the first copy is the intended letter
            return event

        # Normal Typing (Success or Error)
        current_prob_error = PROB_ERROR
        word_diff = get_word_difficulty(self._get_current_word_context() or "")
        if word_diff == "complex":
            current_prob_error *= COMPLEX_WORD_ERROR_MULT
        elif word_diff == "common":
            current_prob_error *= COMMON_WORD_ERROR_MULT
        if self.keyboard.is_composed_accent(char_intended):
            current_prob_error *= COMPOSED_ACCENT_ERROR_MULT
        elif not char_intended.isalnum() and char_intended != ' ':
            current_prob_error *= PUNCTUATION_ERROR_MULT

        # Case errors (Shift mistakes): the correct letter with the wrong case.
        case_error_prob = 0.0
        if char_intended.isalpha() and char_intended.swapcase() != char_intended:
            if char_intended.isupper():
                # Forgot to press Shift ("The" -> "the").
                case_error_prob = PROB_MISSED_SHIFT
            else:
                # Shift held too long after an uppercase key ("The" -> "THe").
                prev = self.state.last_char_typed
                if prev is not None and prev.isalpha() and prev.isupper():
                    case_error_prob = PROB_SHIFT_HELD

        wrong_char = None
        if case_error_prob and np.random.random() < case_error_prob:
            wrong_char = char_intended.swapcase()
        elif np.random.random() < current_prob_error:
            wrong_char = self.keyboard.get_random_neighbor(char_intended)

        if wrong_char is not None:
            # Generate Error
            dt = self._calculate_keystroke_time(wrong_char)
            self.state.total_time += dt
            self.state.current_text += wrong_char
            self.state.last_char_typed = wrong_char
            event = (self.state.total_time, f"TYPED_ERROR '{wrong_char}'", self.state.current_text)
            self.state.history.append(event)
            self.state.mental_cursor_pos += 1
        else:
            # Success
            dt = self._calculate_keystroke_time(char_intended)
            self.state.total_time += dt
            self.state.current_text += char_intended
            self.state.last_char_typed = char_intended
            event = (self.state.total_time, f"TYPED '{char_intended}'", self.state.current_text)
            self.state.history.append(event)
            self.state.mental_cursor_pos += 1

        return event

    def _is_clean_substitution(self, err: int) -> bool:
        """True if the divergence is a single wrong character with the rest of
        the typed text still aligned to the target (fixable in place)."""
        ct, tt = self.state.current_text, self.target_text
        return len(ct) <= len(tt) and ct[err + 1:] == tt[err + 1:len(ct)]

    def _word_correction_step(self) -> tuple[float, str, str]:
        """Emit one keystroke of a word-level correction: arrow-left to the
        error, replace the wrong character, then arrow-right back to resume."""
        e = self.state.word_fix_pos
        ct = self.state.current_text

        if self.state.word_fix_phase == "seek":
            # Navigate left until the caret sits just past the wrong character.
            if self.state.caret_pos > e + 1:
                self.state.caret_pos -= 1
                self.state.total_time += max(MIN_ARROW_TIME, np.random.normal(TIME_ARROW_MEAN, TIME_ARROW_STD))
                event = (self.state.total_time, "ARROW_LEFT", ct)
            else:
                self.state.total_time += max(MIN_BACKSPACE_TIME, np.random.normal(TIME_BACKSPACE_MEAN, TIME_BACKSPACE_STD))
                self.state.current_text = ct[:e] + ct[e + 1:]
                self.state.caret_pos = e
                self.state.word_fix_phase = "type"
                event = (self.state.total_time, "BACKSPACE", self.state.current_text)
            self.state.history.append(event)
            return event

        if self.state.word_fix_phase == "type":
            correct = self.target_text[e]
            self.state.total_time += self._calculate_keystroke_time(correct)
            self.state.current_text = ct[:e] + correct + ct[e:]
            self.state.caret_pos = e + 1
            self.state.last_char_typed = correct
            self.state.word_fix_phase = "return"
            event = (self.state.total_time, f"TYPED '{correct}'", self.state.current_text)
            self.state.history.append(event)
            return event

        # phase == "return": navigate right back to the end, then resume typing.
        if self.state.caret_pos < len(ct):
            self.state.caret_pos += 1
            self.state.total_time += max(MIN_ARROW_TIME, np.random.normal(TIME_ARROW_MEAN, TIME_ARROW_STD))
            event = (self.state.total_time, "ARROW_RIGHT", ct)
            self.state.history.append(event)
            return event

        self.state.word_fix_pos = None
        self.state.word_fix_phase = "seek"
        self.state.mental_cursor_pos = len(ct)
        return self.step()

    def run(self) -> tuple[float, list[tuple[float, str, str]]]:
        steps = 0
        max_steps = len(self.target_text) * 10
        while self.step() is not None:
            steps += 1
            if steps > max_steps:
                break
        return self.state.total_time, self.state.history
