# Typing model configuration.
# User-facing settings live in config.json; the research-derived model constants
# stay here. See README for the config.json field specification.

import json
import os
import sys

SETTINGS_DEFAULTS = {
    "wpm": 60,
    "layout": "qwerty",
    "rhythm": "messaging",
    "base_error_rate": 0.03,
    "prob_notice_error": 0.4,
    "prob_word_level_correction": 0.7,
    "start_delay": 3.0,
    "hotkey": "ctrl+alt+t",
    "graph_chars": 120,
    "text": "",
}


def config_path():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "config.json")


def load_settings():
    settings = dict(SETTINGS_DEFAULTS)
    try:
        with open(config_path(), encoding="utf-8") as f:
            settings.update(json.load(f))
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings):
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


_settings = load_settings()

# --- user-facing (config.json) ---
DEFAULT_WPM = _settings["wpm"]
DEFAULT_LAYOUT = _settings["layout"]
DEFAULT_RHYTHM = _settings["rhythm"]
BASE_ERROR_RATE = _settings["base_error_rate"]
PROB_NOTICE_ERROR = _settings["prob_notice_error"]
PROB_WORD_LEVEL_CORRECTION = _settings["prob_word_level_correction"]
START_DELAY = _settings["start_delay"]
HOTKEY = _settings["hotkey"]

# Average speed spread and word length
WPM_STD = 10
AVG_WORD_LENGTH = 5

# Structural error rates follow Dhakal et al. (CHI 2018, 136M keystrokes):
# substitution (1.65%) > omission (0.8%) > insertion (0.67%); transposition rarest.
PROB_ERROR = BASE_ERROR_RATE * 1.00       # XY: substitution with a neighbouring key
PROB_OMISSION = BASE_ERROR_RATE * 0.48    # OX: a letter is skipped ("major" -> "maor")
PROB_INSERTION = BASE_ERROR_RATE * 0.25   # XO: an extra neighbouring key ("this" -> "thjis")
PROB_DOUBLING = BASE_ERROR_RATE * 0.15    # DOUB12: a letter typed twice ("operation" -> "opperation")
PROB_SWAP_ERROR = BASE_ERROR_RATE * 0.10  # SWAP: two adjacent letters interchanged ("the" -> "hte")

# Case errors (Shift mistakes on letters) — correct letter, wrong case.
PROB_MISSED_SHIFT = 0.02   # uppercase intended, typed lowercase ("The" -> "the")
PROB_SHIFT_HELD = 0.01     # Shift released late after an uppercase key ("The" -> "THe")

# Correction behaviour.
DRIFT_CORRECTION_PROB = 0.7  # Probability to notice error at distance >= 2

# Error multipliers by context. Letters and digits are low; punctuation and
# other peripheral / shifted keys are struck less accurately.
COMPLEX_WORD_ERROR_MULT = 1.5
COMMON_WORD_ERROR_MULT = 0.1
COMPOSED_ACCENT_ERROR_MULT = 2.0
PUNCTUATION_ERROR_MULT = 2.5

# Speed factors (multipliers on keystroke time, < 1.0 = faster). Bigram/hand
# spread follows Dhakal et al.: repetition < alternation < same-hand < awkward.
SPEED_BOOST_COMMON_WORD = 0.6
SPEED_PENALTY_COMPLEX_WORD = 1.3
SPEED_BOOST_REPETITION = 0.74   # same letter twice (fastest)
SPEED_BOOST_BIGRAM = 0.83       # common hand-alternating bigram
SPEED_BOOST_CLOSE_KEYS = 0.9    # adjacent same-hand keys

# Key distance thresholds
CLOSE_KEY_THRESHOLD = 2.0
FAR_KEY_THRESHOLD = 4.0
FAR_KEY_PENALTY = 1.15

# Minimum speed multiplier to prevent unrealistic stacking of boosts
MIN_SPEED_MULTIPLIER = 0.15

# Time (in seconds)
KEYSTROKE_LOG_SIGMA = 0.35  # log-normal spread → right-skewed IKI (scales with speed)
TIME_BACKSPACE_MEAN = 0.12
TIME_BACKSPACE_STD = 0.02
TIME_REACTION_MEAN = 0.35
TIME_REACTION_STD = 0.1
TIME_ARROW_MEAN = 0.09
TIME_ARROW_STD = 0.02

# Floor values for time samples
MIN_KEYSTROKE_TIME = 0.06  # ~human physiological lower bound
MIN_REACTION_TIME = 0.1
MIN_BACKSPACE_TIME = 0.03
MIN_ARROW_TIME = 0.03

# Specific penalties
TIME_DIRECT_ACCENT_PENALTY = 0.15
TIME_COMPOSED_ACCENT_PENALTY = 0.4
TIME_UPPERCASE_PENALTY = 0.2

# Fatigue
FATIGUE_FACTOR = 1.0005
FATIGUE_CAP = 1.5  # Maximum fatigue multiplier

# Typing rhythm. Pause durations follow a mixture of log-normal components tied
# to text location (Baaijen et al. 2012): mechanical within words, lexical
# between words, planning at sentence/paragraph boundaries. Each preset sets the
# boundary pause (median seconds, log sigma) and planning_fluency — how much a
# planning pause lowers the error rate of the burst it precedes (thinking-then-fluent).
RHYTHM_PRESETS = {
    "messaging": {
        "word_pause": (0.10, 0.4),
        "sentence_pause": (0.30, 0.5),
        "paragraph_pause": (0.5, 0.5),
        "planning_fluency": 0.9,
    },
    "writing": {
        "word_pause": (0.22, 0.5),
        "sentence_pause": (1.1, 0.6),
        "paragraph_pause": (2.4, 0.6),
        "planning_fluency": 0.5,
    },
    "coding": {
        "word_pause": (0.28, 0.6),
        "sentence_pause": (0.7, 0.6),
        "paragraph_pause": (1.6, 0.7),
        "planning_fluency": 0.6,
    },
}
FLUENCY_BURST_LEN = 6  # chars after a planning pause that stay cleaner
